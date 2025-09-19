import os
import csv
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from utils.telethon_client import make_client
from telethon.tl.types import Channel
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION = os.getenv("TELEGRAM_SESSION", ".telegram_session")
TELEGRAM_GROUP = os.getenv("TELEGRAM_GROUP", "WhaleBot Rektd ☠️")
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID", "1407057468"))
START_STR = os.getenv("START_DATETIME")
END_STR = os.getenv("END_DATETIME")
FILTER_SUBSTR = os.getenv("FILTER_TEXT_CONTAINS", "Liquidated")
OUT_PATH = Path("data/raw/telegram_messages.csv")


def _parse_dt_utc(s: Optional[str], fallback: Optional[datetime] = None) -> datetime:
    if not s:
        if fallback is None:
            raise ValueError("Missing datetime and no fallback provided")
        return fallback
    dt = pd.to_datetime(s, utc=True)
    return dt.to_pydatetime()


async def fetch_telegram_messages():
    if not API_ID or not API_HASH:
        raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env file")

    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    days_back = int(os.getenv("DAYS_BACK", "7"))
    start_utc = _parse_dt_utc(START_STR, fallback=now_utc - timedelta(days=days_back))
    end_utc = _parse_dt_utc(END_STR, fallback=now_utc)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Fetching messages from {start_utc.date()} to {end_utc.date()}")
    
    rows_written = 0
    total_processed = 0
    
    async with make_client(API_ID, API_HASH, SESSION) as client:
        with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["message_id", "timestamp_utc", "text"])
            
            try:
                channel_entity = await client.get_entity(TELEGRAM_GROUP)
            except Exception:
                try:
                    channel_entity = await client.get_entity(TELEGRAM_GROUP_ID)
                except Exception as e:
                    raise RuntimeError(f"Could not connect to channel: {e}")

            try:
                async for msg in client.iter_messages(channel_entity, limit=5000, reverse=False):
                    total_processed += 1
                    
                    if not msg.date or not msg.text:
                        continue

                    ts_utc = msg.date.astimezone(timezone.utc)

                    if ts_utc < start_utc:
                        break
                    if ts_utc > end_utc:
                        continue 
                        
                    text = msg.text.strip()
                    
                    if FILTER_SUBSTR and FILTER_SUBSTR.lower() not in text.lower():
                        continue

                    writer.writerow([
                        msg.id,
                        ts_utc.isoformat(timespec="seconds"),
                        text.replace("\r", " ").replace("\n", " "),
                    ])
                    rows_written += 1

            except (ChannelPrivateError, ChatAdminRequiredError):
                try:
                    recent_msgs = await client.get_messages(channel_entity, limit=10)
                    for msg in recent_msgs:
                        if msg.text and FILTER_SUBSTR.lower() in msg.text.lower():
                            ts_utc = msg.date.astimezone(timezone.utc)
                            writer.writerow([
                                msg.id,
                                ts_utc.isoformat(timespec="seconds"),
                                msg.text.replace("\r", " ").replace("\n", " "),
                            ])
                            rows_written += 1
                    total_processed = len(recent_msgs)
                except Exception as e:
                    print(f"Channel access failed: {e}")

    print(f"Processed {total_processed} messages, found {rows_written} liquidations")
    print(f"Saved to: {OUT_PATH}")


def main() -> None:
    try:
        asyncio.run(fetch_telegram_messages())
    except Exception as e:
        print(f"Error fetching messages: {e}")
        raise


if __name__ == "__main__":
    main()
