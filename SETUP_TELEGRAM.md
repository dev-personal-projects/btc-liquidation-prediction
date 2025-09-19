# 🚀 Telegram Setup Guide

## 1. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your Telegram account
3. Create a new application
4. Copy the `API ID` and `API Hash`

## 2. Create .env File

Create a `.env` file in the project root with:

```bash
# Telegram API Credentials
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION=.telegram_session

# Group Settings
TELEGRAM_GROUP=WhaleBot Rektd ☠️
TELEGRAM_GROUP_ID=1407057468

# Date Range Settings  
START_DATETIME=2025-08-01T00:00:00+00:00
END_DATETIME=2025-09-20T00:00:00+00:00
DAYS_BACK=50

# Message Filtering
FILTER_TEXT_CONTAINS=Liquidated

# Price Settings
BINANCE_SYMBOL=BTCUSDT
AGG_INTERVAL=1H
```

## 3. Test Connection

Run the debug script:
```bash
python test_telegram_debug.py
```

## 4. Find Available Groups

If the group isn't accessible, list your groups:
```bash
python scripts/list_telegram_groups.py
```

## 5. Common Issues

### No messages found:
- Check if your account has access to the group
- Verify the group name/ID is correct
- Extend the date range (increase DAYS_BACK)

### Connection errors:
- Verify API credentials are correct
- Check internet connection
- Make sure you're logged into the Telegram account

### Group access errors:
- The group might be private
- Your account might not be a member
- Try using the group ID instead of name

## 6. Group Access Methods

The script tries multiple ways to access the group:
1. Exact group name: "WhaleBot Rektd ☠️"
2. Username format: "whalebotrektd"
3. Group ID: 1407057468

If none work, use `list_telegram_groups.py` to find the correct identifier.
