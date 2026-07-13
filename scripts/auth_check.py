"""Verify RTZR API credentials without exposing sensitive values."""

import os
import sys

import requests
from dotenv import load_dotenv

AUTH_URL = "https://openapi.vito.ai/v1/authenticate"
HTTP_TIMEOUT_SECONDS = 10


def authenticate() -> bool:
    """Return whether the configured RTZR credentials authenticate successfully."""
    load_dotenv()

    client_id = os.getenv("RTZR_CLIENT_ID")
    client_secret = os.getenv("RTZR_CLIENT_SECRET")
    if not client_id or not client_secret:
        return False

    try:
        response = requests.post(
            AUTH_URL,
            data={"client_id": client_id, "client_secret": client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        payload = response.json() if response.ok else {}
    except (requests.RequestException, ValueError):
        return False

    return isinstance(payload, dict) and bool(payload.get("access_token"))


def main() -> int:
    """Print the authentication result and return a process exit status."""
    if authenticate():
        print("Authentication succeeded.")
        return 0

    print("Authentication failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
