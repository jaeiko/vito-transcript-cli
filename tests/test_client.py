"""Unit tests for the RTZR file transcription client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
import requests

import vito_transcript.client as client_module
from vito_transcript.client import AUTH_URL, HTTP_TIMEOUT, TRANSCRIBE_URL, RTZRClient
from vito_transcript.exceptions import (
    RTZRAuthenticationError,
    RTZRConfigurationError,
    RTZRResponseError,
    RTZRTimeoutError,
    RTZRTranscriptionFailedError,
)


def make_session() -> MagicMock:
    """Return a requests.Session-compatible mock."""
    return MagicMock(spec=requests.Session)


def make_response(
    payload: object | None = None,
    *,
    status_code: int = 200,
    json_error: ValueError | None = None,
) -> MagicMock:
    """Return a requests.Response-compatible mock."""
    response = MagicMock(spec=requests.Response)
    response.ok = 200 <= status_code < 400
    response.status_code = status_code
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = payload
    return response


def test_from_env_with_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "load_dotenv", Mock())
    monkeypatch.delenv("RTZR_CLIENT_ID", raising=False)
    monkeypatch.delenv("RTZR_CLIENT_SECRET", raising=False)

    with pytest.raises(RTZRConfigurationError):
        RTZRClient.from_env(session=make_session())


def test_successful_authentication() -> None:
    session = make_session()
    response = make_response({"access_token": "access-token"})
    session.post.return_value = response
    client = RTZRClient("client-id", "client-secret", session=session)

    assert client.authenticate() == "access-token"

    session.post.assert_called_once_with(
        AUTH_URL,
        data={"client_id": "client-id", "client_secret": "client-secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=HTTP_TIMEOUT,
    )
    response.close.assert_called_once_with()


def test_authentication_http_error() -> None:
    session = make_session()
    response = make_response(status_code=401)
    session.post.return_value = response
    client = RTZRClient("client-id", "client-secret", session=session)

    with pytest.raises(RTZRAuthenticationError, match="HTTP 401"):
        client.authenticate()

    response.close.assert_called_once_with()


def test_invalid_authentication_json() -> None:
    session = make_session()
    session.post.return_value = make_response(json_error=ValueError("invalid"))
    client = RTZRClient("client-id", "client-secret", session=session)

    with pytest.raises(RTZRResponseError, match="invalid JSON"):
        client.authenticate()


def test_authentication_response_requires_access_token() -> None:
    session = make_session()
    session.post.return_value = make_response({})
    client = RTZRClient("client-id", "client-secret", session=session)

    with pytest.raises(RTZRAuthenticationError, match="access token"):
        client.authenticate()


def test_successful_transcription_submission(tmp_path: Path) -> None:
    audio_path = tmp_path / "korean.m4a"
    audio_path.write_bytes(b"audio")
    session = make_session()
    session.post.side_effect = [
        make_response({"access_token": "access-token"}),
        make_response({"id": "job-id"}),
    ]
    client = RTZRClient("client-id", "client-secret", session=session)

    transcribe_id = client.submit_transcription(
        audio_path,
        {"language": "ko", "note": "한국어"},
    )

    assert transcribe_id == "job-id"
    authentication_call, submission_call = session.post.call_args_list
    assert "Authorization" not in authentication_call.kwargs["headers"]
    assert submission_call.args == (TRANSCRIBE_URL,)
    assert submission_call.kwargs["headers"] == {"Authorization": "Bearer access-token"}
    assert submission_call.kwargs["timeout"] == HTTP_TIMEOUT
    serialized_config = submission_call.kwargs["data"]["config"]
    assert json.loads(serialized_config) == {"language": "ko", "note": "한국어"}
    assert "한국어" in serialized_config
    uploaded_file = submission_call.kwargs["files"]["file"][1]
    assert uploaded_file.closed


def test_submission_rejects_missing_audio_file(tmp_path: Path) -> None:
    session = make_session()
    client = RTZRClient("client-id", "client-secret", session=session)

    with pytest.raises(RTZRConfigurationError, match="regular file"):
        client.submit_transcription(tmp_path / "missing.m4a")

    session.post.assert_not_called()


def test_submission_response_requires_job_id(tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.m4a"
    audio_path.write_bytes(b"audio")
    session = make_session()
    session.post.side_effect = [
        make_response({"access_token": "access-token"}),
        make_response({}),
    ]
    client = RTZRClient("client-id", "client-secret", session=session)

    with pytest.raises(RTZRResponseError, match="job ID"):
        client.submit_transcription(audio_path)

    submission_call = session.post.call_args_list[1]
    assert json.loads(submission_call.kwargs["data"]["config"]) == {}


def test_get_transcription_authenticates_and_sends_bearer_token() -> None:
    session = make_session()
    session.post.return_value = make_response({"access_token": "access-token"})
    result_response = make_response({"id": "job-id", "status": "transcribing"})
    session.get.return_value = result_response
    client = RTZRClient("client-id", "client-secret", session=session)

    payload = client.get_transcription("job-id")

    assert payload["status"] == "transcribing"
    session.get.assert_called_once_with(
        f"{TRANSCRIBE_URL}/job-id",
        headers={"Authorization": "Bearer access-token"},
        timeout=HTTP_TIMEOUT,
    )
    result_response.close.assert_called_once_with()


def test_wait_for_completion_polls_then_returns_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RTZRClient("client-id", "client-secret", session=make_session())
    get_transcription = Mock(
        side_effect=[
            {"id": "job-id", "status": "transcribing"},
            {"id": "job-id", "status": "completed", "results": {}},
        ]
    )
    sleep = Mock()
    monkeypatch.setattr(client, "get_transcription", get_transcription)
    monkeypatch.setattr(
        client_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.0, 1.0, 6.0]),
    )
    monkeypatch.setattr(client_module.time, "sleep", sleep)

    payload = client.wait_for_completion("job-id", timeout=30.0)

    assert payload["status"] == "completed"
    assert get_transcription.call_count == 2
    sleep.assert_called_once_with(5.0)


def test_wait_for_completion_raises_for_failed_transcription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RTZRClient("client-id", "client-secret", session=make_session())
    monkeypatch.setattr(
        client,
        "get_transcription",
        Mock(
            return_value={
                "status": "failed",
                "error": {"code": "INVALID_AUDIO", "message": "Unreadable audio"},
            }
        ),
    )
    monkeypatch.setattr(
        client_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.0]),
    )
    monkeypatch.setattr(client_module.time, "sleep", Mock())

    with pytest.raises(RTZRTranscriptionFailedError) as exc_info:
        client.wait_for_completion("job-id")

    assert "code=INVALID_AUDIO" in str(exc_info.value)
    assert "message=Unreadable audio" in str(exc_info.value)


def test_wait_for_completion_rejects_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RTZRClient("client-id", "client-secret", session=make_session())
    monkeypatch.setattr(
        client,
        "get_transcription",
        Mock(return_value={"status": "queued"}),
    )
    monkeypatch.setattr(
        client_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.0]),
    )

    with pytest.raises(RTZRResponseError, match="unknown or missing status"):
        client.wait_for_completion("job-id")


def test_wait_for_completion_uses_overall_monotonic_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RTZRClient("client-id", "client-secret", session=make_session())
    get_transcription = Mock(return_value={"status": "transcribing"})
    sleep = Mock()
    monkeypatch.setattr(client, "get_transcription", get_transcription)
    monkeypatch.setattr(
        client_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.0, 0.5, 1.0]),
    )
    monkeypatch.setattr(client_module.time, "sleep", sleep)

    with pytest.raises(RTZRTimeoutError):
        client.wait_for_completion("job-id", poll_interval=5.0, timeout=1.0)

    get_transcription.assert_called_once_with("job-id")
    sleep.assert_called_once_with(0.5)


@pytest.mark.parametrize(
    ("keyword_arguments", "name"),
    [
        ({"poll_interval": 0.0}, "poll_interval"),
        ({"timeout": float("inf")}, "timeout"),
    ],
)
def test_wait_for_completion_requires_positive_finite_numbers(
    keyword_arguments: dict[str, float],
    name: str,
) -> None:
    client = RTZRClient("client-id", "client-secret", session=make_session())

    with pytest.raises(RTZRConfigurationError, match=name):
        client.wait_for_completion("job-id", **keyword_arguments)


def test_transcribe_orchestrates_complete_mocked_http_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_path = tmp_path / "sample.m4a"
    audio_path.write_bytes(b"audio")
    session = make_session()
    session.post.side_effect = [
        make_response({"access_token": "access-token"}),
        make_response({"id": "job-id"}),
    ]
    completed_payload = {
        "id": "job-id",
        "status": "completed",
        "results": {"utterances": []},
    }
    session.get.return_value = make_response(completed_payload)
    monkeypatch.setattr(
        client_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.0]),
    )
    monkeypatch.setattr(client_module.time, "sleep", Mock())
    client = RTZRClient("client-id", "client-secret", session=session)

    result = client.transcribe(audio_path, {"language": "ko"})

    assert result == completed_payload
    assert session.post.call_count == 2
    session.get.assert_called_once_with(
        f"{TRANSCRIBE_URL}/job-id",
        headers={"Authorization": "Bearer access-token"},
        timeout=HTTP_TIMEOUT,
    )


def test_failure_exception_redacts_credentials_and_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_id = "sensitive-client-id"
    client_secret = "sensitive-client-secret"
    access_token = "sensitive-access-token"
    session = make_session()
    session.post.return_value = make_response({"access_token": access_token})
    client = RTZRClient(client_id, client_secret, session=session)
    client.authenticate()
    monkeypatch.setattr(
        client,
        "get_transcription",
        Mock(
            return_value={
                "status": "failed",
                "error": {
                    "code": client_id,
                    "message": f"{client_secret} {access_token}",
                },
            }
        ),
    )
    monkeypatch.setattr(
        client_module.time,
        "monotonic",
        Mock(side_effect=[0.0, 0.0]),
    )

    with pytest.raises(RTZRTranscriptionFailedError) as exc_info:
        client.wait_for_completion("job-id")

    exception_message = str(exc_info.value)
    assert client_id not in exception_message
    assert client_secret not in exception_message
    assert access_token not in exception_message
    assert "[REDACTED]" in exception_message


def test_context_manager_does_not_close_injected_session() -> None:
    session = make_session()

    with RTZRClient("client-id", "client-secret", session=session):
        pass

    session.close.assert_not_called()


def test_context_manager_closes_internally_created_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = make_session()
    monkeypatch.setattr(client_module.requests, "Session", Mock(return_value=session))

    with RTZRClient("client-id", "client-secret"):
        pass

    session.close.assert_called_once_with()
