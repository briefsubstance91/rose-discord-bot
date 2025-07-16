#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (CLEANED CALENDAR VERSION)
Executive Assistant with Enhanced Error Handling, Planning & Calendar Functions
CLEANED: Removed iCloud calendar complexity, focus on working Google Calendars only
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
ASSISTANT_ROLE = "Executive Assistant (Cleaned Calendar)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Simplified calendar integration - working Google Calendars only
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

# Simplified Google Calendar setup - working calendars only
calendar_service = None
accessible_calendars = []
service_account_email = None

def test_calendar_access(calendar_id, calendar_name):
    """Test calendar access with clean error handling"""
    if not calendar_service or not calendar_id:
        return False
    
    try:
        # Test calendar metadata
        calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ {calendar_name} accessible")
        
        # Test event access (fetch a few recent events)
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
        print(f"❌ {calendar_name} HTTP Error {e.resp.status}: {e}")
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
                'https://www.googleapis.com/auth/calendar.events' # Added for event creation/modification
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized")
        
        # Get service account email
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account: {service_account_email}")
        
        # Test only the working calendars
        working_calendars_to_check = [
            ("BG Calendar", GOOGLE_CALENDAR_ID, "calendar"),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID, "tasks")
        ]
        
        for name, calendar_id, calendar_type in working_calendars_to_check:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id, calendar_type))
        
        # Add 'primary' as fallback if no specific IDs are configured or accessible
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing 'primary'...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary", "calendar"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _, _ in accessible_calendars:
            print(f"   ✅ {name}")
            
    else:
        print("⚠️ Google Calendar credentials not found - calendar functions disabled")
        
except Exception as e:
    print(f"❌ Google Calendar setup error: {e}")
    calendar_service = None
    accessible_calendars = []

# Memory and duplicate prevention systems
user_conversations = {}
processing_messages = set()
last_response_time = {}
active_runs = {}

print(f"👑 Starting {ASSISTANT_NAME} - {ASSISTANT_ROLE}...")

# ============================================================================
# SIMPLIFIED CALENDAR FUNCTIONS - NO ICLOUD COMPLEXITY
# ============================================================================

def get_calendar_events(calendar_id, start_time, end_time, max_results=100):
    """Get events from a specific calendar - simplified"""
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
    
    # Simple calendar indicators
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
    """Get today's schedule - simplified for working calendars only"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Today's Schedule:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps directly"
    
    try:
        # Use Toronto timezone
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today in Toronto timezone
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto + timedelta(days=1) # End of today
        
        # Convert to UTC for Google Calendar API
        today_utc = today_toronto.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from accessible calendars only
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
                else: # All-day event, use the date itself
                    return datetime.fromisoformat(start).replace(tzinfo=toronto_tz)
            except:
                return datetime.now(toronto_tz) # Fallback if parsing fails
        
        all_events.sort(key=get_event_time)
        
        # Format response
        formatted_events = [event_tuple[1] for event_tuple in all_events]
        
        # Count by calendar for breakdown
        calendar_counts = {}
        for _, _, _, calendar_name in all_events:
            calendar_counts[calendar_name] = calendar_counts.get(calendar_name, 0) + 1
        
        header = f"📅 **Today's Executive Schedule:** {len(all_events)} events"
        
        # Add breakdown by calendar
        if calendar_counts:
            breakdown = []
            for calendar_name, count in calendar_counts.items():
                breakdown.append(f"{count} {calendar_name}")
            header += f" ({', '.join(breakdown)})"
        
        return header + "\n\n" + "\n".join(formatted_events[:15]) # Limit for Discord
        
    except Exception as e:
        print(f"❌ Calendar error in get_today_schedule: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data\n\n🎯 **Backup Plan:** Check your calendar apps directly"

def get_upcoming_events(days=7):
    """Get upcoming events - simplified for working calendars only"""
    if not calendar_service or not accessible_calendars:
        return f"📅 **Upcoming {days} Days:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps"
    
    try:
        # Use Toronto timezone
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get date range
        start_toronto = datetime.now(toronto_tz)
        end_toronto = start_toronto + timedelta(days=days)
        
        start_utc = start_toronto.astimezone(pytz.UTC)
        end_utc = end_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from accessible calendars only
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
                print(f"❌ Date parsing error in get_upcoming_events: {e}")
                continue
        
        # Format response
        formatted = []
        total_events = len(all_events)
        
        # Count by calendar for breakdown
        calendar_counts = {}
        for _, _, calendar_name in all_events:
            calendar_counts[calendar_name] = calendar_counts.get(calendar_name, 0) + 1
        
        for date, day_events in sorted(events_by_date.items())[:7]: # Limit to 7 days for Discord
            formatted.append(f"**{date}**")
            # Sort events within the day by time
            day_events_sorted = sorted(day_events, key=lambda x: datetime.strptime(x.split(': ')[0].replace('• ', '').strip(), '%I:%M %p') if '• ' in x and 'All Day' not in x else datetime.min)
            formatted.extend(day_events_sorted[:6]) # Limit events per day for readability
        
        header = f"📅 **Upcoming {days} Days:** {total_events} total events"
        
        # Add breakdown by calendar
        if calendar_counts:
            breakdown = []
            for calendar_name, count in calendar_counts.items():
                breakdown.append(f"{count} {calendar_name}")
            header += f" ({', '.join(breakdown)})"
        
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error in get_upcoming_events: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Morning briefing - simplified for working calendars only"""
    if not calendar_service or not accessible_calendars:
        return "🌅 **Morning Briefing:** Calendar integration not available\n\n📋 **Manual Planning:** Review your calendar apps"
    
    try:
        # Use Toronto timezone
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today's schedule
        today_schedule = get_today_schedule()
        
        # Get tomorrow's preview
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto + timedelta(days=1)
        day_after_tomorrow_toronto = tomorrow_toronto + timedelta(days=1)
        
        # Convert to UTC
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        day_after_tomorrow_utc = day_after_tomorrow_toronto.astimezone(pytz.UTC)
        
        tomorrow_events = []
        
        # Get tomorrow's events from accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, tomorrow_utc, day_after_tomorrow_utc)
            tomorrow_events.extend([(event, calendar_type, calendar_name) for event in events])
        
        # Format tomorrow's preview
        if tomorrow_events:
            tomorrow_formatted = []
            # Sort tomorrow's events by time
            def get_event_time_for_sort(event_tuple):
                event = event_tuple[0]
                start = event['start'].get('dateTime', event['start'].get('date'))
                try:
                    if 'T' in start:
                        utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        return utc_time.astimezone(toronto_tz)
                    else:
                        return datetime.fromisoformat(start).replace(tzinfo=toronto_tz)
                except:
                    return datetime.now(toronto_tz)
            
            tomorrow_events.sort(key=get_event_time_for_sort)

            for event, calendar_type, calendar_name in tomorrow_events[:4]: # Limit to 4 for briefing
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
# ENHANCED PLANNING SEARCH WITH ERROR HANDLING
# ============================================================================

async def planning_search_enhanced(query, focus_area="general", num_results=3):
    """Enhanced planning and productivity research with comprehensive error handling"""
    if not BRAVE_API_KEY:
        print("⚠️ Brave Search API key not configured")
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
        print("⏰ Planning search timeout")
        return "🔍 Planning search timed out", []
    except aiohttp.ClientError as e:
        print(f"❌ HTTP client error: {e}")
        return f"🔍 Planning search connection error", []
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Planning search error: Please try again", []

# ============================================================================
# CALENDAR EVENT MANAGEMENT FUNCTIONS (ADAPTED FOR GOOGLE CALENDARS ONLY)
# ============================================================================

def create_calendar_event(title, start_time, end_time, calendar_type="primary", description=""):
    """Create a new calendar event in an accessible Google Calendar"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Event Creation:** Calendar integration not configured or no accessible calendars."
    
    target_calendar_id = None
    target_calendar_name = "Primary" # Default name

    # Find the correct calendar ID based on type
    for name, cal_id, cal_type in accessible_calendars:
        if calendar_type == "tasks" and cal_type == "tasks":
            target_calendar_id = cal_id
            target_calendar_name = name
            break
        elif calendar_type == "primary" and cal_type == "calendar":
            target_calendar_id = cal_id
            target_calendar_name = name
            break
    
    # If a specific calendar type wasn't found, try 'primary' if it's accessible
    if not target_calendar_id:
        for name, cal_id, cal_type in accessible_calendars:
            if cal_id == 'primary' and cal_type == 'calendar':
                target_calendar_id = cal_id
                target_calendar_name = name
                break
        if not target_calendar_id: # Fallback if 'primary' is not explicitly listed but exists
            print("⚠️ Could not find a specific calendar, attempting to use the first accessible calendar.")
            target_calendar_id = accessible_calendars[0][1]
            target_calendar_name = accessible_calendars[0][0]


    if not target_calendar_id:
        return "❌ **Event Creation Failed:** No suitable calendar found for event creation."

    try:
        # Ensure times are in Toronto timezone for consistency
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Parse input times as UTC and then ensure they are timezone-aware for Google Calendar API
        # Google Calendar API expects RFC3339 format with Z for UTC or offset
        
        # Attempt to parse as datetime with timezone, then convert to Toronto, then to UTC for API
        try:
            # If start_time/end_time are already ISO format with Z or offset, fromisoformat handles it
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # If they are naive, assume they are local Toronto time and make them timezone-aware
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
            if end_dt.tzinfo is None:
                end_dt = toronto_tz.localize(end_dt)

            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()

        except ValueError:
            # Fallback for simpler date strings if fromisoformat fails
            # This might need more robust parsing depending on user input flexibility
            print(f"⚠️ Could not parse '{start_time}' or '{end_time}' as full ISO. Attempting simpler parse.")
            # For simplicity, if it's just a date, treat as all day, otherwise try to parse as Toronto time
            if 'T' not in start_time and 'T' not in end_time: # Likely all-day event
                event = {
                    'summary': title,
                    'start': {'date': start_time},
                    'end': {'date': end_time},
                    'description': description,
                }
            else: # Try to parse as Toronto time
                try:
                    start_dt = toronto_tz.localize(datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S'))
                    end_dt = toronto_tz.localize(datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S'))
                    start_iso = start_dt.isoformat()
                    end_iso = end_dt.isoformat()
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
                except ValueError as ve:
                    print(f"❌ Failed to parse date/time strings for event creation: {ve}")
                    return f"❌ **Event Creation Failed:** Invalid date/time format for '{title}'. Please use YYYY-MM-DDTHH:MM:SS format."
        
        # Create event object (assuming dateTime format for most cases)
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
        # Convert times to Toronto timezone for display
        display_start_dt = datetime.fromisoformat(created_event['start'].get('dateTime', created_event['start'].get('date')).replace('Z', '+00:00')).astimezone(toronto_tz)
        display_end_dt = datetime.fromisoformat(created_event['end'].get('dateTime', created_event['end'].get('date')).replace('Z', '+00:00')).astimezone(toronto_tz)
        
        return f"✅ **Event Created:** {title}\n📅 **When:** {display_start_dt.strftime('%A, %B %d at %I:%M %p')} - {display_end_dt.strftime('%I:%M %p')}\n🗓️ **Calendar:** {target_calendar_name}\n🔗 **Link:** {created_event.get('htmlLink', 'Available in calendar')}"
        
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return f"❌ **Event Creation Failed:** Unable to create '{title}' - please try again or create manually"

def reschedule_event(event_search, new_start_time, new_end_time):
    """Reschedule an existing calendar event in an accessible Google Calendar"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Event Rescheduling:** Calendar integration not configured or no accessible calendars."
    
    try:
        # Search for the event across all accessible calendars
        toronto_tz = pytz.timezone('America/Toronto')
        today = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        week_later = today + timedelta(days=7) # Search up to 7 days from now
        
        today_utc = today.astimezone(pytz.UTC)
        week_later_utc = week_later.astimezone(pytz.UTC)
        
        found_event = None
        found_calendar_id = None
        found_calendar_name = None
        
        for name, cal_id, cal_type in accessible_calendars:
            try:
                events = calendar_service.events().list(
                    calendarId=cal_id,
                    timeMin=today_utc.isoformat(),
                    timeMax=week_later_utc.isoformat(),
                    q=event_search,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                if events.get('items'):
                    found_event = events['items'][0]  # Get first match
                    found_calendar_id = cal_id
                    found_calendar_name = name
                    break # Found the event, stop searching
                    
            except Exception as e:
                print(f"❌ Error searching calendar {cal_id}: {e}")
                continue
        
        if not found_event:
            return f"❌ **Event Not Found:** No event matching '{event_search}' found in your accessible calendars."
        
        # Parse new times and ensure they are timezone-aware for Google Calendar API
        try:
            new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', '+00:00'))
            new_end_dt = datetime.fromisoformat(new_end_time.replace('Z', '+00:00'))

            if new_start_dt.tzinfo is None:
                new_start_dt = toronto_tz.localize(new_start_dt)
            if new_end_dt.tzinfo is None:
                new_end_dt = toronto_tz.localize(new_end_dt)

            new_start_iso = new_start_dt.isoformat()
            new_end_iso = new_end_dt.isoformat()

        except ValueError as ve:
            print(f"❌ Failed to parse new date/time strings for reschedule: {ve}")
            return f"❌ **Rescheduling Failed:** Invalid new date/time format. Please use YYYY-MM-DDTHH:MM:SS format."

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
        display_start_dt = datetime.fromisoformat(updated_event['start'].get('dateTime', updated_event['start'].get('date')).replace('Z', '+00:00')).astimezone(toronto_tz)
        display_end_dt = datetime.fromisoformat(updated_event['end'].get('dateTime', updated_event['end'].get('date')).replace('Z', '+00:00')).astimezone(toronto_tz)
        
        return f"✅ **Event Rescheduled:** {updated_event['summary']}\n📅 **New Time:** {display_start_dt.strftime('%A, %B %d at %I:%M %p')} - {display_end_dt.strftime('%I:%M %p')}\n🗓️ **Calendar:** {found_calendar_name}\n🔗 **Link:** {updated_event.get('htmlLink', 'Available in calendar')}"
        
    except Exception as e:
        print(f"❌ Error rescheduling event: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return f"❌ **Rescheduling Failed:** Unable to reschedule '{event_search}' - please try again or update manually"

def find_meeting_time(duration_minutes, preferred_day=None, preferred_start_hour=9, preferred_end_hour=17):
    """Find available meeting time slots in accessible Google Calendars"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Meeting Time Search:** Calendar integration not configured or no accessible calendars."
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Set search range
        if preferred_day:
            try:
                # Attempt to parse preferred_day, default to today if invalid
                search_start = toronto_tz.localize(datetime.strptime(preferred_day, '%Y-%m-%d')).replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                search_start = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            search_start = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        search_end = search_start + timedelta(days=7)  # Search next 7 days
        
        # Convert to UTC for API
        search_start_utc = search_start.astimezone(pytz.UTC)
        search_end_utc = search_end.astimezone(pytz.UTC)
        
        # Get all events from all accessible calendars
        all_events = []
        for name, cal_id, cal_type in accessible_calendars:
            try:
                events = get_calendar_events(cal_id, search_start_utc, search_end_utc)
                all_events.extend(events)
            except Exception as e:
                print(f"❌ Error getting events from calendar {cal_id}: {e}")
                continue
        
        # Process events to create busy intervals
        busy_intervals = []
        for event in all_events:
            start_time_str = event['start'].get('dateTime', event['start'].get('date'))
            end_time_str = event['end'].get('dateTime', event['end'].get('date'))
            
            try:
                if 'T' in start_time_str: # Has time component
                    start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00')).astimezone(toronto_tz)
                    end_dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')).astimezone(toronto_tz)
                else: # All-day event
                    start_dt = toronto_tz.localize(datetime.strptime(start_time_str, '%Y-%m-%d')).replace(hour=0, minute=0, second=0)
                    end_dt = toronto_tz.localize(datetime.strptime(end_time_str, '%Y-%m-%d')).replace(hour=23, minute=59, second=59)
                busy_intervals.append((start_dt, end_dt))
            except ValueError as ve:
                print(f"⚠️ Skipping event due to date parsing error: {ve} - {event.get('summary')}")
                continue
        
        # Sort busy intervals by start time
        busy_intervals.sort(key=lambda x: x[0])
        
        available_slots = []
        current_check_day = search_start # Start checking from the beginning of the preferred day or today

        for day_offset in range(7): # Check next 7 days
            day_start_time = current_check_day.replace(hour=preferred_start_hour, minute=0, second=0, microsecond=0)
            day_end_time = current_check_day.replace(hour=preferred_end_hour, minute=0, second=0, microsecond=0)

            # Ensure day_start_time is not in the past relative to now
            if day_start_time < datetime.now(toronto_tz):
                day_start_time = datetime.now(toronto_tz) # Start from current time if it's past preferred_start_hour

            # Filter busy intervals for the current day
            daily_busy_intervals = [
                (start, end) for start, end in busy_intervals
                if start.date() == current_check_day.date() or end.date() == current_check_day.date()
            ]

            # Initialize current available time for the day
            current_available_pointer = day_start_time

            for busy_start, busy_end in daily_busy_intervals:
                # If there's a gap before the busy interval
                if busy_start > current_available_pointer:
                    potential_slot_end = min(busy_start, day_end_time)
                    if (potential_slot_end - current_available_pointer).total_seconds() >= duration_minutes * 60:
                        available_slots.append(f"• {current_check_day.strftime('%A, %B %d')}: {current_available_pointer.strftime('%I:%M %p')} - {potential_slot_end.strftime('%I:%M %p')}")
                
                # Move pointer past the current busy interval
                current_available_pointer = max(current_available_pointer, busy_end)
                
                if len(available_slots) >= 5: # Limit to 5 suggestions
                    break
            
            # Check for remaining time after the last busy interval
            if current_available_pointer < day_end_time:
                if (day_end_time - current_available_pointer).total_seconds() >= duration_minutes * 60:
                    available_slots.append(f"• {current_check_day.strftime('%A, %B %d')}: {current_available_pointer.strftime('%I:%M %p')} - {day_end_time.strftime('%I:%M %p')}")

            current_check_day += timedelta(days=1) # Move to the next day

            if len(available_slots) >= 5: # Limit to 5 suggestions
                break
        
        if not available_slots:
            return f"⏰ **Meeting Time Search:** No {duration_minutes}-minute slots found in next 7 days during business hours\n\n💡 **Suggestion:** Consider extending search range or adjusting meeting duration"
        
        return f"⏰ **Available Meeting Times ({duration_minutes} minutes):**\n\n" + "\n".join(available_slots[:5])
        
    except Exception as e:
        print(f"❌ Error finding meeting time: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return f"❌ **Meeting Time Search Failed:** Unable to find available slots - please try again or check calendars manually"

# ============================================================================
# ENHANCED FUNCTION HANDLING
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with comprehensive error checking"""
    
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
                    
                    # Create output with embedded source information
                    output = f"📊 **Planning Research:** {query}\n\n{search_results}"
                    
                    # Add source information for Rose to use
                    if sources:
                        output += "\n\n📚 **Available Sources:**\n"
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
                calendar_type = arguments.get('calendar_type', 'primary')
                description = arguments.get('description', '')
                
                if title and start_time and end_time:
                    output = create_calendar_event(title, start_time, end_time, calendar_type, description)
                else:
                    output = "❌ **Event Creation:** Missing required details (title, start time, end time)"
                    
            elif function_name == "reschedule_event":
                event_search = arguments.get('event_search', '')
                new_start_time = arguments.get('new_start_time', '')
                new_end_time = arguments.get('new_end_time', '')
                
                if event_search and new_start_time and new_end_time:
                    output = reschedule_event(event_search, new_start_time, new_end_time)
                else:
                    output = "❌ **Event Rescheduling:** Missing required details (event search, new start time, new end time)"
                    
            elif function_name == "find_meeting_time":
                duration_minutes = arguments.get('duration_minutes', 60)
                preferred_day = arguments.get('preferred_day', None)
                preferred_start_hour = arguments.get('preferred_start_hour', 9)
                preferred_end_hour = arguments.get('preferred_end_hour', 17)
                
                output = find_meeting_time(duration_minutes, preferred_day, preferred_start_hour, preferred_end_hour)
                
            elif function_name == "find_free_time": # Placeholder function
                duration = arguments.get('duration', 60)
                date = arguments.get('date', '')
                output = f"⏰ **Free Time Analysis ({duration}min):**\n\n🎯 **Strategic Blocks (Toronto Time):**\n• Early morning: Deep work (6-8am)\n• Mid-morning: Meetings (9-11am)\n• Afternoon: Administrative (2-4pm)\n\n💡 **Tip:** Schedule {duration}-minute blocks for maximum productivity"
                
            elif function_name == "search_emails": # Placeholder function
                query = arguments.get('query', '')
                max_results = arguments.get('max_results', 5)
                if query:
                    output = f"📧 **Email Search:** '{query}'\n\n🎯 **Executive Summary:**\n• 3 priority emails requiring response\n• 2 scheduling requests pending\n• 1 strategic decision needed\n\n💡 **Tip:** Use email templates for faster responses"
                else:
                    output = "📧 No email search query provided"
                
            else:
                output = f"❓ Unknown function: {function_name}"
                print(f"⚠️ Unhandled function call: {function_name}")
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            output = f"❌ Error executing {function_name}: Please try again"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Keep within Discord limits
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
        else:
            print("⚠️ No tool outputs to submit")
    except Exception as e:
        print(f"❌ Error submitting tool outputs: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")

# ============================================================================
# MAIN CONVERSATION HANDLER
# ============================================================================

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with comprehensive error handling"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Check if user already has an active run
        if user_id in active_runs:
            return "👑 Rose is currently analyzing your executive strategy. Please wait a moment..."
        
        # Mark user as having active run
        active_runs[user_id] = True
        
        # Get user's thread
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"👑 Created executive thread for user {user_id}")
        
        thread_id = user_conversations[user_id]
        
        # Clean message
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
        
        # Build string of accessible calendar names for the prompt
        accessible_cal_names = ", ".join([name for name, _, _ in accessible_calendars])
        if not accessible_cal_names:
            accessible_cal_names = "no calendars configured"

        # Enhanced message with executive planning focus + calendar intelligence
        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- SMART CALENDAR DETECTION: Automatically detect if this is a general or specific calendar query
- GENERAL CALENDAR QUERIES (auto-include full schedule): "what's on my calendar", "what's my schedule", "what do I have today", "how does my day look", "what's happening today"
- SPECIFIC CALENDAR QUERIES (answer directly): "what do I have after 5pm", "am I free at 2pm", "what's my first meeting", "when is my next call"
- When using calendar functions, provide insights from accessible calendars: {accessible_cal_names}
- For planning research, include actionable productivity recommendations
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- IMPORTANT: Always provide strategic context and actionable next steps

CALENDAR MANAGEMENT CAPABILITIES:
- Create calendar events with create_calendar_event()
- Reschedule existing events with reschedule_event()
- Find available meeting times with find_meeting_time()
- All times are in Toronto timezone (America/Toronto)"""
        
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
        
        # Run assistant with executive instructions
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID,
                instructions=f"""You are Rose Ashcombe, executive assistant with enhanced Google calendar and planning research capabilities plus calendar event management.

EXECUTIVE APPROACH:
- Use calendar functions for insights from accessible calendars: {accessible_cal_names}
- Use planning_search for productivity and planning information
- SMART CALENDAR DETECTION: Automatically detect general vs specific calendar queries
- GENERAL QUERIES: Auto-call get_today_schedule() and provide executive insights
- SPECIFIC QUERIES: Answer directly without full schedule
- Use create_calendar_event(), reschedule_event(), find_meeting_time() for calendar management
- Apply strategic thinking with systems optimization
- Provide actionable recommendations with clear timelines
- Focus on executive-level insights and life management
- All times are in Toronto timezone (America/Toronto)

CALENDAR QUERY DETECTION:
- GENERAL (auto-include schedule): "what's on my calendar", "what's my schedule", "what do I have today", "how does my day look", "what's happening today"
- SPECIFIC (answer directly): "what do I have after 5pm", "am I free at 2pm", "what's my first meeting", "when is my next call"

FORMATTING: Use professional executive formatting with strategic headers (👑 📊 📅 📧 💼) and provide organized, action-oriented guidance.

ENHANCED EXECUTIVE STRUCTURE:
👑 **Executive Summary:** [strategic overview with key insights]
📅 **Calendar Overview:** [schedule from get_today_schedule() for general queries]
💼 **Executive Insights:** [brief insights: event count, next meeting, largest time block]
📊 **Action Items:** [specific next steps with timing]

Keep core content focused and always provide strategic executive context."""
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
            return "⏱️ Executive office is busy analyzing complex strategies. Please try again in a moment."
        
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
        return "❌ Something went wrong with executive guidance. Please try again!"
    finally:
        # Always remove user from active runs when done
        active_runs.pop(user_id, None)

def format_for_discord_rose(response):
    """Format response for Discord with executive styling"""
    try:
        if not response or not isinstance(response, str):
            return "👑 Executive guidance processing. Please try again."
        
        # Clean excessive spacing
        response = response.replace('\n\n\n\n', '\n\n')
        response = response.replace('\n\n\n', '\n\n')
        
        # Tighten list formatting
        response = re.sub(r'\n\n(\d+\.)', r'\n\1', response)
        response = re.sub(r'\n\n(•)', r'\n•', response)
        
        # Length management
        if len(response) > 1900:
            response = response[:1900] + "\n\n👑 *(Executive insights continue)*"
        
        print(f"👑 Final response: {len(response)} characters")
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
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup event with enhanced status reporting"""
    try:
        print(f"👑 {ASSISTANT_NAME} is online!")
        print(f"🤖 Connected as: {bot.user}")
        print(f"🆔 Bot ID: {bot.user.id}")
        print(f"🎯 Assistant ID: {ASSISTANT_ID}")
        print(f"📅 Calendar Integration: {'✅ Active' if calendar_service and accessible_calendars else '❌ Disabled'}")
        print(f"🔍 Search Integration: {'✅ Active' if BRAVE_API_KEY else '❌ Disabled'}")
        print(f"📺 Allowed Channels: {', '.join(ALLOWED_CHANNELS)}")
        print("🚀 Ready for executive planning and Google Calendar management!")
        
        # Set bot status based on accessible calendars
        status_text = "📅 Google Calendar"
        if any(cal_type == "tasks" for _, _, cal_type in accessible_calendars):
            status_text += " • ✅ Tasks"
        
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=status_text
            ),
            status=discord.Status.online
        )
    except Exception as e:
        print(f"❌ Error in on_ready: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_message(message):
    """Enhanced message handling with comprehensive error checking"""
    try:
        # Skip bot's own messages
        if message.author == bot.user:
            return
        
        # Process commands first
        await bot.process_commands(message)
        
        # Only respond in allowed channels or DMs
        if not isinstance(message.channel, discord.DMChannel) and message.channel.name not in ALLOWED_CHANNELS:
            return

        # Respond to mentions or DMs
        if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            
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
        print(f"❌ Critical on_message error: {e}")
        print(f"📋 Critical traceback: {traceback.format_exc()}")

# ============================================================================
# DISCORD COMMANDS - ENHANCED WITH GOOGLE CALENDAR SUPPORT
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's responsiveness with team-consistent styling"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Pong! Executive operations active!")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's enhanced capabilities"""
    try:
        embed = discord.Embed(
            title=f"👑 {ASSISTANT_NAME} - Status Report",
            description=f"**{ASSISTANT_ROLE}**",
            color=0xd4af37
        )
        
        calendar_status_value = ""
        if calendar_service and accessible_calendars:
            for name, _, _ in accessible_calendars:
                calendar_status_value += f"• {name}: ✅\n"
            calendar_status_value += f"🔧 Service: ✅"
        else:
            calendar_status_value = "❌ Not configured or accessible"

        embed.add_field(
            name="🗓️ Google Calendar Integration",
            value=calendar_status_value,
            inline=True
        )
        
        embed.add_field(
            name="🔧 Executive Functions",
            value="📅 Today's Schedule\n📊 Weekly Planning\n🌅 Morning Briefings\n⏰ Free Time Analysis\n🔍 Planning Research\n📧 Email Management\n➕ Create Event\n🔄 Reschedule Event\n⏱️ Find Meeting Time",
            inline=True
        )
        
        embed.add_field(
            name="📺 Channels",
            value="\n".join([f"#{channel}" for channel in ALLOWED_CHANNELS]),
            inline=True
        )
        
        embed.add_field(
            name="🕐 Timezone",
            value="🇨🇦 Toronto (America/Toronto)",
            inline=True
        )
        
        embed.add_field(
            name="📊 Active Status",
            value=f"👥 Conversations: {len(user_conversations)}\n🏃 Active Runs: {len(active_runs)}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Status command error: {e}")

@bot.command(name='help')
async def help_command(ctx):
    """Show Rose's enhanced help"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Your strategic planning specialist with Google Calendar integration and productivity optimization",
            color=0xd4af37
        )
        
        embed.add_field(
            name="💬 How to Use Rose",
            value=f"• Mention @{ASSISTANT_NAME} for executive planning & productivity advice\n• Ask about time management, scheduling, productivity systems\n• Get strategic insights based on your Google Calendars and goals",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Executive Commands",
            value="• `!schedule` - Get today's schedule from all calendars\n• `!upcoming [days]` - View upcoming events\n• `!briefing` - Morning briefing with all calendars\n• `!plan [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - Show capabilities",
            inline=False
        )
        
        embed.add_field(
            name="👑 Example Requests",
            value="• `@Rose give me my morning briefing`\n• `@Rose help me plan my week strategically`\n• `@Rose what's the best time blocking method?`\n• `@Rose analyze my schedule for optimization`\n• `@Rose create an event 'Team Sync' for tomorrow 10 AM to 11 AM`\n• `@Rose reschedule 'Project Review' to next Monday at 2 PM`\n• `@Rose find a 30-minute meeting slot for me`",
            inline=False
        )
        
        accessible_cal_names_for_help = ", ".join([name for name, _, _ in accessible_calendars])
        if not accessible_cal_names_for_help:
            accessible_cal_names_for_help = "No Google Calendars configured."

        embed.add_field(
            name="📊 Google Calendar Support",
            value=f"Integrated Calendars: {accessible_cal_names_for_help}\n🇨🇦 Toronto Time • 🎯 Productivity Systems",
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Help command error: {e}")

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's schedule with error handling"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await ctx.send(schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("❌ Error retrieving schedule. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Get upcoming events with error handling"""
    try:
        if days < 1 or days > 14: # Limit to a reasonable range
            days = 7
        async with ctx.typing():
            events = get_upcoming_events(days)
            await ctx.send(events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("❌ Error retrieving upcoming events. Please try again.")

@bot.command(name='briefing')
async def morning_briefing_command(ctx):
    """Get morning briefing with error handling"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await ctx.send(briefing)
    except Exception as e:
        print(f"❌ Morning briefing command error: {e}")
        await ctx.send("❌ Error generating morning briefing. Please try again.")

@bot.command(name='plan')
async def planning_search_command(ctx, *, query):
    """Planning research command"""
    try:
        async with ctx.typing():
            search_results, sources = await planning_search_enhanced(query, "planning", 3)
            
            response = f"📊 **Planning Research:** {query}\n\n{search_results}"
            
            if len(response) > 1900: # Truncate if too long for initial send
                response = response[:1900] + "..."
            
            await ctx.send(response)
    except Exception as e:
        print(f"❌ Planning search command error: {e}")
        await ctx.send("❌ Error performing planning research. Please try again.")

# ============================================================================
# ERROR HANDLING AND CLEANUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Command error handler"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================\
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print(f"🚀 Launching {ASSISTANT_NAME}...")
        print(f"📅 Google Calendar Support: {bool(accessible_calendars)}")
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
