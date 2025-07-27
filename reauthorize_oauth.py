#!/usr/bin/env python3
"""
OAuth2 Re-authorization Script for Gmail + Calendar
This script will generate a new OAuth token with Calendar permissions
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Scopes that include both Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

def reauthorize_oauth():
    """Re-authorize OAuth with Calendar scope"""
    
    # Try to get OAuth client config from environment first
    oauth_json = os.getenv('GMAIL_OAUTH_JSON')
    client_config = None
    
    if oauth_json:
        try:
            client_config = json.loads(oauth_json)
            print("✅ Using OAuth config from environment variable")
        except:
            print("❌ Failed to parse GMAIL_OAUTH_JSON environment variable")
    
    # If not in environment, try to find the OAuth client file
    if not client_config:
        oauth_files = [f for f in os.listdir('.') if f.startswith('client_secret_') and f.endswith('.json')]
        if oauth_files:
            oauth_file = oauth_files[0]
            print(f"📁 Found OAuth client file: {oauth_file}")
            try:
                with open(oauth_file, 'r') as f:
                    client_config = json.load(f)
                print("✅ Using OAuth config from client file")
            except Exception as e:
                print(f"❌ Failed to read OAuth client file: {e}")
        else:
            print("❌ No OAuth client configuration found")
            print("Need either GMAIL_OAUTH_JSON environment variable or client_secret_*.json file")
            return False
    
    try:
        
        print("🔧 Starting OAuth2 re-authorization...")
        print(f"📋 Scopes: {SCOPES}")
        
        # Run the OAuth flow
        flow = InstalledAppFlow.from_client_config(
            client_config, SCOPES)
        
        # This will open a browser window for authorization
        creds = flow.run_local_server(port=0)
        
        # Save the credentials to gmail_token.json
        token_file = 'gmail_token.json'
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        print(f"✅ OAuth2 re-authorization successful!")
        print(f"📁 New token saved to: {token_file}")
        print("🔄 You can now restart your Discord bot")
        
        # Show the token info for verification
        token_info = json.loads(creds.to_json())
        print(f"\n📋 Token includes scopes:")
        for scope in token_info.get('scopes', []):
            print(f"   • {scope}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during re-authorization: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Gmail + Calendar OAuth2 Re-authorization")
    print("=" * 50)
    
    # Check if token file exists
    if os.path.exists('gmail_token.json'):
        response = input("📄 gmail_token.json exists. Replace it? (y/N): ")
        if response.lower() != 'y':
            print("❌ Re-authorization cancelled")
            exit(0)
    
    success = reauthorize_oauth()
    
    if success:
        print("\n🎉 Re-authorization complete!")
        print("Next steps:")
        print("1. Restart your Discord bot")
        print("2. Try creating a calendar event")
    else:
        print("\n❌ Re-authorization failed")
        print("Check your GMAIL_OAUTH_JSON environment variable")