import os
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from utils.telethon_client import make_client

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION = os.getenv("TELEGRAM_SESSION", ".telegram_session")
GROUP = os.getenv("TELEGRAM_GROUP", "WhaleBot Rektd ☠️")

START_STR = os.getenv("START_DATETIME")
END_STR = os.getenv("END_DATETIME")
FILTER_SUBSTR: Optional[str] = os.getenv("FILTER_TEXT_CONTAINS", "Liquidated") or None

OUT_PATH = Path("data/raw/telegram_messages.csv")


def _parse_dt_utc(s: Optional[str], fallback: Optional[datetime] = None) -> datetime:
    """
    Parse ISO string to UTC-aware datetime.
    Accepts naive or tz-aware; naive is treated as UTC.
    """
    if not s:
        if fallback is None:
            raise ValueError("Missing datetime and no fallback provided")
        return fallback
    dt = pd.to_datetime(s, utc=True)
    return dt.to_pydatetime()


def main() -> None:
    if not API_ID or not API_HASH:
        raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")

    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_utc = _parse_dt_utc(START_STR, fallback=now_utc.replace(hour=0) - pd.Timedelta(days=30))
    end_utc = _parse_dt_utc(END_STR, fallback=now_utc)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with make_client(API_ID, API_HASH, SESSION) as client, OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["message_id", "timestamp_utc", "text"])

        for msg in client.iter_messages(GROUP, offset_date=end_utc, reverse=True):
            if msg.date is None or msg.text is None:
                continue

            ts_utc = msg.date.astimezone(timezone.utc)

            if ts_utc < start_utc:
                break  

            if ts_utc > end_utc:
                continue 

            text = msg.text.strip()
            if FILTER_SUBSTR and FILTER_SUBSTR not in text:
                continue

            writer.writerow([
                msg.id,
                ts_utc.isoformat(timespec="seconds"),
                text.replace("\r", " ").replace("\n", " "),
            ])
            rows_written += 1

    print(f"saved {OUT_PATH} (rows={rows_written}, group={GROUP})")


if __name__ == "__main__":
    main()
