"""HTTP client for the RTZR file transcription API."""

import json
import math
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Self

import requests
from dotenv import load_dotenv

from vito_transcript.exceptions import (
    RTZRAuthenticationError,
    RTZRConfigurationError,
    RTZRRequestError,
    RTZRResponseError,
    RTZRTimeoutError,
    RTZRTranscriptionFailedError,
)

AUTH_URL = "https://openapi.vito.ai/v1/authenticate"
TRANSCRIBE_URL = "https://openapi.vito.ai/v1/transcribe"
HTTP_TIMEOUT = (5, 60)
TERMINAL_STATUSES = {"completed", "failed"}
KNOWN_STATUSES = {"transcribing", *TERMINAL_STATUSES}


class RTZRClient:
    """Client for authenticating and transcribing files with RTZR."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        session: requests.Session | None = None,
    ) -> None:
        if not isinstance(client_id, str) or not client_id.strip():
            raise RTZRConfigurationError("RTZR client ID must be configured.")
        if not isinstance(client_secret, str) or not client_secret.strip():
            raise RTZRConfigurationError("RTZR client secret must be configured.")

        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._owns_session = session is None
        self._session = session if session is not None else requests.Session()

    @classmethod
    def from_env(cls, *, session: requests.Session | None = None) -> Self:
        """Create a client from RTZR credentials in the local environment."""
        load_dotenv()
        client_id = os.getenv("RTZR_CLIENT_ID")
        client_secret = os.getenv("RTZR_CLIENT_SECRET")
        if (
            not client_id
            or not client_id.strip()
            or not client_secret
            or not client_secret.strip()
        ):
            raise RTZRConfigurationError(
                "RTZR_CLIENT_ID and RTZR_CLIENT_SECRET must be configured."
            )
        return cls(client_id, client_secret, session=session)

    def __enter__(self) -> Self:
        """Return this client for use in a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Release resources owned by this client."""
        self.close()

    def close(self) -> None:
        """Close an internal session; injected sessions remain caller-owned."""
        self._access_token = None
        if self._owns_session:
            self._session.close()

    def authenticate(self) -> str:
        """Authenticate with RTZR and retain the access token in memory."""
        try:
            response = self._session.post(
                AUTH_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            raise RTZRAuthenticationError(
                "The RTZR authentication request could not be completed."
            ) from None

        payload = self._response_json(
            response,
            operation="Authentication",
            http_error=RTZRAuthenticationError,
        )
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise RTZRAuthenticationError(
                "The authentication response did not contain an access token."
            )

        self._access_token = access_token
        return access_token

    def submit_transcription(
        self,
        audio_path: Path,
        config: Mapping[str, Any] | None = None,
    ) -> str:
        """Upload an audio file and return its RTZR transcription job ID."""
        if not audio_path.is_file():
            raise RTZRConfigurationError(
                f"Audio path is not an existing regular file: {audio_path}"
            )

        try:
            serialized_config = json.dumps(
                dict(config) if config is not None else {},
                ensure_ascii=False,
            )
        except (TypeError, ValueError):
            raise RTZRConfigurationError(
                "Transcription config is not JSON serializable."
            ) from None

        headers = self._authenticated_headers()
        try:
            with audio_path.open("rb") as audio_file:
                response = self._session.post(
                    TRANSCRIBE_URL,
                    data={"config": serialized_config},
                    files={
                        "file": (
                            audio_path.name,
                            audio_file,
                            "application/octet-stream",
                        )
                    },
                    headers=headers,
                    timeout=HTTP_TIMEOUT,
                )
        except OSError:
            raise RTZRConfigurationError(
                f"Audio file could not be opened: {audio_path}"
            ) from None
        except requests.RequestException:
            raise RTZRRequestError(
                "The transcription request could not be completed."
            ) from None

        payload = self._response_json(
            response,
            operation="Transcription request",
            http_error=RTZRRequestError,
        )
        transcribe_id = payload.get("id")
        if not isinstance(transcribe_id, str) or not transcribe_id.strip():
            raise RTZRResponseError(
                "The transcription response did not contain a job ID."
            )
        return transcribe_id

    def get_transcription(self, transcribe_id: str) -> dict[str, Any]:
        """Fetch the current payload for an RTZR transcription job."""
        if not isinstance(transcribe_id, str) or not transcribe_id.strip():
            raise RTZRConfigurationError("A transcription job ID is required.")

        headers = self._authenticated_headers()
        try:
            response = self._session.get(
                f"{TRANSCRIBE_URL}/{transcribe_id}",
                headers=headers,
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            raise RTZRRequestError(
                "The transcription status request could not be completed."
            ) from None

        return self._response_json(
            response,
            operation="Transcription status request",
            http_error=RTZRRequestError,
        )

    def wait_for_completion(
        self,
        transcribe_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        """Poll an RTZR transcription job until it completes or fails."""
        self._validate_positive_number(poll_interval, "poll_interval")
        self._validate_positive_number(timeout, "timeout")
        deadline = time.monotonic() + timeout

        while True:
            if time.monotonic() >= deadline:
                raise RTZRTimeoutError(
                    "The transcription did not complete before the timeout."
                )

            payload = self.get_transcription(transcribe_id)
            status = payload.get("status")
            if status not in KNOWN_STATUSES:
                raise RTZRResponseError(
                    "The transcription response contained an unknown or missing status."
                )
            if status == "completed":
                return payload
            if status == "failed":
                raise RTZRTranscriptionFailedError(
                    self._transcription_failure_message(payload)
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RTZRTimeoutError(
                    "The transcription did not complete before the timeout."
                )
            time.sleep(min(poll_interval, remaining))

    def transcribe(
        self,
        audio_path: Path,
        config: Mapping[str, Any] | None = None,
        *,
        poll_interval: float = 5.0,
        timeout: float = 1800.0,
    ) -> dict[str, Any]:
        """Submit an audio file and wait for its completed RTZR payload."""
        transcribe_id = self.submit_transcription(audio_path, config)
        return self.wait_for_completion(
            transcribe_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )

    def _authenticated_headers(self) -> dict[str, str]:
        access_token = self._access_token or self.authenticate()
        return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    def _response_json(
        response: requests.Response,
        *,
        operation: str,
        http_error: type[RTZRRequestError],
    ) -> dict[str, Any]:
        try:
            if not response.ok:
                raise http_error(f"{operation} returned HTTP {response.status_code}.")
            try:
                payload = response.json()
            except ValueError:
                raise RTZRResponseError(f"{operation} returned invalid JSON.") from None
            if not isinstance(payload, dict):
                raise RTZRResponseError(
                    f"{operation} returned an unexpected JSON value."
                )
            return payload
        finally:
            response.close()

    @staticmethod
    def _validate_positive_number(value: float, name: str) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise RTZRConfigurationError(f"{name} must be a positive number.")

    def _transcription_failure_message(self, payload: Mapping[str, Any]) -> str:
        error = payload.get("error")
        if not isinstance(error, Mapping):
            return "RTZR reported that the transcription failed."

        details = []
        code = self._safe_error_detail(error.get("code"))
        message = self._safe_error_detail(error.get("message"))
        if code:
            details.append(f"code={code}")
        if message:
            details.append(f"message={message}")
        if not details:
            return "RTZR reported that the transcription failed."
        return f"RTZR reported that the transcription failed ({'; '.join(details)})."

    def _safe_error_detail(self, value: Any) -> str | None:
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return None

        detail = str(value).replace("\r", " ").replace("\n", " ")
        for sensitive_value in (
            self._client_id,
            self._client_secret,
            self._access_token,
        ):
            if sensitive_value:
                detail = detail.replace(sensitive_value, "[REDACTED]")
        return detail[:500] or None
