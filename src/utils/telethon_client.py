from telethon import TelegramClient

def make_client(api_id: int, api_hash: str, session_path: str) -> TelegramClient:
    """Create a Telegram client with proper error handling"""
    if not api_id or not api_hash:
        raise ValueError("API ID and API Hash are required")
    
    return TelegramClient(session_path, api_id, api_hash)
