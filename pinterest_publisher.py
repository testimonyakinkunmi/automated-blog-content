"""
PINTEREST PUBLISHER — direct API posting (no manual CSV upload)
=================================================================
Publishes a pin straight to Pinterest using the v5 API. Replaces
the "export CSV, upload it yourself" step in bulk_pin_creator.py.

Requires a Pinterest Developer app with Trial access and a
one-time OAuth handshake (see pinterest_get_refresh_token.py).
The refresh token from that handshake is long-lived and this
script uses it to mint a fresh access token on every run — no
manual re-authorization needed.

SETUP (env vars or .env):
  PINTEREST_APP_ID
  PINTEREST_APP_SECRET
  PINTEREST_REFRESH_TOKEN
  PINTEREST_BOARD_ID

USAGE:
  python pinterest_publisher.py --image pin_images/foo.png \\
      --title "Pin title" --description "Pin description" \\
      --link "https://yourblog.github.io/2026/07/26/some-post/"
"""

import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path

import requests

TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
PINS_URL = "https://api.pinterest.com/v5/pins"


def load_env():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()

PINTEREST_APP_ID = os.environ.get("PINTEREST_APP_ID", "")
PINTEREST_APP_SECRET = os.environ.get("PINTEREST_APP_SECRET", "")
PINTEREST_REFRESH_TOKEN = os.environ.get("PINTEREST_REFRESH_TOKEN", "")
PINTEREST_BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "")


def get_access_token() -> str:
    """Exchange the long-lived refresh token for a fresh access token."""
    if not (PINTEREST_APP_ID and PINTEREST_APP_SECRET and PINTEREST_REFRESH_TOKEN):
        raise SystemExit(
            "Missing PINTEREST_APP_ID / PINTEREST_APP_SECRET / PINTEREST_REFRESH_TOKEN.\n"
            "Run pinterest_get_refresh_token.py once to obtain these."
        )

    resp = requests.post(
        TOKEN_URL,
        auth=(PINTEREST_APP_ID, PINTEREST_APP_SECRET),
        data={
            "grant_type": "refresh_token",
            "refresh_token": PINTEREST_REFRESH_TOKEN,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code != 200:
        raise Exception(f"Pinterest token refresh failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json()["access_token"]


def create_pin(image_path: str, title: str, description: str, link: str,
               board_id: str = "") -> dict:
    """Publish a pin directly to Pinterest using an inline base64 image."""
    board_id = board_id or PINTEREST_BOARD_ID
    if not board_id:
        raise SystemExit("Missing board_id. Set PINTEREST_BOARD_ID or pass --board-id.")

    image_bytes = Path(image_path).read_bytes()
    content_type = mimetypes.guess_type(image_path)[0] or "image/png"
    encoded = base64.b64encode(image_bytes).decode()

    access_token = get_access_token()

    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:800],
        "link": link,
        "media_source": {
            "source_type": "image_base64",
            "content_type": content_type,
            "data": encoded,
        },
    }

    resp = requests.post(
        PINS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if resp.status_code not in (200, 201):
        raise Exception(f"Pinterest pin creation failed ({resp.status_code}): {resp.text[:500]}")
    return resp.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish a pin directly to Pinterest")
    parser.add_argument("--image", required=True, help="Path to the pin image")
    parser.add_argument("--title", required=True, help="Pin title")
    parser.add_argument("--description", required=True, help="Pin description")
    parser.add_argument("--link", required=True, help="URL the pin should link to")
    parser.add_argument("--board-id", default="", help="Override PINTEREST_BOARD_ID")

    args = parser.parse_args()

    print(f"Publishing pin -> {args.link}")
    result = create_pin(args.image, args.title, args.description, args.link, args.board_id)
    pin_id = result.get("id", "unknown")
    print(f"Pin created: id={pin_id}")
    print(f"View it: https://www.pinterest.com/pin/{pin_id}/")
