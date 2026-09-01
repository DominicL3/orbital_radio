"""Custom exception classes for Orbital Radio backend."""


class TLEDataError(Exception):
    """Exception raised when satellite TLE data fetching, parsing, or processing fails."""


class RadioBrowserError(Exception):
    """Base exception for Radio Browser request and response failures."""


class RadioBrowserUnavailableError(RadioBrowserError):
    """Raised when no Radio Browser mirror can provide usable data."""


class RadioBrowserResponseError(RadioBrowserError):
    """Raised when a Radio Browser response cannot be safely normalized."""


class GeographicLookupError(Exception):
    """Exception raised when offline country-boundary lookup cannot proceed."""


class NoEligibleStationError(Exception):
    """Exception raised when no playable station matches a country request."""
