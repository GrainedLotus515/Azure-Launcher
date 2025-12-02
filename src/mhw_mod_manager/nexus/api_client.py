"""Nexus Mods API client."""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from ..core.models import NexusMod, NexusModFile, NexusUser

logger = logging.getLogger(__name__)


class RateLimitInfo:
    """Tracks API rate limit information."""

    def __init__(self) -> None:
        """Initialize rate limit tracker."""
        self.hourly_limit: Optional[int] = None
        self.hourly_remaining: Optional[int] = None
        self.hourly_reset: Optional[datetime] = None
        self.daily_limit: Optional[int] = None
        self.daily_remaining: Optional[int] = None
        self.daily_reset: Optional[datetime] = None

    def update_from_headers(self, headers: httpx.Headers) -> None:
        """Update rate limit info from response headers.

        Args:
            headers: HTTP response headers.
        """
        if "X-RL-Hourly-Limit" in headers:
            self.hourly_limit = int(headers["X-RL-Hourly-Limit"])
        if "X-RL-Hourly-Remaining" in headers:
            self.hourly_remaining = int(headers["X-RL-Hourly-Remaining"])
        if "X-RL-Hourly-Reset" in headers:
            try:
                # Try parsing as timestamp first
                reset_timestamp = int(headers["X-RL-Hourly-Reset"])
                self.hourly_reset = datetime.fromtimestamp(reset_timestamp)
            except ValueError:
                # If that fails, try parsing as ISO datetime string
                try:
                    reset_str = headers["X-RL-Hourly-Reset"]
                    # Parse ISO format with timezone
                    self.hourly_reset = datetime.fromisoformat(
                        reset_str.replace(" +0000", "+00:00")
                    )
                except Exception:
                    # If both fail, skip setting reset time
                    pass

        if "X-RL-Daily-Limit" in headers:
            self.daily_limit = int(headers["X-RL-Daily-Limit"])
        if "X-RL-Daily-Remaining" in headers:
            self.daily_remaining = int(headers["X-RL-Daily-Remaining"])
        if "X-RL-Daily-Reset" in headers:
            try:
                # Try parsing as timestamp first
                reset_timestamp = int(headers["X-RL-Daily-Reset"])
                self.daily_reset = datetime.fromtimestamp(reset_timestamp)
            except ValueError:
                # If that fails, try parsing as ISO datetime string
                try:
                    reset_str = headers["X-RL-Daily-Reset"]
                    # Parse ISO format with timezone
                    self.daily_reset = datetime.fromisoformat(reset_str.replace(" +0000", "+00:00"))
                except Exception:
                    # If both fail, skip setting reset time
                    pass

    def is_limited(self) -> bool:
        """Check if we're currently rate limited.

        Returns:
            True if rate limited.
        """
        if self.hourly_remaining is not None and self.hourly_remaining <= 0:
            return True
        if self.daily_remaining is not None and self.daily_remaining <= 0:
            return True
        return False


class NexusAPIError(Exception):
    """Base exception for Nexus API errors."""

    pass


class NexusAuthError(NexusAPIError):
    """Authentication error."""

    pass


class NexusRateLimitError(NexusAPIError):
    """Rate limit exceeded error."""

    pass


class NexusNotFoundError(NexusAPIError):
    """Resource not found error."""

    pass


class NexusAPIClient:
    """Client for interacting with the Nexus Mods API."""

    BASE_URL = "https://api.nexusmods.com/v1"
    GAME_DOMAIN = "monsterhunterworld"

    def __init__(
        self,
        api_key: str,
        app_name: str = "MHW-Mod-Manager",
        app_version: str = "1.0.0",
    ) -> None:
        """Initialize the API client.

        Args:
            api_key: Nexus Mods API key.
            app_name: Application name for API headers.
            app_version: Application version for API headers.
        """
        self.api_key = api_key
        self.app_name = app_name
        self.app_version = app_version
        self.rate_limit = RateLimitInfo()
        self._client: Optional[httpx.Client] = None
        self._backoff_until: Optional[datetime] = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client.

        Returns:
            HTTP client instance.
        """
        if self._client is None:
            headers = {
                "apikey": self.api_key,
                "Application-Name": self.app_name,
                "Application-Version": self.app_version,
            }
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    def _check_backoff(self) -> None:
        """Check if we're in backoff period."""
        if self._backoff_until and datetime.now() < self._backoff_until:
            wait_seconds = (self._backoff_until - datetime.now()).total_seconds()
            raise NexusRateLimitError(f"Rate limited. Please wait {wait_seconds:.0f} seconds.")

    def _handle_rate_limit(self, attempt: int) -> None:
        """Handle rate limiting with exponential backoff.

        Args:
            attempt: Current retry attempt number.
        """
        backoff_seconds = min(60, 2**attempt)
        self._backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
        logger.warning(f"Rate limited. Backing off for {backoff_seconds} seconds.")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Make an API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Query parameters.
            max_retries: Maximum number of retries.

        Returns:
            JSON response data.

        Raises:
            NexusAPIError: On API errors.
        """
        self._check_backoff()

        client = self._get_client()
        url = endpoint

        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = client.get(url, params=params)
                elif method == "POST":
                    response = client.post(url, params=params)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                # Update rate limit info
                self.rate_limit.update_from_headers(response.headers)

                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        self._handle_rate_limit(attempt)
                        time.sleep(min(60, 2**attempt))
                        continue
                    raise NexusRateLimitError("Rate limit exceeded. Please try again later.")

                # Handle authentication errors
                if response.status_code == 401:
                    raise NexusAuthError("Invalid API key. Please check your credentials.")

                # Handle not found
                if response.status_code == 404:
                    raise NexusNotFoundError(f"Resource not found: {endpoint}")

                # Raise for other errors
                response.raise_for_status()

                return response.json()

            except httpx.HTTPStatusError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"HTTP error {e.response.status_code}, retrying...")
                    time.sleep(1)
                    continue
                raise NexusAPIError(f"HTTP error: {e}") from e
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request error, retrying: {e}")
                    time.sleep(1)
                    continue
                raise NexusAPIError(f"Request error: {e}") from e

        raise NexusAPIError("Max retries exceeded")

    def validate_api_key(self) -> NexusUser:
        """Validate the API key and get user information.

        Returns:
            User information.

        Raises:
            NexusAuthError: If API key is invalid.
        """
        data = self._request("GET", "/users/validate")

        try:
            return NexusUser(
                user_id=data["user_id"],
                username=data["name"],
                is_premium=data.get("is_premium", False),
                is_supporter=data.get("is_supporter", False),
                profile_url=data.get("profile_url", ""),
            )
        except (KeyError, ValidationError) as e:
            raise NexusAPIError(f"Invalid user data from API: {e}") from e

    def get_updated_mods(self, period: str = "1d") -> list[NexusMod]:
        """Get recently updated mods.

        Args:
            period: Time period (1d, 1w, 1m).

        Returns:
            List of updated mods.
        """
        endpoint = f"/games/{self.GAME_DOMAIN}/mods/updated.json"
        params = {"period": period}
        data = self._request("GET", endpoint, params=params)

        mods = []
        for item in data:
            try:
                mod = self._parse_mod(item)
                mods.append(mod)
            except (KeyError, ValidationError) as e:
                logger.warning(f"Failed to parse mod {item.get('mod_id')}: {e}")
                continue

        return mods

    def get_latest_added_mods(self) -> list[NexusMod]:
        """Get newly added mods.

        Returns:
            List of new mods.
        """
        endpoint = f"/games/{self.GAME_DOMAIN}/mods/latest_added.json"
        data = self._request("GET", endpoint)

        mods = []
        for item in data:
            try:
                mod = self._parse_mod(item)
                mods.append(mod)
            except (KeyError, ValidationError) as e:
                logger.warning(f"Failed to parse mod {item.get('mod_id')}: {e}")
                continue

        return mods

    def get_trending_mods(self) -> list[NexusMod]:
        """Get trending mods.

        Returns:
            List of trending mods.
        """
        endpoint = f"/games/{self.GAME_DOMAIN}/mods/trending.json"
        data = self._request("GET", endpoint)

        mods = []
        for item in data:
            try:
                mod = self._parse_mod(item)
                mods.append(mod)
            except (KeyError, ValidationError) as e:
                logger.warning(f"Failed to parse mod {item.get('mod_id')}: {e}")
                continue

        return mods

    def get_mod(self, mod_id: int) -> NexusMod:
        """Get detailed information about a specific mod.

        Args:
            mod_id: Mod ID.

        Returns:
            Mod details.

        Raises:
            NexusNotFoundError: If mod not found.
        """
        endpoint = f"/games/{self.GAME_DOMAIN}/mods/{mod_id}.json"
        data = self._request("GET", endpoint)
        return self._parse_mod(data)

    def get_mod_files(self, mod_id: int) -> list[NexusModFile]:
        """Get available files for a mod.

        Args:
            mod_id: Mod ID.

        Returns:
            List of mod files.
        """
        endpoint = f"/games/{self.GAME_DOMAIN}/mods/{mod_id}/files.json"
        data = self._request("GET", endpoint)

        files = []
        for item in data.get("files", []):
            try:
                mod_file = self._parse_mod_file(item, mod_id)
                files.append(mod_file)
            except (KeyError, ValidationError) as e:
                logger.warning(f"Failed to parse file {item.get('file_id')}: {e}")
                continue

        return files

    def get_download_link(
        self,
        mod_id: int,
        file_id: int,
        key: Optional[str] = None,
        expires: Optional[int] = None,
    ) -> list[str]:
        """Get download links for a mod file.

        Args:
            mod_id: Mod ID.
            file_id: File ID.
            key: Download key (required for non-premium users).
            expires: Key expiry timestamp (required for non-premium users).

        Returns:
            List of download URLs.

        Raises:
            NexusAuthError: If user is not premium and no key provided.
            NexusAPIError: If API returns unexpected data.
        """
        endpoint = f"/games/{self.GAME_DOMAIN}/mods/{mod_id}/files/{file_id}/download_link.json"

        # Build params for non-premium users
        params = {}
        if key is not None:
            params["key"] = key
        if expires is not None:
            params["expires"] = expires

        data = self._request("GET", endpoint, params=params if params else None)

        if not isinstance(data, list):
            raise NexusAPIError("Unexpected response format for download link")

        return [item["URI"] for item in data if "URI" in item]

    def _parse_mod(self, data: dict[str, Any]) -> NexusMod:
        """Parse mod data from API response.

        Args:
            data: Raw API data.

        Returns:
            Parsed mod.
        """
        # Parse timestamps - can be Unix timestamp (int) or ISO string
        created_timestamp = data["created_timestamp"]
        if isinstance(created_timestamp, int):
            created_time = datetime.fromtimestamp(created_timestamp)
        else:
            created_time = datetime.fromisoformat(created_timestamp.replace("Z", "+00:00"))

        updated_timestamp = data["updated_timestamp"]
        if isinstance(updated_timestamp, int):
            updated_time = datetime.fromtimestamp(updated_timestamp)
        else:
            updated_time = datetime.fromisoformat(updated_timestamp.replace("Z", "+00:00"))

        return NexusMod(
            mod_id=data["mod_id"],
            name=data["name"],
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            uploaded_by=data.get("uploaded_by", ""),
            picture_url=data.get("picture_url"),
            endorsement_count=data.get("endorsement_count", 0),
            download_count=data.get("total_downloads", 0),
            category_id=data.get("category_id", 0),
            version=data.get("version", ""),
            created_time=created_time,
            updated_time=updated_time,
            game_domain=self.GAME_DOMAIN,
        )

    def _parse_mod_file(self, data: dict[str, Any], mod_id: int) -> NexusModFile:
        """Parse mod file data from API response.

        Args:
            data: Raw API data.
            mod_id: Mod ID this file belongs to.

        Returns:
            Parsed mod file.
        """
        # Parse timestamp - can be Unix timestamp (int) or ISO string
        uploaded_timestamp = data["uploaded_timestamp"]
        if isinstance(uploaded_timestamp, int):
            uploaded_time = datetime.fromtimestamp(uploaded_timestamp)
        else:
            uploaded_time = datetime.fromisoformat(uploaded_timestamp.replace("Z", "+00:00"))

        return NexusModFile(
            file_id=data["file_id"],
            mod_id=mod_id,
            name=data["name"],
            version=data.get("version", ""),
            category_name=data.get("category_name", "main"),
            size_kb=data.get("size_kb", 0),
            size_in_bytes=data.get("size", data.get("size_kb", 0) * 1024),
            uploaded_time=uploaded_time,
            mod_version=data.get("mod_version"),
            description=data.get("description"),
            changelog_html=data.get("changelog_html"),
        )

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "NexusAPIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
