#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from telethon.tl.types import Channel, Chat

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.telethon_client import make_client

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION = os.getenv("TELEGRAM_SESSION", ".telegram_session")
KEYWORDS = os.getenv("SEARCH_KEYWORDS", "liquidation,rekt,whale,alert,bot,trading,crypto").lower().split(",")
CHECK_MESSAGES = os.getenv("CHECK_RECENT_MESSAGES", "true").lower() == "true"


def contains_keywords(text: str, keywords: list) -> list:
    if not text:
        return []
    text_lower = text.lower()
    return [kw for kw in keywords if kw.strip() in text_lower]


def check_recent_messages(client, entity, limit=10):
    try:
        messages = client.get_messages(entity, limit=limit)
        keyword_matches = []
        
        for msg in messages:
            if msg.text:
                matches = contains_keywords(msg.text, KEYWORDS)
                if matches:
                    keyword_matches.extend(matches)
        
        return list(set(keyword_matches))
    except Exception:
        return []


def main() -> None:
    if not API_ID or not API_HASH:
        raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")

    print("🔍 Finding Telegram groups with liquidation data...")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print("=" * 70)

    with make_client(API_ID, API_HASH, SESSION) as client:
        dialogs = client.get_dialogs()
        
        candidates = []
        
        for dialog in dialogs:
            entity = dialog.entity
            
            # Skip private chats
            if not isinstance(entity, (Chat, Channel)):
                continue
                
            title = entity.title or "Unknown"
            entity_type = "Group" if isinstance(entity, Chat) or (isinstance(entity, Channel) and entity.megagroup) else "Channel"
            participants = getattr(entity, 'participants_count', 'Unknown')
            
            # Check title for keywords
            title_matches = contains_keywords(title, KEYWORDS)
            
            # Check recent messages if enabled
            message_matches = []
            if CHECK_MESSAGES:
                message_matches = check_recent_messages(client, entity)
            
            # If we found matches, add to candidates
            all_matches = list(set(title_matches + message_matches))
            if all_matches:
                candidates.append({
                    'title': title,
                    'type': entity_type,
                    'id': entity.id,
                    'participants': participants,
                    'title_matches': title_matches,
                    'message_matches': message_matches,
                    'all_matches': all_matches,
                    'last_message': dialog.date
                })

        # Sort by number of matches (most relevant first)
        candidates.sort(key=lambda x: len(x['all_matches']), reverse=True)

        if not candidates:
            print("❌ No groups found with liquidation-related keywords.")
            print("\n💡 Try adjusting SEARCH_KEYWORDS in your .env file")
            return

        print(f"\n🎯 FOUND {len(candidates)} POTENTIAL LIQUIDATION GROUPS/CHANNELS:")
        print("=" * 70)

        for i, candidate in enumerate(candidates, 1):
            print(f"{i:2d}. {candidate['title']} ({candidate['type']})")
            print(f"    ID: {candidate['id']}")
            print(f"    Members: {candidate['participants']}")
            print(f"    Keywords found: {', '.join(candidate['all_matches'])}")
            
            if candidate['title_matches']:
                print(f"    📝 In title: {', '.join(candidate['title_matches'])}")
            if candidate['message_matches']:
                print(f"    💬 In messages: {', '.join(candidate['message_matches'])}")
            
            if candidate['last_message']:
                last_msg_age = datetime.now(timezone.utc) - candidate['last_message']
                if last_msg_age.days == 0:
                    age_str = f"{last_msg_age.seconds // 3600}h ago"
                else:
                    age_str = f"{last_msg_age.days}d ago"
                print(f"    🕒 Last activity: {age_str}")
            
            print()

        print("=" * 70)
        print("💡 To use a group in your .env file:")
        print("   TELEGRAM_GROUP=\"Group Title Here\"")
        print("\n🔧 To customize search:")
        print("   SEARCH_KEYWORDS=\"liquidation,rekt,whale,your_keywords\"")


if __name__ == "__main__":
    main()