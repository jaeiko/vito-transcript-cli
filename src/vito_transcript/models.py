"""Validated data models for completed RTZR transcription responses."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from vito_transcript.exceptions import RTZRResponseError


@dataclass(frozen=True, slots=True)
class Utterance:
    """A single validated utterance from an RTZR transcription result."""

    start_at: int
    duration: int
    message: str
    speaker: int | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        """Validate timing, text, and optional metadata."""
        _validate_non_negative_integer(self.start_at, "start_at")
        _validate_non_negative_integer(self.duration, "duration")
        if not isinstance(self.message, str):
            raise TypeError("message must be a string")
        if self.speaker is not None:
            _validate_non_negative_integer(self.speaker, "speaker")
        if self.language is not None and not isinstance(self.language, str):
            raise TypeError("language must be a string or None")

    @property
    def end_at(self) -> int:
        """Return the utterance end time in milliseconds."""
        return self.start_at + self.duration


def parse_utterances(payload: Mapping[str, Any]) -> list[Utterance]:
    """Parse and validate utterances from a completed RTZR API payload."""
    results = payload.get("results")
    if not isinstance(results, Mapping):
        raise RTZRResponseError("The transcription response has invalid results.")

    if "utterances" not in results:
        raise RTZRResponseError(
            "The transcription response results are missing utterances."
        )
    raw_utterances = results["utterances"]
    if not isinstance(raw_utterances, list):
        raise RTZRResponseError("The transcription response utterances must be a list.")

    utterances = []
    for index, raw_utterance in enumerate(raw_utterances):
        if not isinstance(raw_utterance, Mapping):
            raise RTZRResponseError(f"Utterance at index {index} must be an object.")
        try:
            utterance = Utterance(
                start_at=raw_utterance.get("start_at"),
                duration=raw_utterance.get("duration"),
                message=raw_utterance.get("msg"),
                speaker=raw_utterance.get("spk"),
                language=raw_utterance.get("lang"),
            )
        except (TypeError, ValueError) as exc:
            raise RTZRResponseError(
                f"Utterance at index {index} is invalid: {exc}."
            ) from None
        utterances.append(utterance)

    return utterances


def _validate_non_negative_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
