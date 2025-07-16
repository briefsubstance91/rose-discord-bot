#!/usr/bin/env python3
"""
Enhanced Rose Calendar Debug Script
Better error handling and troubleshooting for iCloud calendar integration
"""

import json
import pytz
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def debug_calendar_access():
    """Comprehensive calendar debugging"""
    
    # Your calendar IDs
    GOOGLE_CALENDAR_ID = "your_bg_calendar_id"  # Replace with actual ID
    GOOGLE_TASKS_CALENDAR_ID = "your_bg_tasks_id"  # Replace with actual ID  
    BRITT_ICLOUD_CALENDAR_ID = "hgv2ucmvva5b4tvm10lguaqiqftg1mu4@import.calendar.google.com"
    
    # Load service account credentials
    try:
        credentials_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Calendar service initialized")
    except Exception as e:
        print(f"❌ Service initialization error: {e}")
        return

    # Test calendars
    calendars_to_test = [
        ("BG Calendar", GOOGLE_CALENDAR_ID),
        ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID),
        ("Britt iCloud", BRITT_ICLOUD_CALENDAR_ID)
    ]
    
    for name, calendar_id in calendars_to_test:
        print(f"\n🔍 Testing {name} ({calendar_id})")
        test_specific_calendar(calendar_service, calendar_id, name)

def test_specific_calendar(service, calendar_id, name):
    """Test specific calendar with detailed error reporting"""
    
    try:
        # Test 1: Get calendar metadata
        print(f"   📋 Testing calendar metadata...")
        calendar_info = service.calendars().get(calendarId=calendar_id).execute()
        print(f"   ✅ Calendar found: {calendar_info.get('summary', 'No name')}")
        print(f"   📝 Description: {calendar_info.get('description', 'No description')}")
        print(f"   🔐 Access Role: {calendar_info.get('accessRole', 'No access role')}")
        
        # Test 2: Get recent events
        print(f"   📅 Testing event retrieval...")
        now = datetime.now(pytz.UTC)
        past_week = now - timedelta(days=7)
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=past_week.isoformat(),
            timeMax=now.isoformat(),
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        print(f"   ✅ Found {len(events)} events in past week")
        
        if events:
            print(f"   📋 Sample events:")
            for event in events[:3]:
                title = event.get('summary', 'No title')
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"      • {title} ({start})")
        
        # Test 3: Get future events
        print(f"   🔮 Testing future events...")
        future_week = now + timedelta(days=7)
        
        future_events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=future_week.isoformat(),
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        future_events = future_events_result.get('items', [])
        print(f"   ✅ Found {len(future_events)} future events")
        
        return True
        
    except HttpError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   📋 Error details: {e.error_details}")
        
        if e.resp.status == 404:
            print(f"   💡 Calendar not found - check ID format")
        elif e.resp.status == 403:
            print(f"   💡 Permission denied - check service account access")
        elif e.resp.status == 400:
            print(f"   💡 Bad request - check calendar ID format")
            
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def list_all_calendars(service):
    """List all calendars accessible to service account"""
    try:
        print("\n📋 ALL ACCESSIBLE CALENDARS:")
        calendar_list = service.calendarList().list().execute()
        
        for calendar in calendar_list.get('items', []):
            cal_id = calendar['id']
            summary = calendar.get('summary', 'No name')
            access_role = calendar.get('accessRole', 'No access')
            
            print(f"   • {summary}")
            print(f"     ID: {cal_id}")
            print(f"     Access: {access_role}")
            
            # Check if this matches your iCloud calendar
            if 'import.calendar.google.com' in cal_id:
                print(f"     🍎 This is an imported calendar (likely iCloud)")
            print()
            
    except Exception as e:
        print(f"   ❌ Error listing calendars: {e}")

def check_service_account_email():
    """Display service account email for sharing calendars"""
    try:
        credentials_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
        service_email = credentials_info.get('client_email')
        print(f"\n📧 Service Account Email: {service_email}")
        print(f"💡 Share calendars with this email for access")
        return service_email
    except Exception as e:
        print(f"❌ Error getting service account email: {e}")
        return None

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("🔍 ROSE CALENDAR DEBUG SCRIPT")
    print("=" * 50)
    
    # Check service account email
    check_service_account_email()
    
    # Debug calendar access
    debug_calendar_access()
    
    # List all calendars
    try:
        credentials_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        service = build('calendar', 'v3', credentials=credentials)
        list_all_calendars(service)
    except Exception as e:
        print(f"❌ Error in calendar listing: {e}")
