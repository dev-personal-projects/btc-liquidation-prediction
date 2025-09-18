from telethon.sync import TelegramClient

def make_client(api_id: int, api_hash: str, session_path: str) -> TelegramClient:
    return TelegramClient(session_path, api_id, api_hash)
