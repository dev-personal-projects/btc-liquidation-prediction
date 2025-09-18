#!/usr/bin/env python3
"""
List Telegram groups/channels for the authenticated user.
Helps find group names to use in TELEGRAM_GROUP env variable.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from telethon.tl.types import Channel, Chat

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.telethon_client import make_client

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION = os.getenv("TELEGRAM_SESSION", ".telegram_session")


def main() -> None:
    if not API_ID or not API_HASH:
        raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")

    print("Fetching your Telegram groups and channels...")
    print("=" * 60)

    with make_client(API_ID, API_HASH, SESSION) as client:
        dialogs = client.get_dialogs()
        
        groups = []
        channels = []
        
        for dialog in dialogs:
            entity = dialog.entity
            
            if isinstance(entity, Chat):
                # Regular group
                groups.append({
                    'title': entity.title,
                    'id': entity.id,
                    'participants': getattr(entity, 'participants_count', 'Unknown')
                })
            elif isinstance(entity, Channel):
                if entity.megagroup:
                    # Supergroup
                    groups.append({
                        'title': entity.title,
                        'id': entity.id,
                        'participants': getattr(entity, 'participants_count', 'Unknown')
                    })
                else:
                    # Channel
                    channels.append({
                        'title': entity.title,
                        'id': entity.id,
                        'participants': getattr(entity, 'participants_count', 'Unknown')
                    })

        # Print groups
        if groups:
            print(f"\n📱 GROUPS ({len(groups)}):")
            print("-" * 60)
            for i, group in enumerate(groups, 1):
                print(f"{i:2d}. {group['title']}")
                print(f"    ID: {group['id']}")
                print(f"    Members: {group['participants']}")
                print()

        # Print channels
        if channels:
            print(f"\n📢 CHANNELS ({len(channels)}):")
            print("-" * 60)
            for i, channel in enumerate(channels, 1):
                print(f"{i:2d}. {channel['title']}")
                print(f"    ID: {channel['id']}")
                print(f"    Subscribers: {channel['participants']}")
                print()

        print("=" * 60)
        print("💡 To use a group/channel in your .env file:")
        print("   TELEGRAM_GROUP=\"Group Title Here\"")
        print("   (or use the ID instead of title)")


if __name__ == "__main__":
    main()