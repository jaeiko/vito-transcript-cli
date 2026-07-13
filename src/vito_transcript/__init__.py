"""Command-line tools for RTZR VITO transcription."""

from vito_transcript.client import RTZRClient
from vito_transcript.exceptions import (
    RTZRAuthenticationError,
    RTZRConfigurationError,
    RTZRError,
    RTZROutputError,
    RTZRRequestError,
    RTZRResponseError,
    RTZRTimeoutError,
    RTZRTranscriptionFailedError,
)
from vito_transcript.models import Utterance, parse_utterances

__version__ = "0.1.0"

__all__ = [
    "RTZRAuthenticationError",
    "RTZRClient",
    "RTZRConfigurationError",
    "RTZRError",
    "RTZROutputError",
    "RTZRRequestError",
    "RTZRResponseError",
    "RTZRTimeoutError",
    "RTZRTranscriptionFailedError",
    "Utterance",
    "__version__",
    "parse_utterances",
]
