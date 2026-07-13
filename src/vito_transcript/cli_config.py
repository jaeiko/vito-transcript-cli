"""Deterministic validation and configuration helpers for the CLI."""

import math
from enum import StrEnum
from pathlib import Path
from typing import Any

SUPPORTED_AUDIO_EXTENSIONS = frozenset(
    {".mp4", ".m4a", ".mp3", ".amr", ".flac", ".wav"}
)


class OutputFormat(StrEnum):
    """Transcript output formats supported by the CLI."""

    TXT = "txt"
    MARKDOWN = "md"
    SRT = "srt"
    JSON = "json"
    ALL = "all"


class Model(StrEnum):
    """RTZR transcription models exposed by the CLI."""

    SOMMERS = "sommers"
    WHISPER = "whisper"


class Domain(StrEnum):
    """RTZR transcription domains exposed by the CLI."""

    GENERAL = "GENERAL"
    CALL = "CALL"


def validate_audio_file(audio_file: Path) -> None:
    """Validate an audio path without opening or reading it."""
    if not audio_file.exists():
        raise ValueError(f"Audio file does not exist: {audio_file}")
    if not audio_file.is_file():
        raise ValueError(f"Audio path is not a regular file: {audio_file}")
    if audio_file.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ValueError(
            f"Unsupported audio format '{audio_file.suffix}'. Supported: {supported}"
        )


def build_rtzr_config(
    *,
    model: Model,
    language: str,
    domain: Domain,
    diarization: bool,
    speaker_count: int | None,
    keywords: list[str] | None,
) -> dict[str, Any]:
    """Build a validated RTZR configuration from CLI options."""
    if not language.strip():
        raise ValueError("language must not be empty")
    if model is Model.SOMMERS and language not in {"ko", "ja"}:
        raise ValueError("model sommers supports only language ko or ja")
    if speaker_count is not None and speaker_count < 0:
        raise ValueError("speaker-count must be zero or greater")
    if speaker_count is not None and not diarization:
        raise ValueError("speaker-count requires --diarization")

    config: dict[str, Any] = {
        "model_name": model.value,
        "language": language,
        "domain": domain.value,
        "use_diarization": diarization,
    }
    if diarization and speaker_count is not None:
        config["diarization"] = {"spk_count": speaker_count}
    if keywords:
        config["keywords"] = list(keywords)
    return config


def validate_polling_options(poll_interval: float, timeout: float) -> None:
    """Validate finite positive polling values."""
    if not math.isfinite(poll_interval) or poll_interval <= 0:
        raise ValueError("poll-interval must be a positive number")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive number")


def selected_formats(output_format: OutputFormat) -> tuple[OutputFormat, ...]:
    """Expand the all-formats selection in deterministic output order."""
    if output_format is OutputFormat.ALL:
        return (
            OutputFormat.TXT,
            OutputFormat.MARKDOWN,
            OutputFormat.SRT,
            OutputFormat.JSON,
        )
    return (output_format,)
