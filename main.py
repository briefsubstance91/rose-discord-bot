#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (COMPLETE ENHANCED VERSION)
Executive Assistant with Full Google Calendar API Integration & Advanced Task Management
ENHANCED: Complete calendar management, task moving, bulk operations, smart scheduling
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

# Google Calendar integration - Enhanced with full API access
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')  # Primary BG Calendar
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')  # BG Tasks

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

# Discord setup with error handling
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
except Exception as e:
    print(f"❌ CRITICAL: Discord bot initialization failed: {e}")
    exit(1)

# OpenAI setup with error handling
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"❌ CRITICAL: OpenAI client initialization failed: {e}")
    exit(1)

# Enhanced Google Calendar setup with full API access
calendar_service = None
accessible_calendars = []
service_account_email = None

def test_calendar_access(calendar_id, calendar_name):
    """Test calendar access with comprehensive error handling"""
    if not calendar_service or not calendar_id:
        return False
    
    try:
        # Test calendar metadata
        calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ {calendar_name} accessible")
        
        # Test event access
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
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        
        print(f"❌ {calendar_name} HTTP Error {error_code}: {error_details}")
        
        if error_code == 404:
            print(f"💡 {calendar_name}: Calendar not found - check ID format")
        elif error_code == 403:
            print(f"💡 {calendar_name}: Permission denied - share calendar with service account")
        elif error_code == 400:
            print(f"💡 {calendar_name}: Bad request - malformed calendar ID")
        
        return False
        
    except Exception as e:
        print(f"❌ {calendar_name} error: {e}")
        return False

# Initialize Google Calendar service with enhanced capabilities
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized with full API access")
        
        # Get service account email
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account: {service_account_email}")
        
        # Test configured calendars
        working_calendars = [
            ("BG Calendar", GOOGLE_CALENDAR_ID, "calendar"),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID, "tasks")
        ]
        
        for name, calendar_id, calendar_type in working_calendars:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id, calendar_type))
        
        # Add primary as fallback
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
    print(f"❌ Google Calendar setup error: {e}")
    calendar_service = None
    accessible_calendars = []

# Memory and duplicate prevention systems - following team patterns
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
    
    # Calendar indicators
    if calendar_type == "tasks":
        title = f"✅ {title}"
    elif calendar_type == "calendar":
        title = f"📅 {title}"
    
    if 'T' in start:  # Has time
        try:
            utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = utc_time.astimezone(user_timezone)
            time_str = local_time.strftime('%I:%M %p')
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
        
        # Get today in Toronto timezone
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto.replace(hour=23, minute=59, second=59)
        
        # Convert to UTC for Google Calendar API
        today_utc = today_toronto.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, today_utc, tomorrow_utc)
            for event in events:
                formatted = format_event(event, calendar_type, toronto_tz)
                all_events.append((event, formatted, calendar_type, calendar_name))
        
        if not all_events:
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Today's Schedule:** No events found\n\n🎯 **Executive Opportunity:** Clear schedule across {calendar_list} - perfect for strategic planning"
        
        # Sort events by start time
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
        
        # Format response
        formatted_events = [event_tuple[1] for event_tuple in all_events]
        
        # Count by calendar
        calendar_counts = {}
        for _, _, calendar_type, calendar_name in all_events:
            calendar_counts[calendar_name] = calendar_counts.get(calendar_name, 0) + 1
        
        header = f"📅 **Today's Executive Schedule:** {len(all_events)} events"
        
        # Add breakdown by calendar
        if calendar_counts:
            breakdown = []
            for calendar_name, count in calendar_counts.items():
                breakdown.append(f"{count} {calendar_name}")
            header += f" ({', '.join(breakdown)})"
        
        return header + "\n\n" + "\n".join(formatted_events[:15])
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data\n\n🎯 **Backup Plan:** Check your calendar apps directly"

def get_upcoming_events(days=7):
    """Get upcoming events with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return f"📅 **Upcoming {days} Days:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get date range
        start_toronto = datetime.now(toronto_tz)
        end_toronto = start_toronto + timedelta(days=days)
        
        start_utc = start_toronto.astimezone(pytz.UTC)
        end_utc = end_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, start_utc, end_utc)
            for event in events:
                all_events.append((event, calendar_type, calendar_name))
        
        if not all_events:
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Upcoming {days} Days:** No events found\n\n🎯 **Strategic Opportunity:** Clear schedule across {calendar_list}"
        
        # Group by date
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
        
        # Format response
        formatted = []
        total_events = len(all_events)
        
        # Count by calendar
        calendar_counts = {}
        for _, calendar_type, calendar_name in all_events:
            calendar_counts[calendar_name] = calendar_counts.get(calendar_name, 0) + 1
        
        for date, day_events in list(events_by_date.items())[:7]:
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:6])
        
        header = f"📅 **Upcoming {days} Days:** {total_events} total events"
        
        # Add breakdown by calendar
        if calendar_counts:
            breakdown = []
            for calendar_name, count in calendar_counts.items():
                breakdown.append(f"{count} {calendar_name}")
            header += f" ({', '.join(breakdown)})"
        
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Morning briefing with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return "🌅 **Morning Briefing:** Calendar integration not available\n\n📋 **Manual Planning:** Review your calendar apps"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today's schedule
        today_schedule = get_today_schedule()
        
        # Get tomorrow's preview
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto + timedelta(days=1)
        day_after_toronto = tomorrow_toronto + timedelta(days=1)
        
        # Convert to UTC
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        day_after_utc = day_after_toronto.astimezone(pytz.UTC)
        
        tomorrow_events = []
        
        # Get tomorrow's events from accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, tomorrow_utc, day_after_utc)
            tomorrow_events.extend([(event, calendar_type, calendar_name) for event in events])
        
        # Format tomorrow's preview
        if tomorrow_events:
            tomorrow_formatted = []
            for event, calendar_type, calendar_name in tomorrow_events[:4]:
                formatted = format_event(event, calendar_type, toronto_tz)
                tomorrow_formatted.append(formatted)
            tomorrow_preview = "📅 **Tomorrow Preview:**\n" + "\n".join(tomorrow_formatted)
        else:
            tomorrow_preview = "📅 **Tomorrow Preview:** Clear schedule - strategic planning day"
        
        # Combine briefing
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        briefing = f"🌅 **Good Morning! Executive Briefing for {current_time}**\n\n{today_schedule}\n\n{tomorrow_preview}\n\n💼 **Executive Focus:** Prioritize high-impact activities during peak energy hours"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        return "🌅 **Morning Briefing:** Error generating briefing"

# ============================================================================
# ADVANCED CALENDAR MANAGEMENT FUNCTIONS
# ============================================================================

def create_calendar_event(title, start_time, end_time, calendar_type="calendar", description=""):
    """Create a new calendar event in specified Google Calendar"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Event Creation:** Calendar integration not configured."
    
    try:
        # Find target calendar
        target_calendar_id = None
        target_calendar_name = "Primary"
        
        for name, cal_id, cal_type in accessible_calendars:
            if calendar_type == "tasks" and cal_type == "tasks":
                target_calendar_id = cal_id
                target_calendar_name = name
                break
            elif calendar_type == "calendar" and cal_type == "calendar":
                target_calendar_id = cal_id
                target_calendar_name = name
                break
        
        # Fallback to first available calendar
        if not target_calendar_id and accessible_calendars:
            target_calendar_id = accessible_calendars[0][1]
            target_calendar_name = accessible_calendars[0][0]
        
        if not target_calendar_id:
            return "❌ **Event Creation Failed:** No suitable calendar found."
        
        # Parse times
        toronto_tz = pytz.timezone('America/Toronto')
        
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
            if end_dt.tzinfo is None:
                end_dt = toronto_tz.localize(end_dt)
            
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
            
        except ValueError:
            return "❌ **Invalid Time Format:** Please use YYYY-MM-DDTHH:MM:SS format."
        
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
        
        # Format confirmation
        display_start_dt = start_dt.astimezone(toronto_tz)
        display_end_dt = end_dt.astimezone(toronto_tz)
        
        return f"✅ **Event Created:** {title}\n📅 **When:** {display_start_dt.strftime('%A, %B %d at %I:%M %p')} - {display_end_dt.strftime('%I:%M %p')}\n🗓️ **Calendar:** {target_calendar_name}\n🔗 **Link:** {created_event.get('htmlLink', 'Available in calendar')}"
        
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
        return f"❌ **Event Creation Failed:** Unable to create '{title}' - please try again"

def reschedule_event(event_search, new_start_time, new_end_time):
    """Reschedule an existing calendar event"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Event Rescheduling:** Calendar integration not configured."
    
    try:
        # Find the event
        found_event = None
        found_calendar_id = None
        found_calendar_name = None
        
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        week_ago = now - timedelta(days=7)
        month_ahead = now + timedelta(days=30)
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, week_ago, month_ahead)
            for event in events:
                if event_search.lower() in event.get('summary', '').lower():
                    found_event = event
                    found_calendar_id = calendar_id
                    found_calendar_name = calendar_name
                    break
            if found_event:
                break
        
        if not found_event:
            return f"❌ **Event Not Found:** '{event_search}' not found in accessible calendars"
        
        # Parse new times
        try:
            new_start_dt = datetime.fromisoformat(new_start_time)
            new_end_dt = datetime.fromisoformat(new_end_time)
            
            if new_start_dt.tzinfo is None:
                new_start_dt = toronto_tz.localize(new_start_dt)
            if new_end_dt.tzinfo is None:
                new_end_dt = toronto_tz.localize(new_end_dt)
            
            new_start_iso = new_start_dt.isoformat()
            new_end_iso = new_end_dt.isoformat()
            
        except ValueError:
            return "❌ **Invalid Time Format:** Please use YYYY-MM-DDTHH:MM:SS format."
        
        # Update the event
        found_event['start'] = {
            'dateTime': new_start_iso,
            'timeZone': 'America/Toronto',
        }
        found_event['end'] = {
            'dateTime': new_end_iso,
            'timeZone': 'America/Toronto',
        }
        
        updated_event = calendar_service.events().update(
            calendarId=found_calendar_id,
            eventId=found_event['id'],
            body=found_event
        ).execute()
        
        # Format confirmation
        display_start_dt = new_start_dt.astimezone(toronto_tz)
        display_end_dt = new_end_dt.astimezone(toronto_tz)
        
        return f"✅ **Event Rescheduled:** {updated_event['summary']}\n📅 **New Time:** {display_start_dt.strftime('%A, %B %d at %I:%M %p')} - {display_end_dt.strftime('%I:%M %p')}\n🗓️ **Calendar:** {found_calendar_name}\n🔗 **Link:** {updated_event.get('htmlLink', 'Available in calendar')}"
        
    except Exception as e:
        print(f"❌ Error rescheduling event: {e}")
        return f"❌ **Rescheduling Failed:** Unable to reschedule '{event_search}' - please try again"

def move_task_between_calendars(task_search, target_calendar="tasks"):
    """Move tasks/events between different Google calendars"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Task Moving:** Calendar integration not configured."
    
    try:
        # Search across ALL accessible calendars
        found_event = None
        found_calendar_id = None
        found_calendar_name = None
        
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        search_start = now - timedelta(days=30)  # Search past month
        search_end = now + timedelta(days=90)    # Search next 3 months
        
        # Search all accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, search_start, search_end, max_results=200)
            for event in events:
                event_title = event.get('summary', '').lower()
                if task_search.lower() in event_title:
                    found_event = event
                    found_calendar_id = calendar_id
                    found_calendar_name = calendar_name
                    break
            if found_event:
                break
        
        if not found_event:
            available_calendars = [name for name, _, _ in accessible_calendars]
            return f"❌ **Task Not Found:** '{task_search}' not found in any accessible calendar.\n📅 **Searched:** {', '.join(available_calendars)}"
        
        # Find target calendar
        target_calendar_id = None
        target_calendar_name = None
        
        for name, cal_id, cal_type in accessible_calendars:
            if target_calendar == "tasks" and cal_type == "tasks":
                target_calendar_id = cal_id
                target_calendar_name = name
                break
            elif target_calendar == "calendar" and cal_type == "calendar":
                target_calendar_id = cal_id
                target_calendar_name = name
                break
            elif target_calendar == "primary" and cal_id == "primary":
                target_calendar_id = cal_id
                target_calendar_name = name
                break
        
        if not target_calendar_id:
            available_types = [f"{name} ({cal_type})" for name, _, cal_type in accessible_calendars]
            return f"❌ **Target Calendar Not Found:** '{target_calendar}' calendar not accessible.\n📅 **Available:** {', '.join(available_types)}"
        
        if found_calendar_id == target_calendar_id:
            return f"📅 **Already There:** '{found_event['summary']}' is already in {target_calendar_name}"
        
        # Create event copy for target calendar
        event_copy = {
            'summary': found_event.get('summary'),
            'description': found_event.get('description', ''),
            'start': found_event.get('start'),
            'end': found_event.get('end'),
            'location': found_event.get('location', ''),
            'reminders': found_event.get('reminders', {}),
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
        
        return f"✅ **Task Moved Successfully:**\n📋 **Task:** {found_event['summary']}\n📍 **From:** {found_calendar_name}\n📍 **To:** {target_calendar_name}\n🔗 **New Link:** {created_event.get('htmlLink', 'Available in Google Calendar')}"
        
    except HttpError as e:
        return f"❌ **Google Calendar Error:** {e.resp.status} - {e}"
    except Exception as e:
        print(f"❌ Error moving task: {e}")
        return f"❌ **Move Failed:** Unable to move '{task_search}' - please try manually"

def delete_calendar_event(event_search):
    """Delete a calendar event"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Event Deletion:** Calendar integration not configured."
    
    try:
        # Find the event
        found_event = None
        found_calendar_id = None
        found_calendar_name = None
        
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        week_ago = now - timedelta(days=7)
        month_ahead = now + timedelta(days=30)
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, week_ago, month_ahead)
            for event in events:
                if event_search.lower() in event.get('summary', '').lower():
                    found_event = event
                    found_calendar_id = calendar_id
                    found_calendar_name = calendar_name
                    break
            if found_event:
                break
        
        if not found_event:
            return f"❌ **Event Not Found:** '{event_search}' not found in accessible calendars"
        
        # Delete the event
        calendar_service.events().delete(
            calendarId=found_calendar_id,
            eventId=found_event['id']
        ).execute()
        
        return f"✅ **Event Deleted:** '{found_event['summary']}' from {found_calendar_name}"
        
    except Exception as e:
        print(f"❌ Error deleting event: {e}")
        return f"❌ **Deletion Failed:** Unable to delete '{event_search}' - please try manually"

def bulk_reschedule_events(search_pattern, days_to_shift=1, time_shift_hours=0):
    """Bulk reschedule multiple events matching a pattern"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Bulk Rescheduling:** Calendar integration not configured."
    
    try:
        found_events = []
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        search_start = now - timedelta(days=7)
        search_end = now + timedelta(days=60)
        
        # Find all matching events
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, search_start, search_end)
            for event in events:
                event_title = event.get('summary', '').lower()
                if search_pattern.lower() in event_title:
                    found_events.append({
                        'event': event,
                        'calendar_id': calendar_id,
                        'calendar_name': calendar_name
                    })
        
        if not found_events:
            return f"❌ **No Matching Events:** No events found matching '{search_pattern}'"
        
        if len(found_events) > 10:
            return f"⚠️ **Too Many Events:** Found {len(found_events)} events. Please be more specific to avoid accidental changes."
        
        # Reschedule each event
        rescheduled = []
        failed = []
        
        for item in found_events:
            try:
                event = item['event']
                calendar_id = item['calendar_id']
                
                # Calculate new times
                start_time_str = event['start'].get('dateTime', event['start'].get('date'))
                end_time_str = event['end'].get('dateTime', event['end'].get('date'))
                
                if 'T' in start_time_str:  # DateTime event
                    start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    
                    # Apply shifts
                    new_start = start_dt + timedelta(days=days_to_shift, hours=time_shift_hours)
                    new_end = end_dt + timedelta(days=days_to_shift, hours=time_shift_hours)
                    
                    # Update event
                    event['start'] = {
                        'dateTime': new_start.isoformat(),
                        'timeZone': 'America/Toronto'
                    }
                    event['end'] = {
                        'dateTime': new_end.isoformat(),
                        'timeZone': 'America/Toronto'
                    }
                    
                    updated_event = calendar_service.events().update(
                        calendarId=calendar_id,
                        eventId=event['id'],
                        body=event
                    ).execute()
                    
                    rescheduled.append(f"✅ {event['summary']} → {new_start.strftime('%m/%d at %I:%M %p')}")
                
            except Exception as e:
                failed.append(f"❌ {event.get('summary', 'Unknown event')}: {str(e)[:50]}")
        
        result = f"📅 **Bulk Reschedule Results:** {len(rescheduled)} moved, {len(failed)} failed\n\n"
        
        if rescheduled:
            result += "**Successfully Rescheduled:**\n" + "\n".join(rescheduled[:5])
            if len(rescheduled) > 5:
                result += f"\n...and {len(rescheduled) - 5} more"
        
        if failed:
            result += "\n\n**Failed:**\n" + "\n".join(failed[:3])
        
        return result
        
    except Exception as e:
        print(f"❌ Error in bulk reschedule: {e}")
        return f"❌ **Bulk Reschedule Failed:** {str(e)[:100]}"

def smart_event_scheduling(title, duration_minutes=60, preferred_days=None, preferred_hours=None, avoid_conflicts=True):
    """Intelligently schedule events in the best available time slots"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Smart Scheduling:** Calendar integration not configured."
    
    try:
        if preferred_days is None:
            preferred_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        if preferred_hours is None:
            preferred_hours = list(range(9, 17))  # 9 AM to 5 PM
        
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        search_end = now + timedelta(days=14)  # Look ahead 2 weeks
        
        # Get all existing events to avoid conflicts
        all_busy_times = []
        if avoid_conflicts:
            for calendar_name, calendar_id, calendar_type in accessible_calendars:
                events = get_calendar_events(calendar_id, now, search_end)
                for event in events:
                    start_str = event['start'].get('dateTime', event['start'].get('date'))
                    end_str = event['end'].get('dateTime', event['end'].get('date'))
                    
                    if 'T' in start_str:  # DateTime event
                        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(toronto_tz)
                        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00')).astimezone(toronto_tz)
                        all_busy_times.append((start_dt, end_dt))
        
        # Find best available slot
        current_date = now.date()
        best_slots = []
        
        for day_offset in range(14):  # Check next 14 days
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
                if avoid_conflicts:
                    for busy_start, busy_end in all_busy_times:
                        if (slot_start < busy_end and slot_end > busy_start):
                            has_conflict = True
                            break
                
                if not has_conflict:
                    # Score this slot (earlier in day = higher score, sooner date = higher score)
                    date_score = 14 - day_offset  # Prefer sooner
                    time_score = 17 - hour  # Prefer earlier in day
                    total_score = date_score * 10 + time_score
                    
                    best_slots.append({
                        'start': slot_start,
                        'end': slot_end,
                        'score': total_score
                    })
        
        if not best_slots:
            return f"❌ **No Available Slots:** No suitable times found for '{title}' in the next 2 weeks.\n💡 **Suggestion:** Try reducing duration or expanding preferred hours."
        
        # Get the best slot
        best_slot = max(best_slots, key=lambda x: x['score'])
        
        # Create the event
        result = create_calendar_event(
            title=title,
            start_time=best_slot['start'].strftime('%Y-%m-%dT%H:%M:%S'),
            end_time=best_slot['end'].strftime('%Y-%m-%dT%H:%M:%S'),
            calendar_type="calendar",
            description=f"Smart-scheduled for optimal availability"
        )
        
        # Add smart scheduling info
        alternatives = sorted(best_slots, key=lambda x: x['score'], reverse=True)[1:4]
        if alternatives:
            alt_times = [alt['start'].strftime('%A %m/%d at %I:%M %p') for alt in alternatives]
            result += f"\n\n🎯 **Alternative Times:** {', '.join(alt_times)}"
        
        return result
        
    except Exception as e:
        print(f"❌ Error in smart scheduling: {e}")
        return f"❌ **Smart Scheduling Failed:** {str(e)[:100]}"

# ============================================================================
# ENHANCED PLANNING SEARCH WITH ERROR HANDLING
# ============================================================================

async def planning_search_enhanced(query, focus_area="general", num_results=3):
    """Enhanced planning and productivity research with comprehensive error handling"""
    if not BRAVE_API_KEY:
        return "🔍 Planning research requires Brave Search API configuration", []
    
    try:
        # Enhance query for planning content
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
                        
                        # Extract domain for credibility
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
# ENHANCED FUNCTION HANDLING WITH COMPLETE OPENAI API INTEGRATION
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
            if function_name == "planning_search":
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
                    
            elif function_name == "get_today_schedule":
                output = get_today_schedule()
                    
            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)
                
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()
                
            elif function_name == "create_calendar_event":
                title = arguments.get('title', '')
                start_time = arguments.get('start_time', '')
                end_time = arguments.get('end_time', '')
                calendar_type = arguments.get('calendar_type', 'calendar')
                description = arguments.get('description', '')
                
                if title and start_time and end_time:
                    output = create_calendar_event(title, start_time, end_time, calendar_type, description)
                else:
                    output = "❌ Missing required parameters for event creation"
                    
            elif function_name == "reschedule_event":
                event_search = arguments.get('event_search', '')
                new_start_time = arguments.get('new_start_time', '')
                new_end_time = arguments.get('new_end_time', '')
                
                if event_search and new_start_time and new_end_time:
                    output = reschedule_event(event_search, new_start_time, new_end_time)
                else:
                    output = "❌ Missing required parameters for event rescheduling"
                    
            elif function_name == "move_task_between_calendars":
                task_search = arguments.get('task_search', '')
                target_calendar = arguments.get('target_calendar', 'tasks')
                
                if task_search:
                    output = move_task_between_calendars(task_search, target_calendar)
                else:
                    output = "❌ Missing task search parameter"
                    
            elif function_name == "delete_calendar_event":
                event_search = arguments.get('event_search', '')
                
                if event_search:
                    output = delete_calendar_event(event_search)
                else:
                    output = "❌ Missing event search parameter"
                    
            elif function_name == "bulk_reschedule_events":
                search_pattern = arguments.get('search_pattern', '')
                days_to_shift = arguments.get('days_to_shift', 1)
                time_shift_hours = arguments.get('time_shift_hours', 0)
                
                if search_pattern:
                    output = bulk_reschedule_events(search_pattern, days_to_shift, time_shift_hours)
                else:
                    output = "❌ Missing search pattern for bulk rescheduling"
                    
            elif function_name == "smart_event_scheduling":
                title = arguments.get('title', '')
                duration_minutes = arguments.get('duration_minutes', 60)
                preferred_days = arguments.get('preferred_days', None)
                preferred_hours = arguments.get('preferred_hours', None)
                avoid_conflicts = arguments.get('avoid_conflicts', True)
                
                if title:
                    output = smart_event_scheduling(title, duration_minutes, preferred_days, preferred_hours, avoid_conflicts)
                else:
                    output = "❌ Missing event title for smart scheduling"
                
            else:
                output = f"❓ Function {function_name} not fully implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: Please try again"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Keep within reasonable limits
        })
    
    # Submit tool outputs with error handling
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
# MAIN CONVERSATION HANDLER WITH ENHANCED OPENAI API INTEGRATION
# ============================================================================

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with complete calendar integration"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Check if user already has an active run
        if user_id in user_conversations and user_conversations[user_id].get('active', False):
            return "👑 Rose is currently analyzing your executive strategy. Please wait a moment..."
        
        # Get user's thread
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = {'thread_id': thread.id, 'active': False}
            print(f"👑 Created executive thread for user {user_id}")
        
        # Mark as active
        user_conversations[user_id]['active'] = True
        thread_id = user_conversations[user_id]['thread_id']
        
        # Clean message
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
        
        # Enhanced message with executive planning focus and calendar capabilities
        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- SMART CALENDAR DETECTION: Automatically detect if this is a general or specific calendar query
- GENERAL CALENDAR QUERIES (auto-include full schedule): "what's on my calendar", "what's my schedule", "what do I have today", "how does my day look", "what's happening today"
- SPECIFIC CALENDAR QUERIES (answer directly): "what do I have after 5pm", "am I free at 2pm", "what's my first meeting", "when is my next call"
- BRIEFING REQUESTS: "morning briefing", "daily briefing", "executive briefing", "give me a briefing", "brief me", "what's my day like"
- TASK MANAGEMENT: Can move, create, reschedule, delete events between calendars
- AVAILABLE CALENDARS: {[name for name, _, _ in accessible_calendars]}
- CALENDAR CAPABILITIES: Create events, reschedule, move between calendars, bulk operations, smart scheduling
- For planning research, include actionable productivity recommendations
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- IMPORTANT: Always provide strategic context and actionable next steps
- All times are in Toronto timezone (America/Toronto)
- ENHANCED FEATURES: Smart scheduling, bulk rescheduling, conflict detection, morning briefings"""
        
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
        
        # Run assistant with enhanced executive instructions
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID,
                instructions="""You are Rose Ashcombe, executive assistant specialist with complete Google Calendar API integration and advanced task management capabilities.

EXECUTIVE APPROACH:
- Use executive calendar functions to provide comprehensive scheduling insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines
- Focus on high-impact activity identification and time management
- Leverage advanced calendar management: move tasks between calendars, bulk operations, smart scheduling
- BRIEFING INTELLIGENCE: For briefing requests, automatically use get_morning_briefing() function

CALENDAR CAPABILITIES:
- Create events in any accessible calendar
- Move tasks/events between calendars (BG Calendar ↔ BG Tasks)
- Reschedule individual or bulk events
- Smart scheduling with conflict detection
- Delete unnecessary events
- Find optimal meeting times

FORMATTING: Use professional executive formatting with strategic headers (👑 📊 📅 🎯 💼) and provide organized, action-oriented guidance.

STRUCTURE:
👑 **Executive Summary:** [strategic overview with calendar insights]
📊 **Strategic Analysis:** [research-backed recommendations]
🎯 **Action Items:** [specific next steps with timing]

Keep core content focused and always provide strategic context with calendar coordination. Leverage all available calendar management functions to provide comprehensive executive assistance."""
            )
        except Exception as e:
            print(f"❌ Run creation error: {e}")
            return "❌ Error starting executive analysis. Please try again."
        
        print(f"👑 Rose run created: {run.id}")
        
        # Wait for completion with function handling
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
                return "❌ Executive analysis interrupted. Please try again with a different request."
            
            await asyncio.sleep(2)
        else:
            print("⏱️ Run timed out")
            return "⏱️ Executive office is busy with strategic planning. Please try again in a moment."
        
        # Get response and apply enhanced formatting
        try:
            messages = client.beta.threads.messages.list(thread_id=thread_id, limit=5)
            for msg in messages.data:
                if msg.role == "assistant":
                    response = msg.content[0].text.value
                    return format_for_discord_rose(response)
        except Exception as e:
            print(f"❌ Error retrieving messages: {e}")
            return "❌ Error retrieving executive guidance. Please try again."
        
        return "👑 Executive analysis unclear. Please try again with a different approach."
        
    except Exception as e:
        print(f"❌ Rose error: {e}")
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return "❌ Something went wrong with executive strategy. Please try again!"
    finally:
        # Always remove user from active runs when done
        if user_id in user_conversations:
            user_conversations[user_id]['active'] = False

def format_for_discord_rose(response):
    """Format response for Discord with error handling"""
    try:
        if not response or not isinstance(response, str):
            return "👑 Executive strategy processing. Please try again."
        
        # Clean excessive spacing
        response = response.replace('\n\n\n\n', '\n\n')
        response = response.replace('\n\n\n', '\n\n')
        
        # Length management
        if len(response) > 1900:
            response = response[:1900] + "\n\n👑 *(Executive insights continue)*"
        
        return response.strip()
        
    except Exception as e:
        print(f"❌ Discord formatting error: {e}")
        return "👑 Executive message needs refinement. Please try again."

# ============================================================================
# ENHANCED MESSAGE HANDLING WITH COMPREHENSIVE ERROR HANDLING
# ============================================================================

async def send_long_message(original_message, response):
    """Send response with length handling and error recovery"""
    try:
        if len(response) <= 2000:
            await original_message.reply(response)
        else:
            # Split into chunks
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
            
            # Send chunks
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
# DISCORD BOT EVENT HANDLERS WITH ERROR HANDLING
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
        
        # Set status
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
        # Skip bot's own messages
        if message.author == bot.user:
            return
        
        # Process commands first
        await bot.process_commands(message)
        
        # Only respond in allowed channels or DMs
        channel_name = message.channel.name.lower() if hasattr(message.channel, 'name') else 'dm'
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_allowed_channel = any(allowed in channel_name for allowed in ALLOWED_CHANNELS)
        
        if not (is_dm or is_allowed_channel):
            return

        # Respond to mentions or DMs
        if bot.user.mentioned_in(message) or is_dm:
            
            # DUPLICATE PREVENTION
            message_key = f"{message.author.id}_{message.content[:50]}"
            current_time = time.time()
            
            # Check if we're already processing this message
            if message_key in processing_messages:
                return
            
            # Check if user sent same message too quickly (within 5 seconds)
            if message.author.id in last_response_time:
                if current_time - last_response_time[message.author.id] < 5:
                    return
            
            # Mark message as being processed
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
                # Always clean up
                processing_messages.discard(message_key)
                    
    except Exception as e:
        print(f"❌ Message event error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")

# ============================================================================
# STANDARDIZED COMMANDS FOLLOWING TEAM PATTERNS
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
    """Enhanced help command with complete calendar management features"""
    try:
        help_text = f"""👑 **{ASSISTANT_NAME} - Complete Executive Assistant Commands**

**📅 Calendar & Scheduling:**
• `!today` - Today's executive schedule
• `!upcoming [days]` - Upcoming events (default 7 days)
• `!briefing` / `!daily` / `!morning` - Morning executive briefing
• `!calendar` - Quick calendar overview with AI insights
• `!schedule [timeframe]` - Flexible schedule view (today/week/month/[number])
• `!agenda` - Comprehensive executive agenda overview
• `!overview` - Complete executive overview (briefing + 3-day outlook)

**🔧 Task & Event Management:**
• `!create` - Create new calendar events
• `!move` - Move tasks between calendars
• `!reschedule` - Reschedule existing events
• `!delete` - Delete calendar events
• `!bulk` - Bulk reschedule multiple events

**🔍 Planning & Research:**
• `!research <query>` - Strategic planning research
• `!planning <topic>` - Productivity insights
• `!smart <event title>` - Smart event scheduling

**💼 Executive Functions:**
• `!status` - System and calendar status
• `!ping` - Test connectivity
• `!help` - This command menu

**🎯 Enhanced Features:**
• **Smart Scheduling:** AI-powered optimal time finding
• **Bulk Operations:** Reschedule multiple events at once
• **Cross-Calendar Management:** Move tasks between BG Calendar ↔ BG Tasks
• **Conflict Detection:** Automatic scheduling conflict avoidance
• **Strategic Planning Research:** Actionable productivity insights
• **Toronto Timezone Support:** All times in America/Toronto

**📱 Usage:**
• Mention @{bot.user.name if bot.user else 'Rose'} in any message
• Use executive keywords: calendar, schedule, planning, strategy, move, reschedule
• Available in: {', '.join(ALLOWED_CHANNELS)}

**💡 Example Commands:**
• `!briefing` or `!daily` - Get comprehensive morning briefing
• `!today` - See today's complete schedule
• `!overview` - Complete executive overview with 3-day outlook
• `!schedule week` - View this week's agenda
• `!upcoming 3` - See next 3 days of events
• `!agenda` - Comprehensive agenda overview
• "Give me my morning briefing" - Natural language briefing request
• "What's my day like?" - Natural language schedule request
• "Move my dentist appointment to my tasks calendar"
• "Reschedule all team meetings to next Tuesday"
• "Find me 2 hours this week for deep work"
"""
        
        await ctx.send(help_text)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Help system needs calibration. Please try again.")

@bot.command(name='status')
async def status_command(ctx):
    """Executive system status with comprehensive diagnostics"""
    try:
        # Calendar status
        calendar_status = "❌ No calendars accessible"
        if accessible_calendars:
            calendar_names = [name for name, _, _ in accessible_calendars]
            calendar_status = f"✅ {len(accessible_calendars)} calendars: {', '.join(calendar_names)}"
        
        # Research status
        research_status = "✅ Enabled" if BRAVE_API_KEY else "❌ Disabled"
        
        # Assistant status
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        
        # Service account info
        sa_info = "Not configured"
        if service_account_email:
            sa_info = f"✅ {service_account_email}"
        
        # Calendar capabilities
        capabilities = []
        if accessible_calendars:
            capabilities = [
                "📅 Read Events", "✅ Create Events", "🔄 Reschedule Events",
                "📋 Move Tasks", "🗑️ Delete Events", "🔄 Bulk Operations",
                "🎯 Smart Scheduling", "⚠️ Conflict Detection"
            ]
        
        status_text = f"""👑 **{ASSISTANT_NAME} Complete Executive Status**

**🤖 Core Systems:**
• Discord: ✅ Connected as {bot.user.name if bot.user else 'Unknown'}
• OpenAI Assistant: {assistant_status}
• Service Account: {sa_info}

**📅 Calendar Integration:**
• Status: {calendar_status}
• Timezone: 🇨🇦 Toronto (America/Toronto)
• Capabilities: {', '.join(capabilities) if capabilities else 'Limited'}

**🔍 Planning Research:**
• Brave Search API: {research_status}

**💼 Executive Features:**
• Active conversations: {len(user_conversations)}
• Channels: {', '.join(ALLOWED_CHANNELS)}
• Enhanced Functions: Complete Calendar Management, Smart Scheduling, Bulk Operations

**⚡ Performance:**
• Uptime: Ready for complete executive assistance
• Memory: {len(processing_messages)} processing
• Calendar Access: Full Google Calendar API integration"""
        
        await ctx.send(status_text)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
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
            # Limit days to reasonable range
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
            calendar_query = "what's on my calendar today and upcoming strategic overview executive summary"
            response = await get_rose_response(calendar_query, user_id)
            await send_long_message(ctx.message, response)
    except Exception as e:
        print(f"❌ Calendar command error: {e}")
        await ctx.send("👑 Calendar overview unavailable. Please try again.")

@bot.command(name='schedule')
async def schedule_command(ctx, *, timeframe: str = "today"):
    """Flexible schedule command - can show today, upcoming, or specific timeframes"""
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
                days = max(1, min(days, 30))  # Limit range
                response = get_upcoming_events(days)
            else:
                # Default to today
                response = get_today_schedule()
            
            await ctx.send(response)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("👑 Schedule view unavailable. Please try again.")

@bot.command(name='agenda')
async def agenda_command(ctx):
    """Executive agenda command - comprehensive view"""
    try:
        async with ctx.typing():
            # Get comprehensive agenda view
            today_schedule = get_today_schedule()
            tomorrow_events = get_upcoming_events(1)
            
            agenda = f"📋 **Executive Agenda Overview**\n\n{today_schedule}\n\n**Tomorrow:**\n{tomorrow_events}"
            
            # Limit response length
            if len(agenda) > 1900:
                agenda = agenda[:1900] + "\n\n👑 *Use `!today` and `!upcoming` for detailed views*"
            
            await ctx.send(agenda)
    except Exception as e:
        print(f"❌ Agenda command error: {e}")
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
    """Executive overview command - comprehensive briefing"""
    try:
        async with ctx.typing():
            # Get comprehensive overview
            briefing = get_morning_briefing()
            upcoming = get_upcoming_events(3)
            
            overview = f"{briefing}\n\n📋 **3-Day Executive Outlook:**\n{upcoming}"
            
            # Manage length
            if len(overview) > 1900:
                # Send briefing first, then upcoming
                await ctx.send(briefing)
                await ctx.send(f"📋 **3-Day Executive Outlook:**\n{upcoming}")
            else:
                await ctx.send(overview)
                
    except Exception as e:
        print(f"❌ Overview command error: {e}")
        await ctx.send("👑 Executive overview unavailable. Please try again.")

# ============================================================================
# STANDARDIZED COMMANDS FOLLOWING TEAM PATTERNS
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
    """Enhanced help command with complete calendar management features"""
    try:
        help_text = f"""👑 **{ASSISTANT_NAME} - Complete Executive Assistant Commands**

**📅 Calendar & Scheduling:**
• `!today` - Today's executive schedule
• `!upcoming [days]` - Upcoming events (default 7 days)
• `!briefing` / `!daily` / `!morning` - Morning executive briefing
• `!calendar` - Quick calendar overview with AI insights
• `!schedule [timeframe]` - Flexible schedule view (today/week/month/[number])
• `!agenda` - Comprehensive executive agenda overview
• `!overview` - Complete executive overview (briefing + 3-day outlook)

**🔧 Task & Event Management:**
• `!create` - Create new calendar events
• `!move` - Move tasks between calendars
• `!reschedule` - Reschedule existing events
• `!delete` - Delete calendar events
• `!bulk` - Bulk reschedule multiple events

**🔍 Planning & Research:**
• `!research <query>` - Strategic planning research
• `!planning <topic>` - Productivity insights
• `!smart <event title>` - Smart event scheduling

**💼 Executive Functions:**
• `!status` - System and calendar status
• `!ping` - Test connectivity
• `!help` - This command menu

**🎯 Enhanced Features:**
• **Smart Scheduling:** AI-powered optimal time finding
• **Bulk Operations:** Reschedule multiple events at once
• **Cross-Calendar Management:** Move tasks between BG Calendar ↔ BG Tasks
• **Conflict Detection:** Automatic scheduling conflict avoidance
• **Strategic Planning Research:** Actionable productivity insights
• **Toronto Timezone Support:** All times in America/Toronto

**📱 Usage:**
• Mention @{bot.user.name if bot.user else 'Rose'} in any message
• Use executive keywords: calendar, schedule, planning, strategy, move, reschedule
• Available in: {', '.join(ALLOWED_CHANNELS)}

**💡 Example Commands:**
• `!briefing` or `!daily` - Get comprehensive morning briefing
• `!today` - See today's complete schedule
• `!overview` - Complete executive overview with 3-day outlook
• `!schedule week` - View this week's agenda
• `!upcoming 3` - See next 3 days of events
• `!agenda` - Comprehensive agenda overview
• "Give me my morning briefing" - Natural language briefing request
• "What's my day like?" - Natural language schedule request
• "Move my dentist appointment to my tasks calendar"
• "Reschedule all team meetings to next Tuesday"
• "Find me 2 hours this week for deep work"
"""
        
        await ctx.send(help_text)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Help system needs calibration. Please try again.")

@bot.command(name='status')
async def status_command(ctx):
    """Executive system status with comprehensive diagnostics"""
    try:
        # Calendar status
        calendar_status = "❌ No calendars accessible"
        if accessible_calendars:
            calendar_names = [name for name, _, _ in accessible_calendars]
            calendar_status = f"✅ {len(accessible_calendars)} calendars: {', '.join(calendar_names)}"
        
        # Research status
        research_status = "✅ Enabled" if BRAVE_API_KEY else "❌ Disabled"
        
        # Assistant status
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        
        # Service account info
        sa_info = "Not configured"
        if service_account_email:
            sa_info = f"✅ {service_account_email}"
        
        # Calendar capabilities
        capabilities = []
        if accessible_calendars:
            capabilities = [
                "📅 Read Events", "✅ Create Events", "🔄 Reschedule Events",
                "📋 Move Tasks", "🗑️ Delete Events", "🔄 Bulk Operations",
                "🎯 Smart Scheduling", "⚠️ Conflict Detection"
            ]
        
        status_text = f"""👑 **{ASSISTANT_NAME} Complete Executive Status**

**🤖 Core Systems:**
• Discord: ✅ Connected as {bot.user.name if bot.user else 'Unknown'}
• OpenAI Assistant: {assistant_status}
• Service Account: {sa_info}

**📅 Calendar Integration:**
• Status: {calendar_status}
• Timezone: 🇨🇦 Toronto (America/Toronto)
• Capabilities: {', '.join(capabilities) if capabilities else 'Limited'}

**🔍 Planning Research:**
• Brave Search API: {research_status}

**💼 Executive Features:**
• Active conversations: {len(user_conversations)}
• Channels: {', '.join(ALLOWED_CHANNELS)}
• Enhanced Functions: Complete Calendar Management, Smart Scheduling, Bulk Operations

**⚡ Performance:**
• Uptime: Ready for complete executive assistance
• Memory: {len(processing_messages)} processing
• Calendar Access: Full Google Calendar API integration"""
        
        await ctx.send(status_text)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Status diagnostics experiencing issues. Please try again.")

@bot.command(name='schedule')
async def schedule_command(ctx, *, timeframe: str = "today"):
    """Flexible schedule command - can show today, upcoming, or specific timeframes"""
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
                days = max(1, min(days, 30))  # Limit range
                response = get_upcoming_events(days)
            else:
                # Default to today
                response = get_today_schedule()
            
            await ctx.send(response)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("👑 Schedule view unavailable. Please try again.")

@bot.command(name='agenda')
async def agenda_command(ctx):
    """Executive agenda command - comprehensive view"""
    try:
        async with ctx.typing():
            # Get comprehensive agenda view
            today_schedule = get_today_schedule()
            tomorrow_events = get_upcoming_events(1)
            
            agenda = f"📋 **Executive Agenda Overview**\n\n{today_schedule}\n\n**Tomorrow:**\n{tomorrow_events}"
            
            # Limit response length
            if len(agenda) > 1900:
                agenda = agenda[:1900] + "\n\n👑 *Use `!today` and `!upcoming` for detailed views*"
            
            await ctx.send(agenda)
    except Exception as e:
        print(f"❌ Agenda command error: {e}")
        await ctx.send("👑 Executive agenda unavailable. Please try again.")

@bot.command(name='overview')
async def overview_command(ctx):
    """Executive overview command - comprehensive briefing"""
    try:
        async with ctx.typing():
            # Get comprehensive overview
            briefing = get_morning_briefing()
            upcoming = get_upcoming_events(3)
            
            overview = f"{briefing}\n\n📋 **3-Day Executive Outlook:**\n{upcoming}"
            
            # Manage length
            if len(overview) > 1900:
                # Send briefing first, then upcoming
                await ctx.send(briefing)
                await ctx.send(f"📋 **3-Day Executive Outlook:**\n{upcoming}")
            else:
                await ctx.send(overview)
                
    except Exception as e:
        print(f"❌ Overview command error: {e}")
        await ctx.send("👑 Executive overview unavailable. Please try again.")

@bot.command(name='move')
async def move_command(ctx, *, move_details: str = None):
    """Move task between calendars command"""
    try:
        if not move_details:
            await ctx.send("👑 **Move Task Usage:** `!move <task details>`\n\nExamples:\n• `!move dentist appointment to tasks calendar`\n• `!move team meeting to main calendar`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            move_query = f"move task between calendars: {move_details}"
            response = await get_rose_response(move_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Move command error: {e}")
        await ctx.send("👑 Task moving unavailable. Please try again.")

@bot.command(name='delete')
async def delete_command(ctx, *, delete_details: str = None):
    """Delete calendar event command"""
    try:
        if not delete_details:
            await ctx.send("👑 **Delete Event Usage:** `!delete <event details>`\n\nExamples:\n• `!delete cancelled lunch meeting`\n• `!delete old team standup`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            delete_query = f"delete calendar event: {delete_details}"
            response = await get_rose_response(delete_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Delete command error: {e}")
        await ctx.send("👑 Event deletion unavailable. Please try again.")

@bot.command(name='bulk')
async def bulk_command(ctx, *, bulk_details: str = None):
    """Bulk reschedule events command"""
    try:
        if not bulk_details:
            await ctx.send("👑 **Bulk Reschedule Usage:** `!bulk <bulk operation details>`\n\nExamples:\n• `!bulk move all team meetings forward by 2 hours`\n• `!bulk reschedule client calls to next week`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            bulk_query = f"bulk reschedule events: {bulk_details}"
            response = await get_rose_response(bulk_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Bulk command error: {e}")
        await ctx.send("👑 Bulk operations unavailable. Please try again.")

@bot.command(name='smart')
async def smart_command(ctx, *, smart_details: str = None):
    """Smart event scheduling command"""
    try:
        if not smart_details:
            await ctx.send("👑 **Smart Scheduling Usage:** `!smart <event title and preferences>`\n\nExamples:\n• `!smart quarterly review meeting 2 hours`\n• `!smart deep work session weekday mornings`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            smart_query = f"smart schedule event with optimal timing: {smart_details}"
            response = await get_rose_response(smart_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Smart scheduling command error: {e}")
        await ctx.send("👑 Smart scheduling unavailable. Please try again.")

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
            planning_query = f"executive planning insights for {topic} productivity optimization time management"
            response = await get_rose_response(planning_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Planning command error: {e}")
        await ctx.send("👑 Executive planning insights unavailable. Please try again.")

@bot.command(name='calendar')
async def calendar_command(ctx):
    """Quick calendar overview command"""
    try:
        async with ctx.typing():
            user_id = str(ctx.author.id)
            calendar_query = "what's on my calendar today and upcoming strategic overview executive summary"
            response = await get_rose_response(calendar_query, user_id)
            await send_long_message(ctx.message, response)
    except Exception as e:
        print(f"❌ Calendar command error: {e}")
        await ctx.send("👑 Calendar overview unavailable. Please try again.")

@bot.command(name='create')
async def create_command(ctx, *, event_details: str = None):
    """Create calendar event command"""
    try:
        if not event_details:
            await ctx.send("👑 **Create Event Usage:** `!create <event details>`\n\nExamples:\n• `!create Team meeting tomorrow at 2pm for 1 hour`\n• `!create Doctor appointment Friday at 10am`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            create_query = f"create a calendar event: {event_details}"
            response = await get_rose_response(create_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Create command error: {e}")
        await ctx.send("👑 Event creation unavailable. Please try again.")

@bot.command(name='reschedule')
async def reschedule_command(ctx, *, reschedule_details: str = None):
    """Reschedule event command"""
    try:
        if not reschedule_details:
            await ctx.send("👑 **Reschedule Usage:** `!reschedule <event details>`\n\nExamples:\n• `!reschedule team meeting to tomorrow at 3pm`\n• `!reschedule doctor appointment to next Friday`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            reschedule_query = f"reschedule event: {reschedule_details}"
            response = await get_rose_response(reschedule_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Reschedule command error: {e}")
        await ctx.send("👑 Event rescheduling unavailable. Please try again.")

@bot.command(name='smart')
async def smart_command(ctx, *, smart_details: str = None):
    """Smart event scheduling command"""
    try:
        if not smart_details:
            await ctx.send("👑 **Smart Scheduling Usage:** `!smart <event title and preferences>`\n\nExamples:\n• `!smart quarterly review meeting 2 hours`\n• `!smart deep work session weekday mornings`")
            return
        
        async with ctx.typing():
            user_id = str(ctx.author.id)
            smart_query = f"smart schedule event with optimal timing: {smart_details}"
            response = await get_rose_response(smart_query, user_id)
            await send_long_message(ctx.message, response)
            
    except Exception as e:
        print(f"❌ Smart scheduling command error: {e}")
        await ctx.send("👑 Smart scheduling unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling for all commands"""
    if isinstance(error, commands.CommandNotFound):
        # Don't respond to unknown commands to avoid spam
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
        print(f"🔧 Calendar Capabilities: Create, Move, Reschedule, Delete, Bulk Operations")
        print(f"🎯 Smart Features: Conflict Detection, Optimal Scheduling")
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