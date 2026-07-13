"""SubRip subtitle transcript rendering."""

from collections.abc import Sequence

from vito_transcript.exporters import format_srt_timestamp
from vito_transcript.models import Utterance


def render_srt(utterances: Sequence[Utterance]) -> str:
    """Render utterances in SubRip subtitle format."""
    entries = []
    for sequence_number, utterance in enumerate(utterances, start=1):
        start = format_srt_timestamp(utterance.start_at)
        end = format_srt_timestamp(utterance.end_at)
        message = utterance.message
        if utterance.speaker is not None:
            message = f"[Speaker {utterance.speaker + 1}] {message}"
        entries.append(f"{sequence_number}\n{start} --> {end}\n{message}")

    if not entries:
        return ""
    return "\n\n".join(entries).rstrip("\n") + "\n"
