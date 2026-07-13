"""Exercise the RTZR file transcription flow with a local audio file."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

AUTH_URL = "https://openapi.vito.ai/v1/authenticate"
TRANSCRIBE_URL = "https://openapi.vito.ai/v1/transcribe"
DEFAULT_AUDIO_PATH = Path("samples/sample.m4a")
OUTPUT_PATH = Path("outputs/transcription_result.json")
TRANSCRIPTION_CONFIG = {"language": "ko"}

CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 60
HTTP_TIMEOUT = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
POLL_INTERVAL_SECONDS = 5
OVERALL_TIMEOUT_SECONDS = 10 * 60


class IntegrationCheckError(Exception):
    """A safe-to-display integration check failure."""


def response_json(response: requests.Response, operation: str) -> dict[str, Any]:
    """Validate an HTTP response and return its JSON object."""
    if not response.ok:
        raise IntegrationCheckError(
            f"{operation} returned HTTP {response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise IntegrationCheckError(
            f"{operation} returned an invalid JSON response."
        ) from exc

    if not isinstance(payload, dict):
        raise IntegrationCheckError(
            f"{operation} returned an unexpected JSON response."
        )
    return payload


def authenticate(session: requests.Session, client_id: str, client_secret: str) -> str:
    """Authenticate and return the access token without displaying it."""
    try:
        with session.post(
            AUTH_URL,
            data={"client_id": client_id, "client_secret": client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=HTTP_TIMEOUT,
        ) as response:
            payload = response_json(response, "Authentication")
    except requests.Timeout as exc:
        raise IntegrationCheckError("Authentication request timed out.") from exc
    except requests.RequestException as exc:
        raise IntegrationCheckError(
            "Authentication request could not be sent."
        ) from exc

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise IntegrationCheckError(
            "Authentication response did not contain an access token."
        )
    return access_token


def create_transcription_job(session: requests.Session, audio_path: Path) -> str:
    """Upload an audio file and return the transcription job ID."""
    try:
        with audio_path.open("rb") as audio_file:
            with session.post(
                TRANSCRIBE_URL,
                data={
                    "config": json.dumps(
                        TRANSCRIPTION_CONFIG,
                        ensure_ascii=False,
                    )
                },
                files={
                    "file": (
                        audio_path.name,
                        audio_file,
                        "application/octet-stream",
                    )
                },
                timeout=HTTP_TIMEOUT,
            ) as response:
                payload = response_json(response, "Transcription request")
    except OSError as exc:
        raise IntegrationCheckError(f"Could not read audio file: {audio_path}") from exc
    except requests.Timeout as exc:
        raise IntegrationCheckError("Transcription request timed out.") from exc
    except requests.RequestException as exc:
        raise IntegrationCheckError("Transcription request could not be sent.") from exc

    transcribe_id = payload.get("id")
    if not isinstance(transcribe_id, str) or not transcribe_id:
        raise IntegrationCheckError("Transcription response did not contain a job ID.")
    return transcribe_id


def poll_transcription(session: requests.Session, transcribe_id: str) -> dict[str, Any]:
    """Poll until the transcription completes or reaches a terminal failure."""
    deadline = time.monotonic() + OVERALL_TIMEOUT_SECONDS
    result_url = f"{TRANSCRIBE_URL}/{transcribe_id}"

    while True:
        if time.monotonic() >= deadline:
            raise IntegrationCheckError(
                "The transcription exceeded the 10-minute overall timeout."
            )

        try:
            with session.get(result_url, timeout=HTTP_TIMEOUT) as response:
                payload = response_json(response, "Transcription status request")
        except requests.Timeout as exc:
            raise IntegrationCheckError(
                "Transcription status request timed out."
            ) from exc
        except requests.RequestException as exc:
            raise IntegrationCheckError(
                "Transcription status request could not be sent."
            ) from exc

        status = payload.get("status")
        if status not in {"transcribing", "completed", "failed"}:
            raise IntegrationCheckError(
                "Transcription status response contained an unexpected status."
            )

        print(f"Current status: {status}")
        if status == "completed":
            return payload
        if status == "failed":
            raise IntegrationCheckError("RTZR reported a failed transcription status.")

        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise IntegrationCheckError(
                "The transcription exceeded the 10-minute overall timeout."
            )
        time.sleep(min(POLL_INTERVAL_SECONDS, remaining_seconds))


def save_result(payload: dict[str, Any]) -> None:
    """Save the raw completed response as UTF-8 JSON."""
    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
            json.dump(payload, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
    except OSError as exc:
        raise IntegrationCheckError(
            f"Could not save transcription result to {OUTPUT_PATH}."
        ) from exc


def run(audio_path: Path) -> None:
    """Run authentication, submission, polling, and result persistence."""
    if not audio_path.is_file():
        raise IntegrationCheckError(f"Audio file does not exist: {audio_path}")

    load_dotenv()
    client_id = os.getenv("RTZR_CLIENT_ID")
    client_secret = os.getenv("RTZR_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise IntegrationCheckError(
            "RTZR_CLIENT_ID and RTZR_CLIENT_SECRET must be set."
        )

    with requests.Session() as session:
        access_token = authenticate(session, client_id, client_secret)
        print("Authentication succeeded.")

        session.headers.update({"Authorization": f"Bearer {access_token}"})
        transcribe_id = create_transcription_job(session, audio_path)
        print(f"Transcription job created: {transcribe_id}")

        result = poll_transcription(session, transcribe_id)

    save_result(result)
    print("Transcription completed.")


def main() -> int:
    """Select an input file, run the check, and return a process exit status."""
    arguments = sys.argv[1:]
    if len(arguments) > 1:
        print("Transcription failed.")
        print("Error: Provide at most one audio file path.")
        return 2

    audio_path = Path(arguments[0]) if arguments else DEFAULT_AUDIO_PATH

    try:
        run(audio_path)
    except IntegrationCheckError as exc:
        print("Transcription failed.")
        print(f"Error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
