"""Plain-text transcript rendering."""

from collections.abc import Sequence

from vito_transcript.models import Utterance


def render_text(utterances: Sequence[Utterance]) -> str:
    """Render non-empty utterance messages as plain text, one per line."""
    messages = [utterance.message for utterance in utterances if utterance.message]
    if not messages:
        return ""
    return "\n".join(messages).rstrip("\n") + "\n"
