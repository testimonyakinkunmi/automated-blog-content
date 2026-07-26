"""
PINTEREST ONE-TIME AUTH — run this ONCE, on your own machine
===============================================================
Walks you through Pinterest's OAuth login and prints the
long-lived refresh token that pinterest_publisher.py needs.
You will not need to run this again unless you revoke the app.

SETUP:
  export PINTEREST_APP_ID="your-app-id"
  export PINTEREST_APP_SECRET="your-app-secret"

USAGE:
  python pinterest_get_refresh_token.py
"""

import base64
import os
import sys
from urllib.parse import urlencode

import requests

REDIRECT_URI = "https://localhost:8085/"
SCOPES = "pins:read,pins:write,boards:read,boards:write,user_accounts:read"

APP_ID = os.environ.get("PINTEREST_APP_ID", "")
APP_SECRET = os.environ.get("PINTEREST_APP_SECRET", "")

if not (APP_ID and APP_SECRET):
    print("ERROR: export PINTEREST_APP_ID and PINTEREST_APP_SECRET first.")
    sys.exit(1)

params = {
    "client_id": APP_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPES,
}
authorize_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"

print("=" * 70)
print("STEP 1 — Open this URL in your browser and log in / approve access:")
print("=" * 70)
print(authorize_url)
print()
print("After you approve, your browser will try to load")
print(f"  {REDIRECT_URI}...")
print("and probably show a 'can't reach this page' / connection error.")
print("That's expected — localhost isn't actually running anything.")
print()
print("Look at your browser's ADDRESS BAR. It will look like:")
print(f"  {REDIRECT_URI}?code=SOME_LONG_CODE")
print("Copy everything after 'code=' and paste it below.")
print("=" * 70)

code = input("\nPaste the code here: ").strip()

resp = requests.post(
    "https://api.pinterest.com/v5/oauth/token",
    auth=(APP_ID, APP_SECRET),
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)

if resp.status_code != 200:
    print(f"\nERROR ({resp.status_code}): {resp.text}")
    sys.exit(1)

data = resp.json()
print("\n" + "=" * 70)
print("SUCCESS — save these as GitHub Actions secrets:")
print("=" * 70)
print(f"PINTEREST_REFRESH_TOKEN = {data.get('refresh_token')}")
print()
print("(The access_token printed below is short-lived and only for your")
print(" own quick testing — the automation only needs the refresh token.)")
print(f"access_token (temporary, for testing only) = {data.get('access_token')}")
