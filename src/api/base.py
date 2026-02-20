"""
Filename: base.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Base API client implementation.

This module provides the base class for all API clients, implementing
common functionality like request handling, authentication, and error
handling.
"""

from abc import ABC, abstractmethod
import asyncio
import json
import os
import aiohttp
from typing import List, Tuple, Optional, Any

from ..utils.logger import get_logger
from ..config.settings import config


def filter_root_folders(paths: List[str], service_config: dict) -> List[str]:
    """Filter root folder paths based on service exclusion config.

    Args:
        paths: List of root folder paths from the API.
        service_config: Service-level config dict (e.g. config["radarr"]).

    Returns:
        Filtered list of paths.
    """
    paths_config = service_config.get("paths", {})
    excluded = paths_config.get("excludedRootFolders", [])
    if excluded:
        narrow = paths_config.get("narrowRootFolderNames", False)
        if narrow:
            paths = [
                p for p in paths
                if os.path.basename(p.rstrip("/")) not in excluded
            ]
        else:
            paths = [p for p in paths if p not in excluded]
    return paths


class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class BaseApiClient(ABC):
    """Base class for API clients"""

    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 2
    DEFAULT_BACKOFF_BASE = 1.0
    RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})

    def __init__(self, service_name, request_timeout=None):
        self.service_name = service_name
        self.config = config[service_name]
        self.logger = get_logger(f"addarr.{service_name}")
        self.base_url = self._build_base_url()
        self.request_timeout = (
            request_timeout if request_timeout is not None
            else self.DEFAULT_TIMEOUT
        )
        self._session = None

    async def _get_session(self):
        """Get or create a reusable aiohttp session with default timeout."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the aiohttp session if open."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    def _build_base_url(self):
        """Build the base URL for API requests"""
        server_config = self.config["server"]
        protocol = "https" if server_config.get("ssl", False) else "http"
        return f"{protocol}://{server_config['addr']}:{server_config['port']}{server_config['path']}"

    def _get_headers(self):
        """Get headers for API requests"""
        return {
            'X-Api-Key': self.config["auth"]["apikey"],
            'Content-Type': 'application/json'
        }

    def _parse_error_response(self, response_text: str, title: str = None) -> str:
        """Parse error response from API

        Args:
            response_text: Raw response text from API
            title: Title/name of the item being processed

        Returns:
            str: User-friendly error message
        """
        try:
            if response_text.startswith("["):
                error_data = json.loads(response_text)
                if isinstance(error_data, list) and error_data:
                    error_msg = error_data[0].get("errorMessage")
                    if error_msg:
                        # Add title to "already exists" messages
                        if "already" in error_msg.lower() and title:
                            return f"{title} is already in your library"
                        return error_msg
            return response_text
        except json.JSONDecodeError:
            return response_text

    def _is_retryable_status(self, status_code: int) -> bool:
        """Check if an HTTP status code is retryable."""
        return status_code in self.RETRYABLE_STATUS_CODES

    async def _make_request(self, endpoint: str, method: str = "GET", data: Optional[dict] = None, title: str = None, timeout: int = None, max_retries: int = None) -> Tuple[bool, Any, Optional[str]]:
        """Make an API request with retry and exponential backoff.

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            title: Title/name of the item being processed
            timeout: Per-request timeout in seconds (overrides instance default)
            max_retries: Max retry attempts (overrides instance default)

        Returns:
            Tuple[bool, Any, Optional[str]]: (success, data, error_message)
        """
        url = f"{self.base_url}/api/v3/{endpoint}"
        retries = (
            max_retries if max_retries is not None
            else self.DEFAULT_MAX_RETRIES
        )

        request_kwargs = {
            "headers": self._get_headers(),
            "json": data,
        }
        if timeout is not None:
            request_kwargs["timeout"] = aiohttp.ClientTimeout(total=timeout)

        last_error_message = None

        for attempt in range(retries + 1):
            self.logger.info(f"🌐 API Request: {method} {url}")

            try:
                session = await self._get_session()
                async with session.request(method, url, **request_kwargs) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        self.logger.info(f"✅ API Response: {response.status}")
                        return True, json.loads(response_text) if response_text else None, None

                    # Parse error response with title context
                    error_message = self._parse_error_response(
                        response_text, title
                    )

                    # Retry on retryable status codes
                    if (
                        self._is_retryable_status(response.status)
                        and attempt < retries
                    ):
                        delay = self.DEFAULT_BACKOFF_BASE * (2 ** attempt)
                        self.logger.warning(
                            f"⚠️ Retryable error ({response.status}), "
                            f"retrying in {delay}s "
                            f"(attempt {attempt + 1}/{retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        last_error_message = error_message
                        continue

                    # Non-retryable or final attempt
                    if "already" in error_message.lower():
                        self.logger.info(f"ℹ️ {error_message}")
                    else:
                        self.logger.error(
                            f"❌ API request failed ({response.status}): "
                            f"{error_message}"
                        )
                    return False, None, error_message

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, asyncio.TimeoutError):
                    error_message = "Connection error: timeout"
                else:
                    error_message = f"Connection error: {str(e)}"
                last_error_message = error_message

                if attempt < retries:
                    delay = self.DEFAULT_BACKOFF_BASE * (2 ** attempt)
                    self.logger.warning(
                        f"⚠️ {error_message}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue

                self.logger.error(f"❌ {error_message}")
                return False, None, error_message

            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"
                self.logger.error(f"❌ {error_message}")
                return False, None, error_message

        # Should not reach here, but safety fallback
        return False, None, last_error_message

    @abstractmethod
    def search(self, term):
        """Search for media"""
        pass

    async def check_status(self) -> bool:
        """Check if the service is available"""
        try:
            # Most APIs have a system/status endpoint
            response = await self.get("system/status")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error checking API status: {e}")
            return False
