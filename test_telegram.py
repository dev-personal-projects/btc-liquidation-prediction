#!/usr/bin/env python3
"""
Simple Telegram connectivity test
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

async def test_telegram():
    """Test Telegram connection and fetch a few messages"""
    
    try:
        # Add src to path
        import sys
        sys.path.append('src')
        from utils.telethon_client import make_client
        
        API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
        API_HASH = os.getenv("TELEGRAM_API_HASH", "")
        SESSION = os.getenv("TELEGRAM_SESSION", ".telegram_session")
        CHANNEL_ID = int(os.getenv("TELEGRAM_GROUP_ID", "1407057468"))
        
        print("🔧 TELEGRAM CONNECTION TEST")
        print("=" * 40)
        
        if not API_ID or not API_HASH:
            print("❌ Missing credentials:")
            print(f"   API_ID: {'✅ Set' if API_ID else '❌ Missing'}")
            print(f"   API_HASH: {'✅ Set' if API_HASH else '❌ Missing'}")
            print("\\n💡 Add these to your .env file:")
            print("   TELEGRAM_API_ID=your_api_id")
            print("   TELEGRAM_API_HASH=your_api_hash")
            return False
        
        print(f"✅ Credentials found")
        print(f"📺 Target Channel ID: {CHANNEL_ID}")
        
        async with make_client(API_ID, API_HASH, SESSION) as client:
            print("🔄 Connecting to Telegram...")
            
            # Get channel info
            channel = await client.get_entity(CHANNEL_ID)
            print(f"✅ Connected to: {channel.title}")
            print(f"📊 Subscribers: {getattr(channel, 'participants_count', 'Unknown')}")
            
            # Fetch a few recent messages
            print("🔄 Fetching recent messages...")
            count = 0
            liquidation_count = 0
            
            async for message in client.iter_messages(channel, limit=100):
                count += 1
                if message.text and "liquidated" in message.text.lower():
                    liquidation_count += 1
                    if liquidation_count <= 3:  # Show first 3 liquidations
                        print(f"📝 Sample {liquidation_count}: {message.text[:80]}...")
            
            print(f"\\n📊 Results:")
            print(f"   Total messages checked: {count}")
            print(f"   Liquidation messages found: {liquidation_count}")
            
            if liquidation_count > 0:
                print("✅ SUCCESS: Can fetch liquidation data!")
                return True
            else:
                print("⚠️  No liquidation messages found in recent messages")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\\n💡 Possible solutions:")
        print("   - Check your API credentials")
        print("   - Make sure you're subscribed to the channel")
        print("   - Try running: python scripts/list_telegram_groups.py")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_telegram())
    if success:
        print("\\n🎉 Ready to run the notebook!")
    else:
        print("\\n🔧 Fix the issues above before running the notebook")