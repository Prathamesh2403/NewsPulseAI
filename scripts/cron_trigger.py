"""
Render Cron Job — Ingestion Trigger Script

Logs in to the NewsPulse API to obtain a JWT token, then calls the
ingestion trigger endpoint. Render runs this script on the schedule
defined in render.yaml (midnight and noon UTC).

Required environment variables:
    API_URL          — Base URL of the deployed API (e.g. https://newspulse-api.onrender.com)
    ADMIN_USERNAME   — Admin username
    ADMIN_PASSWORD   — Admin plain-text password
"""

import os
import sys

import httpx


def main() -> None:
    api_url = os.environ["API_URL"].rstrip("/")
    username = os.environ["ADMIN_USERNAME"]
    password = os.environ["ADMIN_PASSWORD"]

    print(f"Connecting to API at {api_url} ...")

    # Step 1: obtain JWT token
    login_resp = httpx.post(
        f"{api_url}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    login_resp.raise_for_status()
    token = login_resp.json()["access_token"]
    print("Login successful.")

    # Step 2: trigger ingestion
    trigger_resp = httpx.post(
        f"{api_url}/api/v1/admin/ingestion/trigger",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    trigger_resp.raise_for_status()
    print("Ingestion triggered successfully:", trigger_resp.json())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Cron job failed: {exc}", file=sys.stderr)
        sys.exit(1)
