"""Tests for RTZR transcript response models and parsing."""

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from vito_transcript.exceptions import RTZRResponseError
from vito_transcript.models import Utterance, parse_utterances


def verified_payload() -> dict[str, Any]:
    """Return a payload matching the verified completed API response."""
    return {
        "id": "job-id",
        "status": "completed",
        "results": {
            "utterances": [
                {
                    "start_at": 2036,
                    "duration": 5220,
                    "spk": 0,
                    "spk_type": "NORMAL",
                    "msg": "안녕하세요.",
                    "lang": "ko",
                }
            ]
        },
    }


def test_parse_verified_payload() -> None:
    utterances = parse_utterances(verified_payload())

    assert utterances == [
        Utterance(
            start_at=2036,
            duration=5220,
            message="안녕하세요.",
            speaker=0,
            language="ko",
        )
    ]


def test_parse_preserves_utterance_order() -> None:
    payload = verified_payload()
    payload["results"]["utterances"].append(
        {
            "start_at": 7996,
            "duration": 5120,
            "msg": "두 번째 발화입니다.",
        }
    )

    utterances = parse_utterances(payload)

    assert [utterance.message for utterance in utterances] == [
        "안녕하세요.",
        "두 번째 발화입니다.",
    ]


def test_utterance_end_at_and_immutability() -> None:
    utterance = Utterance(start_at=2036, duration=5220, message="안녕하세요.")

    assert utterance.end_at == 7256
    with pytest.raises(FrozenInstanceError):
        utterance.duration = 1  # type: ignore[misc]


def test_parse_rejects_missing_results() -> None:
    with pytest.raises(RTZRResponseError, match="results"):
        parse_utterances({"status": "completed"})


def test_parse_rejects_missing_utterances() -> None:
    with pytest.raises(RTZRResponseError, match="missing utterances"):
        parse_utterances({"results": {}})


def test_parse_rejects_non_list_utterances() -> None:
    with pytest.raises(RTZRResponseError, match="must be a list"):
        parse_utterances({"results": {"utterances": {}}})


def test_parse_rejects_malformed_utterance_item_with_index() -> None:
    payload = {"results": {"utterances": [42]}}

    with pytest.raises(RTZRResponseError, match="index 0"):
        parse_utterances(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("start_at", -1, "start_at must be non-negative"),
        ("duration", -1, "duration must be non-negative"),
        ("start_at", True, "start_at must be an integer"),
        ("duration", False, "duration must be an integer"),
    ],
)
def test_parse_rejects_invalid_timing(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = verified_payload()
    payload["results"]["utterances"][0][field] = value

    with pytest.raises(RTZRResponseError, match=f"index 0.*{message}"):
        parse_utterances(payload)


def test_parse_rejects_missing_message_with_index() -> None:
    payload = verified_payload()
    del payload["results"]["utterances"][0]["msg"]

    with pytest.raises(RTZRResponseError, match="index 0.*message"):
        parse_utterances(payload)


@pytest.mark.parametrize("speaker", [True, -1, "0"])
def test_parse_rejects_invalid_optional_speaker(speaker: object) -> None:
    payload = verified_payload()
    payload["results"]["utterances"][0]["spk"] = speaker

    with pytest.raises(RTZRResponseError, match="index 0.*speaker"):
        parse_utterances(payload)


def test_parse_allows_missing_or_null_optional_fields() -> None:
    payload = verified_payload()
    raw_utterance = payload["results"]["utterances"][0]
    raw_utterance.pop("spk")
    raw_utterance["lang"] = None

    utterance = parse_utterances(payload)[0]

    assert utterance.speaker is None
    assert utterance.language is None
