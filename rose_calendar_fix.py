def test_calendar_access(calendar_id, calendar_name):
    """Enhanced calendar testing with better error messages"""
    if not calendar_service or not calendar_id:
        return False
    
    try:
        # Test calendar metadata
        calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ {calendar_name} metadata retrieved")
        
        # Test event access with recent events
        now = datetime.now(pytz.UTC)
        past_24h = now - timedelta(hours=24)
        
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=past_24h.isoformat(),
            timeMax=now.isoformat(),
            maxResults=5,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        print(f"✅ {calendar_name} events retrieved: {len(events)} events")
        
        # Additional check: try to get calendar's access role
        calendar_list = calendar_service.calendarList().list().execute()
        for cal in calendar_list.get('items', []):
            if cal['id'] == calendar_id:
                access_role = cal.get('accessRole', 'unknown')
                print(f"📋 {calendar_name} access role: {access_role}")
                break
        
        return True
        
    except HttpError as e:
        error_code = e.resp.status
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        
        print(f"❌ {calendar_name} HTTP Error {error_code}: {error_details}")
        
        if error_code == 404:
            print(f"💡 {calendar_name}: Calendar not found - check ID format")
            print(f"   ID used: {calendar_id}")
        elif error_code == 403:
            print(f"💡 {calendar_name}: Permission denied")
            print(f"   Suggestion: Share calendar with service account")
        elif error_code == 400:
            print(f"💡 {calendar_name}: Bad request - malformed calendar ID")
        
        return False
        
    except Exception as e:
        print(f"❌ {calendar_name} unexpected error: {e}")
        print(f"   Exception type: {type(e).__name__}")
        return False

def get_all_accessible_calendars():
    """Get list of all calendars accessible to service account"""
    if not calendar_service:
        return []
    
    try:
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = []
        
        print(f"📋 Found {len(calendar_list.get('items', []))} accessible calendars:")
        
        for calendar in calendar_list.get('items', []):
            cal_id = calendar['id']
            summary = calendar.get('summary', 'Unnamed')
            access_role = calendar.get('accessRole', 'unknown')
            
            print(f"   • {summary}")
            print(f"     ID: {cal_id}")
            print(f"     Access: {access_role}")
            
            # Identify imported calendars
            if 'import.calendar.google.com' in cal_id:
                print(f"     🍎 Imported calendar (likely iCloud)")
            elif cal_id == 'primary':
                print(f"     📅 Primary Google Calendar")
            elif '@group.calendar.google.com' in cal_id:
                print(f"     👥 Shared Google Calendar")
            
            calendars.append((summary, cal_id, access_role))
            print()
        
        return calendars
        
    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return []

# Replace your existing calendar setup with this enhanced version
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized")
        
        # Get service account email for sharing instructions
        service_email = credentials_info.get('client_email')
        print(f"📧 Service Account Email: {service_email}")
        print(f"💡 Share calendars with this email for access")
        
        # List all accessible calendars first
        all_calendars = get_all_accessible_calendars()
        
        # Test specific calendars
        calendars_to_test = [
            ("BG Calendar", GOOGLE_CALENDAR_ID),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID),
            ("Britt iCloud", BRITT_ICLOUD_CALENDAR_ID)
        ]
        
        accessible_calendars = []
        
        for name, calendar_id in calendars_to_test:
            if calendar_id and test_calendar_access(calendar_id, name):
                # Determine calendar type
                if "task" in name.lower():
                    accessible_calendars.append((name, calendar_id, "tasks"))
                elif "britt" in name.lower():
                    accessible_calendars.append((name, calendar_id, "britt"))
                else:
                    accessible_calendars.append((name, calendar_id, "calendar"))
        
        # If no calendars work, try primary as fallback
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary", "calendar"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _, _ in accessible_calendars:
            print(f"   ✅ {name}")
        
        if not accessible_calendars:
            print("❌ No accessible calendars found")
            print("💡 Next steps:")
            print("   1. Check service account email above")
            print("   2. Share calendars with service account")
            print("   3. Verify calendar IDs are correct")
            
    else:
        print("⚠️ Google Calendar credentials not found")
        
except Exception as e:
    print(f"❌ Google Calendar setup error: {e}")
    calendar_service = None
    accessible_calendars = []
