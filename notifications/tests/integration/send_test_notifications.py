#!/usr/bin/env python3
"""Manual test script: send N random notifications to a single user via the notification-file-upload API.

Usage:
    python notifications/tests/integration/send_test_notifications.py \
        --system-number 100 \
        --api-key <your-api-token> \
        --count 5

    # Optional: target a non-local server
    python ... --base-url https://test.myabf.com.au

The API token must belong to a user who has the 'notifications.realtime_send.edit' RBAC role.
You can create one in the Django admin under API Tokens, or via the Django shell:
    from accounts.models import APIToken
    from accounts.models import User
    u = User.objects.get(system_number=100)
    t = APIToken(user=u); t.save(); print(t.token)
"""

import argparse
import io
import json
import random
import sys

import requests

SAMPLE_MESSAGES = [
    "Your entry for the upcoming tournament has been confirmed.",
    "Reminder: Club session starts at 7:30pm tonight.",
    "Your masterpoints tally has been updated.",
    "A new result has been posted for last week's pairs event.",
    "Your payment of $25.00 has been received.",
    "You have been invited to join the Friday Night Duplicate.",
    "Your membership renewal is due in 14 days.",
    "Congratulations! You finished 2nd in last night's Swiss Pairs.",
    "The director has posted a ruling on Board 12 from Tuesday.",
    "A message from your club secretary is waiting in your inbox.",
    "System maintenance is scheduled for Saturday 2am–4am AEST.",
    "Your partner request from Alan Larkin has been accepted.",
    "New discussion post in 'Bidding Theory' — you were mentioned.",
    "Event registration closes tomorrow at midnight.",
    "Your Bridge Credits balance is running low.",
]


def build_file_content(system_number: int, count: int) -> bytes:
    """Return tab-separated file content: one line per message, all for the same user."""
    messages = random.choices(SAMPLE_MESSAGES, k=count)
    lines = [f"{system_number}\t{msg}" for msg in messages]
    return "\n".join(lines).encode("utf-8")


def send(
    base_url: str, api_key: str, system_number: int, count: int, sender_id: str | None
):
    url = f"{base_url}/api/cobalt/notification-file-upload/v1.0"
    headers = {"key": api_key}

    file_bytes = build_file_content(system_number, count)
    files = {"file": ("test_notifications.txt", io.BytesIO(file_bytes), "text/plain")}
    data = {}
    if sender_id:
        data["sender_identification"] = sender_id

    print(f"POST {url}")
    print(f"  system_number : {system_number}")
    print(f"  message count : {count}")
    if sender_id:
        print(f"  sender_id     : {sender_id}")
    print()

    response = requests.post(url, headers=headers, files=files, data=data)

    try:
        body = response.json()
        print(json.dumps(body, indent=2))
    except Exception:
        print(f"HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)

    if response.status_code != 200:
        print(f"\nFailed with HTTP {response.status_code}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Send test notifications via the file-upload API."
    )
    parser.add_argument(
        "--system-number",
        type=int,
        required=True,
        help="ABF system number of the recipient",
    )
    parser.add_argument("--api-key", required=True, help="API token for authentication")
    parser.add_argument(
        "--count", type=int, default=5, help="Number of messages to send (default: 5)"
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the Cobalt instance",
    )
    parser.add_argument(
        "--sender", default=None, help="Optional sender_identification string"
    )
    args = parser.parse_args()

    send(
        base_url=args.base_url,
        api_key=args.api_key,
        system_number=args.system_number,
        count=args.count,
        sender_id=args.sender,
    )


if __name__ == "__main__":
    main()
