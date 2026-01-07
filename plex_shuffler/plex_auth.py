"""Plex PIN authentication helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

PLEX_PIN_URL = "https://plex.tv/api/v2/pins"
PLEX_AUTH_URL = "https://app.plex.tv/auth"
PLEX_USER_URL = "https://plex.tv/api/v2/user"
PLEX_RESOURCES_URL = "https://plex.tv/api/v2/resources"


class PlexAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlexPin:
    pin_id: int
    code: str
    expires_at: str
    auth_url: str
    auth_token: str | None = None


def create_pin(
    client_id: str,
    product: str,
    platform: str,
    device: str,
    device_name: str,
    version: str,
    forward_url: str | None = None,
) -> PlexPin:
    headers = _plex_headers(client_id, product, platform, device, device_name, version)
    url = f"{PLEX_PIN_URL}?{urlencode({'strong': 'true'})}"
    data = _request_json(url, headers=headers, method="POST")

    pin_id = int(data.get("id"))
    code = data.get("code")
    expires_at = data.get("expiresAt")
    auth_url = build_auth_url(
        client_id=client_id,
        code=code,
        product=product,
        platform=platform,
        device=device,
        device_name=device_name,
        model=device_name,
        forward_url=forward_url,
    )

    return PlexPin(pin_id=pin_id, code=code, expires_at=expires_at, auth_url=auth_url)


def check_pin(
    pin_id: int,
    client_id: str,
    product: str,
    platform: str,
    device: str,
    device_name: str,
    version: str,
) -> PlexPin:
    headers = _plex_headers(client_id, product, platform, device, device_name, version)
    data = _request_json(f"{PLEX_PIN_URL}/{pin_id}", headers=headers)

    auth_token = data.get("authToken")
    return PlexPin(
        pin_id=int(data.get("id")),
        code=data.get("code"),
        expires_at=data.get("expiresAt"),
        auth_url="",
        auth_token=auth_token,
    )


def fetch_user(
    token: str,
    client_id: str,
    product: str,
    platform: str,
    device: str,
    device_name: str,
    version: str,
) -> dict[str, Any]:
    headers = _plex_headers(client_id, product, platform, device, device_name, version)
    headers["X-Plex-Token"] = token
    return _request_json(PLEX_USER_URL, headers=headers)


def fetch_resources(
    token: str,
    client_id: str,
    product: str,
    platform: str,
    device: str,
    device_name: str,
    version: str,
) -> list[dict[str, Any]]:
    headers = _plex_headers(client_id, product, platform, device, device_name, version)
    headers["X-Plex-Token"] = token
    params = urlencode({"includeHttps": "1", "includeRelay": "1", "includeIPv6": "1"})
    data = _request_json(f"{PLEX_RESOURCES_URL}?{params}", headers=headers)
    if isinstance(data, list):
        return data
    return []


def build_auth_url(
    client_id: str,
    code: str,
    product: str,
    platform: str,
    device: str,
    device_name: str,
    model: str,
    forward_url: str | None = None,
) -> str:
    params = {
        "clientID": client_id,
        "code": code,
        "context[device][product]": product,
        "context[device][platform]": platform,
        "context[device][device]": device,
        "context[device][deviceName]": device_name,
        "context[device][model]": model,
    }
    if forward_url:
        params["forwardUrl"] = forward_url
    return f"{PLEX_AUTH_URL}#?{urlencode(params, quote_via=quote)}"


def _plex_headers(
    client_id: str,
    product: str,
    platform: str,
    device: str,
    device_name: str,
    version: str,
) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "X-Plex-Client-Identifier": client_id,
        "X-Plex-Product": product,
        "X-Plex-Platform": platform,
        "X-Plex-Device": device,
        "X-Plex-Device-Name": device_name,
        "X-Plex-Version": version,
    }


def _request_json(url: str, headers: dict[str, str], method: str = "GET") -> dict[str, Any]:
    request = Request(url, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise PlexAuthError(f"Plex auth error {exc.code} for {url}: {body}") from exc
    except URLError as exc:
        raise PlexAuthError(f"Plex auth connection error for {url}: {exc}") from exc

    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        snippet = payload[:200].decode("utf-8", errors="replace")
        raise PlexAuthError(f"Invalid Plex auth response: {snippet}") from exc
