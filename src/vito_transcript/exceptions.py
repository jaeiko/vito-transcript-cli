"""Project-specific exceptions for RTZR API operations."""


class RTZRError(Exception):
    """Base exception for all RTZR client errors."""


class RTZRConfigurationError(RTZRError):
    """Raised when client configuration or local input is invalid."""


class RTZRRequestError(RTZRError):
    """Raised when an RTZR HTTP request cannot be completed successfully."""


class RTZRAuthenticationError(RTZRRequestError):
    """Raised when authentication with RTZR fails."""


class RTZRResponseError(RTZRError):
    """Raised when an RTZR response has an unexpected format."""


class RTZRTranscriptionFailedError(RTZRError):
    """Raised when RTZR reports that a transcription job failed."""


class RTZRTimeoutError(RTZRError):
    """Raised when a transcription does not finish before its deadline."""


class RTZROutputError(RTZRError):
    """Raised when rendered transcript output cannot be written."""
