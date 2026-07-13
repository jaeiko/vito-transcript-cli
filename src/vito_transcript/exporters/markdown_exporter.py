"""Markdown transcript rendering."""

from collections.abc import Sequence

from vito_transcript.exporters import format_markdown_timestamp
from vito_transcript.models import Utterance


def render_markdown(
    utterances: Sequence[Utterance],
    *,
    title: str | None = None,
) -> str:
    """Render utterances with Markdown timestamps and speaker labels."""
    sections = []
    if title is not None:
        sections.append(f"# {title}")

    for utterance in utterances:
        timestamp = format_markdown_timestamp(utterance.start_at)
        if utterance.speaker is None:
            speaker = "Speaker Unknown"
        else:
            speaker = f"Speaker {utterance.speaker + 1}"
        sections.append(f"**[{timestamp}] {speaker}**\n\n{utterance.message}")

    if not sections:
        return ""
    return "\n\n".join(sections).rstrip("\n") + "\n"
