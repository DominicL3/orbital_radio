"""Small, defensive client for the Spotify Web API."""

from collections import OrderedDict
import time
from typing import Any, Callable
from urllib.parse import quote, urlencode, urlparse

import requests

from src.config import get_settings


class SpotifyClient:
    """Call the Spotify OAuth and Web API endpoints."""

    _TOKEN_URL = "https://accounts.spotify.com/api/token"
    _API_URL = "https://api.spotify.com/v1"
    _TIMEOUT = 5
    _MAX_ATTEMPTS = 3

    def __init__(self) -> None:
        """Load required Spotify configuration from the environment."""
        settings = get_settings()
        values = {
            "SPOTIFY_CLIENT_ID": settings.spotify_client_id,
            "SPOTIFY_CLIENT_SECRET": settings.spotify_client_secret,
            "SPOTIFY_REDIRECT_URI": settings.spotify_redirect_uri,
        }
        if not all(values.values()):
            raise ValueError("Spotify configuration is missing")
        self.client_id = values["SPOTIFY_CLIENT_ID"]
        self.client_secret = values["SPOTIFY_CLIENT_SECRET"]
        self.redirect_uri = values["SPOTIFY_REDIRECT_URI"]
        self._token_cache: dict[str, Any] = {}
        self._playlist_cache: OrderedDict[tuple[str, str], list[dict[str, Any]]] = (
            OrderedDict()
        )

    @staticmethod
    def _required(value: str, name: str) -> str:
        """Return a non-empty string input."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    def _request(
        self,
        method: Callable[..., requests.Response],
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: str | None = None,
        auth: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a request, retrying only rate limits and server failures."""
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                response = method(
                    url,
                    headers=headers,
                    data=data,
                    auth=auth,
                    timeout=self._TIMEOUT,
                )
            except (requests.exceptions.Timeout, TimeoutError) as exc:
                raise RuntimeError("Spotify request timeout") from exc
            except (requests.exceptions.ConnectionError, ConnectionError) as exc:
                raise RuntimeError("Spotify network connection failed") from exc

            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < self._MAX_ATTEMPTS:
                    delay = 1
                    if response.status_code == 429:
                        try:
                            delay = min(
                                max(int(response.headers.get("Retry-After", 1)), 1), 60
                            )
                        except (AttributeError, TypeError, ValueError):
                            delay = 1
                    time.sleep(delay)
                    continue
                raise RuntimeError(
                    f"Spotify request failed after max retries ({response.status_code})"
                )

            if response.status_code < 200 or response.status_code >= 300:
                detail = ""
                try:
                    payload = response.json()
                    if isinstance(payload, dict):
                        error = payload.get("error")
                        if isinstance(error, str):
                            detail = error
                        elif isinstance(error, dict):
                            detail = str(
                                error.get("message") or error.get("status") or ""
                            )
                except (ValueError, TypeError):
                    pass
                suffix = f": {detail}" if detail in {"invalid_grant", "expired"} else ""
                raise RuntimeError(
                    f"Spotify request failed ({response.status_code}){suffix}"
                )

            try:
                payload = response.json()
            except (ValueError, TypeError) as exc:
                raise RuntimeError("Spotify returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise RuntimeError("Spotify returned an invalid response")
            return payload
        raise RuntimeError("Spotify request failed after max retries")

    def authenticate_user(self, auth_code: str) -> dict[str, Any]:
        """Exchange an OAuth authorization code for user tokens."""
        code = self._required(auth_code, "auth_code")
        body = urlencode(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
        )
        return self._request(
            requests.post,
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=body,
            auth=(self.client_id, self.client_secret),
        )

    def refresh_user_token(self, refresh_token: str) -> dict[str, Any]:
        """Exchange a refresh token for a new access token."""
        token = self._required(refresh_token, "refresh_token")
        return self._request(
            requests.post,
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=urlencode({"grant_type": "refresh_token", "refresh_token": token}),
            auth=(self.client_id, self.client_secret),
        )

    def get_user_profile(self, access_token: str) -> dict[str, Any]:
        """Fetch the current Spotify user's profile."""
        token = self._required(access_token, "access_token")
        return self._request(
            requests.get,
            f"{self._API_URL}/me",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    def search_tracks(
        self, query: str, access_token: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search Spotify tracks and return normalized track dictionaries."""
        query = self._required(query, "query")
        token = self._required(access_token, "access_token")
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 50
        ):
            raise ValueError("limit must be between 1 and 50")
        payload = self._request(
            requests.get,
            f"{self._API_URL}/search?{urlencode({'q': query, 'type': 'track', 'limit': limit})}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        tracks = payload.get("tracks")
        return self._tracks(tracks.get("items")) if isinstance(tracks, dict) else []

    def search_country_playlists(
        self, country: str, playlist_type: str, access_token: str
    ) -> list[dict[str, Any]]:
        """Find a country's playlist and return its normalized tracks."""
        country = self._required(country, "country")
        playlist_type = self._required(playlist_type, "playlist_type")
        token = self._required(access_token, "access_token")
        key = (country, playlist_type)
        if key in self._playlist_cache:
            return self._playlist_cache[key]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        query = urlencode(
            {"q": f"Top 50 {country} {playlist_type}", "type": "playlist", "limit": 50}
        )
        found = self._request(
            requests.get, f"{self._API_URL}/search?{query}", headers=headers
        )
        playlists = found.get("playlists")
        items = playlists.get("items") if isinstance(playlists, dict) else []
        playlist_id = (
            items[0].get("id")
            if isinstance(items, list) and items and isinstance(items[0], dict)
            else None
        )
        tracks: list[dict[str, Any]] = []
        if playlist_id:
            page = (
                f"{self._API_URL}/playlists/{quote(str(playlist_id), safe='')}/tracks"
            )
            for _ in range(100):
                payload = self._request(requests.get, page, headers=headers)
                tracks.extend(self._tracks(payload.get("items")))
                next_url = payload.get("next")
                if not isinstance(next_url, str) or not self._safe_next_url(next_url):
                    break
                page = next_url
        self._playlist_cache[key] = tracks
        if len(self._playlist_cache) > 100:
            self._playlist_cache.popitem(last=False)
        return tracks

    @staticmethod
    def _tracks(items: Any) -> list[dict[str, Any]]:
        """Normalize valid track entries from an API list."""
        if not isinstance(items, list):
            return []
        result = []
        for item in items:
            track = (
                item.get("track")
                if isinstance(item, dict) and "track" in item
                else item
            )
            if not isinstance(track, dict) or not track.get("id"):
                continue
            result.append(
                {
                    "id": track["id"],
                    "name": track.get("name", ""),
                    "duration_ms": track.get("duration_ms", 0),
                    "artists": track.get("artists", [])
                    if isinstance(track.get("artists", []), list)
                    else [],
                    "album": track.get("album", {})
                    if isinstance(track.get("album", {}), dict)
                    else {},
                    "preview_url": track.get("preview_url"),
                }
            )
        return result

    @staticmethod
    def _safe_next_url(value: str) -> bool:
        """Accept only Spotify API HTTPS pagination URLs."""
        try:
            parsed = urlparse(value)
            return (
                parsed.scheme == "https"
                and parsed.hostname == "api.spotify.com"
                and not parsed.username
                and not parsed.password
                and parsed.port in (None, 443)
            )
        except ValueError:
            return False
