"""Tests for transcript timestamp, rendering, and file-output helpers."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from vito_transcript.exceptions import RTZROutputError
from vito_transcript.exporters import (
    format_markdown_timestamp,
    format_srt_timestamp,
    render_json,
    render_markdown,
    render_srt,
    render_text,
    write_text_file,
)
from vito_transcript.models import Utterance


def test_public_api_exports_all_renderers_and_file_writer() -> None:
    assert callable(render_json)
    assert callable(render_markdown)
    assert callable(render_srt)
    assert callable(render_text)
    assert callable(write_text_file)


@pytest.mark.parametrize(
    ("milliseconds", "markdown", "srt"),
    [
        (0, "00:00:00.000", "00:00:00,000"),
        (7, "00:00:00.007", "00:00:00,007"),
        (2036, "00:00:02.036", "00:00:02,036"),
        (60_000, "00:01:00.000", "00:01:00,000"),
        (3_600_000, "01:00:00.000", "01:00:00,000"),
        (3_661_007, "01:01:01.007", "01:01:01,007"),
        (90_061_007, "25:01:01.007", "25:01:01,007"),
    ],
)
def test_timestamp_formatting(
    milliseconds: int,
    markdown: str,
    srt: str,
) -> None:
    assert format_markdown_timestamp(milliseconds) == markdown
    assert format_srt_timestamp(milliseconds) == srt


@pytest.mark.parametrize("formatter", [format_markdown_timestamp, format_srt_timestamp])
def test_timestamp_rejects_negative_value(formatter: Callable[[int], str]) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        formatter(-1)


@pytest.mark.parametrize("formatter", [format_markdown_timestamp, format_srt_timestamp])
def test_timestamp_rejects_boolean(formatter: Callable[[int], str]) -> None:
    with pytest.raises(TypeError, match="integer"):
        formatter(True)


def test_render_text_with_multiple_utterances() -> None:
    utterances = [
        Utterance(0, 1000, "첫 번째 문장입니다."),
        Utterance(1000, 1000, "두 번째 문장입니다."),
    ]

    assert render_text(utterances) == "첫 번째 문장입니다.\n두 번째 문장입니다.\n"


def test_render_text_empty_input_and_trailing_newline() -> None:
    assert render_text([]) == ""
    assert render_text([Utterance(0, 0, "문장\n")]) == "문장\n"


def test_render_markdown_with_title_speakers_and_timestamps() -> None:
    utterances = [
        Utterance(2036, 5220, "안녕하세요.", speaker=0),
        Utterance(7996, 5120, "두 번째 발화입니다."),
    ]

    rendered = render_markdown(utterances, title="Transcript: sample.m4a")

    assert rendered == (
        "# Transcript: sample.m4a\n\n"
        "**[00:00:02.036] Speaker 1**\n\n"
        "안녕하세요.\n\n"
        "**[00:00:07.996] Speaker Unknown**\n\n"
        "두 번째 발화입니다.\n"
    )


def test_render_markdown_without_title_or_excess_blank_lines() -> None:
    rendered = render_markdown([Utterance(0, 1, "메시지", speaker=1)])

    assert rendered == "**[00:00:00.000] Speaker 2**\n\n메시지\n"
    assert render_markdown([]) == ""


def test_render_srt_sequence_timing_speakers_and_multiline_message() -> None:
    utterances = [
        Utterance(2036, 5220, "안녕하세요.\n반갑습니다.", speaker=0),
        Utterance(3_600_000, 1007, "화자 정보 없음"),
    ]

    rendered = render_srt(utterances)

    assert rendered == (
        "1\n"
        "00:00:02,036 --> 00:00:07,256\n"
        "[Speaker 1] 안녕하세요.\n"
        "반갑습니다.\n\n"
        "2\n"
        "01:00:00,000 --> 01:00:01,007\n"
        "화자 정보 없음\n"
    )


def test_render_srt_empty_input_and_exact_trailing_newline() -> None:
    assert render_srt([]) == ""
    rendered = render_srt([Utterance(0, 0, "메시지\n")])
    assert rendered == "1\n00:00:00,000 --> 00:00:00,000\n메시지\n"


def test_render_json_preserves_nested_payload_and_korean() -> None:
    payload = {
        "id": "job-id",
        "status": "completed",
        "results": {
            "utterances": [{"start_at": 0, "duration": 1000, "msg": "안녕하세요."}]
        },
    }

    rendered = render_json(payload)

    assert json.loads(rendered) == payload
    assert "안녕하세요." in rendered
    assert "\\uc548" not in rendered
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")


def test_write_text_file_creates_parent_and_writes_utf8(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "transcript.txt"

    result = write_text_file(output_path, "안녕하세요.\n")

    assert result == output_path
    assert output_path.read_text(encoding="utf-8") == "안녕하세요.\n"


def test_write_text_file_wraps_file_system_error(tmp_path: Path) -> None:
    output_path = tmp_path / "directory"
    output_path.mkdir()

    with pytest.raises(RTZROutputError, match="Could not write output file"):
        write_text_file(output_path, "내용")
