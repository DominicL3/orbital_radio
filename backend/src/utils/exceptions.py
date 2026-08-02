"""Custom exception classes for Orbital Radio backend."""


class TLEDataError(Exception):
    """Exception raised when satellite TLE data fetching, parsing, or processing fails."""
