#!/usr/bin/env python3
"""
fetch_telegram.py

Notebook-first Telegram fetcher for liquidation messages.

- Date window is provided by the caller (start_dt, end_dt). No .env dependency for dates.
- Iterates messages chronologically (oldest -> newest) starting at start_dt, stops after end_dt.
- Case-insensitive substring filter (default: "Liquidated").
- Returns a pandas DataFrame (message_id, timestamp_utc, text).
- Optionally saves CSV to data/raw/telegram_messages.csv.
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError
from utils.telethon_client import make_client

load_dotenv()

API_ID_ENV = os.getenv("TELEGRAM_API_ID")
API_HASH_ENV = os.getenv("TELEGRAM_API_HASH")
SESSION_ENV = os.getenv("TELEGRAM_SESSION", ".telegram_session")

GROUP_ENV = os.getenv("TELEGRAM_GROUP", "@WhaleBotRektd")
GROUP_ID_ENV = os.getenv("TELEGRAM_GROUP_ID")  # numeric string OK

DEFAULT_OUT_PATH = Path("data/raw/telegram_messages.csv")


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _resolve_entity(client, channel: Optional[str], channel_id: Optional[int]):
    last_err = None
    if channel:
        try:
            return await client.get_entity(channel)
        except Exception as e:
            last_err = e
    if channel_id is not None:
        try:
            return await client.get_entity(int(channel_id))
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not resolve Telegram channel. Last error: {last_err}")


async def fetch_telegram_messages(
    start_dt: datetime,
    end_dt: datetime,
    *,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
    session_path: Optional[str] = None,
    channel: Optional[str] = None,
    channel_id: Optional[int] = None,
    substr_filter: Optional[str] = "Liquidated",
    out_path: Path = DEFAULT_OUT_PATH,
    save_csv: bool = True,
    hard_limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Fetch Telegram messages within [start_dt, end_dt] inclusive.
    Returns DataFrame: message_id, timestamp_utc, text
    """
    api_id = api_id or (int(API_ID_ENV) if API_ID_ENV else None)
    api_hash = api_hash or API_HASH_ENV
    session_path = session_path or SESSION_ENV
    channel = channel or GROUP_ENV
    channel_id = channel_id if channel_id is not None else (int(GROUP_ID_ENV) if GROUP_ID_ENV else None)

    if not api_id or not api_hash:
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required (pass as args or set in .env).")

    start_utc = _to_utc(start_dt).replace(microsecond=0)
    end_utc = _to_utc(end_dt).replace(microsecond=0)
    if end_utc < start_utc:
        raise ValueError("end_dt must be >= start_dt")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    async with make_client(api_id, api_hash, session_path) as client:
        entity = await _resolve_entity(client, channel, channel_id)

        try:
            # reverse=True => oldest→newest; offset_date=start_utc => start cursor
            async for msg in client.iter_messages(entity, offset_date=start_utc, reverse=True):
                if not getattr(msg, "date", None) or not getattr(msg, "text", None):
                    continue

                ts = msg.date
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                ts_utc = ts.astimezone(timezone.utc)

                if ts_utc > end_utc:
                    break
                if ts_utc < start_utc:
                    continue

                text = (msg.text or "").strip()
                if substr_filter and substr_filter.lower() not in text.lower():
                    continue

                rows.append((
                    int(msg.id),
                    ts_utc.isoformat(timespec="seconds"),
                    text.replace("\r", " ").replace("\n", " "),
                ))

                if hard_limit and len(rows) >= hard_limit:
                    break

        except (ChannelPrivateError, ChatAdminRequiredError) as e:
            raise RuntimeError(
                "Channel is private or requires admin privileges. "
                "Ensure your account can read this channel."
            ) from e

    df = pd.DataFrame(rows, columns=["message_id", "timestamp_utc", "text"])
    if not df.empty:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
        df = df.sort_values("timestamp_utc").reset_index(drop=True)

    if save_csv:
        df.to_csv(out_path, index=False)

    print(f"Fetched {len(df)} liquidation messages from {channel or channel_id} "
          f"between {start_utc} and {end_utc}. Saved: {save_csv} -> {out_path}")
    return df


# Minimal CLI fallback (keeps compatibility if you run the file directly)
def _parse_env_dt(name: str, fallback: datetime) -> datetime:
    s = os.getenv(name)
    if not s:
        return fallback
    dt = pd.to_datetime(s, utc=True)
    return dt.to_pydatetime()


def main() -> None:
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = _parse_env_dt("START_DATETIME", now_utc - timedelta(days=7))
    end = _parse_env_dt("END_DATETIME", now_utc)
    asyncio.run(fetch_telegram_messages(start, end, save_csv=True))


if __name__ == "__main__":
    main()
