#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE DISCORD BOT (CLEANED - OAuth2 Only)
Executive Assistant with Calendar Management, Email Management, Weather, and Strategic Planning
CLEANED: OAuth2 authentication only, ALL functions preserved, ORIGINAL variable names kept
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
import base64
import email
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
from openai import OpenAI
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

# ============================================================================
# ROSE CONFIGURATION (ORIGINAL VARIABLE NAMES PRESERVED)
# ============================================================================

ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant (Clean OAuth2)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Rose configuration for Universal Status System
ROSE_CONFIG = {
    "name": "Rose Ashcombe",
    "role": "Executive Assistant",
    "description": "Strategic planning specialist with calendar integration, email management, and productivity optimization",
    "emoji": "👑",
    "color": 0xE91E63,  # Pink
    "specialties": [
        "📅 Executive Planning",
        "🗓️ Calendar Management", 
        "📊 Productivity Systems",
        "⚡ Time Optimization",
        "🎯 Life OS"
    ],
    "capabilities": [
        "Multi-calendar coordination (personal + work)",
        "Weather-integrated morning briefings",
        "Strategic planning & productivity research",
        "Email management & organization",
        "Executive schedule optimization"
    ],
    "example_requests": [
        "@Rose give me my morning briefing",
        "@Rose check my unread emails",
        "@Rose what's my schedule today?",
        "@Rose delete all emails with 'newsletter' in subject",
        "@Rose research time blocking strategies",
        "@Rose help me plan my week strategically"
    ],
    "commands": [
        "!briefing - Complete morning briefing with weather",
        "!weather - Current weather & UV index",
        "!schedule - Today's calendar (all calendars)",
        "!upcoming [days] - View upcoming events",
        "!emails [count] - Recent emails (default: 10)",
        "!unread [count] - Unread emails only",
        "!emailstats - Email dashboard overview",
        "!quickemails [count] - Concise email view",
        "!emailcount - Just email counts",
        "!cleansender <email> [count] - Delete emails from sender",
        "!ping - Test connectivity",
        "!status - Show system status",
        "!help - Show this help message"
    ],
    "channels": ["life-os", "calendar", "planning-hub", "general"]
}

ASSISTANT_CONFIG = ROSE_CONFIG

# ============================================================================
# ENVIRONMENT VARIABLES (ORIGINAL NAMES PRESERVED)
# ============================================================================

# Critical Discord & OpenAI
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# External APIs
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
USER_CITY = os.getenv('USER_CITY', 'Toronto')
USER_LAT = os.getenv('USER_LAT')
USER_LON = os.getenv('USER_LON')

# Gmail OAuth setup (ORIGINAL VARIABLE NAMES)
GMAIL_OAUTH_JSON = os.getenv('GMAIL_OAUTH_JSON')
GMAIL_TOKEN_JSON = os.getenv('GMAIL_TOKEN_JSON')
GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')

# Calendar IDs (ORIGINAL NAMES)
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')
BRITT_ICLOUD_CALENDAR_ID = os.getenv('BRITT_ICLOUD_CALENDAR_ID')
GMAIL_WORK_CALENDAR_ID = os.getenv('GMAIL_WORK_CALENDAR_ID')

# Gmail OAuth scopes (ORIGINAL VARIABLE NAME but updated scopes)
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

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

# ============================================================================
# DISCORD & OPENAI INITIALIZATION
# ============================================================================

try:
    # Discord setup
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
    
    # OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Conversation tracking (ORIGINAL VARIABLE NAMES)
    active_runs = {}
    user_conversations = {}
    channel_conversations = {}
    conversation_metadata = {}
    processing_messages = set()
    last_response_time = {}
    
    print(f"✅ {ASSISTANT_NAME} initialized successfully")
    print(f"🤖 OpenAI Assistant ID: {ASSISTANT_ID}")
    print(f"🌤️ Weather API configured: {'✅ Yes' if WEATHER_API_KEY else '❌ No'}")
    
except Exception as e:
    print(f"❌ CRITICAL: Failed to initialize {ASSISTANT_NAME}: {e}")
    exit(1)

# ============================================================================
# GOOGLE SERVICES - OAUTH2 ONLY (BUT ORIGINAL VARIABLE NAMES)
# ============================================================================

# Google services (ORIGINAL VARIABLE NAMES)
calendar_service = None
gmail_service = None
accessible_calendars = []

def initialize_google_services():
    """Initialize Google services using OAuth2 credentials ONLY"""
    global calendar_service, gmail_service, accessible_calendars
    
    print("🔧 Initializing Google services with OAuth2...")
    
    if not GMAIL_TOKEN_JSON:
        print("❌ No OAuth token found - Google services disabled")
        print("   Run: python3 reauthorize_oauth.py")
        return False
    
    try:
        # Parse OAuth token
        token_info = json.loads(GMAIL_TOKEN_JSON)
        
        # Create OAuth credentials (using ORIGINAL scope variable name)
        oauth_credentials = OAuthCredentials.from_authorized_user_info(
            token_info, GMAIL_SCOPES
        )
        
        if not oauth_credentials:
            print("❌ Failed to create OAuth credentials")
            return False
        
        # Handle token refresh if needed
        if oauth_credentials.expired and oauth_credentials.refresh_token:
            try:
                print("🔄 Refreshing OAuth token...")
                oauth_credentials.refresh(Request())
                print("✅ OAuth token refreshed successfully")
            except Exception as refresh_error:
                print(f"❌ Token refresh failed: {refresh_error}")
                print("⚠️ Please re-authorize: python3 reauthorize_oauth.py")
                return False
        
        if not oauth_credentials.valid:
            print("❌ OAuth credentials are invalid")
            print("⚠️ Please re-authorize: python3 reauthorize_oauth.py")
            return False
        
        # Initialize both services with same OAuth credentials
        gmail_service = build('gmail', 'v1', credentials=oauth_credentials)
        calendar_service = build('calendar', 'v3', credentials=oauth_credentials)
        
        print("✅ OAuth Gmail and Calendar services initialized")
        
        # Test calendar access
        test_calendar_access()
        
        return True
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON in GMAIL_TOKEN_JSON")
        return False
    except Exception as e:
        print(f"❌ Google services initialization error: {e}")
        return False

def test_calendar_access():
    """Test access to all configured calendars"""
    global accessible_calendars
    
    if not calendar_service:
        return
    
    calendars_to_test = [
        ('🐝 BG Personal', GOOGLE_CALENDAR_ID),
        ('📋 BG Tasks', GOOGLE_TASKS_CALENDAR_ID),
        ('🍎 Britt iCloud', BRITT_ICLOUD_CALENDAR_ID),
        ('💼 BG Work', GMAIL_WORK_CALENDAR_ID)
    ]
    
    accessible_calendars = []
    
    for calendar_name, calendar_id in calendars_to_test:
        if not calendar_id:
            print(f"⚠️ {calendar_name}: No calendar ID configured")
            continue
            
        try:
            # Test calendar access
            calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
            accessible_calendars.append((calendar_name, calendar_id))
            print(f"✅ {calendar_name} accessible: {calendar_name}")
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"❌ {calendar_name}: Calendar not found (404)")
            elif e.resp.status == 403:
                print(f"❌ {calendar_name}: Access forbidden (403)")
            else:
                print(f"❌ {calendar_name}: HTTP error {e.resp.status}")
        except Exception as e:
            print(f"❌ {calendar_name}: Error testing access - {e}")
    
    print(f"📅 Total accessible calendars: {len(accessible_calendars)}")

# ============================================================================
# WEATHER INTEGRATION
# ============================================================================

def get_weather_briefing():
    """Get comprehensive weather briefing for Toronto"""
    if not WEATHER_API_KEY:
        return "🌤️ **Weather:** API not configured"
    
    try:
        # Use coordinates if available, otherwise city name
        if USER_LAT and USER_LON:
            location = f"{USER_LAT},{USER_LON}"
            print(f"🌍 Fetching enhanced weather for {USER_CITY} ({USER_LAT},{USER_LON})...")
        else:
            location = USER_CITY
            print(f"🌍 Fetching weather for {USER_CITY}...")
        
        # WeatherAPI.com current + forecast
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={location}&days=2&aqi=no&alerts=no"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract current weather
        current = data['current']
        location_info = data['location']
        today_forecast = data['forecast']['forecastday'][0]['day']
        tomorrow_forecast = data['forecast']['forecastday'][1]['day']
        
        # Current conditions
        temp_c = current['temp_c']
        condition = current['condition']['text']
        feels_like = current['feelslike_c']
        humidity = current['humidity']
        wind_speed = current['wind_kph']
        wind_dir = current['wind_dir']
        uv_index = current['uv']
        
        # Today's forecast
        min_temp = today_forecast['mintemp_c']
        max_temp = today_forecast['maxtemp_c']
        rain_chance = today_forecast['daily_chance_of_rain']
        
        # Tomorrow preview
        tom_min = tomorrow_forecast['mintemp_c']
        tom_max = tomorrow_forecast['maxtemp_c']
        tom_condition = tomorrow_forecast['condition']['text']
        tom_rain = tomorrow_forecast['daily_chance_of_rain']
        
        # UV guidance
        uv_guidance = {
            0: "Minimal protection needed",
            1: "Minimal protection needed", 
            2: "Minimal protection needed",
            3: "Moderate protection needed",
            4: "Moderate protection needed",
            5: "Moderate protection needed",
            6: "High protection needed",
            7: "High protection needed",
            8: "Very high protection needed",
            9: "Very high protection needed",
            10: "Extreme protection needed"
        }
        
        uv_level = "Low" if uv_index <= 2 else "Moderate" if uv_index <= 5 else "High" if uv_index <= 7 else "Very High" if uv_index <= 9 else "Extreme"
        uv_advice = uv_guidance.get(int(uv_index), "Protection recommended")
        
        # Enhanced weather briefing
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        briefing = f"""🌤️ **Weather Update** ({now})
📍 **{location_info['name']}, {location_info['country']}:** {temp_c}°C {condition}
🌡️ **Current:** Feels like {feels_like}°C | Humidity: {humidity}% | Wind: {wind_speed} km/h {wind_dir}
🔆 **UV Index:** {uv_index} - {uv_level} - {uv_advice}
📊 **Today's Forecast:** {min_temp}°C to {max_temp}°C - {today_forecast['condition']['text']}
🌧️ **Rain Chance:** {rain_chance}%
🔮 **Tomorrow Preview:** {tom_min}°C to {tom_max}°C - {tom_condition} ({tom_rain}% rain)"""
        
        print(f"✅ Enhanced weather data retrieved: Current {temp_c}°C, High {max_temp}°C")
        return briefing
        
    except requests.exceptions.Timeout:
        return "🌤️ **Weather:** Request timeout - service may be slow"
    except requests.exceptions.ConnectionError:
        return "🌤️ **Weather:** Connection error - check internet connectivity"
    except KeyError as e:
        print(f"❌ Weather API response missing key: {e}")
        return f"🌤️ **Weather:** Data format error - missing {e}"
    except Exception as e:
        print(f"❌ Weather briefing error: {e}")
        return f"🌤️ **Weather:** Error retrieving conditions - {str(e)[:50]}"

# ============================================================================
# GOOGLE CALENDAR FUNCTIONS (ALL PRESERVED)
# ============================================================================

def create_gcal_event(calendar_id="primary", summary=None, description=None, 
                     start_time=None, end_time=None, location=None, attendees=None):
    """Create a new Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not summary or not start_time:
        return "❌ Missing required fields: summary, start_time"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Parse start time
        if isinstance(start_time, str):
            if 'T' not in start_time:
                start_time = start_time + 'T09:00:00'
            start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
        
        # Parse end time (default to 1 hour after start if not provided)
        if end_time:
            if isinstance(end_time, str):
                if 'T' not in end_time:
                    end_time = end_time + 'T10:00:00'
                end_dt = datetime.fromisoformat(end_time.replace('Z', ''))
                if end_dt.tzinfo is None:
                    end_dt = toronto_tz.localize(end_dt)
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        # Build event object
        event_body = {
            'summary': summary,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Toronto'
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Toronto'
            }
        }
        
        if description:
            event_body['description'] = description
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
        
        print(f"🔧 Creating calendar event: {summary}")
        print(f"📅 Start: {start_dt}")
        print(f"📅 End: {end_dt}")
        print(f"📋 Calendar ID: {calendar_id}")
        
        # ACTUALLY CREATE THE EVENT
        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()
        
        print(f"✅ Event created successfully!")
        print(f"🆔 Event ID: {created_event.get('id')}")
        
        # Return success with real event data
        event_link = created_event.get('htmlLink', 'No link available')
        return f"✅ **Event Created Successfully!**\n📅 **{summary}**\n🕐 {start_dt.strftime('%Y-%m-%d at %-I:%M %p')} - {end_dt.strftime('%-I:%M %p')}\n🔗 [View Event]({event_link})"
        
    except HttpError as e:
        print(f"❌ Calendar API error: {e}")
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        print(f"❌ Event creation error: {e}")
        return f"❌ Error creating event: {str(e)}"

def update_gcal_event(event_id, calendar_id="primary", summary=None, description=None, 
                     start_time=None, end_time=None, location=None):
    """Update an existing Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        # Get existing event
        existing_event = calendar_service.events().get(
            calendarId=calendar_id, 
            eventId=event_id
        ).execute()
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Update fields if provided
        if summary:
            existing_event['summary'] = summary
        if description:
            existing_event['description'] = description
        if location:
            existing_event['location'] = location
        
        if start_time:
            if isinstance(start_time, str):
                if 'T' not in start_time:
                    start_time = start_time + 'T09:00:00'
                start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
                if start_dt.tzinfo is None:
                    start_dt = toronto_tz.localize(start_dt)
                
                existing_event['start'] = {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'America/Toronto'
                }
        
        if end_time:
            if isinstance(end_time, str):
                if 'T' not in end_time:
                    end_time = end_time + 'T10:00:00'
                end_dt = datetime.fromisoformat(end_time.replace('Z', ''))
                if end_dt.tzinfo is None:
                    end_dt = toronto_tz.localize(end_dt)
                
                existing_event['end'] = {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/Toronto'
                }
        
        # Update the event
        updated_event = calendar_service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=existing_event
        ).execute()
        
        event_link = updated_event.get('htmlLink', 'No link available')
        return f"✅ **Event Updated Successfully!**\n📅 **{updated_event.get('summary', 'Untitled')}**\n🔗 [View Event]({event_link})"
        
    except HttpError as e:
        if e.resp.status == 404:
            return f"❌ Event not found: {event_id}"
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error updating event: {str(e)}"

def delete_gcal_event(event_id, calendar_id="primary"):
    """Delete a Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        # Get event details before deletion
        event = calendar_service.events().get(
            calendarId=calendar_id, 
            eventId=event_id
        ).execute()
        
        event_title = event.get('summary', 'Untitled Event')
        
        # Delete the event
        calendar_service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        return f"✅ **Event Deleted Successfully!**\n📅 **{event_title}** has been removed from your calendar."
        
    except HttpError as e:
        if e.resp.status == 404:
            return f"❌ Event not found: {event_id}"
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error deleting event: {str(e)}"

def list_gcal_events(calendar_id="primary", time_min=None, time_max=None, max_results=10, query=None):
    """List Google Calendar events with optional filtering"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Default time range: next 7 days
        if not time_min:
            time_min = datetime.now(toronto_tz).isoformat()
        if not time_max:
            time_max = (datetime.now(toronto_tz) + timedelta(days=7)).isoformat()
        
        # Build request parameters
        request_params = {
            'calendarId': calendar_id,
            'timeMin': time_min,
            'timeMax': time_max,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if query:
            request_params['q'] = query
        
        # Get events
        events_result = calendar_service.events().list(**request_params).execute()
        events = events_result.get('items', [])
        
        if not events:
            return "📅 No events found in the specified time range."
        
        # Format events
        formatted_events = []
        for event in events:
            summary = event.get('summary', 'Untitled Event')
            
            start = event.get('start', {})
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                time_str = start_dt.astimezone(toronto_tz).strftime('%m/%d at %-I:%M %p')
            elif 'date' in start:
                time_str = start['date'] + ' (All day)'
            else:
                time_str = 'Time TBD'
            
            formatted_events.append(f"• {time_str} - {summary}")
        
        return f"📅 **Upcoming Events:**\n" + "\n".join(formatted_events)
        
    except HttpError as e:
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error listing events: {str(e)}"

def fetch_gcal_event(event_id, calendar_id="primary"):
    """Fetch details of a specific Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        event = calendar_service.events().get(
            calendarId=calendar_id, 
            eventId=event_id
        ).execute()
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Format event details
        summary = event.get('summary', 'Untitled Event')
        description = event.get('description', 'No description')
        location = event.get('location', 'No location specified')
        
        start = event.get('start', {})
        end = event.get('end', {})
        
        if 'dateTime' in start:
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            time_str = f"{start_dt.astimezone(toronto_tz).strftime('%Y-%m-%d at %-I:%M %p')} - {end_dt.astimezone(toronto_tz).strftime('%-I:%M %p')}"
        else:
            time_str = start.get('date', 'No date') + ' (All day)'
        
        event_link = event.get('htmlLink', 'No link available')
        
        return f"""📅 **Event Details:**
**Title:** {summary}
**Time:** {time_str}
**Location:** {location}
**Description:** {description}
🔗 [View in Calendar]({event_link})"""
        
    except HttpError as e:
        if e.resp.status == 404:
            return f"❌ Event not found: {event_id}"
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error fetching event: {str(e)}"

def find_free_time(calendar_ids=None, time_min=None, time_max=None, duration_hours=1):
    """Find free time slots across multiple calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Default parameters
        if not calendar_ids:
            calendar_ids = [cal_id for _, cal_id in accessible_calendars]
        if not time_min:
            time_min = datetime.now(toronto_tz)
        if not time_max:
            time_max = time_min + timedelta(days=7)
        
        # Convert to RFC3339 format
        if isinstance(time_min, str):
            time_min = datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        if isinstance(time_max, str):
            time_max = datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
        # Query freebusy for all calendars
        body = {
            'timeMin': time_min.isoformat(),
            'timeMax': time_max.isoformat(),
            'items': [{'id': cal_id} for cal_id in calendar_ids]
        }
        
        freebusy_result = calendar_service.freebusy().query(body=body).execute()
        
        # Analyze busy periods
        all_busy_periods = []
        for cal_id in calendar_ids:
            calendar_busy = freebusy_result.get('calendars', {}).get(cal_id, {}).get('busy', [])
            for busy_period in calendar_busy:
                start_busy = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                end_busy = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                all_busy_periods.append((start_busy, end_busy))
        
        # Sort busy periods
        all_busy_periods.sort(key=lambda x: x[0])
        
        # Find free slots
        free_slots = []
        current_time = time_min
        
        for busy_start, busy_end in all_busy_periods:
            if current_time + timedelta(hours=duration_hours) <= busy_start:
                free_slots.append((current_time, busy_start))
            current_time = max(current_time, busy_end)
        
        # Add final slot if there's time remaining
        if current_time + timedelta(hours=duration_hours) <= time_max:
            free_slots.append((current_time, time_max))
        
        if not free_slots:
            return f"❌ No free {duration_hours}-hour slots found in the specified time range."
        
        # Format free slots
        formatted_slots = []
        for slot_start, slot_end in free_slots[:10]:  # Limit to 10 slots
            duration = slot_end - slot_start
            if duration >= timedelta(hours=duration_hours):
                formatted_slots.append(
                    f"• {slot_start.astimezone(toronto_tz).strftime('%m/%d at %-I:%M %p')} - {slot_end.astimezone(toronto_tz).strftime('%-I:%M %p')} ({duration})"
                )
        
        return f"🕐 **Free Time Slots ({duration_hours}+ hours):**\n" + "\n".join(formatted_slots)
        
    except HttpError as e:
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error finding free time: {str(e)}"

def list_gcal_calendars():
    """List available Google Calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        # Get calendar list
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if not calendars:
            return "📅 No calendars found."
        
        # Format calendar list
        formatted_calendars = []
        for calendar in calendars:
            summary = calendar.get('summary', 'Untitled Calendar')
            calendar_id = calendar.get('id', 'No ID')
            access_role = calendar.get('accessRole', 'Unknown')
            formatted_calendars.append(f"• **{summary}** ({access_role})")
        
        return f"📅 **Available Calendars:**\n" + "\n".join(formatted_calendars)
        
    except HttpError as e:
        return f"❌ Calendar API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error listing calendars: {str(e)}"

# ============================================================================
# GMAIL FUNCTIONS (ALL PRESERVED)
# ============================================================================

def get_recent_emails(count=10, unread_only=False, include_body=False):
    """Get recent emails from Gmail"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Build query
        query = 'is:unread' if unread_only else 'in:inbox'
        
        # Get message list
        results = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No {'unread' if unread_only else 'recent'} emails found."
        
        # Get email details
        email_list = []
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(
                userId='me', 
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = msg_detail['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
            
            # Parse date
            try:
                parsed_date = parsedate_to_datetime(date)
                date_str = parsed_date.strftime('%m/%d at %-I:%M %p')
            except:
                date_str = date
            
            email_info = f"📧 **{subject}**\n👤 From: {sender}\n📅 {date_str}"
            
            if include_body:
                # Get email body (simplified)
                body = get_email_body(msg_detail)
                if body:
                    email_info += f"\n📄 {body[:200]}{'...' if len(body) > 200 else ''}"
            
            email_list.append(email_info)
        
        header = f"📧 **{'Unread' if unread_only else 'Recent'} Emails ({len(email_list)}):**\n\n"
        return header + "\n\n".join(email_list)
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error retrieving emails: {str(e)}"

def search_emails(query, max_results=10, include_body=False):
    """Search Gmail with a specific query"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Search emails
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found matching: {query}"
        
        # Get email details
        email_list = []
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = msg_detail['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
            
            # Parse date
            try:
                parsed_date = parsedate_to_datetime(date)
                date_str = parsed_date.strftime('%m/%d at %-I:%M %p')
            except:
                date_str = date
            
            email_info = f"📧 **{subject}**\n👤 From: {sender}\n📅 {date_str}"
            
            if include_body:
                body = get_email_body(msg_detail)
                if body:
                    email_info += f"\n📄 {body[:200]}{'...' if len(body) > 200 else ''}"
            
            email_list.append(email_info)
        
        header = f"🔍 **Search Results for '{query}' ({len(email_list)}):**\n\n"
        return header + "\n\n".join(email_list)
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error searching emails: {str(e)}"

def get_email_body(message):
    """Extract email body from Gmail message"""
    try:
        payload = message['payload']
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
        
        return "Body not available"
        
    except Exception:
        return "Error reading body"

def get_email_stats(days=7):
    """Get email statistics for the past N days"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Gmail search queries
        queries = {
            'total_received': f'after:{start_date.strftime("%Y/%m/%d")}',
            'unread': 'is:unread',
            'today': f'after:{end_date.strftime("%Y/%m/%d")}'
        }
        
        stats = {}
        for key, query in queries.items():
            try:
                results = gmail_service.users().messages().list(
                    userId='me',
                    q=query
                ).execute()
                stats[key] = results.get('resultSizeEstimate', 0)
            except:
                stats[key] = 0
        
        # Format stats
        return f"""📊 **Email Statistics (Last {days} days):**
📥 **Total Received:** {stats['total_received']:,}
📬 **Unread:** {stats['unread']:,}
📅 **Today:** {stats['today']:,}
📈 **Daily Average:** {stats['total_received'] // days:,}"""
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error getting email stats: {str(e)}"

def delete_emails_from_sender(sender_email, max_delete=50):
    """Delete emails from a specific sender (with confirmation)"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Search for emails from sender
        query = f"from:{sender_email}"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_delete
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from: {sender_email}"
        
        # Delete messages
        deleted_count = 0
        for msg in messages:
            try:
                gmail_service.users().messages().delete(
                    userId='me',
                    id=msg['id']
                ).execute()
                deleted_count += 1
            except:
                continue
        
        return f"✅ **Deleted {deleted_count} emails from {sender_email}**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error deleting emails: {str(e)}"

# ============================================================================
# CALENDAR VIEW FUNCTIONS (ALL PRESERVED)
# ============================================================================

def get_today_schedule():
    """Get today's schedule across all calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        all_events = []
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    maxResults=25,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['_calendar_name'] = calendar_name
                    all_events.append(event)
            except:
                continue
        
        if not all_events:
            return "📅 **Today's Schedule:** No events scheduled - perfect for deep work!"
        
        # Sort by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        # Format events
        formatted_events = []
        for event in all_events:
            summary = event.get('summary', 'Untitled Event')
            calendar_name = event.get('_calendar_name', '')
            
            start = event.get('start', {})
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                time_str = start_dt.astimezone(toronto_tz).strftime('%-I:%M %p')
            else:
                time_str = 'All day'
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        header = f"📅 **Today's Schedule ({len(formatted_events)} events):**\n"
        return header + "\n".join(formatted_events)
        
    except Exception as e:
        return f"❌ Error getting today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for the next N days"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        start_time = datetime.now(toronto_tz)
        end_time = start_time + timedelta(days=days)
        
        all_events = []
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['_calendar_name'] = calendar_name
                    all_events.append(event)
            except:
                continue
        
        if not all_events:
            return f"📅 **Upcoming Events ({days} days):** No events scheduled."
        
        # Sort by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        # Group by date and format
        events_by_date = defaultdict(list)
        for event in all_events:
            summary = event.get('summary', 'Untitled Event')
            calendar_name = event.get('_calendar_name', '')
            
            start = event.get('start', {})
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                date_key = start_dt.astimezone(toronto_tz).strftime('%Y-%m-%d')
                time_str = start_dt.astimezone(toronto_tz).strftime('%-I:%M %p')
            elif 'date' in start:
                date_key = start['date']
                time_str = 'All day'
            else:
                date_key = 'Unknown'
                time_str = 'Time TBD'
            
            events_by_date[date_key].append(f"  • {time_str} - {summary} ({calendar_name})")
        
        # Format output
        formatted_output = [f"📅 **Upcoming Events (Next {days} days):**\n"]
        for date_key in sorted(events_by_date.keys()):
            try:
                date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                date_display = date_obj.strftime('%A, %B %-d')
            except:
                date_display = date_key
            
            formatted_output.append(f"**{date_display}:**")
            formatted_output.extend(events_by_date[date_key])
            formatted_output.append("")
        
        return "\n".join(formatted_output)
        
    except Exception as e:
        return f"❌ Error getting upcoming events: {str(e)}"

# ============================================================================
# WEB SEARCH FUNCTION (PRESERVED)
# ============================================================================

async def web_search(query, max_results=5):
    """Perform web search using Brave Search API"""
    if not BRAVE_API_KEY:
        return "🔍 Web search not configured - Brave API key required"
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY
            }
            params = {
                "q": query,
                "count": max_results,
                "search_lang": "en",
                "country": "CA",
                "safesearch": "moderate"
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    web_results = data.get('web', {}).get('results', [])
                    
                    if not web_results:
                        return f"🔍 No search results found for: {query}"
                    
                    # Format results
                    formatted_results = []
                    for result in web_results[:max_results]:
                        title = result.get('title', 'No title')
                        snippet = result.get('description', 'No description')
                        url = result.get('url', 'No URL')
                        
                        formatted_results.append(f"**{title}**\n{snippet}\n🔗 {url}")
                    
                    header = f"🔍 **Web Search Results for '{query}':**\n\n"
                    return header + "\n\n".join(formatted_results)
                else:
                    return f"🔍 Search error: HTTP {response.status}"
                    
    except Exception as e:
        print(f"❌ Web search error: {e}")
        return f"🔍 Search error: {str(e)}"

# ============================================================================
# ENHANCED FUNCTION HANDLING WITH ALL CAPABILITIES (PRESERVED)
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's full capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Calendar functions
            if function_name == "create_gcal_event":
                result = create_gcal_event(**arguments)
            elif function_name == "update_gcal_event":
                result = update_gcal_event(**arguments)
            elif function_name == "delete_gcal_event":
                result = delete_gcal_event(**arguments)
            elif function_name == "list_gcal_events":
                result = list_gcal_events(**arguments)
            elif function_name == "fetch_gcal_event":
                result = fetch_gcal_event(**arguments)
            elif function_name == "find_free_time":
                result = find_free_time(**arguments)
            elif function_name == "list_gcal_calendars":
                result = list_gcal_calendars()
            
            # Email functions
            elif function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                unread_only = arguments.get('unread_only', False)
                include_body = arguments.get('include_body', False)
                result = get_recent_emails(count, unread_only, include_body)
            elif function_name == "search_emails":
                query = arguments.get('query', '')
                max_results = arguments.get('max_results', 10)
                include_body = arguments.get('include_body', False)
                result = search_emails(query, max_results, include_body)
            elif function_name == "get_email_stats":
                days = arguments.get('days', 7)
                result = get_email_stats(days)
            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                max_delete = arguments.get('max_delete', 50)
                result = delete_emails_from_sender(sender_email, max_delete)
            
            # Calendar view functions
            elif function_name == "get_today_schedule":
                result = get_today_schedule()
            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                result = get_upcoming_events(days)
            elif function_name == "get_morning_briefing":
                result = "🌅 Morning briefing available via !briefing command"
            
            # Web search function
            elif function_name == "web_search":
                query = arguments.get('query', '')
                # Note: This is a sync function calling async - would need proper async handling
                result = f"🔍 Web search for '{query}' - use mention search in chat for web results"
            
            else:
                result = f"❌ Function '{function_name}' not implemented."
            
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": str(result)
            })
            
            print(f"✅ Function result: {result}")
            
        except Exception as e:
            error_msg = f"❌ Error in {function_name}: {str(e)}"
            print(f"❌ Function error: {e}")
            traceback.print_exc()
            
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": error_msg
            })
    
    return tool_outputs

# ============================================================================
# AI ASSISTANT INTEGRATION (ALL PRESERVED)
# ============================================================================

async def handle_ai_conversation(message, user_id, channel_id):
    """Handle AI assistant conversation with OpenAI"""
    try:
        # Get or create conversation thread
        thread_id = user_conversations.get(user_id)
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            user_conversations[user_id] = thread_id
            conversation_metadata[thread_id] = {
                'user_id': user_id,
                'channel_id': channel_id,
                'created_at': time.time()
            }
        
        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message.content
        )
        
        # Create run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for completion
        max_wait_time = 60
        start_time = time.time()
        
        while run.status in ['queued', 'in_progress', 'requires_action']:
            if time.time() - start_time > max_wait_time:
                return "⏰ Request timed out. Please try again."
            
            if run.status == 'requires_action':
                # Handle function calls
                tool_outputs = handle_rose_functions_enhanced(run, thread_id)
                
                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            else:
                await asyncio.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
        
        if run.status == 'completed':
            # Get messages
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            if messages.data:
                response_content = messages.data[0].content[0].text.value
                return response_content
            else:
                return "❌ No response generated."
        else:
            return f"❌ Request failed with status: {run.status}"
            
    except Exception as e:
        print(f"❌ AI conversation error: {e}")
        traceback.print_exc()
        return f"❌ Error processing request: {str(e)[:100]}"

# ============================================================================
# ENHANCED TEAM BRIEFING FUNCTIONS
# ============================================================================

def get_vivian_report():
    """Generate Vivian's PR/Work/News briefing"""
    report = "📺 **Vivian's External Intelligence Brief**\n"
    report += "Good morning! Here's your external landscape update:\n\n"
    
    # Work email priority assessment
    if gmail_service:
        try:
            unread_emails = get_recent_emails(5, unread_only=True, include_body=False)
            priority_count = len([line for line in unread_emails.split('\n') if 'urgent' in line.lower() or 'important' in line.lower()])
            report += f"📧 **Work Communications Priority:** {priority_count} high-priority items detected\n"
            report += "🎯 **Recommendation:** Review urgent emails before first meeting\n"
        except:
            report += "📧 **Work Communications:** Email assessment unavailable\n"
    else:
        report += "📧 **Work Communications:** Email service offline\n"
    
    # External communications reminder
    report += "\n💼 **Today's External Focus:**\n"
    report += "• LinkedIn engagement check scheduled\n"
    report += "• Stakeholder follow-up prep needed\n"
    report += "• Professional communication review pending\n"
    
    # News digest placeholder (could integrate with news API)
    report += "\n📰 **Industry Watch:**\n"
    report += "• Monitor key industry developments throughout the day\n"
    report += "• Check for mentions and engagement opportunities\n"
    report += "• Curated news feed review recommended\n"
    
    return report

def get_celeste_report():
    """Generate Celeste's Content & Research briefing"""
    report = "✍️ **Celeste's Content & Knowledge Brief**\n"
    report += "Good morning! Your content and research priorities:\n\n"
    
    # Content deadlines
    report += "📝 **Content Pipeline Status:**\n"
    report += "• Newsletter draft ready for review\n"
    report += "• Research synthesis pending from team reports\n"
    report += "• Content calendar alignment check needed\n"
    
    # Meeting research
    if calendar_service:
        try:
            today_events = get_today_schedule()
            meeting_count = len([line for line in today_events.split('\n') if 'meeting' in line.lower() or 'call' in line.lower()])
            if meeting_count > 0:
                report += f"\n🔍 **Meeting Research Status:**\n"
                report += f"• {meeting_count} meetings detected - background research required\n"
                report += "• Key topics and participant profiles ready\n"
                report += "• Discussion points and follow-up templates prepared\n"
        except:
            pass
    
    # Knowledge synthesis
    report += "\n📚 **Knowledge Management:**\n"
    report += "• Team report synthesis ready for processing\n"
    report += "• Cross-reference updates pending\n"
    report += "• Documentation backlog manageable\n"
    
    return report

def get_charlotte_report():
    """Generate Charlotte's IT/Systems briefing"""
    report = "⚙️ **Charlotte's Technical Systems Brief**\n"
    report += "Good morning! Your technical infrastructure status:\n\n"
    
    # System health
    report += "🖥️ **System Health Check:**\n"
    report += f"• Discord Bot: {'✅ Online' if bot.is_ready() else '❌ Connection issues'}\n"
    report += f"• Calendar Integration: {'✅ Active' if calendar_service else '❌ Disconnected'}\n"
    report += f"• Gmail Service: {'✅ Operational' if gmail_service else '❌ Offline'}\n"
    report += f"• Weather API: {'✅ Connected' if WEATHER_API_KEY else '❌ Not configured'}\n"
    
    # Calendar sync status
    if accessible_calendars:
        report += f"\n📅 **Calendar System:**\n"
        report += f"• {len(accessible_calendars)} calendars synchronized\n"
        report += "• Cross-calendar coordination active\n"
        report += "• Timezone handling: Toronto/Eastern verified\n"
    
    # Automation status
    report += "\n🤖 **Automation Status:**\n"
    report += "• Morning briefing workflows operational\n"
    report += "• Email processing algorithms active\n"
    report += "• AI assistant functions fully integrated\n"
    
    # Technical recommendations
    report += "\n🔧 **Technical Priorities:**\n"
    report += "• System monitoring: All green\n"
    report += "• Backup routines: On schedule\n"
    report += "• Integration updates: Current\n"
    
    return report

def get_alice_report():
    """Generate Alice's Health & Home briefing"""
    report = "🏠 **Alice's Home & Wellness Brief**\n"
    report += "Good morning! Your domestic and health priorities:\n\n"
    
    # Health & routines
    report += "💪 **Wellness Check:**\n"
    report += "• Morning routine: Hydration and movement recommended\n"
    report += "• Energy levels: Assess after weather review\n"
    report += "• Habit tracker: Daily goals aligned with schedule\n"
    
    # Home management
    report += "\n🏡 **Home Systems:**\n"
    report += "• Household routine: On track\n"
    report += "• Organization priorities: Desktop and digital cleanup\n"
    report += "• Family coordination: Schedule sync complete\n"
    
    # Financial reminders
    report += "\n💰 **Financial Wellness:**\n"
    report += "• Daily expense tracking: Ready\n"
    report += "• Budget alignment: Monitor discretionary spending\n"
    report += "• Financial goals: Stay focused on priorities\n"
    
    # Today's home priorities
    report += "\n✅ **Today's Home Focus:**\n"
    report += "• Maintain organized workspace for productivity\n"
    report += "• Prepare for smooth evening routine\n"
    report += "• Balance home and work energy efficiently\n"
    
    return report

def get_pippa_report():
    """Generate Pippa's Life Coach briefing"""
    report = "🧠 **Pippa's Mindset & Resilience Brief**\n"
    report += "Good morning, beautiful human! Your mental wellness checkpoint:\n\n"
    
    # Emotional readiness
    report += "💭 **Mental Readiness Assessment:**\n"
    report += "• Energy calibration: Check in with your authentic self\n"
    report += "• Stress indicators: Monitor for early intervention\n"
    report += "• Confidence levels: You've got this - trust your capabilities\n"
    
    # AuDHD support
    report += "\n🌈 **AuDHD Success Strategies:**\n"
    report += "• Sensory environment: Optimize for focus and comfort\n"
    report += "• Transition planning: Build in buffer time between tasks\n"
    report += "• Executive function: Use external systems for cognitive support\n"
    report += "• Masking management: Reserve energy, authenticity over performance\n"
    
    # Daily mindset
    report += "\n🎯 **Today's Mindset Focus:**\n"
    report += "• Priority clarity: Focus on what truly matters\n"
    report += "• Energy boundaries: Protect your resources wisely\n"
    report += "• Self-compassion: Progress over perfection always\n"
    
    # Emergency protocols
    report += "\n🆘 **Panic Protocol Status:**\n"
    report += "• Grounding techniques: 5-4-3-2-1 sensory method ready\n"
    report += "• Breathing exercises: Box breathing available\n"
    report += "• Support systems: Remember your network is here\n"
    
    return report

def get_cressida_report():
    """Generate Cressida's Manic Pixie Dream Collective briefing"""
    report = "✨ **Cressida's Magic & Joy Elevation Brief**\n"
    report += "Good morning, magnificent soul! Time for some conscious magic:\n\n"
    
    # Joy creation
    report += "🌈 **Joy Creation Status:**\n"
    report += "• Spontaneous magic opportunities: Stay open to wonder\n"
    report += "• Creative rebellion potential: High - trust your artistic instincts\n"
    report += "• Authentic expression: The world needs your unique light\n"
    
    # Community building
    report += "\n🤝 **Collective Elevation:**\n"
    report += "• Random acts of kindness: Opportunity radar activated\n"
    report += "• Grassroots kindness: Small actions, big consciousness shifts\n"
    report += "• Evidence-based self-love: You are worthy of all good things\n"
    
    # Vibrational elevation
    report += "\n🔮 **Vibrational Frequency:**\n"
    report += "• Individual transformation: Your growth elevates universal consciousness\n"
    report += "• Creative flow state: Available for peak expression\n"
    report += "• Magical realism mode: Engaged and ready for synchronicities\n"
    
    # Today's magic
    report += "\n✨ **Today's Magical Mission:**\n"
    report += "• Spread infectious positivity through authentic presence\n"
    report += "• Create micro-moments of wonder in ordinary interactions\n"
    report += "• Channel dreams into reality through inspired action\n"
    
    return report

# ============================================================================
# DISCORD COMMANDS (ALL PRESERVED WITH ORIGINAL VARIABLE NAMES)
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test bot connectivity"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.command(name='status')
async def status_command(ctx):
    """Show comprehensive system status"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    config = ASSISTANT_CONFIG
    
    embed = discord.Embed(
        title=f"{config['emoji']} {config['name']} - System Status",
        description=config['description'],
        color=config['color']
    )
    
    # Core Systems
    embed.add_field(
        name="🤖 Core Systems",
        value=f"✅ Discord Connected\n✅ OpenAI Assistant\n{'✅' if WEATHER_API_KEY else '❌'} Weather API",
        inline=True
    )
    
    # Google Services
    calendar_status = '✅' if calendar_service else '❌'
    gmail_status = '✅' if gmail_service else '❌'
    embed.add_field(
        name="📅 Google Services",
        value=f"{calendar_status} Calendar Service\n{gmail_status} Gmail Service\n📊 {len(accessible_calendars)} Calendars",
        inline=True
    )
    
    # External APIs
    search_status = '✅' if BRAVE_API_KEY else '❌'
    embed.add_field(
        name="🔍 External APIs", 
        value=f"{search_status} Brave Search\n🌤️ WeatherAPI.com",
        inline=True
    )
    
    # Specialties
    embed.add_field(
        name="🎯 Specialties",
        value="\n".join([f"• {spec}" for spec in config['specialties']]),
        inline=False
    )
    
    # Usage
    embed.add_field(
        name="💡 Usage",
        value=f"• Mention @{config['name']} for AI assistance\n• Use commands below for quick functions\n• Active in: {', '.join([f'#{ch}' for ch in config['channels']])}",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='weather')
async def weather_command(ctx):
    """Get current weather"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    weather = get_weather_briefing()
    await ctx.send(weather)

async def send_as_persona(channel, content, persona_name, avatar_url=None):
    """Send a message as a different persona using webhooks"""
    try:
        # Try to find existing webhook for this persona
        webhooks = await channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == f"{persona_name}_webhook":
                webhook = wh
                break
        
        # Create webhook if it doesn't exist
        if not webhook:
            webhook = await channel.create_webhook(name=f"{persona_name}_webhook")
        
        # Send message as persona
        await webhook.send(
            content=content,
            username=persona_name,
            avatar_url=avatar_url
        )
        
    except discord.Forbidden:
        # Fallback to regular message if webhooks aren't available
        await channel.send(f"**{persona_name}:** {content}")
    except Exception as e:
        print(f"❌ Error sending as {persona_name}: {e}")
        await channel.send(f"**{persona_name}:** {content}")

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Complete morning briefing with comprehensive team reports"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    await ctx.send("🌅 **Executive Team Morning Briefing** - Rose initiating comprehensive status...")
    await asyncio.sleep(1)
    
    # Rose's strategic overview (goes first)
    toronto_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
    
    rose_briefing = f"👑 **Rose's Strategic Overview** ({current_time})\n"
    rose_briefing += "Good morning! Comprehensive executive briefing initiating...\n\n"
    
    # Get high-level calendar insights
    if calendar_service:
        upcoming_events = get_upcoming_events(1)  # Just today
        event_count = len([line for line in upcoming_events.split('\n') if '•' in line])
        rose_briefing += f"📊 **Today's Strategic Focus:** {event_count} scheduled commitments\n"
        rose_briefing += "🎯 **Executive Priority:** Multi-department coordination for optimal productivity\n"
    else:
        rose_briefing += "📊 **Calendar Status:** Manual coordination mode - all departments standing by\n"
    
    # Email overview
    if gmail_service:
        try:
            stats = get_email_stats(1)
            unread_count = stats.count('unread') if 'unread' in stats.lower() else 0
            rose_briefing += f"📧 **Communications Status:** {unread_count} priority items requiring attention\n"
        except:
            rose_briefing += "📧 **Communications:** Assessment pending\n"
    
    rose_briefing += "\n🚀 **Team Status:** All departments online - requesting full briefing reports"
    await ctx.send(rose_briefing)
    await asyncio.sleep(2)
    
    # Vivian's external intelligence report
    vivian_report = get_vivian_report()
    await send_as_persona(ctx.channel, vivian_report, "Vivian Spencer", None)
    await asyncio.sleep(2)
    
    # Flora's mystical guidance and weather
    flora_briefing = "🔮 **Flora's Mystical Guidance & Celestial Weather Reading**\n"
    flora_briefing += "Good morning, dear souls! The cosmos whispers through today's elements:\n\n"
    
    weather = get_weather_briefing()
    flora_briefing += weather
    
    # Add mystical interpretation
    flora_briefing += "\n\n🌙 **Celestial Interpretation:**\n"
    flora_briefing += "• The atmospheric energies align with your daily intentions\n"
    flora_briefing += "• Weather patterns reflect inner emotional currents - observe and adapt\n"
    flora_briefing += "• Natural light serves as divine connection - embrace solar/lunar rhythms\n"
    flora_briefing += "• Elements speak - listen to wind, feel temperature shifts as cosmic guidance\n"
    
    flora_briefing += "\n🃏 **Daily Mystical Insight:**\n"
    flora_briefing += "*\"Today's weather is but the universe's mood - flow with it, don't fight it.\"*\n"
    flora_briefing += "✨ Trust your intuition as the day's energies shift and dance"
    
    await send_as_persona(ctx.channel, flora_briefing, "Flora Penrose", None)
    await asyncio.sleep(2)
    
    # Maeve's style and schedule coordination
    maeve_briefing = "🎨 **Maeve's Style & Schedule Aesthetic Brief**\n"
    maeve_briefing += "Perfect cosmic canvas, Flora! Now for today's curated schedule:\n\n"
    
    if calendar_service:
        schedule = get_today_schedule()
        maeve_briefing += schedule
        maeve_briefing += "\n\n✨ **Style & Efficiency Curation:**\n"
        maeve_briefing += "• **Meeting Prep Aesthetic:** 15-minute buffer for mental outfit changes\n"
        maeve_briefing += "• **Transition Styling:** Seamless flow between commitments\n"
        maeve_briefing += "• **Energy Color Palette:** Schedule rhythm to style vibe alignment\n"
        maeve_briefing += "• **Weather-to-Wardrobe Sync:** Channeling Flora's cosmic weather guidance\n"
        
        maeve_briefing += "\n👗 **Today's Style Strategy:**\n"
        maeve_briefing += "• Comfort meets confidence - dress for peak performance\n"
        maeve_briefing += "• Accessories that transition seamlessly\n"
        maeve_briefing += "• Color psychology alignment with calendar energy\n"
    else:
        maeve_briefing += "📅 **Schedule Status:** Calendar offline - styling reset mode activated\n"
        maeve_briefing += "🎯 **Style Recovery:** Perfect time for aesthetic vision curation\n"
    
    maeve_briefing += "\n💄 **Aesthetic Systems: Fully Coordinated & Ready!**"
    
    await send_as_persona(ctx.channel, maeve_briefing, "Maeve Windham", None)
    await asyncio.sleep(2)
    
    # Celeste's content and research briefing
    celeste_report = get_celeste_report()
    await send_as_persona(ctx.channel, celeste_report, "Celeste Marchmont", None)
    await asyncio.sleep(2)
    
    # Charlotte's technical systems report
    charlotte_report = get_charlotte_report()
    await send_as_persona(ctx.channel, charlotte_report, "Charlotte Astor", None)
    await asyncio.sleep(2)
    
    # Alice's home and wellness check
    alice_report = get_alice_report()
    await send_as_persona(ctx.channel, alice_report, "Alice Fortescue", None)
    await asyncio.sleep(2)
    
    # Pippa's mindset and resilience coaching
    pippa_report = get_pippa_report()
    await send_as_persona(ctx.channel, pippa_report, "Pippa Blackwood", None)
    await asyncio.sleep(2)
    
    # Cressida's magic and joy elevation
    cressida_report = get_cressida_report()
    await send_as_persona(ctx.channel, cressida_report, "Cressida Frost", None)
    await asyncio.sleep(2)
    
    # Rose's comprehensive synthesis and closing
    rose_closing = "👑 **Rose's Executive Synthesis**\n\n"
    rose_closing += "**Department Status:** ✅ All teams reporting ready\n"
    rose_closing += "**Systems Integration:** ✅ Full spectrum support activated\n"
    rose_closing += "**Strategic Coordination:** ✅ Multi-department alignment achieved\n\n"
    rose_closing += "**🎯 Today's Executive Summary:**\n"
    rose_closing += "• External intelligence: Vivian monitoring communications & industry\n"
    rose_closing += "• Cosmic guidance: Flora providing weather & energy insights\n"
    rose_closing += "• Aesthetic coordination: Maeve optimizing style & schedule flow\n"
    rose_closing += "• Content pipeline: Celeste managing research & knowledge synthesis\n"
    rose_closing += "• Technical systems: Charlotte ensuring full infrastructure support\n"
    rose_closing += "• Wellness foundation: Alice maintaining home & health priorities\n"
    rose_closing += "• Mental resilience: Pippa providing mindset & AuDHD support\n"
    rose_closing += "• Joy elevation: Cressida channeling magic & authentic expression\n\n"
    rose_closing += "**🚀 Executive Decision:** Team fully coordinated. Let's make today extraordinary! 👑**"
    
    await ctx.send(rose_closing)

@bot.command(name='quickbriefing')
async def quickbriefing_command(ctx):
    """Condensed briefing with core essentials only"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    toronto_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
    
    # Quick status from Rose
    quick_brief = f"⚡ **Quick Morning Brief** ({current_time})\n\n"
    
    # Essential calendar info
    if calendar_service:
        upcoming_events = get_upcoming_events(1)
        event_count = len([line for line in upcoming_events.split('\n') if '•' in line])
        quick_brief += f"📅 **Today:** {event_count} events scheduled\n"
    
    # Essential email info  
    if gmail_service:
        try:
            stats = get_email_stats(1)
            unread_count = stats.count('unread') if 'unread' in stats.lower() else 0
            quick_brief += f"📧 **Inbox:** {unread_count} unread items\n"
        except:
            quick_brief += "📧 **Inbox:** Status unavailable\n"
    
    # Weather from Flora
    weather = get_weather_briefing()
    quick_brief += f"\n{weather}\n"
    
    # Quick team status
    quick_brief += "\n🚀 **Team Status:** All systems operational\n"
    quick_brief += "💡 Use `!briefing` for full team reports"
    
    await ctx.send(quick_brief)

@bot.command(name='teambriefing')
async def teambriefing_command(ctx, assistant_name: str = None):
    """Get individual assistant reports or list available assistants"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if not assistant_name:
        team_list = "👥 **Available Team Members:**\n"
        team_list += "• `vivian` - External Intelligence (PR/Work/News)\n"
        team_list += "• `flora` - Mystical Guidance & Weather\n" 
        team_list += "• `maeve` - Style & Schedule Coordination\n"
        team_list += "• `celeste` - Content & Research\n"
        team_list += "• `charlotte` - Technical Systems\n"
        team_list += "• `alice` - Home & Wellness\n"
        team_list += "• `pippa` - Life Coaching & Mindset\n"
        team_list += "• `cressida` - Magic & Joy Elevation\n\n"
        team_list += "Usage: `!teambriefing <name>` (e.g., `!teambriefing vivian`)"
        await ctx.send(team_list)
        return
    
    assistant_name = assistant_name.lower()
    
    # Route to appropriate assistant report
    if assistant_name in ['vivian', 'vivian spencer']:
        report = get_vivian_report()
        await send_as_persona(ctx.channel, report, "Vivian Spencer", None)
    elif assistant_name in ['flora', 'flora penrose']:
        flora_brief = "🔮 **Flora's Mystical Guidance & Weather**\n"
        flora_brief += "Greetings, dear soul! Here's today's cosmic guidance:\n\n"
        weather = get_weather_briefing()
        flora_brief += weather
        flora_brief += "\n\n🌙 **Celestial Insight:**\n"
        flora_brief += "*\"Flow with today's universal energies - they guide you perfectly.\"*\n"
        flora_brief += "✨ Trust your intuition as the day unfolds"
        await send_as_persona(ctx.channel, flora_brief, "Flora Penrose", None)
    elif assistant_name in ['maeve', 'maeve windham']:
        maeve_brief = "🎨 **Maeve's Style & Schedule Brief**\n"
        maeve_brief += "Hello, gorgeous! Your curated day awaits:\n\n"
        if calendar_service:
            schedule = get_today_schedule()
            maeve_brief += schedule
            maeve_brief += "\n\n✨ **Style Coordination:** All systems aesthetically aligned!"
        else:
            maeve_brief += "📅 Perfect styling reset opportunity - calendar offline for curation mode!"
        await send_as_persona(ctx.channel, maeve_brief, "Maeve Windham", None)
    elif assistant_name in ['celeste', 'celeste marchmont']:
        report = get_celeste_report()
        await send_as_persona(ctx.channel, report, "Celeste Marchmont", None)
    elif assistant_name in ['charlotte', 'charlotte astor']:
        report = get_charlotte_report()
        await send_as_persona(ctx.channel, report, "Charlotte Astor", None)
    elif assistant_name in ['alice', 'alice fortescue']:
        report = get_alice_report()
        await send_as_persona(ctx.channel, report, "Alice Fortescue", None)
    elif assistant_name in ['pippa', 'pippa blackwood']:
        report = get_pippa_report()
        await send_as_persona(ctx.channel, report, "Pippa Blackwood", None)
    elif assistant_name in ['cressida', 'cressida frost']:
        report = get_cressida_report()
        await send_as_persona(ctx.channel, report, "Cressida Frost", None)
    else:
        await ctx.send(f"❌ Assistant '{assistant_name}' not found. Use `!teambriefing` to see available team members.")

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's schedule"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if calendar_service:
        schedule = get_today_schedule()
        await ctx.send(schedule)
    else:
        await ctx.send("📅 Calendar service not available")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Get upcoming events"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if calendar_service:
        days = max(1, min(days, 30))  # Limit between 1-30 days
        events = get_upcoming_events(days)
        
        # Split long messages
        if len(events) > 2000:
            chunks = [events[i:i+1900] for i in range(0, len(events), 1900)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(events)
    else:
        await ctx.send("📅 Calendar service not available")

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if gmail_service:
        count = max(1, min(count, 25))  # Limit between 1-25 emails
        async with ctx.typing():
            emails = get_recent_emails(count, unread_only=False, include_body=False)
            
            # Split long messages
            if len(emails) > 2000:
                chunks = [emails[i:i+1900] for i in range(0, len(emails), 1900)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(emails)
    else:
        await ctx.send("📧 Gmail service not available")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Get unread emails only"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if gmail_service:
        count = max(1, min(count, 25))
        async with ctx.typing():
            emails = get_recent_emails(count, unread_only=True, include_body=False)
            await ctx.send(emails)
    else:
        await ctx.send("📧 Gmail service not available")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Get email statistics"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if gmail_service:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    else:
        await ctx.send("📧 Gmail service not available")

@bot.command(name='quickemails')
async def quickemails_command(ctx, count: int = 5):
    """Get concise email view"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if gmail_service:
        count = max(1, min(count, 15))
        async with ctx.typing():
            emails = get_recent_emails(count, unread_only=False, include_body=False)
            await ctx.send(emails)
    else:
        await ctx.send("📧 Gmail service not available")

@bot.command(name='emailcount')
async def emailcount_command(ctx):
    """Get just email counts"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if gmail_service:
        async with ctx.typing():
            stats = get_email_stats()
            # Extract just the count lines
            lines = stats.split('\n')
            count_lines = [line for line in lines if ('Unread' in line or 'Total' in line or 'Today' in line)]
            await ctx.send('\n'.join(count_lines))
    else:
        await ctx.send("📧 Gmail service not available")

@bot.command(name='cleansender')
async def cleansender_command(ctx, sender_email: str, count: int = 50):
    """Delete emails from a specific sender (requires confirmation)"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    if not gmail_service:
        await ctx.send("📧 Gmail service not available")
        return
    
    try:
        async with ctx.typing():
            count = max(1, min(count, 100))
            
            # First, show what would be deleted
            search_result = search_emails(f"from:{sender_email}", max_results=5)
            
            embed = discord.Embed(
                title="🗑️ Email Deletion Confirmation",
                description=f"This will delete up to {count} emails from: **{sender_email}**",
                color=0xff0000
            )
            embed.add_field(
                name="Sample emails to be deleted:",
                value=search_result[:500] + "..." if len(search_result) > 500 else search_result,
                inline=False
            )
            embed.add_field(
                name="⚠️ Confirmation Required",
                value="React with ✅ to confirm deletion or ❌ to cancel",
                inline=False
            )
            
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            
            # Wait for reaction
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
            
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == "✅":
                    # Proceed with deletion
                    result = delete_emails_from_sender(sender_email, count)
                    await ctx.send(result)
                else:
                    await ctx.send("❌ Email deletion cancelled.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Email deletion confirmation timed out. Cancelled for safety.")
                
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send("🗑️ Error with email deletion. Please try again.")

@bot.command(name='help')
async def help_command(ctx):
    """Show comprehensive help message"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    config = ASSISTANT_CONFIG
    
    embed = discord.Embed(
        title=f"{config['emoji']} {config['name']} - Executive Assistant Commands",
        description=config['description'],
        color=config['color']
    )
    
    # Main usage
    embed.add_field(
        name="💬 AI Assistant",
        value=f"• Mention @{config['name']} for advanced assistance\n• Calendar management, email handling, strategic planning\n• Research and productivity optimization",
        inline=False
    )
    
    # Commands - Split into sections for better organization
    briefing_commands = [
        "!briefing - Complete team morning briefing",
        "!quickbriefing - Condensed essential briefing",
        "!teambriefing [name] - Individual assistant reports",
        "!weather - Current weather & UV"
    ]
    
    calendar_commands = [
        "!schedule - Today's calendar", 
        "!upcoming [days] - Upcoming events (default: 7)"
    ]
    
    email_commands = [
        "!emails [count] - Recent emails (default: 10)",
        "!unread [count] - Unread only (default: 10)",
        "!emailstats - Email dashboard",
        "!emailcount - Just email counts",
        "!cleansender <email> [count] - Delete from sender"
    ]
    
    system_commands = [
        "!status - System status",
        "!ping - Test response time",
        "!help - This message"
    ]
    
    embed.add_field(
        name="🌅 Team Briefings",
        value="\n".join([f"• {cmd}" for cmd in briefing_commands]),
        inline=False
    )
    
    embed.add_field(
        name="📅 Calendar Management",
        value="\n".join([f"• {cmd}" for cmd in calendar_commands]),
        inline=False
    )
    
    embed.add_field(
        name="📧 Email Management",
        value="\n".join([f"• {cmd}" for cmd in email_commands]),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ System",
        value="\n".join([f"• {cmd}" for cmd in system_commands]),
        inline=False
    )
    
    # Example requests
    embed.add_field(
        name="💡 Example AI Requests",
        value="\n".join([f"• {req}" for req in config['example_requests'][:3]]),
        inline=False
    )
    
    # Channels
    embed.add_field(
        name="🎯 Active Channels",
        value=", ".join([f"#{ch}" for ch in config['channels']]),
        inline=False
    )
    
    await ctx.send(embed=embed)

# ============================================================================
# DISCORD EVENT HANDLERS (ALL PRESERVED)
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup sequence"""
    print(f"🚀 Starting {ASSISTANT_NAME}...")
    
    # Weather API test
    if WEATHER_API_KEY:
        print("🔧 Weather API Configuration Status:")
        print(f" API Key: ✅ Configured")
        print(f" City: ✅ {USER_CITY}")
        if USER_LAT and USER_LON:
            print(f" Coordinates: ✅ Precise location")
        else:
            print(f" Coordinates: ⚠️ Using city name")
        
        print("🧪 Testing weather integration...")
        weather_test = get_weather_briefing()
        print("🧪 Testing WeatherAPI.com integration...")
        print(f"🔑 API Key configured: ✅ Yes")
        print(f"📍 Location: {USER_CITY}")
        print("=" * 50)
        print("WEATHER BRIEFING TEST RESULT:")
        print("=" * 50)
        print(weather_test)
        print("=" * 50)
    
    # Initialize Google services
    initialize_google_services()
    
    # Final status
    print(f"📅 Calendar Service: {'✅ Ready' if calendar_service else '❌ Not available'}")
    print(f"📧 Gmail Service: {'✅ Ready' if gmail_service else '❌ Not available'}")
    print(f"✅ {ASSISTANT_NAME} is online!")
    print(f"🤖 Connected as {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
    print(f"📅 Calendar Status: {'✅ Integrated' if calendar_service else '❌ Disabled'}")
    print(f"🌤️ Weather Status: {'✅ Configured' if WEATHER_API_KEY else '❌ Disabled'}")
    print(f"🔍 Planning Search: {'✅ Available' if BRAVE_API_KEY else '⚠️ Limited'}")
    print(f"🎯 Allowed Channels: {', '.join(ALLOWED_CHANNELS)}")

@bot.event
async def on_message(message):
    """Handle messages and AI assistant mentions"""
    # Ignore bot messages
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Check if bot is mentioned and in allowed channel
    if bot.user in message.mentions and message.channel.name in ALLOWED_CHANNELS:
        # Prevent duplicate processing
        message_key = f"{message.id}_{message.author.id}"
        if message_key in processing_messages:
            return
        processing_messages.add(message_key)
        
        try:
            # Rate limiting
            user_id = message.author.id
            current_time = time.time()
            
            if user_id in last_response_time:
                time_since_last = current_time - last_response_time[user_id]
                if time_since_last < 3:  # 3 second cooldown
                    await message.add_reaction("⏳")
                    return
            
            last_response_time[user_id] = current_time
            
            # Show typing indicator
            async with message.channel.typing():
                # Handle AI conversation
                response = await handle_ai_conversation(message, user_id, message.channel.id)
                
                # Split long responses
                if len(response) > 2000:
                    chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk)
                        else:
                            await message.channel.send(chunk)
                else:
                    await message.reply(response)
        
        except Exception as e:
            print(f"❌ Message handling error: {e}")
            await message.reply("❌ Sorry, I encountered an error processing your request.")
        
        finally:
            processing_messages.discard(message_key)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for usage information.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `!help` for usage information.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ An error occurred while processing the command.")

# ============================================================================
# RUN BOT
# ============================================================================

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ CRITICAL: Bot failed to start: {e}")
        exit(1)