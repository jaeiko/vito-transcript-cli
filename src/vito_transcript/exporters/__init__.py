"""Shared timestamp and file-writing utilities for transcript exporters."""

from pathlib import Path

from vito_transcript.exceptions import RTZROutputError


def format_markdown_timestamp(milliseconds: int) -> str:
    """Format non-negative milliseconds as ``HH:MM:SS.mmm``."""
    return _format_timestamp(milliseconds, millisecond_separator=".")


def format_srt_timestamp(milliseconds: int) -> str:
    """Format non-negative milliseconds as ``HH:MM:SS,mmm``."""
    return _format_timestamp(milliseconds, millisecond_separator=",")


def write_text_file(path: Path, content: str) -> Path:
    """Write UTF-8 text to a path, creating parent directories as needed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as output_file:
            output_file.write(content)
    except OSError:
        raise RTZROutputError(f"Could not write output file: {path}") from None
    return path


def _format_timestamp(milliseconds: int, *, millisecond_separator: str) -> str:
    if isinstance(milliseconds, bool) or not isinstance(milliseconds, int):
        raise TypeError("milliseconds must be an integer")
    if milliseconds < 0:
        raise ValueError("milliseconds must be non-negative")

    total_seconds, milliseconds_part = divmod(milliseconds, 1_000)
    total_minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(total_minutes, 60)
    return (
        f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        f"{millisecond_separator}{milliseconds_part:03d}"
    )


# Renderer modules reuse the timestamp helpers defined above.
from vito_transcript.exporters.json_exporter import render_json  # noqa: E402
from vito_transcript.exporters.markdown_exporter import render_markdown  # noqa: E402
from vito_transcript.exporters.srt_exporter import render_srt  # noqa: E402
from vito_transcript.exporters.text_exporter import render_text  # noqa: E402

__all__ = [
    "format_markdown_timestamp",
    "format_srt_timestamp",
    "render_json",
    "render_markdown",
    "render_srt",
    "render_text",
    "write_text_file",
]
