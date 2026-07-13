"""Command-line tools for RTZR VITO transcription."""

from vito_transcript.client import RTZRClient
from vito_transcript.exceptions import (
    RTZRAuthenticationError,
    RTZRConfigurationError,
    RTZRError,
    RTZRRequestError,
    RTZRResponseError,
    RTZRTimeoutError,
    RTZRTranscriptionFailedError,
)

__version__ = "0.1.0"

__all__ = [
    "RTZRAuthenticationError",
    "RTZRClient",
    "RTZRConfigurationError",
    "RTZRError",
    "RTZRRequestError",
    "RTZRResponseError",
    "RTZRTimeoutError",
    "RTZRTranscriptionFailedError",
    "__version__",
]
