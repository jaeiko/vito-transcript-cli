"""Tests for the production Typer command-line interface."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

import vito_transcript.cli as cli_module
from vito_transcript.cli import app
from vito_transcript.exceptions import (
    RTZRAuthenticationError,
    RTZROutputError,
    RTZRRequestError,
    RTZRTranscriptionFailedError,
)

runner = CliRunner()


def completed_payload() -> dict[str, object]:
    """Return a completed response suitable for every exporter."""
    return {
        "id": "job-id",
        "status": "completed",
        "results": {
            "utterances": [
                {
                    "start_at": 2036,
                    "duration": 5220,
                    "spk": 0,
                    "msg": "안녕하세요.",
                    "lang": "ko",
                }
            ]
        },
    }


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    """Create a temporary supported audio file without using local samples."""
    path = tmp_path / "sample.m4a"
    path.write_bytes(b"audio")
    return path


@pytest.fixture
def mocked_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MagicMock, MagicMock]:
    """Replace RTZRClient with a context-manager-compatible mock."""
    client = MagicMock()
    client.transcribe.return_value = completed_payload()
    context_manager = MagicMock()
    context_manager.__enter__.return_value = client
    client_class = MagicMock()
    client_class.from_env.return_value = context_manager
    monkeypatch.setattr(cli_module, "RTZRClient", client_class)
    return client, client_class


def invoke_success(
    audio_file: Path,
    output_dir: Path,
    *options: str,
) -> object:
    """Invoke the command with a temporary input and output directory."""
    return runner.invoke(
        app,
        [
            "transcribe",
            str(audio_file),
            "--output-dir",
            str(output_dir),
            *options,
        ],
    )


def test_root_help_lists_transcribe_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "transcribe" in result.stdout


def test_transcribe_help_lists_important_options() -> None:
    result = runner.invoke(app, ["transcribe", "--help"])

    assert result.exit_code == 0
    for option in (
        "--output-dir",
        "--format",
        "--model",
        "--language",
        "--domain",
        "--diarization",
        "--speaker-count",
        "--keyword",
        "--poll-interval",
        "--timeout",
    ):
        assert option in result.stdout


def test_missing_input_file_is_usage_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["transcribe", str(tmp_path / "missing.m4a")])

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_directory_input_is_usage_error(tmp_path: Path) -> None:
    directory = tmp_path / "directory.m4a"
    directory.mkdir()

    result = runner.invoke(app, ["transcribe", str(directory)])

    assert result.exit_code == 2
    assert "not a regular file" in result.output


def test_unsupported_extension_is_usage_error(tmp_path: Path) -> None:
    audio_file = tmp_path / "sample.ogg"
    audio_file.write_bytes(b"audio")

    result = runner.invoke(app, ["transcribe", str(audio_file)])

    assert result.exit_code == 2
    assert "Unsupported audio format" in result.output


def test_uppercase_supported_extension_is_accepted(
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
) -> None:
    audio_file = tmp_path / "INTERVIEW.M4A"
    audio_file.write_bytes(b"audio")

    result = invoke_success(
        audio_file,
        tmp_path / "outputs",
        "--format",
        "txt",
    )

    assert result.exit_code == 0
    assert (tmp_path / "outputs" / "INTERVIEW.txt").is_file()


def test_negative_speaker_count_is_usage_error(audio_file: Path) -> None:
    result = runner.invoke(
        app,
        ["transcribe", str(audio_file), "--diarization", "--speaker-count", "-1"],
    )

    assert result.exit_code == 2
    assert "speaker-count must be zero or greater" in result.output


def test_speaker_count_requires_diarization(audio_file: Path) -> None:
    result = runner.invoke(
        app,
        ["transcribe", str(audio_file), "--speaker-count", "2"],
    )

    assert result.exit_code == 2
    assert "speaker-count requires --diarization" in result.output


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("--poll-interval", "0", "poll-interval must be a positive number"),
        ("--timeout", "-1", "timeout must be a positive number"),
    ],
)
def test_non_positive_polling_option_is_usage_error(
    audio_file: Path,
    option: str,
    value: str,
    message: str,
) -> None:
    result = runner.invoke(app, ["transcribe", str(audio_file), option, value])

    assert result.exit_code == 2
    assert message in result.output


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--model", "unknown"),
        ("--domain", "MEETING"),
        ("--format", "xml"),
    ],
)
def test_enum_option_validation_is_usage_error(
    audio_file: Path,
    option: str,
    value: str,
) -> None:
    result = runner.invoke(app, ["transcribe", str(audio_file), option, value])

    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_sommers_rejects_unsupported_language(audio_file: Path) -> None:
    result = runner.invoke(
        app,
        ["transcribe", str(audio_file), "--model", "sommers", "--language", "en"],
    )

    assert result.exit_code == 2
    assert "sommers supports only language ko or ja" in result.output


def test_all_formats_are_written_with_input_stem_and_paths_printed(
    audio_file: Path,
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
) -> None:
    output_dir = tmp_path / "exports"

    result = invoke_success(audio_file, output_dir)

    assert result.exit_code == 0
    assert {path.name for path in output_dir.iterdir()} == {
        "sample.txt",
        "sample.md",
        "sample.srt",
        "sample.json",
    }
    assert "# Transcript: sample.m4a" in (output_dir / "sample.md").read_text(
        encoding="utf-8"
    )
    assert json.loads((output_dir / "sample.json").read_text(encoding="utf-8")) == (
        completed_payload()
    )
    for extension in ("txt", "md", "srt", "json"):
        assert f"- {output_dir / f'sample.{extension}'}" in result.stdout


@pytest.mark.parametrize("output_format", ["txt", "md", "srt", "json"])
def test_only_requested_format_is_written(
    output_format: str,
    audio_file: Path,
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
) -> None:
    output_dir = tmp_path / f"{output_format}-output"

    result = invoke_success(
        audio_file,
        output_dir,
        "--format",
        output_format,
    )

    assert result.exit_code == 0
    assert [path.name for path in output_dir.iterdir()] == [f"sample.{output_format}"]


def test_custom_options_build_expected_config_and_polling_arguments(
    audio_file: Path,
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
) -> None:
    client, client_class = mocked_client

    result = invoke_success(
        audio_file,
        tmp_path / "outputs",
        "--format",
        "json",
        "--model",
        "whisper",
        "--language",
        "en",
        "--domain",
        "CALL",
        "--diarization",
        "--speaker-count",
        "2",
        "--keyword",
        "리턴제로",
        "--keyword",
        "음성인식",
        "--poll-interval",
        "2.5",
        "--timeout",
        "30",
    )

    assert result.exit_code == 0
    client_class.from_env.assert_called_once_with()
    client.transcribe.assert_called_once_with(
        audio_file,
        {
            "model_name": "whisper",
            "language": "en",
            "domain": "CALL",
            "use_diarization": True,
            "diarization": {"spk_count": 2},
            "keywords": ["리턴제로", "음성인식"],
        },
        poll_interval=2.5,
        timeout=30.0,
    )


def test_default_options_build_expected_config(
    audio_file: Path,
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
) -> None:
    client, _ = mocked_client

    result = invoke_success(audio_file, tmp_path / "outputs", "--format", "json")

    assert result.exit_code == 0
    client.transcribe.assert_called_once_with(
        audio_file,
        {
            "model_name": "sommers",
            "language": "ko",
            "domain": "GENERAL",
            "use_diarization": False,
        },
        poll_interval=5.0,
        timeout=1800.0,
    )


@pytest.mark.parametrize(
    "error",
    [
        RTZRAuthenticationError("Authentication failed."),
        RTZRRequestError("Request failed."),
        RTZRTranscriptionFailedError("Transcription failed."),
        RTZROutputError("Output failed."),
    ],
)
def test_rtzr_errors_exit_with_code_one_and_leave_no_outputs(
    error: Exception,
    audio_file: Path,
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
) -> None:
    client, _ = mocked_client
    client.transcribe.side_effect = error
    output_dir = tmp_path / "failed-output"

    result = invoke_success(audio_file, output_dir)

    assert result.exit_code == 1
    assert f"Error: {error}" in result.output
    assert not output_dir.exists()


def test_error_output_does_not_expose_fake_credentials_or_token(
    audio_file: Path,
    tmp_path: Path,
    mocked_client: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client_id = "fake-client-id"
    fake_secret = "fake-client-secret"
    fake_token = "fake-access-token"
    monkeypatch.setenv("RTZR_CLIENT_ID", fake_client_id)
    monkeypatch.setenv("RTZR_CLIENT_SECRET", fake_secret)
    client, _ = mocked_client
    client.transcribe.side_effect = RTZRRequestError("Safe request failure.")

    result = invoke_success(audio_file, tmp_path / "outputs")

    assert result.exit_code == 1
    assert fake_client_id not in result.output
    assert fake_secret not in result.output
    assert fake_token not in result.output
    assert "Safe request failure" in result.output
