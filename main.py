        calendar_status = "❌ No calendars accessible"
        if accessible_calendars:
            calendar_names = [name for name, _, _ in accessible_calendars]
            calendar_status = f"✅ {len(accessible_calendars)} calendars: {', '.join(calendar_names)}"
        
        gmail_status = "❌ Not configured"
        if gmail_service and gmail_user_email:
            gmail_status = f"✅ Connected: {gmail_user_email}"
        
        research_status = "✅ Enabled" if BRAVE_API_KEY else "❌ Disabled"
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        
        sa_info = "Not configured"
        if service_account_email:
            sa_info = f"✅ {service_account_email}"
        
        status_text = f"""👑 **{ASSISTANT_NAME} Executive Status**

**🤖 Core Systems:**
• Discord: ✅ Connected as {bot.user.name if bot.user else 'Unknown'}
• OpenAI Assistant: {assistant_status}
• Service Account: {sa_info}

**📅 Calendar Integration:**
• Status: {calendar_status}
• Timezone: 🇨🇦 Toronto (America/Toronto)

**📧 Gmail Integration:**
• Status: {gmail_status}

**🔍 Planning Research:**
• Brave Search API: {research_status}

**💼 Executive Features:**
• Active conversations: {len(user_conversations)}
• Channels: {', '.join(ALLOWED_CHANNELS)}

**⚡ Performance:**
• Uptime: Ready for executive assistance
• Memory: {len(processing_messages)} processing"""#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (FIXED VERSION)
Executive Assistant with Full Google Calendar API Integration & Advanced Task Management
"""
import pytz
import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
import json
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

# Rose's executive configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant (Complete Enhanced)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Calendar integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')

# Gmail integration
GMAIL_USER_EMAIL = os.getenv('GMAIL_USER_EMAIL')  # Your main email address
GMAIL_DELEGATE_EMAIL = os.getenv('GMAIL_DELEGATE_EMAIL', GMAIL_USER_EMAIL)  # Email to impersonate

# Validate critical environment variables
if not DISCORD_TOKEN:
    print("❌ CRITICAL: DISCORD_TOKEN not found in environment variables")
    exit(1)

if not OPENAI_API_KEY:
    print("❌ CRITICAL: OPENAI_API_KEY not found in environment variables")
    exit(1)

if not ASSISTANT_ID:
    print("❌ CRITICAL: ROSE_ASSISTANT_ID not found in environment variables")
    exit(1)

# Discord setup
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
except Exception as e:
    print(f"❌ CRITICAL: Discord bot initialization failed: {e}")
    exit(1)

# OpenAI setup
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"❌ CRITICAL: OpenAI client initialization failed: {e}")
    exit(1)

# Google Calendar setup
calendar_service = None
accessible_calendars = []
service_account_email = None

# Gmail setup
gmail_service = None
gmail_user_email = None

def test_calendar_access(calendar_id, calendar_name):
    """Test calendar access with comprehensive error handling"""
    if not calendar_service or not calendar_id:
        return False
    
    try:
        calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ {calendar_name} accessible")
        
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
        print(f"✅ {calendar_name} events: {len(events)} found")
        
        return True
        
    except HttpError as e:
        error_code = e.resp.status
        print(f"❌ {calendar_name} HTTP Error {error_code}")
        return False
    except Exception as e:
        print(f"❌ {calendar_name} error: {e}")
        return False

# Initialize Google Calendar service
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized")
        
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account: {service_account_email}")
        
        # Initialize Gmail service with domain-wide delegation
        if GMAIL_USER_EMAIL:
            delegated_credentials = credentials.with_subject(GMAIL_DELEGATE_EMAIL or GMAIL_USER_EMAIL)
            gmail_service = build('gmail', 'v1', credentials=delegated_credentials)
            gmail_user_email = GMAIL_DELEGATE_EMAIL or GMAIL_USER_EMAIL
            print(f"✅ Gmail service initialized for: {gmail_user_email}")
        else:
            print("⚠️ GMAIL_USER_EMAIL not configured - Gmail features disabled")
        
        working_calendars = [
            ("BG Calendar", GOOGLE_CALENDAR_ID, "calendar"),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID, "tasks")
        ]
        
        for name, calendar_id, calendar_type in working_calendars:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id, calendar_type))
        
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary", "calendar"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _, _ in accessible_calendars:
            print(f"   ✅ {name}")
            
    else:
        print("⚠️ Google Calendar credentials not found")
        
except Exception as e:
    print(f"❌ Google services setup error: {e}")
    calendar_service = None
    gmail_service = None
    accessible_calendars = []

# Memory and duplicate prevention systems
user_conversations = {}
processing_messages = set()
last_response_time = {}

print(f"👑 Starting {ASSISTANT_NAME} - {ASSISTANT_ROLE}...")

# ============================================================================
# CORE CALENDAR FUNCTIONS
# ============================================================================

def get_calendar_events(calendar_id, start_time, end_time, max_results=100):
    """Get events from a specific calendar"""
    if not calendar_service:
        return []
    
    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
        
    except Exception as e:
        print(f"❌ Error getting events from {calendar_id}: {e}")
        return []

def format_event(event, calendar_type="", user_timezone=None):
    """Format a single event with Toronto timezone"""
    if user_timezone is None:
        user_timezone = pytz.timezone('America/Toronto')
    
    start = event['start'].get('dateTime', event['start'].get('date'))
    title = event.get('summary', 'Untitled Event')
    
    if calendar_type == "tasks":
        title = f"✅ {title}"
    elif calendar_type == "calendar":
        title = f"📅 {title}"
    
    if 'T' in start:  # Has time
        try:
            utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = utc_time.astimezone(user_timezone)
            time_str = local_time.strftime('%H:%M')  # 24-hour format
            return f"• {time_str}: {title}"
        except Exception as e:
            print(f"❌ Error formatting event: {e}")
            return f"• {title}"
    else:  # All day event
        return f"• All Day: {title}"

def get_today_schedule():
    """Get today's schedule with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Today's Schedule:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps directly"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto.replace(hour=23, minute=59, second=59)
        
        today_utc = today_toronto.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, today_utc, tomorrow_utc)
            for event in events:
                formatted = format_event(event, calendar_type, toronto_tz)
                all_events.append((event, formatted, calendar_type, calendar_name))
        
        if not all_events:
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Today's Schedule:** No events found\n\n🎯 **Executive Opportunity:** Clear schedule across {calendar_list}"
        
        def get_event_time(event_tuple):
            event = event_tuple[0]
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                if 'T' in start:
                    utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    return utc_time.astimezone(toronto_tz)
                else:
                    return datetime.fromisoformat(start)
            except:
                return datetime.now(toronto_tz)
        
        all_events.sort(key=get_event_time)
        
        formatted_events = [event_tuple[1] for event_tuple in all_events]
        
        calendar_counts = {}
        for _, _, calendar_type, calendar_name in all_events:
            calendar_counts[calendar_name] = calendar_counts.get(calendar_name, 0) + 1
        
        header = f"📅 **Today's Executive Schedule:** {len(all_events)} events"
        
        if calendar_counts:
            breakdown = []
            for calendar_name, count in calendar_counts.items():
                breakdown.append(f"{count} {calendar_name}")
            header += f" ({', '.join(breakdown)})"
        
        return header + "\n\n" + "\n".join(formatted_events[:15])
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data"

def get_upcoming_events(days=7):
    """Get upcoming events with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return f"📅 **Upcoming {days} Days:** Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        start_toronto = datetime.now(toronto_tz)
        end_toronto = start_toronto + timedelta(days=days)
        
        start_utc = start_toronto.astimezone(pytz.UTC)
        end_utc = end_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, start_utc, end_utc)
            for event in events:
                all_events.append((event, calendar_type, calendar_name))
        
        if not all_events:
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Upcoming {days} Days:** No events found"
        
        events_by_date = defaultdict(list)
        
        for event, calendar_type, calendar_name in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            try:
                if 'T' in start:
                    utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    toronto_time = utc_time.astimezone(toronto_tz)
                    date_str = toronto_time.strftime('%a %m/%d')
                    formatted = format_event(event, calendar_type, toronto_tz)
                    events_by_date[date_str].append(formatted)
                else:
                    date_obj = datetime.fromisoformat(start)
                    date_str = date_obj.strftime('%a %m/%d')
                    formatted = format_event(event, calendar_type, toronto_tz)
                    events_by_date[date_str].append(formatted)
            except Exception as e:
                print(f"❌ Date parsing error: {e}")
                continue
        
        formatted = []
        total_events = len(all_events)
        
        for date, day_events in list(events_by_date.items())[:7]:
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:6])
        
        header = f"📅 **Upcoming {days} Days:** {total_events} total events"
        
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Morning briefing with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return "🌅 **Morning Briefing:** Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        today_schedule = get_today_schedule()
        
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto + timedelta(days=1)
        day_after_toronto = tomorrow_toronto + timedelta(days=1)
        
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        day_after_utc = day_after_toronto.astimezone(pytz.UTC)
        
        tomorrow_events = []
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, tomorrow_utc, day_after_utc)
            tomorrow_events.extend([(event, calendar_type, calendar_name) for event in events])
        
        if tomorrow_events:
            tomorrow_formatted = []
            for event, calendar_type, calendar_name in tomorrow_events[:4]:
                formatted = format_event(event, calendar_type, toronto_tz)
                tomorrow_formatted.append(formatted)
            tomorrow_preview = "📅 **Tomorrow Preview:**\n" + "\n".join(tomorrow_formatted)
        else:
            tomorrow_preview = "📅 **Tomorrow Preview:** Clear schedule - strategic planning day"
        
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        briefing = f"🌅 **Good Morning! Executive Briefing for {current_time}**\n\n{today_schedule}\n\n{tomorrow_preview}\n\n💼 **Executive Focus:** Prioritize high-impact activities"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        return "🌅 **Morning Briefing:** Error generating briefing"

def create_calendar_event(title, start_time, end_time, calendar_type="calendar", description=""):
    """Create a new calendar event in specified Google Calendar with concise confirmation"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Enhanced calendar selection logic
        target_calendar_id = None
        target_calendar_name = None
        
        print(f"🔍 Looking for calendar type: {calendar_type}")
        print(f"📅 Available calendars: {[(name, cal_type) for name, _, cal_type in accessible_calendars]}")
        
        # First, try exact calendar type match
        for name, cal_id, cal_type in accessible_calendars:
            if calendar_type == cal_type:
                target_calendar_id = cal_id
                target_calendar_name = name
                print(f"✅ Exact match found: {name} ({cal_type})")
                break
        
        # If no exact match, try keyword matching
        if not target_calendar_id:
            for name, cal_id, cal_type in accessible_calendars:
                if calendar_type.lower() in name.lower() or calendar_type.lower() in cal_type.lower():
                    target_calendar_id = cal_id
                    target_calendar_name = name
                    print(f"✅ Keyword match found: {name} ({cal_type})")
                    break
        
        # Last resort: use tasks calendar if available for task-related requests
        if not target_calendar_id and calendar_type == "tasks":
            for name, cal_id, cal_type in accessible_calendars:
                if "task" in name.lower() or cal_type == "tasks":
                    target_calendar_id = cal_id
                    target_calendar_name = name
                    print(f"✅ Task calendar found: {name} ({cal_type})")
                    break
        
        # Final fallback to primary calendar only if no specific calendar found
        if not target_calendar_id:
            for name, cal_id, cal_type in accessible_calendars:
                if "primary" in name.lower() or cal_id == "primary":
                    target_calendar_id = cal_id
                    target_calendar_name = name
                    print(f"⚠️ Using primary fallback: {name} ({cal_type})")
                    break
        
        # If still no calendar found, use first available
        if not target_calendar_id and accessible_calendars:
            target_calendar_id = accessible_calendars[0][1]
            target_calendar_name = accessible_calendars[0][0]
            print(f"⚠️ Using first available: {target_calendar_name}")
        
        if not target_calendar_id:
            return "❌ No suitable calendar found"
        
        print(f"🎯 Creating event in: {target_calendar_name} ({target_calendar_id})")
        
        # Parse times
        toronto_tz = pytz.timezone('America/Toronto')
        
        try:
            # Handle different time formats
            if "T" not in start_time:
                start_time = f"{start_time}T15:00:00"
            if "T" not in end_time:
                end_time = f"{end_time}T16:00:00"
                
            start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
            end_dt = datetime.fromisoformat(end_time.replace('Z', ''))
            
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
            if end_dt.tzinfo is None:
                end_dt = toronto_tz.localize(end_dt)
            
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
            
        except ValueError as e:
            return f"❌ Invalid time format: {e}"
        
        # Create event object
        event = {
            'summary': title,
            'start': {
                'dateTime': start_iso,
                'timeZone': 'America/Toronto',
            },
            'end': {
                'dateTime': end_iso,
                'timeZone': 'America/Toronto',
            },
            'description': description,
        }
        
        # Create the event
        created_event = calendar_service.events().insert(
            calendarId=target_calendar_id,
            body=event
        ).execute()
        
        # CONCISE CONFIRMATION with 24-hour time format
        display_start_dt = start_dt.astimezone(toronto_tz)
        display_end_dt = end_dt.astimezone(toronto_tz)
        
        # Format day and date
        day_date = display_start_dt.strftime('%A, %B %d, %Y')
        start_time_24h = display_start_dt.strftime('%H:%M')
        end_time_24h = display_end_dt.strftime('%H:%M')
        
        return f"✅ **{title}** created\n📅 {day_date}, {start_time_24h} - {end_time_24h}\n🗓️ {target_calendar_name}\n🔗 [View Event]({created_event.get('htmlLink', '#')})"
        
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
        return f"❌ Failed to create '{title}': {str(e)}"

def find_calendar_event(search_term, days_range=30):
    """Find calendar events matching a search term"""
    if not calendar_service or not accessible_calendars:
        return None, None, None
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        past_search = now - timedelta(days=7)  # Search past week
        future_search = now + timedelta(days=days_range)  # Search ahead
        
        # Search all accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, past_search, future_search, max_results=200)
            for event in events:
                event_title = event.get('summary', '').lower()
                if search_term.lower() in event_title:
                    return event, calendar_id, calendar_name
        
        return None, None, None
        
    except Exception as e:
        print(f"❌ Error finding event: {e}")
        return None, None, None

def update_calendar_event(event_search, new_title=None, new_start_time=None, new_end_time=None, new_description=None):
    """Update an existing calendar event"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Find the event
        found_event, found_calendar_id, found_calendar_name = find_calendar_event(event_search)
        
        if not found_event:
            return f"❌ '{event_search}' not found"
        
        # Update fields as needed
        updated_fields = []
        
        if new_title:
            found_event['summary'] = new_title
            updated_fields.append(f"Title → {new_title}")
        
        if new_start_time or new_end_time:
            toronto_tz = pytz.timezone('America/Toronto')
            
            if new_start_time:
                try:
                    if "T" not in new_start_time:
                        new_start_time = f"{new_start_time}T{found_event['start']['dateTime'].split('T')[1]}"
                    new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', ''))
                    if new_start_dt.tzinfo is None:
                        new_start_dt = toronto_tz.localize(new_start_dt)
                    found_event['start'] = {
                        'dateTime': new_start_dt.isoformat(),
                        'timeZone': 'America/Toronto',
                    }
                    updated_fields.append(f"Start → {new_start_dt.strftime('%m/%d %H:%M')}")
                except ValueError as e:
                    return f"❌ Invalid start time: {e}"
            
            if new_end_time:
                try:
                    if "T" not in new_end_time:
                        new_end_time = f"{new_end_time}T{found_event['end']['dateTime'].split('T')[1]}"
                    new_end_dt = datetime.fromisoformat(new_end_time.replace('Z', ''))
                    if new_end_dt.tzinfo is None:
                        new_end_dt = toronto_tz.localize(new_end_dt)
                    found_event['end'] = {
                        'dateTime': new_end_dt.isoformat(),
                        'timeZone': 'America/Toronto',
                    }
                    updated_fields.append(f"End → {new_end_dt.strftime('%m/%d %H:%M')}")
                except ValueError as e:
                    return f"❌ Invalid end time: {e}"
        
        if new_description is not None:
            found_event['description'] = new_description
            updated_fields.append("Description updated")
        
        # Update the event
        updated_event = calendar_service.events().update(
            calendarId=found_calendar_id,
            eventId=found_event['id'],
            body=found_event
        ).execute()
        
        # Concise confirmation with 24-hour time
        return f"✅ **{updated_event['summary']}** updated\n🔄 {', '.join(updated_fields)}\n🗓️ {found_calendar_name}\n🔗 [View Event]({updated_event.get('htmlLink', '#')})"
        
    except Exception as e:
        print(f"❌ Error updating event: {e}")
        return f"❌ Failed to update '{event_search}': {str(e)}"

def reschedule_event(event_search, new_start_time, new_end_time=None):
    """Reschedule an existing calendar event to new time"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Find the event
        found_event, found_calendar_id, found_calendar_name = find_calendar_event(event_search)
        
        if not found_event:
            return f"❌ '{event_search}' not found"
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Parse new start time
        try:
            if "T" not in new_start_time:
                original_time = found_event['start']['dateTime'].split('T')[1] if 'dateTime' in found_event['start'] else '15:00:00'
                new_start_time = f"{new_start_time}T{original_time}"
            
            new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', ''))
            if new_start_dt.tzinfo is None:
                new_start_dt = toronto_tz.localize(new_start_dt)
                
        except ValueError:
            return "❌ Invalid time format"
        
        # Calculate new end time
        if new_end_time:
            try:
                if "T" not in new_end_time:
                    original_time = found_event['end']['dateTime'].split('T')[1] if 'dateTime' in found_event['end'] else '16:00:00'
                    new_end_time = f"{new_end_time}T{original_time}"
                new_end_dt = datetime.fromisoformat(new_end_time.replace('Z', ''))
                if new_end_dt.tzinfo is None:
                    new_end_dt = toronto_tz.localize(new_end_dt)
            except ValueError:
                return "❌ Invalid end time format"
        else:
            # Calculate duration from original event
            original_start = datetime.fromisoformat(found_event['start']['dateTime'].replace('Z', '+00:00'))
            original_end = datetime.fromisoformat(found_event['end']['dateTime'].replace('Z', '+00:00'))
            duration = original_end - original_start
            new_end_dt = new_start_dt + duration
        
        # Update the event
        found_event['start'] = {
            'dateTime': new_start_dt.isoformat(),
            'timeZone': 'America/Toronto',
        }
        found_event['end'] = {
            'dateTime': new_end_dt.isoformat(),
            'timeZone': 'America/Toronto',
        }
        
        updated_event = calendar_service.events().update(
            calendarId=found_calendar_id,
            eventId=found_event['id'],
            body=found_event
        ).execute()
        
        # Concise confirmation with 24-hour time
        display_start_dt = new_start_dt.astimezone(toronto_tz)
        display_end_dt = new_end_dt.astimezone(toronto_tz)
        
        day_date = display_start_dt.strftime('%A, %B %d')
        start_time_24h = display_start_dt.strftime('%H:%M')
        end_time_24h = display_end_dt.strftime('%H:%M')
        
        return f"✅ **{updated_event['summary']}** rescheduled\n📅 {day_date}, {start_time_24h} - {end_time_24h}\n🗓️ {found_calendar_name}\n🔗 [View Event]({updated_event.get('htmlLink', '#')})"
        
    except Exception as e:
        print(f"❌ Error rescheduling event: {e}")
        return f"❌ Failed to reschedule '{event_search}': {str(e)}"

def move_task_between_calendars(task_search, target_calendar="tasks"):
    """Move tasks/events between different Google calendars"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Find the event
        found_event, found_calendar_id, found_calendar_name = find_calendar_event(task_search)
        
        if not found_event:
            return f"❌ '{task_search}' not found"
        
        # Find target calendar with enhanced logic
        target_calendar_id = None
        target_calendar_name = None
        
        # Try exact type match first
        for name, cal_id, cal_type in accessible_calendars:
            if target_calendar == cal_type:
                target_calendar_id = cal_id
                target_calendar_name = name
                break
        
        # Try keyword matching
        if not target_calendar_id:
            for name, cal_id, cal_type in accessible_calendars:
                if target_calendar.lower() in name.lower() or target_calendar.lower() in cal_type.lower():
                    target_calendar_id = cal_id
                    target_calendar_name = name
                    break
        
        if not target_calendar_id:
            available_types = [f"{name} ({cal_type})" for name, _, cal_type in accessible_calendars]
            return f"❌ '{target_calendar}' calendar not found\n📅 Available: {', '.join(available_types)}"
        
        if found_calendar_id == target_calendar_id:
            return f"📅 '{found_event['summary']}' already in {target_calendar_name}"
        
        # Create event copy for target calendar
        event_copy = {
            'summary': found_event.get('summary'),
            'description': found_event.get('description', ''),
            'start': found_event.get('start'),
            'end': found_event.get('end'),
            'location': found_event.get('location', ''),
        }
        
        # Remove read-only fields
        for field in ['id', 'htmlLink', 'iCalUID', 'created', 'updated', 'creator', 'organizer']:
            event_copy.pop(field, None)
        
        # Create in target calendar
        created_event = calendar_service.events().insert(
            calendarId=target_calendar_id,
            body=event_copy
        ).execute()
        
        # Delete from original calendar
        calendar_service.events().delete(
            calendarId=found_calendar_id,
            eventId=found_event['id']
        ).execute()
        
        # Concise confirmation
        return f"✅ **{found_event['summary']}** moved\n📍 {found_calendar_name} → {target_calendar_name}\n🔗 [View Event]({created_event.get('htmlLink', '#')})"
        
    except HttpError as e:
        return f"❌ Calendar error: {e.resp.status}"
    except Exception as e:
        print(f"❌ Error moving task: {e}")
        return f"❌ Failed to move '{task_search}': {str(e)}"

def delete_calendar_event(event_search):
    """Delete a calendar event"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Find the event
        found_event, found_calendar_id, found_calendar_name = find_calendar_event(event_search)
        
        if not found_event:
            return f"❌ '{event_search}' not found"
        
        # Store event details before deletion
        event_title = found_event.get('summary', 'Unknown Event')
        
        # Delete the event
        calendar_service.events().delete(
            calendarId=found_calendar_id,
            eventId=found_event['id']
        ).execute()
        
        # Concise confirmation
        return f"✅ **{event_title}** deleted from {found_calendar_name}"
        
    except Exception as e:
        print(f"❌ Error deleting event: {e}")
        return f"❌ Failed to delete '{event_search}': {str(e)}"

def find_free_time(duration_minutes=60, preferred_days=None, preferred_hours=None, days_ahead=7):
    """Find free time slots in the calendar"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Free Time Search:** Calendar integration not configured."
    
    try:
        if preferred_days is None:
            preferred_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        if preferred_hours is None:
            preferred_hours = list(range(9, 17))  # 9 AM to 5 PM
        
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        search_end = now + timedelta(days=days_ahead)
        
        # Get all existing events to find gaps
        all_busy_times = []
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, now, search_end)
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                
                if 'T' in start_str:  # DateTime event
                    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(toronto_tz)
                    end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00')).astimezone(toronto_tz)
                    all_busy_times.append((start_dt, end_dt))
        
        # Find available slots
        available_slots = []
        current_date = now.date()
        
        for day_offset in range(days_ahead):
            check_date = current_date + timedelta(days=day_offset)
            weekday = check_date.strftime('%A')
            
            if weekday not in preferred_days:
                continue
            
            for hour in preferred_hours:
                slot_start = datetime.combine(check_date, datetime.min.time().replace(hour=hour)).replace(tzinfo=toronto_tz)
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                # Skip past times
                if slot_start <= now:
                    continue
                
                # Check for conflicts
                has_conflict = False
                for busy_start, busy_end in all_busy_times:
                    if (slot_start < busy_end and slot_end > busy_start):
                        has_conflict = True
                        break
                
                if not has_conflict:
                    available_slots.append({
                        'start': slot_start,
                        'end': slot_end,
                        'date': check_date.strftime('%A, %B %d'),
                        'time': slot_start.strftime('%H:%M')  # 24-hour format
                    })
        
        if not available_slots:
            return f"❌ **No Available Slots:** No {duration_minutes}-minute slots found in the next {days_ahead} days.\n💡 **Suggestion:** Try reducing duration or expanding preferred hours."
        
        # Return top 5 slots with 24-hour time
        result = f"📅 **Available {duration_minutes}-minute slots:**\n\n"
        for i, slot in enumerate(available_slots[:5]):
            result += f"**{i+1}.** {slot['date']} at {slot['time']}\n"
        
        if len(available_slots) > 5:
            result += f"\n*...and {len(available_slots) - 5} more slots available*"
        
        return result
        
    except Exception as e:
        print(f"❌ Error finding free time: {e}")
        return f"❌ **Free Time Search Failed:** {str(e)}"

# ============================================================================
# GMAIL FUNCTIONS
# ============================================================================

import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def get_recent_emails(max_results=10, query=""):
    """Get recent emails from Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Build query for recent emails
        search_query = query if query else "in:inbox"
        
        # Get message IDs
        results = gmail_service.users().messages().list(
            userId='me',
            q=search_query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Recent Emails:** No emails found"
        
        formatted_emails = []
        
        for msg in messages[:max_results]:
            try:
                # Get full message
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                
                # Extract email details
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Parse date for better formatting
                try:
                    from dateutil import parser
                    parsed_date = parser.parse(date)
                    toronto_tz = pytz.timezone('America/Toronto')
                    local_date = parsed_date.astimezone(toronto_tz)
                    formatted_date = local_date.strftime('%m/%d %H:%M')
                except:
                    formatted_date = date[:16] if len(date) > 16 else date
                
                # Check if unread
                labels = message.get('labelIds', [])
                unread_indicator = "🔴" if 'UNREAD' in labels else "📧"
                
                # Format sender (extract name/email)
                if '<' in from_email:
                    sender = from_email.split('<')[0].strip().strip('"')
                    if not sender:
                        sender = from_email.split('<')[1].split('>')[0]
                else:
                    sender = from_email
                
                formatted_emails.append(f"{unread_indicator} **{subject[:50]}{'...' if len(subject) > 50 else ''}**\n   From: {sender[:30]}{'...' if len(sender) > 30 else ''} | {formatted_date}")
                
            except Exception as e:
                print(f"❌ Error processing email {msg['id']}: {e}")
                continue
        
        header = f"📧 **Recent Emails:** {len(formatted_emails)} messages"
        return header + "\n\n" + "\n\n".join(formatted_emails)
        
    except Exception as e:
        print(f"❌ Error getting emails: {e}")
        return f"📧 **Email Error:** {str(e)}"

def search_emails(query, max_results=10):
    """Search emails with specific query"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Search for emails
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Search Results:** No emails found for '{query}'"
        
        formatted_results = []
        
        for msg in messages[:max_results]:
            try:
                # Get message metadata
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
                
                # Parse date
                try:
                    from dateutil import parser
                    parsed_date = parser.parse(date)
                    toronto_tz = pytz.timezone('America/Toronto')
                    local_date = parsed_date.astimezone(toronto_tz)
                    formatted_date = local_date.strftime('%m/%d %H:%M')
                except:
                    formatted_date = date[:16] if len(date) > 16 else date
                
                # Format sender
                if '<' in from_email:
                    sender = from_email.split('<')[0].strip().strip('"')
                    if not sender:
                        sender = from_email.split('<')[1].split('>')[0]
                else:
                    sender = from_email
                
                formatted_results.append(f"📧 **{subject[:45]}{'...' if len(subject) > 45 else ''}**\n   {sender[:25]}{'...' if len(sender) > 25 else ''} | {formatted_date}")
                
            except Exception as e:
                print(f"❌ Error processing search result {msg['id']}: {e}")
                continue
        
        return f"📧 **Search: '{query}'** ({len(formatted_results)} results)\n\n" + "\n\n".join(formatted_results)
        
    except Exception as e:
        print(f"❌ Error searching emails: {e}")
        return f"📧 **Search Error:** {str(e)}"

def get_email_details(search_term):
    """Get detailed view of a specific email"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Search for the email
        query = f"subject:{search_term}" if search_term else "in:inbox"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Email Not Found:** No email matching '{search_term}'"
        
        # Get full message
        message = gmail_service.users().messages().get(
            userId='me',
            id=messages[0]['id'],
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
        
        # Extract body
        def extract_body(payload):
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
                    elif part['mimeType'] == 'text/html' and not body:
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                if payload['mimeType'] == 'text/plain':
                    data = payload['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            return body[:500] + "..." if len(body) > 500 else body
        
        body = extract_body(message['payload'])
        
        # Format date
        try:
            from dateutil import parser
            parsed_date = parser.parse(date)
            toronto_tz = pytz.timezone('America/Toronto')
            local_date = parsed_date.astimezone(toronto_tz)
            formatted_date = local_date.strftime('%A, %B %d, %Y at %H:%M')
        except:
            formatted_date = date
        
        response = f"""📧 **Email Details:**

**Subject:** {subject}
**From:** {from_email}
**To:** {to_email}
**Date:** {formatted_date}

**Message Preview:**
{body if body else "No content available"}"""
        
        return response
        
    except Exception as e:
        print(f"❌ Error getting email details: {e}")
        return f"📧 **Email Details Error:** {str(e)}"

def send_email(to_email, subject, body, cc_email=None, bcc_email=None):
    """Send an email via Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = subject
        message['From'] = gmail_user_email
        
        if cc_email:
            message['Cc'] = cc_email
        if bcc_email:
            message['Bcc'] = bcc_email
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send email
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        # Get message details for confirmation
        sent_details = gmail_service.users().messages().get(
            userId='me',
            id=sent_message['id'],
            format='metadata',
            metadataHeaders=['Message-ID', 'Date']
        ).execute()
        
        return f"✅ **Email Sent Successfully**\n📧 To: {to_email}\n📝 Subject: {subject}\n🕐 Sent at: {datetime.now(pytz.timezone('America/Toronto')).strftime('%H:%M')}"
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return f"❌ **Failed to send email:** {str(e)}"

def reply_to_email(search_term, reply_body):
    """Reply to an email"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Find the original email
        query = f"subject:{search_term}" if search_term else "in:inbox"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Original Email Not Found:** No email matching '{search_term}'"
        
        # Get original message
        original_message = gmail_service.users().messages().get(
            userId='me',
            id=messages[0]['id'],
            format='full'
        ).execute()
        
        headers = original_message['payload'].get('headers', [])
        
        # Extract original details
        original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        original_message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
        # Create reply
        reply_subject = f"Re: {original_subject}" if not original_subject.startswith('Re:') else original_subject
        
        message = MIMEMultipart()
        message['To'] = original_from
        message['Subject'] = reply_subject
        message['From'] = gmail_user_email
        message['In-Reply-To'] = original_message_id
        message['References'] = original_message_id
        
        # Add reply body
        message.attach(MIMEText(reply_body, 'plain'))
        
        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        sent_reply = gmail_service.users().messages().send(
            userId='me',
            body={
                'raw': raw_message,
                'threadId': original_message['threadId']
            }
        ).execute()
        
        return f"✅ **Reply Sent Successfully**\n📧 To: {original_from}\n📝 Subject: {reply_subject}\n🕐 Sent at: {datetime.now(pytz.timezone('America/Toronto')).strftime('%H:%M')}"
        
    except Exception as e:
        print(f"❌ Error sending reply: {e}")
        return f"❌ **Failed to send reply:** {str(e)}"

def mark_email_as_read(search_term):
    """Mark an email as read"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Find the email
        query = f"subject:{search_term} is:unread" if search_term else "is:unread"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Email Not Found:** No unread email matching '{search_term}'"
        
        # Mark as read by removing UNREAD label
        gmail_service.users().messages().modify(
            userId='me',
            id=messages[0]['id'],
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"✅ **Email marked as read:** {search_term}"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ **Failed to mark as read:** {str(e)}"

def archive_email(search_term):
    """Archive an email"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Find the email
        query = f"subject:{search_term} in:inbox" if search_term else "in:inbox"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Email Not Found:** No inbox email matching '{search_term}'"
        
        # Archive by removing INBOX label
        gmail_service.users().messages().modify(
            userId='me',
            id=messages[0]['id'],
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"✅ **Email archived:** {search_term}"
        
    except Exception as e:
        print(f"❌ Error archiving email: {e}")
        return f"❌ **Failed to archive:** {str(e)}"

def delete_email(search_term):
    """Delete an email (move to trash)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Find the email
        query = f"subject:{search_term}" if search_term else "in:inbox"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Email Not Found:** No email matching '{search_term}'"
        
        # Move to trash
        gmail_service.users().messages().trash(
            userId='me',
            id=messages[0]['id']
        ).execute()
        
        return f"✅ **Email moved to trash:** {search_term}"
        
    except Exception as e:
        print(f"❌ Error deleting email: {e}")
        return f"❌ **Failed to delete:** {str(e)}"

def get_unread_count():
    """Get count of unread emails"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread emails count
        results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread in:inbox',
            maxResults=1
        ).execute()
        
        # Get the estimated total count
        unread_count = results.get('resultSizeEstimate', 0)
        
        if unread_count == 0:
            return "📧 **Inbox Status:** All caught up! No unread emails"
        elif unread_count == 1:
            return "📧 **Inbox Status:** 1 unread email"
        else:
            return f"📧 **Inbox Status:** {unread_count} unread emails"
        
    except Exception as e:
        print(f"❌ Error getting unread count: {e}")
        return f"📧 **Inbox Status Error:** {str(e)}"

def get_inbox_summary():
    """Get a comprehensive inbox summary"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get recent emails
        recent_emails = get_recent_emails(5, "in:inbox")
        
        # Get unread count
        unread_status = get_unread_count()
        
        # Combine into summary
        summary = f"""📧 **Inbox Executive Summary**

{unread_status}

**Recent Emails:**
{recent_emails.split('📧 **Recent Emails:** 5 messages')[1] if '📧 **Recent Emails:** 5 messages' in recent_emails else recent_emails}"""
        
        return summary
        
    except Exception as e:
        print(f"❌ Error getting inbox summary: {e}")
        return f"📧 **Inbox Summary Error:** {str(e)}"

# ============================================================================
# ENHANCED PLANNING SEARCH
# ============================================================================

async def planning_search_enhanced(query, focus_area="general", num_results=3):
    """Enhanced planning and productivity research with comprehensive error handling"""
    if not BRAVE_API_KEY:
        return "🔍 Planning research requires Brave Search API configuration", []
    
    try:
        planning_query = f"{query} {focus_area} productivity executive planning time management 2025"
        
        headers = {
            'X-Subscription-Token': BRAVE_API_KEY,
            'Accept': 'application/json'
        }
        
        params = {
            'q': planning_query,
            'count': num_results,
            'country': 'US',
            'search_lang': 'en',
            'ui_lang': 'en',
            'safesearch': 'moderate'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.search.brave.com/res/v1/web/search', 
                                   headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return "🔍 No planning research results found for this query", []
                    
                    formatted_results = []
                    sources = []
                    
                    for i, result in enumerate(results[:num_results]):
                        title = result.get('title', 'No title')
                        snippet = result.get('description', 'No description')
                        url = result.get('url', '')
                        
                        domain = url.split('/')[2] if len(url.split('/')) > 2 else 'Unknown'
                        
                        formatted_results.append(f"**{i+1}. {title}**\n{snippet}")
                        sources.append({
                            'number': i+1,
                            'title': title,
                            'url': url,
                            'domain': domain
                        })
                    
                    return "\n\n".join(formatted_results), sources
                else:
                    return f"🔍 Planning search error: HTTP {response.status}", []
                    
    except asyncio.TimeoutError:
        return "🔍 Planning search timed out", []
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Planning search error: Please try again", []

# ============================================================================
# ENHANCED FUNCTION HANDLING
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with complete calendar management"""
    
    if not run or not hasattr(run, 'required_action') or not run.required_action:
        return
        
    if not hasattr(run.required_action, 'submit_tool_outputs') or not run.required_action.submit_tool_outputs:
        return
    
    if not hasattr(run.required_action.submit_tool_outputs, 'tool_calls') or not run.required_action.submit_tool_outputs.tool_calls:
        return
    
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = getattr(tool_call.function, 'name', 'unknown')
        
        try:
            arguments_str = getattr(tool_call.function, 'arguments', '{}')
            arguments = json.loads(arguments_str) if arguments_str else {}
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"❌ Error parsing function arguments: {e}")
            arguments = {}
        
        print(f"👑 Rose Function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # CALENDAR VIEWING FUNCTIONS
            if function_name == "get_today_schedule":
                output = get_today_schedule()
                    
            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)
                
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()
                
            elif function_name == "find_free_time":
                duration_minutes = arguments.get('duration_minutes', 60)
                preferred_days = arguments.get('preferred_days', None)
                preferred_hours = arguments.get('preferred_hours', None)
                days_ahead = arguments.get('days_ahead', 7)
                output = find_free_time(duration_minutes, preferred_days, preferred_hours, days_ahead)
            
            # CALENDAR MODIFICATION FUNCTIONS
            elif function_name == "create_calendar_event":
                title = arguments.get('title', '')
                start_time = arguments.get('start_time', '')
                end_time = arguments.get('end_time', '')
                calendar_type = arguments.get('calendar_type', 'calendar')
                description = arguments.get('description', '')
                
                if title and start_time and end_time:
                    output = create_calendar_event(title, start_time, end_time, calendar_type, description)
                else:
                    output = "❌ Missing required parameters: title, start_time, end_time"
                    
            elif function_name == "update_calendar_event":
                event_search = arguments.get('event_search', '')
                new_title = arguments.get('new_title', None)
                new_start_time = arguments.get('new_start_time', None)
                new_end_time = arguments.get('new_end_time', None)
                new_description = arguments.get('new_description', None)
                
                if event_search:
                    output = update_calendar_event(event_search, new_title, new_start_time, new_end_time, new_description)
                else:
                    output = "❌ Missing required parameter: event_search"
                    
            elif function_name == "reschedule_event":
                event_search = arguments.get('event_search', '')
                new_start_time = arguments.get('new_start_time', '')
                new_end_time = arguments.get('new_end_time', None)
                
                if event_search and new_start_time:
                    output = reschedule_event(event_search, new_start_time, new_end_time)
                else:
                    output = "❌ Missing required parameters: event_search, new_start_time"
                    
            elif function_name == "move_task_between_calendars":
                task_search = arguments.get('task_search', '')
                target_calendar = arguments.get('target_calendar', 'tasks')
                
                if task_search:
                    output = move_task_between_calendars(task_search, target_calendar)
                else:
                    output = "❌ Missing required parameter: task_search"
                    
            elif function_name == "delete_calendar_event":
                event_search = arguments.get('event_search', '')
                
                if event_search:
                    output = delete_calendar_event(event_search)
                else:
                    output = "❌ Missing required parameter: event_search"
            
            # PLANNING RESEARCH FUNCTIONS
            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus = arguments.get('focus', 'general')
                num_results = arguments.get('num_results', 3)
                
                if query:
                    search_results, sources = await planning_search_enhanced(query, focus, num_results)
                    output = f"📊 **Planning Research:** {query}\n\n{search_results}"
                    
                    if sources:
                        output += "\n\n📚 **Sources:**\n"
                        for source in sources:
                            output += f"({source['number']}) {source['title']} - {source['domain']}\n"
                else:
                    output = "🔍 No planning research query provided"
                
            # GMAIL FUNCTIONS
            elif function_name == "get_recent_emails":
                max_results = arguments.get('max_results', 10)
                query = arguments.get('query', '')
                output = get_recent_emails(max_results, query)
                
            elif function_name == "search_emails":
                query = arguments.get('query', '')
                max_results = arguments.get('max_results', 10)
                
                if query:
                    output = search_emails(query, max_results)
                else:
                    output = "❌ Missing required parameter: query"
                    
            elif function_name == "get_email_details":
                search_term = arguments.get('search_term', '')
                
                if search_term:
                    output = get_email_details(search_term)
                else:
                    output = "❌ Missing required parameter: search_term"
                    
            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                cc_email = arguments.get('cc_email', None)
                bcc_email = arguments.get('bcc_email', None)
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body, cc_email, bcc_email)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"
                    
            elif function_name == "reply_to_email":
                search_term = arguments.get('search_term', '')
                reply_body = arguments.get('reply_body', '')
                
                if search_term and reply_body:
                    output = reply_to_email(search_term, reply_body)
                else:
                    output = "❌ Missing required parameters: search_term, reply_body"
                    
            elif function_name == "mark_email_as_read":
                search_term = arguments.get('search_term', '')
                
                if search_term:
                    output = mark_email_as_read(search_term)
                else:
                    output = "❌ Missing required parameter: search_term"
                    
            elif function_name == "archive_email":
                search_term = arguments.get('search_term', '')
                
                if search_term:
                    output = archive_email(search_term)
                else:
                    output = "❌ Missing required parameter: search_term"
                    
            elif function_name == "delete_email":
                search_term = arguments.get('search_term', '')
                
                if search_term:
                    output = delete_email(search_term)
                else:
                    output = "❌ Missing required parameter: search_term"
                    
            elif function_name == "get_unread_count":
                output = get_unread_count()
                
            elif function_name == "get_inbox_summary":
                output = get_inbox_summary()
                
            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Keep within reasonable limits
        })
    
    # Submit tool outputs
    try:
        if tool_outputs:
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            print(f"✅ Submitted {len(tool_outputs)} tool outputs successfully")
    except Exception as e:
        print(f"❌ Error submitting tool outputs: {e}")

# ============================================================================
# MAIN CONVERSATION HANDLER
# ============================================================================

def format_calendar_response_simple(response_text):
    """Simplify calendar responses by removing Strategic Analysis and Action Items"""
    import re
    
    # Check if this is a calendar-related response
    calendar_keywords = ["calendar", "meeting", "event", "scheduled", "appointment", "briefing"]
    is_calendar_response = any(keyword in response_text.lower() for keyword in calendar_keywords)
    
    if not is_calendar_response:
        return response_text  # Return unchanged for non-calendar responses
    
    # Extract Executive Summary
    executive_summary = ""
    summary_match = re.search(r'👑\s*\*\*Executive Summary:\*\*\s*([^👑📊🎯📅💼🗓️]*)', response_text, re.DOTALL)
    if summary_match:
        executive_summary = summary_match.group(1).strip()
    
    # Extract Meeting Details section (look for the original format)
    meeting_details = ""
    
    # Look for Meeting Details section with Google Calendar link
    meeting_details_match = re.search(r'💼\s*\*\*Meeting Details:\*\*\s*(.*?)(?=🔗|$)', response_text, re.DOTALL)
    if meeting_details_match:
        meeting_details = meeting_details_match.group(1).strip()
    
    # Look for the Google Calendar link section
    calendar_link = ""
    link_match = re.search(r'🔗\s*View Event.*?Google Calendar.*?(?:\n.*?)*', response_text, re.DOTALL)
    if link_match:
        calendar_link = link_match.group(0).strip()
    
    # If no Meeting Details found, try to extract from other sections
    if not meeting_details:
        # Try Calendar Coordination section
        coord_match = re.search(r'📅\s*\*\*Calendar Coordination:\*\*\s*([^👑📊🎯📅💼🗓️]*)', response_text, re.DOTALL)
        if coord_match:
            meeting_details = coord_match.group(1).strip()
        
        # If still nothing, extract basic meeting info
        if not meeting_details:
            detail_lines = []
            for line in response_text.split('\n'):
                if any(word in line.lower() for word in ['title:', 'date & time:', 'location:', 'calendar:', 'description:']):
                    detail_lines.append(f"• {line.strip()}")
            meeting_details = "\n".join(detail_lines) if detail_lines else "Meeting details confirmed"
    
    # Build the response with Meeting Details header
    simplified_response = f"""👑 **Executive Summary:**
{executive_summary}

💼 **Meeting Details:**
{meeting_details}"""
    
    # Add the calendar link if found
    if calendar_link:
        simplified_response += f"\n\n{calendar_link}"
    
    return simplified_response.strip()

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with fixed API calls"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Create user thread if needed
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"👑 Created executive thread for user {user_id}")
        
        thread_id = user_conversations[user_id]
        
        # Clean message
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
        
        # Get current date context for Rose
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        today_formatted = now.strftime('%A, %B %d, %Y')
        today_date = now.strftime('%Y-%m-%d')
        tomorrow = now + timedelta(days=1)
        tomorrow_formatted = tomorrow.strftime('%A, %B %d, %Y') 
        tomorrow_date = tomorrow.strftime('%Y-%m-%d')

        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

CURRENT DATE & TIME CONTEXT:
- TODAY: {today_formatted} ({today_date})
- TOMORROW: {tomorrow_formatted} ({tomorrow_date})
- TIMEZONE: America/Toronto

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- AVAILABLE CALENDARS: {[name for name, _, _ in accessible_calendars]}
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- When user says "tomorrow" use {tomorrow_date} ({tomorrow_formatted})
- When user says "today" use {today_date} ({today_formatted})
- All times are in Toronto timezone (America/Toronto)
- Use 24-hour time format (14:30, not 2:30 PM)"""
        
        try:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=enhanced_message
            )
        except Exception as e:
            if "while a run" in str(e) and "is active" in str(e):
                print("⏳ Waiting for previous executive analysis to complete...")
                await asyncio.sleep(3)
                try:
                    client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=enhanced_message
                    )
                except Exception as e2:
                    print(f"❌ Still can't add message: {e2}")
                    return "👑 Executive office is busy. Please try again in a moment."
            else:
                print(f"❌ Message creation error: {e}")
                return "❌ Error creating executive message. Please try again."
        
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID,
                instructions="""You are Rose Ashcombe, executive assistant specialist with Google Calendar integration.

EXECUTIVE APPROACH:
- Use executive calendar functions to provide comprehensive scheduling insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines

FORMATTING: Use professional executive formatting with strategic headers (👑 📊 📅 🎯 💼) and provide organized, action-oriented guidance.

STRUCTURE:
👑 **Executive Summary:** [strategic overview with calendar insights]
📊 **Strategic Analysis:** [research-backed recommendations]
🎯 **Action Items:** [specific next steps with timing]

Keep core content focused and always provide strategic context with calendar coordination."""
            )
        except Exception as e:
            print(f"❌ Run creation error: {e}")
            return "❌ Error starting executive analysis. Please try again."
        
        print(f"👑 Rose run created: {run.id}")
        
        for attempt in range(20):
            try:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            except Exception as e:
                print(f"❌ Error retrieving run status: {e}")
                await asyncio.sleep(2)
                continue
            
            print(f"🔄 Status: {run_status.status} (attempt {attempt + 1})")
            
            if run_status.status == "completed":
                break
            elif run_status.status == "requires_action":
                await handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ["failed", "cancelled", "expired"]:
                print(f"❌ Run {run_status.status}")
                return "❌ Executive analysis interrupted. Please try again."
            
            await asyncio.sleep(2)
        else:
            print("⏱️ Run timed out")
            return "⏱️ Executive office is busy. Please try again in a moment."
        
        try:
            messages = client.beta.threads.messages.list(thread_id=thread_id, limit=5)
            for msg in messages.data:
                if msg.role == "assistant":
                    response = msg.content[0].text.value
                    
                    # NEW: Apply calendar response simplification
                    response = format_calendar_response_simple(response)
                    
                    return format_for_discord_rose(response)
        except Exception as e:
            print(f"❌ Error retrieving messages: {e}")
            return "❌ Error retrieving executive guidance. Please try again."
        
        return "👑 Executive analysis unclear. Please try again with a different approach."
        
    except Exception as e:
        print(f"❌ Rose error: {e}")
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return "❌ Something went wrong with executive strategy. Please try again!"

def format_for_discord_rose(response):
    """Format response for Discord with error handling"""
    try:
        if not response or not isinstance(response, str):
            return "👑 Executive strategy processing. Please try again."
        
        response = response.replace('\n\n\n\n', '\n\n')
        response = response.replace('\n\n\n', '\n\n')
        
        if len(response) > 1900:
            response = response[:1900] + "\n\n👑 *(Executive insights continue)*"
        
        return response.strip()
        
    except Exception as e:
        print(f"❌ Discord formatting error: {e}")
        return "👑 Executive message needs refinement. Please try again."

# ============================================================================
# ENHANCED MESSAGE HANDLING
# ============================================================================

async def send_long_message(original_message, response):
    """Send response with length handling and error recovery"""
    try:
        if len(response) <= 2000:
            await original_message.reply(response)
        else:
            chunks = []
            current_chunk = ""
            
            for line in response.split('\n'):
                if len(current_chunk + line + '\n') > 1900:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await original_message.reply(chunk)
                else:
                    await original_message.channel.send(chunk)
                    
    except discord.HTTPException as e:
        print(f"❌ Discord HTTP error: {e}")
        try:
            await original_message.reply("👑 Executive guidance too complex for Discord. Please try a more specific request.")
        except:
            pass
    except Exception as e:
        print(f"❌ Message sending error: {e}")

# ============================================================================
# DISCORD BOT EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup with comprehensive initialization"""
    try:
        print(f"✅ {ASSISTANT_NAME} has awakened!")
        print(f"🤖 Connected as: {bot.user.name} (ID: {bot.user.id})")
        print(f"🎯 Role: {ASSISTANT_ROLE}")
        print(f"📅 Calendar Status: {len(accessible_calendars)} accessible calendars")
        print(f"🔍 Research: {'Enabled' if BRAVE_API_KEY else 'Disabled'}")
        print(f"🏢 Allowed channels: {', '.join(ALLOWED_CHANNELS)}")
        
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📅 Executive Calendar & Task Management"
            )
        )
        print("👑 Rose is ready for complete executive assistance!")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_message(message):
    """Enhanced message handling following team patterns"""
    try:
        if message.author == bot.user:
            return
        
        await bot.process_commands(message)
        
        channel_name = message.channel.name.lower() if hasattr(message.channel, 'name') else 'dm'
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_allowed_channel = any(allowed in channel_name for allowed in ALLOWED_CHANNELS)
        
        if not (is_dm or is_allowed_channel):
            return

        if bot.user.mentioned_in(message) or is_dm:
            
            message_key = f"{message.author.id}_{message.content[:50]}"
            current_time = time.time()
            
            if message_key in processing_messages:
                return
            
            if message.author.id in last_response_time:
                if current_time - last_response_time[message.author.id] < 5:
                    return
            
            processing_messages.add(message_key)
            last_response_time[message.author.id] = current_time
            
            try:
                async with message.channel.typing():
                    response = await get_rose_response(message.content, message.author.id)
                    await send_long_message(message, response)
            except Exception as e:
                print(f"❌ Message error: {e}")
                print(f"📋 Message traceback: {traceback.format_exc()}")
                try:
                    await message.reply("❌ Something went wrong with executive consultation. Please try again!")
                except:
                    pass
            finally:
                processing_messages.discard(message_key)
                    
    except Exception as e:
        print(f"❌ Message event error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")

# ============================================================================
# STANDARDIZED COMMANDS
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Executive response time: {latency}ms")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='help')
async def help_command(ctx):
    """Enhanced help command"""
    try:
        help_text = f"""👑 **{ASSISTANT_NAME} - Executive Assistant Commands**

**📅 Calendar & Scheduling:**
• `!today` - Today's executive schedule
• `!upcoming [days]` - Upcoming events (default 7 days)
• `!briefing` / `!daily` / `!morning` - Morning executive briefing
• `!calendar` - Quick calendar overview with AI insights
• `!schedule [timeframe]` - Flexible schedule view
• `!agenda` - Comprehensive executive agenda overview
• `!overview` - Complete executive overview

**📧 Gmail & Email:**
• `!inbox` - Recent inbox summary
• `!emails [count]` - Recent emails (default 10)
• `!unread` - Count of unread emails
• `!search <query>` - Search emails

**🔍 Planning & Research:**
• `!research <query>` - Strategic planning research
• `!planning <topic>` - Productivity insights

**💼 Executive Functions:**
• `!status` - System and calendar status
• `!ping` - Test connectivity
• `!help` - This command menu

**📱 Usage:**
• Mention @{bot.user.name if bot.user else 'Rose'} in any message
• Available in: {', '.join(ALLOWED_CHANNELS)}

**💡 Example Commands:**
• `!briefing` - Get comprehensive morning briefing
• `!today` - See today's complete schedule
• `!inbox` - Check recent emails and unread count
• `!overview` - Complete executive overview
• `@Rose send an email to john@example.com about meeting`
• `@Rose search emails from yesterday`
"""
        
        await ctx.send(help_text)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Help system needs calibration. Please try again.")

@bot.command(name='status')
async def status_command(ctx):
    """Executive system status with comprehensive diagnostics"""
    try:
        calendar_status = "❌ No calendars accessible"
        if accessible_calendars:
            calendar_names = [name for name, _, _ in accessible_calendars]
            calendar_status = f"✅ {len(accessible_calendars)} calendars: {', '.join(calendar_names)}"
        
        research_status = "✅ Enabled" if BRAVE_API_KEY else "❌ Disabled"
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        
        sa_info = "Not configured"
        if service_account_email:
            sa_info = f"✅ {service_account_email}"
        
        status_text = f"""👑 **{ASSISTANT_NAME} Executive Status**

**🤖 Core Systems:**
• Discord: ✅ Connected as {bot.user.name if bot.user else 'Unknown'}
• OpenAI Assistant: {assistant_status}
• Service Account: {sa_info}

**📅 Calendar Integration:**
• Status: {calendar_status}
• Timezone: 🇨🇦 Toronto (America/Toronto)

**🔍 Planning Research:**
• Brave Search API: {research_status}

**💼 Executive Features:**
• Active conversations: {len(user_conversations)}
• Channels: {', '.join(ALLOWED_CHANNELS)}

**⚡ Performance:**
• Uptime: Ready for executive assistance
• Memory: {len(processing_messages)} processing"""
        
        await ctx.send(status_text)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Status diagnostics experiencing issues. Please try again.")

@bot.command(name='today')
async def today_command(ctx):
    """Today's executive schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await ctx.send(schedule)
    except Exception as e:
        print(f"❌ Today command error: {e}")
        await ctx.send("👑 Today's schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await ctx.send(events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("👑 Upcoming events unavailable. Please try again.")

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await ctx.send(briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("👑 Executive briefing unavailable. Please try again.")

@bot.command(name='calendar')
async def calendar_command(ctx):
    """Quick calendar overview command"""
    try:
        async with ctx.typing():
            user_id = str(ctx.author.id)
            calendar_query = "what's on my calendar today and upcoming strategic overview"
            response = await get_rose_response(calendar_query, user_id)
            await send_long_message(ctx.message, response)
    except Exception as e:
        print(f"❌ Calendar command error: {e}")
        await ctx.send("👑 Calendar overview unavailable. Please try again.")

@bot.command(name='schedule')
async def schedule_command(ctx, *, timeframe: str = "today"):
    """Flexible schedule command"""
    try:
        async with ctx.typing():
            timeframe_lower = timeframe.lower()
            
            if any(word in timeframe_lower for word in ["today", "now", "current"]):
                response = get_today_schedule()
            elif any(word in timeframe_lower for word in ["tomorrow", "next"]):
                response = get_upcoming_events(1)
            elif any(word in timeframe_lower for word in ["week", "7"]):
                response = get_upcoming_events(7)
            elif any(word in timeframe_lower for word in ["month", "30"]):
                response = get_upcoming_events(30)
            elif timeframe_lower.isdigit():
                days = int(timeframe_lower)
                days = max(1, min(days, 30))
                response = get_upcoming_events(days)
            else:
                response = get_today_schedule()
            
            await ctx.send(response)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("👑 Schedule view unavailable. Please try again.")

@bot.command(name='agenda')
async def agenda_command(ctx):
    """Executive agenda command"""
    try:
        async with ctx.typing():
            today_schedule = get_today_schedule()
            tomorrow_events = get_upcoming_events(1)
            
            agenda = f"📋 **Executive Agenda Overview**\n\n{today_schedule}\n\n**Tomorrow:**\n{tomorrow_events}"
            
            if len(agenda) > 1900:
                agenda = agenda[:1900] + "\n\n👑 *Use `!today` and `!upcoming` for detailed views*"
            
            await ctx.send(agenda)
    except Exception as e:
        print(f"❌ Agenda command error: {e}")
        await ctx.send("👑 Executive agenda unavailable. Please try again.")

@bot.command(name='daily')
async def daily_command(ctx):
    """Daily executive briefing - alias for briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await ctx.send(briefing)
    except Exception as e:
        print(f"❌ Daily briefing command error: {e}")
        await ctx.send("👑 Daily executive briefing unavailable. Please try again.")

@bot.command(name='morning')
async def morning_command(ctx):
    """Morning briefing command - alias for briefing"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await ctx.send(briefing)
    except Exception as e:
        print(f"❌ Morning briefing command error: {e}")
        await ctx.send("👑 Morning executive briefing unavailable. Please try again.")

@bot.command(name='overview')
async def overview_command(ctx):
    """Executive overview command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            upcoming = get_upcoming_events(3)
            
            overview = f"{briefing}\n\n📋 **3-Day Executive Outlook:**\n{upcoming}"
            
            if len(overview) > 1900:
                await ctx.send(briefing)
                await ctx.send(f"📋 **3-Day Executive Outlook:**\n{upcoming}")
            else:
                await ctx.send(overview)
                
    except Exception as e:
        print(f"❌ Overview command error: {e}")
        await ctx.send("👑 Executive overview unavailable. Please try again.")

@bot.command(name='research')
async def research_command(ctx, *, query: str = None):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("👑 **Executive Research Usage:** `!research <your planning query>`\n\nExamples:\n• `!research time management strategies`\n• `!research productivity systems for executives`")
            return
        
        async with ctx.typing():
            results, sources = await planning_search_enhanced(query, "executive planning", 3)
            
            response = f"📊 **Executive Research:** {query}\n\n{results}"
            
            if sources:
                response += "\n\n📚 **Strategic Sources:**\n"
                for source in sources:
                    response += f"({source['number']}) {source['title']} - {source['domain']}\n"
            
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Research command error: {e}")
        await ctx.send("👑 Executive research unavailable. Please try again.")

@bot.command(name='planning')
async def planning_command(ctx, *, topic: str = None):
    """Quick planning insights command"""
    try:
        if not topic:
            await ctx.send("👑 **Executive Planning Usage:** `!planning <planning topic>`\n\nExamples:\n• `!planning quarterly review`\n• `!planning meeting preparation`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            planning_query = f"executive planning insights for {topic} productivity optimization"
            response = await get_rose_response(planning_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Planning command error: {e}")
        await ctx.send("👑 Executive planning insights unavailable. Please try again.")

@bot.command(name='inbox')
async def inbox_command(ctx):
    """Get inbox summary"""
    try:
        async with ctx.typing():
            summary = get_inbox_summary()
            await ctx.send(summary)
    except Exception as e:
        print(f"❌ Inbox command error: {e}")
        await ctx.send("📧 Inbox summary unavailable. Please try again.")

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 25))  # Limit between 1-25
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx):
    """Get unread email count"""
    try:
        async with ctx.typing():
            unread_status = get_unread_count()
            await ctx.send(unread_status)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread count unavailable. Please try again.")

@bot.command(name='search')
async def search_command(ctx, *, query: str = None):
    """Search emails"""
    try:
        if not query:
            await ctx.send("📧 **Email Search Usage:** `!search <search query>`\n\nExamples:\n• `!search from:john@example.com`\n• `!search subject:meeting`\n• `!search yesterday`")
            return
        
        async with ctx.typing():
            search_results = search_emails(query, 10)
            await send_long_message(ctx.message, search_results)
    except Exception as e:
        print(f"❌ Search command error: {e}")
        await ctx.send("📧 Email search unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling for all commands"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required information. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `!help` for command usage.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"👑 Executive office is busy. Please wait {error.retry_after:.1f} seconds.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print(f"🚀 Launching {ASSISTANT_NAME}...")
        print(f"📅 Google Calendar API: {bool(accessible_calendars)} calendars accessible")
        print(f"🔍 Planning Research: {bool(BRAVE_API_KEY)}")
        print(f"🇨🇦 Timezone: Toronto (America/Toronto)")
        print("🎯 Starting Discord bot...")
        
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Rose shutdown requested")
    except Exception as e:
        print(f"❌ Critical error starting Rose: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
    finally:
        print("👑 Rose Ashcombe shutting down gracefully...")