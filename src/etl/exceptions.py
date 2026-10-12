"""Custom exceptions so the pipeline can distinguish failure types and decide
whether to retry, quarantine rows, or abort a source entirely."""


class ETLError(Exception):
    """Base class for all ETL errors."""


class ExtractionError(ETLError):
    """Raised when a source cannot be read (missing file, unreachable API, bad response)."""


class TransientAPIError(ExtractionError):
    """Raised for retryable failures from the mock Shipping API (5xx, timeout, connection reset)."""


class ValidationError(ETLError):
    """Raised when a batch fails validation badly enough that it cannot be loaded at all
    (e.g. required columns missing entirely). Row-level issues are quarantined instead
    of raising this."""


class LoadError(ETLError):
    """Raised when writing validated data to data/processed/ fails."""
