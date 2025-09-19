#!/usr/bin/env python3

import os
from pathlib import Path

def check_setup():
    print("SETUP CHECKER")
    print("=" * 50)
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("✓ .env file found")
        
        # Load .env manually
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        env_vars = {}
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
        
        # Check required variables
        required_vars = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH']
        for var in required_vars:
            if var in env_vars and env_vars[var] not in ['', 'your_api_id_here', 'your_api_hash_here']:
                print(f"✓ {var}: Set")
            else:
                print(f"✗ {var}: Missing or placeholder")
        
        # Check optional variables
        optional_vars = ['TELEGRAM_GROUP', 'TELEGRAM_GROUP_ID', 'DAYS_BACK']
        for var in optional_vars:
            if var in env_vars:
                print(f"• {var}: {env_vars[var]}")
            else:
                print(f"! {var}: Not set (will use default)")
                
    else:
        print("✗ .env file not found")
        print("Copy env_template.txt to .env and fill in your credentials")
    
    print("\nGET TELEGRAM CREDENTIALS:")
    print("1. Go to https://my.telegram.org/apps")
    print("2. Log in with your Telegram account") 
    print("3. Create a new application")
    print("4. Copy API ID and API Hash to your .env file")
    
    print("\nEXAMPLE .env CONTENT:")
    print("TELEGRAM_API_ID=12345678")
    print("TELEGRAM_API_HASH=your_hash_here")
    print("TELEGRAM_GROUP=WhaleBot Rektd ☠️")
    print("DAYS_BACK=7")

if __name__ == "__main__":
    check_setup()
