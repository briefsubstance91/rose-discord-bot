#!/usr/bin/env python3
"""
ROSE CALENDAR TEST SCRIPT (CLEAN VERSION)
Test only the working Google Calendars - no iCloud complexity
"""

import os
import json
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

def test_rose_calendars():
    """Test Rose's working calendars only"""
    
    print("🧪 TESTING ROSE'S WORKING CALENDARS")
    print("=" * 50)
    
    # Load credentials
    try:
        credentials_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        
        service_email = credentials_info.get('client_email')
        print(f"📧 Service Account: {service_email}")
        print()
        
    except Exception as e:
        print(f"❌ CRITICAL: Service setup failed: {e}")
        return
    
    # Test working calendars only
    calendars_to_test = [
        ("BG Calendar", os.getenv('GOOGLE_CALENDAR_ID')),
        ("BG Tasks", os.getenv('GOOGLE_TASKS_CALENDAR_ID')),
        ("Primary Fallback", "primary")
    ]
    
    working_calendars = []
    
    for name, calendar_id in calendars_to_test:
        if not calendar_id and calendar_id != "primary":
            print(f"⏭️ {name}: No calendar ID configured")
            continue
            
        print(f"🔍 Testing {name}...")
        
        try:
            # Test metadata access
            calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
            calendar_title = calendar_info.get('summary', 'No name')
            print(f"   ✅ Metadata: {calendar_title}")
            
            # Test event access (past 7 days)
            now = datetime.now(pytz.UTC)
            past_week = now - timedelta(days=7)
            
            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=past_week.isoformat(),
                timeMax=now.isoformat(),
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"   ✅ Events: {len(events)} found in past week")
            
            # Show sample events
            if events:
                print(f"   📋 Sample events:")
                for event in events[:3]:
                    title = event.get('summary', 'No title')
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(f"      • {title} ({start[:10]})")
            
            # Test future events
            future_week = now + timedelta(days=7)
            future_events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),
                timeMax=future_week.isoformat(),
                maxResults=5,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            future_events = future_events_result.get('items', [])
            print(f"   ✅ Upcoming: {len(future_events)} events next week")
            
            working_calendars.append((name, calendar_id, calendar_title))
            print(f"   🎯 {name}: FULLY WORKING\n")
            
        except HttpError as e:
            print(f"   ❌ HTTP Error {e.resp.status}: {e}")
            if e.resp.status == 404:
                print(f"   💡 Calendar not found - check ID")
            elif e.resp.status == 403:
                print(f"   💡 Permission denied - share with {service_email}")
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
    
    # Summary
    print("📊 FINAL RESULTS")
    print("=" * 30)
    
    if working_calendars:
        print(f"✅ Working calendars: {len(working_calendars)}")
        for name, calendar_id, title in working_calendars:
            print(f"   • {name}: {title}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Update Rose's main.py with the cleaned code")
        print(f"   2. Deploy to Railway with these calendar IDs")
        print(f"   3. Test with Discord commands: !calendars, !schedule")
        
    else:
        print(f"❌ No working calendars found")
        print(f"\n🔧 TROUBLESHOOTING:")
        print(f"   1. Share calendars with: {service_email}")
        print(f"   2. Check calendar IDs in environment variables")
        print(f"   3. Verify Google Calendar API is enabled")
    
    print(f"\n📋 REMOVED iCloud calendar - focusing on Google Calendars only")

if __name__ == "__main__":
    test_rose_calendars()
