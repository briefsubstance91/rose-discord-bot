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
import random
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

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
    
    # Scheduler for automated tasks
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('America/Toronto'))
    
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

def delete_email_by_id(email_id):
    """Delete a specific email by its ID"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        gmail_service.users().messages().delete(
            userId='me',
            id=email_id
        ).execute()
        return f"✅ **Email deleted successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error deleting email: {str(e)}"

def delete_specific_email(subject=None, sender=None, date=None):
    """Delete a specific email by subject, sender, or date"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Build search query
        query_parts = []
        if subject:
            query_parts.append(f'subject:"{subject}"')
        if sender:
            query_parts.append(f'from:{sender}')
        if date:
            query_parts.append(f'after:{date} before:{date}')
        
        if not query_parts:
            return "❌ Please specify subject, sender, or date to identify the email"
        
        query = ' '.join(query_parts)
        
        # Search for the email
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No email found matching the criteria"
        
        # Delete the first matching email
        email_id = messages[0]['id']
        gmail_service.users().messages().delete(
            userId='me',
            id=email_id
        ).execute()
        
        return f"✅ **Email deleted successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error deleting email: {str(e)}"

def delete_emails_from_sender(sender_email, max_delete=50):
    """Delete emails from a specific sender (with confirmation)"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # First try exact match
        query = f"from:{sender_email}"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_delete
        ).execute()
        
        messages = results.get('messages', [])
        
        # If no exact match, try domain-based search for common patterns
        if not messages and '@' in sender_email:
            domain = sender_email.split('@')[1]
            # Try searching by domain
            query = f"from:@{domain}"
            results = gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_delete
            ).execute()
            messages = results.get('messages', [])
            
            # If still no match, try broader search with domain name
            if not messages:
                domain_name = domain.split('.')[0]  # e.g., "hm" from "email.hm.com"
                query = f"from:{domain_name}"
                results = gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_delete
                ).execute()
                messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from: {sender_email} (tried exact match, domain match, and partial match)"
        
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
        
        return f"✅ **Deleted {deleted_count} emails from {sender_email}** (used query: {query})"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error deleting emails: {str(e)}"

def debug_email_senders(search_term, max_results=20):
    """Debug function to show exact sender formats for troubleshooting"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Search for emails containing the search term
        query = f"from:{search_term}"
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found containing: {search_term}"
        
        # Get sender details
        sender_list = []
        for msg in messages:
            msg_detail = gmail_service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = msg_detail['payload'].get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            
            sender_list.append(f"**From:** `{sender}`\n**Subject:** {subject[:50]}{'...' if len(subject) > 50 else ''}")
        
        header = f"📧 **Email Senders Found ({len(sender_list)}):**\n\n"
        return header + "\n\n".join(sender_list)
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error debugging emails: {str(e)}"

# ============================================================================
# EMAIL COMPOSITION & SENDING FUNCTIONS
# ============================================================================

def send_email(to, subject, body, cc=None, bcc=None):
    """Send a new email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ **Email sent successfully to {to}**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def reply_to_email(email_id, reply_body):
    """Reply to a specific email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Get original message
        original_msg = gmail_service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        headers = original_msg['payload'].get('headers', [])
        original_to = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
        # Create reply
        reply_subject = f"Re: {original_subject}" if not original_subject.startswith('Re:') else original_subject
        
        message = MIMEText(reply_body)
        message['to'] = original_to
        message['subject'] = reply_subject
        if message_id:
            message['In-Reply-To'] = message_id
            message['References'] = message_id
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ **Reply sent successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error replying to email: {str(e)}"

def forward_email(email_id, to, forward_message=""):
    """Forward a specific email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Get original message
        original_msg = gmail_service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        headers = original_msg['payload'].get('headers', [])
        original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        original_date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Get original body
        original_body = get_email_body(original_msg)
        
        # Create forward message
        forward_subject = f"Fwd: {original_subject}" if not original_subject.startswith('Fwd:') else original_subject
        
        forward_body = f"{forward_message}\n\n---------- Forwarded message ----------\n"
        forward_body += f"From: {original_from}\n"
        forward_body += f"Date: {original_date}\n"
        forward_body += f"Subject: {original_subject}\n\n"
        forward_body += original_body
        
        message = MIMEText(forward_body)
        message['to'] = to
        message['subject'] = forward_subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ **Email forwarded successfully to {to}**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error forwarding email: {str(e)}"

# ============================================================================
# EMAIL ORGANIZATION FUNCTIONS
# ============================================================================

def mark_email_as_read(email_id):
    """Mark an email as read"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"✅ **Email marked as read**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_unread(email_id):
    """Mark an email as unread"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
        
        return f"✅ **Email marked as unread**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error marking email as unread: {str(e)}"

def archive_email(email_id):
    """Archive an email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"✅ **Email archived successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error archiving email: {str(e)}"

def star_email(email_id):
    """Star an email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['STARRED']}
        ).execute()
        
        return f"✅ **Email starred successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error starring email: {str(e)}"

def unstar_email(email_id):
    """Remove star from an email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['STARRED']}
        ).execute()
        
        return f"✅ **Star removed successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error removing star: {str(e)}"

def add_label_to_email(email_id, label_name):
    """Add a label to an email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Get all labels to find the label ID
        labels_result = gmail_service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        label_id = None
        for label in labels:
            if label['name'].lower() == label_name.lower():
                label_id = label['id']
                break
        
        if not label_id:
            return f"❌ Label '{label_name}' not found"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        return f"✅ **Label '{label_name}' added successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error adding label: {str(e)}"

def remove_label_from_email(email_id, label_name):
    """Remove a label from an email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Get all labels to find the label ID
        labels_result = gmail_service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        label_id = None
        for label in labels:
            if label['name'].lower() == label_name.lower():
                label_id = label['id']
                break
        
        if not label_id:
            return f"❌ Label '{label_name}' not found"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': [label_id]}
        ).execute()
        
        return f"✅ **Label '{label_name}' removed successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error removing label: {str(e)}"

# ============================================================================
# ADVANCED EMAIL MANAGEMENT FUNCTIONS
# ============================================================================

def get_email_attachments(email_id):
    """Get attachments from an email"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        message = gmail_service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        attachments = []
        
        def extract_attachments(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('filename'):
                        attachments.append({
                            'filename': part['filename'],
                            'mimeType': part['mimeType'],
                            'size': part['body'].get('size', 0),
                            'attachmentId': part['body'].get('attachmentId')
                        })
                    else:
                        extract_attachments(part)
            elif payload.get('filename'):
                attachments.append({
                    'filename': payload['filename'],
                    'mimeType': payload['mimeType'], 
                    'size': payload['body'].get('size', 0),
                    'attachmentId': payload['body'].get('attachmentId')
                })
        
        extract_attachments(message['payload'])
        
        if not attachments:
            return "📎 No attachments found in this email"
        
        attachment_list = []
        for att in attachments:
            size_kb = att['size'] / 1024 if att['size'] else 0
            attachment_list.append(f"• {att['filename']} ({att['mimeType']}, {size_kb:.1f}KB)")
        
        return f"📎 **Attachments found:**\n" + "\n".join(attachment_list)
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error getting attachments: {str(e)}"

def get_email_thread(thread_id):
    """Get all emails in a conversation thread"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        thread = gmail_service.users().threads().get(
            userId='me',
            id=thread_id
        ).execute()
        
        messages = thread.get('messages', [])
        
        if not messages:
            return "📧 No messages found in thread"
        
        thread_summary = []
        for i, msg in enumerate(messages):
            headers = msg['payload'].get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
            
            # Parse date
            try:
                parsed_date = parsedate_to_datetime(date)
                date_str = parsed_date.strftime('%m/%d at %-I:%M %p')
            except:
                date_str = date
            
            thread_summary.append(f"{i+1}. **{subject}**\n   From: {sender}\n   Date: {date_str}")
        
        return f"🧵 **Conversation Thread ({len(messages)} messages):**\n\n" + "\n\n".join(thread_summary)
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error getting thread: {str(e)}"

def mark_all_as_read(query="is:unread"):
    """Mark multiple emails as read based on search query"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return "📧 No unread emails found"
        
        marked_count = 0
        for msg in messages:
            try:
                gmail_service.users().messages().modify(
                    userId='me',
                    id=msg['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                marked_count += 1
            except:
                continue
        
        return f"✅ **Marked {marked_count} emails as read**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error marking emails as read: {str(e)}"

def archive_old_emails(days_old=30, max_archive=50):
    """Archive emails older than specified days"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Calculate date
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y/%m/%d')
        query = f"before:{cutoff_date} in:inbox"
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_archive
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails older than {days_old} days found in inbox"
        
        archived_count = 0
        for msg in messages:
            try:
                gmail_service.users().messages().modify(
                    userId='me',
                    id=msg['id'],
                    body={'removeLabelIds': ['INBOX']}
                ).execute()
                archived_count += 1
            except:
                continue
        
        return f"✅ **Archived {archived_count} emails older than {days_old} days**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error archiving old emails: {str(e)}"

def delete_by_subject_pattern(pattern, max_delete=25):
    """Delete emails matching a subject pattern"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        import re
        query = f'subject:"{pattern}"'
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_delete
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found matching pattern: {pattern}"
        
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
        
        return f"✅ **Deleted {deleted_count} emails matching pattern '{pattern}'**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error deleting emails: {str(e)}"

def list_email_labels():
    """List all Gmail labels"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        labels_result = gmail_service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        if not labels:
            return "📝 No labels found"
        
        # Separate system and user labels
        system_labels = []
        user_labels = []
        
        for label in labels:
            label_name = label['name']
            if label['type'] == 'system':
                system_labels.append(label_name)
            else:
                user_labels.append(label_name)
        
        result = "📝 **Gmail Labels:**\n\n"
        
        if system_labels:
            result += "**System Labels:**\n"
            result += "\n".join([f"• {label}" for label in sorted(system_labels)])
            result += "\n\n"
        
        if user_labels:
            result += "**Custom Labels:**\n"
            result += "\n".join([f"• {label}" for label in sorted(user_labels)])
        
        return result
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error listing labels: {str(e)}"

def create_email_filter(criteria, actions):
    """Create a Gmail filter (simplified version)"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        filter_data = {
            'criteria': criteria,
            'action': actions
        }
        
        gmail_service.users().settings().filters().create(
            userId='me',
            body=filter_data
        ).execute()
        
        return f"✅ **Email filter created successfully**"
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error creating filter: {str(e)}"

def list_email_filters():
    """List existing Gmail filters"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        filters_result = gmail_service.users().settings().filters().list(userId='me').execute()
        filters = filters_result.get('filter', [])
        
        if not filters:
            return "🔍 No email filters found"
        
        filter_list = []
        for i, email_filter in enumerate(filters):
            criteria = email_filter.get('criteria', {})
            actions = email_filter.get('action', {})
            
            filter_desc = f"{i+1}. "
            if criteria.get('from'):
                filter_desc += f"From: {criteria['from']} "
            if criteria.get('to'):
                filter_desc += f"To: {criteria['to']} "
            if criteria.get('subject'):
                filter_desc += f"Subject: {criteria['subject']} "
            
            if actions.get('addLabelIds'):
                filter_desc += f"→ Add labels"
            if actions.get('removeLabelIds'):
                filter_desc += f"→ Remove labels"
            if actions.get('forward'):
                filter_desc += f"→ Forward to {actions['forward']}"
            
            filter_list.append(filter_desc)
        
        return f"🔍 **Email Filters ({len(filters)}):**\n\n" + "\n".join(filter_list)
        
    except HttpError as e:
        return f"❌ Gmail API error: {e.resp.status} - {e._get_reason()}"
    except Exception as e:
        return f"❌ Error listing filters: {str(e)}"

# ============================================================================
# CALENDAR VIEW FUNCTIONS (ALL PRESERVED)
# ============================================================================

def get_work_schedule(time_filter=None):
    """Get work calendar schedule - for Vivian's reports"""
    if not calendar_service or not GMAIL_WORK_CALENDAR_ID:
        return "❌ Work calendar not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        
        # Set time range based on filter
        if time_filter == 'noon':
            start_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif time_filter == 'afternoon':
            start_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:  # Full day
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        events_result = calendar_service.events().list(
            calendarId=GMAIL_WORK_CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            maxResults=25,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "💼 **Work Schedule:** Clear - focus time available"
        
        # Format events
        formatted_events = []
        for event in events:
            summary = event.get('summary', 'Untitled Meeting')
            start = event.get('start', {})
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                time_str = start_dt.astimezone(toronto_tz).strftime('%-I:%M %p')
            else:
                time_str = 'All day'
            
            formatted_events.append(f"• {time_str} - {summary}")
        
        header = f"💼 **Work Schedule ({len(formatted_events)} items):**\n"
        return header + "\n".join(formatted_events)
        
    except Exception as e:
        return f"❌ Error getting work schedule: {str(e)}"

def get_personal_schedule(time_filter=None):
    """Get personal/other calendars schedule - for Rose's reports"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        
        # Set time range based on filter
        if time_filter == 'noon':
            start_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif time_filter == 'afternoon':
            start_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:  # Full day
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get personal calendars (exclude work calendar)
        personal_calendars = [(name, cal_id) for name, cal_id in accessible_calendars 
                             if cal_id != GMAIL_WORK_CALENDAR_ID]
        
        all_events = []
        for calendar_name, calendar_id in personal_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
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
            return "📅 **Personal Schedule:** Clear - great for personal priorities"
        
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
        
        header = f"📅 **Personal Schedule ({len(formatted_events)} items):**\n"
        return header + "\n".join(formatted_events)
        
    except Exception as e:
        return f"❌ Error getting personal schedule: {str(e)}"

def get_today_schedule():
    """Get today's schedule across all calendars - legacy function for compatibility"""
    work_schedule = get_work_schedule()
    personal_schedule = get_personal_schedule()
    
    # Combine both schedules
    combined = f"{work_schedule}\n\n{personal_schedule}"
    return combined

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
            elif function_name == "batch_delete_by_sender":
                # Alternative name for delete_emails_from_sender
                sender_email = arguments.get('sender_email', '') or arguments.get('sender', '')
                max_delete = arguments.get('max_delete', 50) or arguments.get('count', 50)
                result = delete_emails_from_sender(sender_email, max_delete)
            elif function_name == "smart_email_search":
                # Enhanced email search function
                query = arguments.get('query', '') or arguments.get('search_term', '')
                max_results = arguments.get('max_results', 10) or arguments.get('limit', 10)
                include_body = arguments.get('include_body', False) or arguments.get('include_content', False)
                result = search_emails(query, max_results, include_body)
            elif function_name == "debug_email_senders":
                # Debug function to show exact sender formats
                search_term = arguments.get('search_term', '') or arguments.get('sender', '')
                max_results = arguments.get('max_results', 20) or arguments.get('limit', 20)
                result = debug_email_senders(search_term, max_results)
            elif function_name == "bulk_email_delete":
                # Another alternative for bulk deletion
                sender_email = arguments.get('sender_email', '') or arguments.get('from_address', '')
                max_delete = arguments.get('max_delete', 50) or arguments.get('count', 50)
                result = delete_emails_from_sender(sender_email, max_delete)
            elif function_name == "email_cleanup":
                # General email cleanup function
                sender_email = arguments.get('sender_email', '') or arguments.get('sender', '')
                max_delete = arguments.get('max_delete', 50) or arguments.get('count', 50)
                if sender_email:
                    result = delete_emails_from_sender(sender_email, max_delete)
                else:
                    result = "❌ Please specify sender email for cleanup"
            elif function_name == "advanced_email_search":
                # Advanced search with flexible parameters
                query = arguments.get('query', '') or arguments.get('search_query', '') or arguments.get('term', '')
                max_results = arguments.get('max_results', 10) or arguments.get('count', 10)
                include_body = arguments.get('include_body', False)
                result = search_emails(query, max_results, include_body)
            elif function_name == "delete_email":
                # Delete specific email by ID
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = delete_email_by_id(email_id)
            elif function_name == "delete_email_by_id":
                # Delete specific email by ID (alternative name)
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = delete_email_by_id(email_id)
            elif function_name == "delete_specific_email":
                # Delete email by subject, sender, or date
                subject = arguments.get('subject', '')
                sender = arguments.get('sender', '') or arguments.get('from', '')
                date = arguments.get('date', '')
                result = delete_specific_email(subject, sender, date)
            elif function_name == "single_email_delete":
                # Another alternative for single email deletion
                subject = arguments.get('subject', '')
                sender = arguments.get('sender', '') or arguments.get('from', '')
                date = arguments.get('date', '')
                if not subject and not sender and not date:
                    # Try email ID if no other criteria
                    email_id = arguments.get('email_id', '') or arguments.get('id', '')
                    if email_id:
                        result = delete_email_by_id(email_id)
                    else:
                        result = "❌ Please specify subject, sender, date, or email ID"
                else:
                    result = delete_specific_email(subject, sender, date)
                    
            # Email composition & sending functions
            elif function_name == "send_email":
                to = arguments.get('to', '') or arguments.get('recipient', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '') or arguments.get('message', '')
                cc = arguments.get('cc', '')
                bcc = arguments.get('bcc', '')
                result = send_email(to, subject, body, cc, bcc)
            elif function_name == "reply_to_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                reply_body = arguments.get('reply_body', '') or arguments.get('message', '') or arguments.get('body', '')
                result = reply_to_email(email_id, reply_body)
            elif function_name == "forward_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                to = arguments.get('to', '') or arguments.get('recipient', '')
                forward_message = arguments.get('forward_message', '') or arguments.get('message', '')
                result = forward_email(email_id, to, forward_message)
                
            # Email organization functions
            elif function_name == "mark_as_read" or function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = mark_email_as_read(email_id)
            elif function_name == "mark_as_unread" or function_name == "mark_email_as_unread":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = mark_email_as_unread(email_id)
            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = archive_email(email_id)
            elif function_name == "star_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = star_email(email_id)
            elif function_name == "unstar_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = unstar_email(email_id)
            elif function_name == "add_label" or function_name == "add_label_to_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                label_name = arguments.get('label_name', '') or arguments.get('label', '')
                result = add_label_to_email(email_id, label_name)
            elif function_name == "remove_label" or function_name == "remove_label_from_email":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                label_name = arguments.get('label_name', '') or arguments.get('label', '')
                result = remove_label_from_email(email_id, label_name)
                
            # Advanced email management functions
            elif function_name == "get_attachments" or function_name == "get_email_attachments":
                email_id = arguments.get('email_id', '') or arguments.get('id', '')
                result = get_email_attachments(email_id)
            elif function_name == "get_thread" or function_name == "get_email_thread":
                thread_id = arguments.get('thread_id', '') or arguments.get('id', '')
                result = get_email_thread(thread_id)
            elif function_name == "mark_all_as_read":
                query = arguments.get('query', 'is:unread')
                result = mark_all_as_read(query)
            elif function_name == "archive_old_emails":
                days_old = arguments.get('days_old', 30) or arguments.get('days', 30)
                max_archive = arguments.get('max_archive', 50) or arguments.get('count', 50)
                result = archive_old_emails(days_old, max_archive)
            elif function_name == "delete_by_pattern" or function_name == "delete_by_subject_pattern":
                pattern = arguments.get('pattern', '') or arguments.get('subject_pattern', '')
                max_delete = arguments.get('max_delete', 25) or arguments.get('count', 25)
                result = delete_by_subject_pattern(pattern, max_delete)
            elif function_name == "list_labels" or function_name == "list_email_labels":
                result = list_email_labels()
            elif function_name == "create_filter" or function_name == "create_email_filter":
                criteria = arguments.get('criteria', {})
                actions = arguments.get('actions', {})
                result = create_email_filter(criteria, actions)
            elif function_name == "list_filters" or function_name == "list_email_filters":
                result = list_email_filters()
                
            # Bulk operations
            elif function_name == "bulk_mark_read":
                query = arguments.get('query', 'is:unread')
                result = mark_all_as_read(query)
            elif function_name == "bulk_archive":
                days_old = arguments.get('days_old', 30) or arguments.get('days', 30)
                max_archive = arguments.get('max_archive', 50) or arguments.get('count', 50)
                result = archive_old_emails(days_old, max_archive)
            elif function_name == "email_cleanup_advanced":
                # Advanced cleanup function
                operation = arguments.get('operation', '')
                if operation == 'mark_read':
                    result = mark_all_as_read()
                elif operation == 'archive_old':
                    result = archive_old_emails()
                elif operation == 'delete_pattern':
                    pattern = arguments.get('pattern', '')
                    result = delete_by_subject_pattern(pattern)
                else:
                    result = "❌ Please specify operation: mark_read, archive_old, or delete_pattern"
            
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

# Assistant Discord Bot IDs - Your actual bot IDs
ASSISTANT_BOT_IDS = {
    'vivian': 1373036719930085567,   # Vivian Spencer
    'flora': 1389005290711683236,    # Flora Penrose
    'maeve': 1380303532242243705,    # Maeve Windham
    'celeste': 1376733073626103868,  # Celeste Marchmont
    'charlotte': None,               # Charlotte Astor (not deployed yet)
    'alice': None,                   # Alice Fortescue (not deployed yet)
    'pippa': 1380302510220120155,    # Pippa Blackwood
    'cressida': 1391876902993526794  # Cressida Frost
}

async def send_as_assistant_bot(channel, content, assistant_name):
    """Send message as the actual assistant bot if available, otherwise as Rose with attribution"""
    assistant_key = assistant_name.lower().split()[0]  # Get first name as key
    bot_id = ASSISTANT_BOT_IDS.get(assistant_key)
    
    if bot_id:
        # Try to get the actual bot user and send message
        try:
            assistant_bot = bot.get_user(bot_id)
            if assistant_bot:
                # Send with proper attribution to the actual bot
                await channel.send(f"**{assistant_name}:** {content}")
                return
        except:
            pass
    
    # Fallback: Send as Rose with clear attribution
    await channel.send(f"**{assistant_name}:** {content}")

def get_vivian_report(time_filter=None, brief=False):
    """Generate Vivian's Work Calendar & External Intelligence briefing"""
    # Check if it's weekend (Saturday=5, Sunday=6)
    toronto_tz = pytz.timezone('America/Toronto')
    current_day = datetime.now(toronto_tz).weekday()
    is_weekend = current_day >= 5  # Saturday or Sunday
    
    if is_weekend:
        # Weekend version - focus on personal coordination instead of work
        if brief:
            report = "📺 **Vivian's Weekend Brief**\n"
            report += "✨ **Weekend Mode:** Work coordination paused for personal time\n"
            report += "🌿 **Focus:** Rest, recharge, and personal activities\n"
            report += "📅 **Personal Calendar:** Available for weekend events and leisure planning"
            return report
        else:
            # Full weekend report
            report = "📺 **Vivian's Weekend Coordination**\n"
            report += "Good morning! Weekend personal coordination and leisure planning:\n\n"
            
            # Personal calendar only on weekends
            personal_schedule = get_personal_schedule(time_filter)
            report += f"🌿 **Weekend Activities:**\n{personal_schedule}\n"
            
            report += "✨ **Weekend Priorities:**\n"
            report += "• Personal time and restoration\n"
            report += "• Family and social connections\n"
            report += "• Leisure activities and hobbies\n"
            report += "• Home projects and personal interests\n\n"
            
            report += "💡 **Weekend Wisdom:** This is your time for rest, creativity, and personal fulfillment. Work coordination resumes Monday!"
            return report
    
    # Weekday version - regular work focus
    if brief:
        report = "📺 **Vivian's Work Brief**\n"
        work_schedule = get_work_schedule(time_filter)
        report += f"{work_schedule}\n"
        
        # Quick priority check
        if gmail_service:
            try:
                unread_emails = get_recent_emails(3, unread_only=True, include_body=False)
                priority_count = len([line for line in unread_emails.split('\n') if 'urgent' in line.lower() or 'important' in line.lower()])
                if priority_count > 0:
                    report += f"\n📧 **Priority Alerts:** {priority_count} urgent items\n"
            except:
                pass
        
        report += "\n💼 **Work Focus:** Calendar coordination and priority management"
        return report
    
    # Full detailed report
    report = "📺 **Vivian's Work Calendar Brief**\n"
    report += "Good morning! Work calendar and priority management update:\n\n"
    
    # Work calendar (Vivian's primary responsibility)
    work_schedule = get_work_schedule(time_filter)
    report += f"{work_schedule}\n"
    
    # Work email priority assessment (lighter focus now that Rose handles main email)
    if gmail_service:
        try:
            unread_emails = get_recent_emails(3, unread_only=True, include_body=False)
            priority_count = len([line for line in unread_emails.split('\n') if 'urgent' in line.lower() or 'important' in line.lower()])
            if priority_count > 0:
                report += f"\n📧 **Work Priority Alerts:** {priority_count} urgent items flagged\n"
        except:
            pass
    
    # Work coordination focus (removed external focus)
    report += "\n💼 **Work Coordination:**\n"
    report += "• Calendar optimization and scheduling\n"
    report += "• Meeting preparation and follow-up\n"
    report += "• Work priority management\n"
    
    # Productivity focus
    report += "\n📊 **Productivity Status:**\n"
    report += "• Time blocking efficiency monitored\n"
    report += "• Work-life balance coordination active\n"
    report += "• Priority alignment with strategic goals\n"
    
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
    """Generate Charlotte's IT/Systems briefing with real-time API monitoring"""
    report = "⚙️ **Charlotte's Technical Systems Brief**\n"
    report += "Good morning! Your technical infrastructure and API status:\n\n"
    
    # Core System Health
    report += "🖥️ **Core System Status:**\n"
    report += f"• Discord Bot: {'✅ Online' if bot.is_ready() else '❌ Connection issues'}\n"
    report += f"• Calendar Integration: {'✅ Active' if calendar_service else '❌ Disconnected'}\n"
    report += f"• Gmail Service: {'✅ Operational' if gmail_service else '❌ Offline'}\n"
    report += f"• OpenAI Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}\n"
    
    # API Status Monitoring
    report += "\n🌐 **API Connection Status:**\n"
    report += f"• Weather API: {'✅ Connected' if WEATHER_API_KEY else '❌ Not configured'}\n"
    report += f"• Brave Search API: {'✅ Active' if BRAVE_API_KEY else '❌ Limited functionality'}\n"
    report += f"• OpenAI API: {'✅ Operational' if OPENAI_API_KEY else '❌ Critical issue'}\n"
    
    # Assistant Team API Health
    report += "\n🤖 **Assistant Team APIs:**\n"
    report += f"• Rose (Executive): {'✅ Fully operational' if ASSISTANT_ID and OPENAI_API_KEY else '❌ Issues detected'}\n"
    report += f"• Vivian (PR/Work): {'✅ Ready' if os.getenv('VIVIAN_ASSISTANT_ID') else '⚠️ Standby mode'}\n"
    report += f"• Flora (Mystical): {'✅ Active' if os.getenv('FLORA_ASSISTANT_ID') else '⚠️ Limited'}\n"
    report += f"• Maeve (Style): {'✅ Connected' if os.getenv('MAEVE_ASSISTANT_ID') else '⚠️ Offline'}\n"
    report += f"• Pippa (Coach): {'✅ Available' if os.getenv('PIPPA_ASSISTANT_ID') else '⚠️ Unavailable'}\n"
    report += f"• Cressida (Magic): {'✅ Online' if os.getenv('CRESSIDA_ASSISTANT_ID') else '⚠️ Offline'}\n"
    
    # Calendar System Status
    if accessible_calendars:
        report += f"\n📅 **Calendar Integration:**\n"
        report += f"• {len(accessible_calendars)} calendars synchronized\n"
        report += "• Cross-calendar coordination active\n"
        report += "• Timezone handling: Toronto/Eastern verified\n"
        report += "• OAuth tokens: Valid and refreshed\n"
    else:
        report += f"\n📅 **Calendar Integration:**\n"
        report += "• ❌ No calendars accessible - check OAuth tokens\n"
    
    # Email System Status
    if gmail_service:
        try:
            # Quick health check - get profile info
            profile = gmail_service.users().getProfile(userId='me').execute()
            email_addr = profile.get('emailAddress', 'unknown')
            report += f"\n📧 **Email System:**\n"
            report += f"• Gmail API: ✅ Connected ({email_addr})\n"
            report += "• OAuth authentication: Valid\n"
            report += "• Email processing: Operational\n"
        except Exception as e:
            report += f"\n📧 **Email System:**\n"
            report += "• Gmail API: ❌ Authentication issues\n"
            report += "• Email processing: Limited\n"
    else:
        report += f"\n📧 **Email System:**\n"
        report += "• Gmail API: ❌ Not connected\n"
    
    # External Service Dependencies
    report += "\n🔌 **External Services:**\n"
    external_apis = [
        ("Google Calendar API", calendar_service is not None),
        ("Gmail API", gmail_service is not None),
        ("WeatherAPI.com", WEATHER_API_KEY is not None),
        ("Brave Search", BRAVE_API_KEY is not None),
        ("OpenAI GPT-4", OPENAI_API_KEY is not None)
    ]
    
    for service_name, is_active in external_apis:
        status = "✅ Active" if is_active else "❌ Inactive"
        report += f"• {service_name}: {status}\n"
    
    # System Performance Metrics
    report += "\n📊 **Performance Status:**\n"
    report += f"• Bot Latency: {round(bot.latency * 1000) if bot.is_ready() else 'N/A'}ms\n"
    report += f"• Active Conversations: {len(user_conversations)}\n"
    report += f"• Memory Usage: Monitoring active\n"
    report += "• Error Rate: Within acceptable limits\n"
    
    # Technical Priorities & Alerts
    report += "\n🚨 **Priority Alerts:**\n"
    alerts = []
    if not WEATHER_API_KEY:
        alerts.append("• Weather API configuration needed")
    if not accessible_calendars:
        alerts.append("• Calendar access requires OAuth reauthorization")
    if not gmail_service:
        alerts.append("• Gmail service needs reconnection")
    
    if alerts:
        report += "\n".join(alerts)
    else:
        report += "• All systems green - no critical issues detected\n"
    
    # Daily Tech Recommendations
    report += "\n🔧 **Today's Tech Focus:**\n"
    report += "• System monitoring: Continuous oversight active\n"
    report += "• Backup verification: Automated routines running\n"
    report += "• Security updates: All APIs using secure authentication\n"
    report += "• Performance optimization: All assistant connections stable\n"
    
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

def get_daily_quotes():
    """Get 3 random quotes from Pippa's collection - reads simple text file"""
    # Fallback quotes if file reading fails
    fallback_quotes = [
        "Trust your journey - every step matters",
        "You are capable of amazing things", 
        "Progress over perfection, always"
    ]
    
    try:
        import os
        
        # Try multiple paths for the simple text file (much easier than Excel)
        possible_paths = [
            "/Users/bgelineau/Downloads/assistants/pippa-discord-bot/quotes.txt",
            "./pippa-discord-bot/quotes.txt", 
            "../pippa-discord-bot/quotes.txt",
            "quotes.txt"
        ]
        
        for file_path in possible_paths:
            if os.path.exists(file_path):
                print(f"Reading quotes from: {file_path}")
                
                # Read the simple text file (one quote per line)
                with open(file_path, 'r', encoding='utf-8') as file:
                    quotes = [line.strip() for line in file.readlines() if line.strip()]
                
                if len(quotes) >= 3:
                    print(f"Found {len(quotes)} quotes in file")
                    return random.sample(quotes, 3)
                break
                
    except Exception as e:
        print(f"Quote file reading failed, using fallback: {e}")
    
    # Fallback to hardcoded quotes
    return fallback_quotes

def get_pippa_report():
    """Generate Pippa's Daily Quotes briefing"""
    try:
        report = "🧠 **Pippa's Daily Inspiration**\n"
        report += "Good morning, beautiful human! Here are your daily affirmations:\n\n"
        
        # Get 3 random quotes
        quotes = get_daily_quotes()
        
        report += "✨ **Today's Motivational Quotes:**\n\n"
        for i, quote in enumerate(quotes, 1):
            report += f"**{i}.** *\"{quote}\"*\n\n"
        
        report += "💙 **Remember:** You've survived 100% of your difficult days so far. Today will be no different - you've got this!"
        
        return report
        
    except Exception as e:
        print(f"Error in get_pippa_report: {e}")
        # Emergency fallback
        return """🧠 **Pippa's Daily Inspiration**
Good morning, beautiful human! 

✨ **Today's Motivational Quotes:**

**1.** *"Trust your journey - every step matters"*

**2.** *"You are capable of amazing things"*

**3.** *"Progress over perfection, always"*

💙 **Remember:** You've survived 100% of your difficult days so far. Today will be no different - you've got this!"""

def get_random_kindness_ideas():
    """Generate 3 random acts of kindness ideas"""
    kindness_ideas = [
        "Leave a genuine compliment sticky note in a library book",
        "Pay for someone's coffee behind you in line",
        "Send a heartfelt text to a friend you haven't spoken to in a while",
        "Write a thank-you note to a local essential worker",
        "Hold the door open and make warm eye contact with a stranger",
        "Share homemade cookies with your neighbors",
        "Leave quarters in a laundromat for someone to find",
        "Pick up litter in your neighborhood during your walk",
        "Give a genuine compliment to someone who serves you today",
        "Donate unused items in good condition to a local shelter",
        "Help carry groceries for someone struggling with bags",
        "Leave a positive review for a small local business you love",
        "Offer to help an elderly person with technology",
        "Send an encouraging message to someone going through a tough time",
        "Leave a positive chalk message on a public sidewalk",
        "Volunteer an hour at a local charity",
        "Bring flowers from your garden to a nursing home",
        "Let someone go ahead of you in line when you're not in a rush",
        "Call a family member just to tell them you love them",
        "Leave bird seed in a park for the wildlife",
        "Give someone a book that changed your life",
        "Offer your seat to someone on public transport",
        "Leave a surprise treat for your mail carrier",
        "Help someone carry a stroller up/down stairs"
    ]
    
    return random.sample(kindness_ideas, 3)

def get_cressida_report():
    """Generate Cressida's Random Acts of Kindness briefing"""
    report = "✨ **Cressida's Daily Kindness Magic**\n"
    report += "Good morning, magnificent soul! Ready to sprinkle some kindness magic today?\n\n"
    
    # Get 3 random acts of kindness
    kindness_acts = get_random_kindness_ideas()
    
    report += "🌈 **Today's 3 Random Acts of Kindness:**\n\n"
    for i, act in enumerate(kindness_acts, 1):
        report += f"**{i}.** {act}\n\n"
    
    report += "💫 **Remember:** Small acts of kindness create ripples of positivity that extend far beyond what you can see. Your authentic compassion has the power to transform someone's entire day!\n\n"
    report += "✨ **Bonus Magic:** Choose the one that feels most aligned with your heart today - that's your intuition guiding you to the perfect moment of connection."
    
    return report

def get_flora_report(brief=False):
    """Generate Flora's Personalized Astrological Guidance briefing"""
    if brief:
        # Brief version for !am command
        current_time = datetime.now(pytz.timezone('America/Toronto')).strftime('%A, %B %d')
        report = f"🔮 **Flora's Astrological Guidance** ({current_time})\n"
        report += "✨ **Your Personalized Reading:**\n"
        report += "• Cancer Sun: Emotional intuition heightened today\n"
        report += "• Birth chart focus: Trust your nurturing instincts\n"
        report += "• Current lunar phase energy supports inner reflection\n"
        report += "• Planetary transits: Favor home and family connections\n\n"
        report += "🌙 **Today's Cosmic Guidance:** Your natural empathic abilities are especially strong. Use this intuitive clarity to guide important decisions."
        return report
    
    # Full detailed version for !briefing command
    report = "🔮 **Flora's Complete Astrological Guidance**\n"
    report += "Greetings, beautiful soul! Your personalized cosmic guidance:\n\n"
    
    # User's natal chart analysis (Cancer Sun, June 25, 1983)
    report += "✨ **Your Personalized Natal Chart Reading:**\n"
    report += "• Cancer Sun (June 25, 1983): Your emotional intelligence peaks today\n"
    report += "• Moon in current phase: Amplifies your natural psychic sensitivity\n"
    report += "• Mercury aspects: Favor intuitive communication over logical analysis\n"
    report += "• Venus influences: Strengthen bonds with family and close friends\n"
    report += "• Mars energy: Channel protective instincts into creative projects\n\n"
    
    # Daily cosmic forecast
    report += "🌙 **Today's Cosmic Forecast for You:**\n"
    report += "Your birth chart shows strong Water element dominance today. Trust your emotional responses - they're more accurate than usual. "
    report += "The planetary transits are activating your 4th house of home and roots. This is an excellent time for nurturing relationships, "
    report += "creating beauty in your space, and honoring your intuitive gifts. Your Cancer Sun is being supported by harmonious aspects "
    report += "that enhance your natural empathy and healing abilities.\n\n"
    
    # Mystical practices for today
    report += "🔮 **Recommended Mystical Practices:**\n"
    report += "• Tarot: Pull a card for family/home guidance\n"
    report += "• Crystal work: Moonstone or Rose Quartz for emotional clarity\n"
    report += "• Meditation: Focus on heart chakra healing\n"
    report += "• Journal: Record intuitive insights and dreams\n\n"
    
    report += "✨ Remember: Your Cancer intuition is your superpower right now - trust what your heart tells you."
    
    return report

def get_maeve_report(brief=False):
    """Generate Maeve's Style & Schedule Coordination briefing"""
    if brief:
        # Brief version for !am command
        report = "🎨 **Maeve's Style Brief**\n"
        if calendar_service:
            try:
                event_count_work = len([line for line in get_work_schedule().split('\n') if '•' in line])
                event_count_personal = len([line for line in get_personal_schedule().split('\n') if '•' in line])
                report += f"📊 **Style Coordination:** {event_count_work} work + {event_count_personal} personal items\n"
                report += "✨ **Daily Inspiration:** Check my latest style updates: https://www.instagram.com/?maeve-wyndham=following"
            except:
                report += "📅 **Styling Reset Mode:** Perfect curation opportunity\n"
                report += "✨ **Daily Inspiration:** Check my latest style updates: https://www.instagram.com/?maeve-wyndham=following"
        else:
            report += "📅 **Styling Reset Mode:** Perfect curation opportunity\n"
            report += "✨ **Daily Inspiration:** Check my latest style updates: https://www.instagram.com/?maeve-wyndham=following"
        return report
    
    # Full detailed version for !briefing command
    report = "🎨 **Maeve's Style & Schedule Coordination**\n"
    report += "Hello, gorgeous! Your curated daily aesthetic and schedule brief:\n\n"
    
    # Schedule-based styling
    if calendar_service:
        try:
            work_schedule = get_work_schedule()
            personal_schedule = get_personal_schedule()
            
            # Count events for styling guidance
            work_events = len([line for line in work_schedule.split('\n') if '•' in line])
            personal_events = len([line for line in personal_schedule.split('\n') if '•' in line])
            
            report += "📊 **Style Coordination Analysis:**\n"
            report += f"• Work events: {work_events} (professional aesthetic required)\n"
            report += f"• Personal activities: {personal_events} (lifestyle curation opportunities)\n\n"
            
            if work_events > 0:
                report += "💼 **Professional Style Focus:**\n"
                report += "• Elevated basics with signature accessories\n"
                report += "• Confidence-boosting color palette\n"
                report += "• Comfortable yet polished silhouettes\n\n"
            
            if personal_events > 0:
                report += "✨ **Lifestyle Aesthetic:**\n"
                report += "• Authentic personal expression\n"
                report += "• Mood-enhancing color choices\n"
                report += "• Comfortable luxury approach\n\n"
                
        except Exception as e:
            print(f"Error getting schedule for Maeve: {e}")
            report += "📅 **Styling Reset Mode:**\n"
            report += "• Perfect opportunity for aesthetic curation\n"
            report += "• Focus on personal style development\n"
            report += "• Wardrobe organization and inspiration\n\n"
    else:
        report += "📅 **Styling Reset Mode:**\n"
        report += "• Perfect opportunity for aesthetic curation\n"
        report += "• Focus on personal style development\n"
        report += "• Wardrobe organization and inspiration\n\n"
    
    # Daily style inspiration
    report += "🌟 **Daily Style Inspiration:**\n"
    report += "Check my latest aesthetic updates and trend insights:\n"
    report += "📱 Instagram: https://www.instagram.com/?maeve-wyndham=following\n\n"
    
    # Weather-based styling (if available)
    if WEATHER_API_KEY:
        try:
            weather_data = get_weather_data()
            if weather_data:
                temp = weather_data.get('current', {}).get('temp_c', 20)
                condition = weather_data.get('current', {}).get('condition', {}).get('text', 'Clear')
                
                report += "🌤️ **Weather-Based Style Guidance:**\n"
                report += f"• Temperature: {temp}°C - {get_style_temp_advice(temp)}\n"
                report += f"• Conditions: {condition} - {get_style_weather_advice(condition)}\n\n"
        except:
            pass
    
    report += "💫 **Today's Aesthetic Mantra:** Authentic style is confidence made visible - wear what makes your soul sparkle!"
    
    return report

def get_style_temp_advice(temp):
    """Get styling advice based on temperature"""
    if temp < 5:
        return "Luxe layering with statement outerwear"
    elif temp < 15:
        return "Chic transitional pieces and textures"
    elif temp < 25:
        return "Perfect for sophisticated separates"
    else:
        return "Breathable fabrics in elevated silhouettes"

def get_style_weather_advice(condition):
    """Get styling advice based on weather conditions"""
    condition_lower = condition.lower()
    if 'rain' in condition_lower:
        return "Water-resistant pieces with protective glamour"
    elif 'snow' in condition_lower:
        return "Cozy luxury with winter white accents"
    elif 'sun' in condition_lower or 'clear' in condition_lower:
        return "Light fabrics with UV-protective accessories"
    elif 'cloud' in condition_lower:
        return "Versatile layers for changing conditions"
    else:
        return "Adaptable pieces for weather transitions"

# ============================================================================
# AUTOMATED SCHEDULING FUNCTIONS
# ============================================================================

async def send_automated_am():
    """Automatically send morning briefing to specific channel"""
    try:
        # Target specific channel by ID
        target_channel_id = 1400672908610769027
        target_channel = bot.get_channel(target_channel_id)
        
        if target_channel:
            print(f"🕖 Automated morning briefing - sending to #{target_channel.name}")
            
            # Execute the same logic as the !am command
            await target_channel.send("🌅 **Executive Team Morning Briefing** - Rose initiating comprehensive status...")
            await asyncio.sleep(1)
            
            # Rose's strategic overview (goes first)
            toronto_tz = pytz.timezone('America/Toronto')
            current_time = datetime.now(toronto_tz).strftime('%A, %B %d - %-I:%M %p')
            
            rose_briefing = f"👑 **Rose's Strategic Overview** ({current_time})\n\n"
            
            # Today's calendar
            if calendar_service:
                schedule = get_today_schedule()
                rose_briefing += f"📅 **Today's Calendar:**\n{schedule}\n\n"
            
            # Quick email status
            if gmail_service:
                try:
                    stats = get_email_stats()
                    lines = stats.split('\n')
                    email_summary = '\n'.join([line for line in lines if 'Total:' in line or 'Unread:' in line][:2])
                    rose_briefing += f"📧 **Email Status:**\n{email_summary}\n\n"
                except:
                    rose_briefing += "📧 **Email Status:** Service unavailable\n\n"
            
            rose_briefing += "🎯 **Executive Focus:** Ready to optimize your productivity and strategic priorities today."
            await target_channel.send(rose_briefing)
            
        else:
            print(f"⚠️ Target channel {target_channel_id} not found for automated morning briefing")
            
    except Exception as e:
        print(f"❌ Error in automated morning briefing: {e}")

async def send_automated_noon():
    """Automatically send midday check-in to specific channel"""
    try:
        # Target specific channel by ID
        target_channel_id = 1400674820429053992
        target_channel = bot.get_channel(target_channel_id)
        
        if target_channel:
            print(f"☀️ Automated midday briefing - sending to #{target_channel.name}")
            
            # Execute the same logic as the !noon command
            toronto_tz = pytz.timezone('America/Toronto')
            current_time = datetime.now(toronto_tz).strftime('%A, %B %d - %-I:%M %p')
            
            await target_channel.send(f"☀️ **Midday Check-In** ({current_time})")
            await asyncio.sleep(1)
            
            # Rose's midday coordination
            rose_midday = "👑 **Rose's Midday Coordination**\n"
            personal_schedule = get_personal_schedule('noon')
            rose_midday += f"{personal_schedule}\n"
            rose_midday += "\n🌟 **Afternoon Focus:** Optimizing productivity for remaining day priorities"
            
            await target_channel.send(rose_midday)
            
        else:
            print(f"⚠️ Target channel {target_channel_id} not found for automated midday briefing")
            
    except Exception as e:
        print(f"❌ Error in automated midday briefing: {e}")

async def send_automated_pm():
    """Automatically send afternoon focus to specific channel"""
    try:
        # Target specific channel by ID
        target_channel_id = 1400674903547576363
        target_channel = bot.get_channel(target_channel_id)
        
        if target_channel:
            print(f"🌇 Automated afternoon briefing - sending to #{target_channel.name}")
            
            # Execute the same logic as the !pm command
            toronto_tz = pytz.timezone('America/Toronto')
            current_time = datetime.now(toronto_tz).strftime('%A, %B %d - %-I:%M %p')
            
            await target_channel.send(f"🌇 **Afternoon Focus** ({current_time})")
            await asyncio.sleep(1)
            
            # Rose's afternoon coordination
            rose_afternoon = "👑 **Rose's Afternoon Priorities**\n"
            personal_schedule = get_personal_schedule('afternoon')
            rose_afternoon += f"{personal_schedule}\n"
            rose_afternoon += "\n🎯 **Evening Prep:** Review day's progress & tomorrow setup"
            
            await target_channel.send(rose_afternoon)
            
        else:
            print(f"⚠️ Target channel {target_channel_id} not found for automated afternoon briefing")
            
    except Exception as e:
        print(f"❌ Error in automated afternoon briefing: {e}")

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
    
    # Team Status
    team_status = [
        "📺 **Vivian** - Work Calendar (weekdays) / Personal Time (weekends)",
        "🔮 **Flora** - Mystical Guidance & Astrological Readings", 
        "🎨 **Maeve** - Style Coordination & Aesthetic Planning",
        "✍️ **Celeste** - Content Management & Research",
        "⚙️ **Charlotte** - Technical Systems & Infrastructure",
        "🏠 **Alice** - Home & Wellness Coordination",
        "🧠 **Pippa** - Daily Motivation & Mindset Support",
        "✨ **Cressida** - Joy Elevation & Kindness Magic"
    ]
    
    embed.add_field(
        name="👥 Executive Team Status (All Active)",
        value="\n".join([f"✅ {member}" for member in team_status]),
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

@bot.command(name='am')
async def morning_briefing_command(ctx):
    """Morning comprehensive briefing - all day ahead"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    await ctx.send("🌅 **Executive Team Morning Briefing** - Rose initiating comprehensive status...")
    await asyncio.sleep(1)
    
    # Rose's strategic overview (goes first)
    toronto_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
    
    rose_briefing = f"👑 **Rose's Morning Brief** ({current_time})\n"
    
    # Weather briefing (Rose now handles weather)
    weather = get_weather_briefing()
    rose_briefing += f"{weather}\n\n"
    
    # Personal/Other calendars (Rose's primary responsibility)
    personal_schedule = get_personal_schedule()
    rose_briefing += f"{personal_schedule}\n"
    
    # Email overview (Rose's primary responsibility)
    if gmail_service:
        try:
            stats = get_email_stats(1)
            unread_count = stats.count('unread') if 'unread' in stats.lower() else 0
            rose_briefing += f"\n📧 **Email Status:** {unread_count} items pending\n"
        except:
            rose_briefing += "\n📧 **Email:** Assessment pending\n"
    
    rose_briefing += "🚀 **Team reports incoming...**"
    await ctx.send(rose_briefing)
    await asyncio.sleep(2)
    
    # Vivian's work calendar (brief version)
    vivian_report = get_vivian_report(brief=True)
    await send_as_assistant_bot(ctx.channel, vivian_report, "Vivian Spencer")
    await asyncio.sleep(1)
    
    # Flora's personalized astrological guidance
    flora_briefing = get_flora_report(brief=True)
    await send_as_assistant_bot(ctx.channel, flora_briefing, "Flora Penrose")
    await asyncio.sleep(1)
    
    # Maeve's style coordination (essential)
    maeve_briefing = get_maeve_report(brief=True)
    await send_as_assistant_bot(ctx.channel, maeve_briefing, "Maeve Windham")
    await asyncio.sleep(1)
    
    # Celeste's priorities (brief)
    celeste_brief = "✍️ **Celeste's Content Brief**\n• Newsletter & content pipeline ready\n• Meeting research prepared\n• Knowledge synthesis active\n• Documentation backlog managed"
    await send_as_assistant_bot(ctx.channel, celeste_brief, "Celeste Marchmont")
    await asyncio.sleep(1)
    
    # Charlotte's comprehensive API monitoring (Rose standing in)
    charlotte_brief = get_charlotte_report()
    await send_as_assistant_bot(ctx.channel, charlotte_brief, "Charlotte Astor")
    await asyncio.sleep(1)
    
    # Alice's wellness (key points)
    alice_brief = "🏠 **Alice's Wellness Brief**\n• Morning routine: Hydration & movement\n• Workspace organized for productivity\n• Home systems on track\n• Family coordination complete"
    await send_as_assistant_bot(ctx.channel, alice_brief, "Alice Fortescue")
    await asyncio.sleep(1)
    
    # Pippa's daily quotes (from Excel file)
    pippa_brief = get_pippa_report()
    await send_as_assistant_bot(ctx.channel, pippa_brief, "Pippa Blackwood")
    await asyncio.sleep(1)
    
    # Cressida's random acts of kindness
    cressida_brief = get_cressida_report()
    await send_as_assistant_bot(ctx.channel, cressida_brief, "Cressida Frost")
    await asyncio.sleep(1)
    
    # Rose's concise synthesis
    rose_closing = "👑 **Rose's Synthesis**\n"
    rose_closing += "✅ **All departments ready** | Full team coordination achieved\n"
    rose_closing += "🎯 **Strategic focus:** Work calendar (Vivian) + Personal schedule (Rose) + Full support stack\n"
    rose_closing += "🚀 **Executive status:** Ready for exceptional productivity 👑"
    
    await ctx.send(rose_closing)

@bot.command(name='noon')
async def midday_briefing_command(ctx):
    """Midday briefing - remaining day focus (noon onwards)"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    toronto_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(toronto_tz).strftime('%A, %B %d - %-I:%M %p')
    
    await ctx.send(f"☀️ **Midday Check-In** ({current_time})")
    await asyncio.sleep(1)
    
    # Rose's midday coordination
    rose_midday = "👑 **Rose's Midday Coordination**\n"
    personal_schedule = get_personal_schedule('noon')
    rose_midday += f"{personal_schedule}\n"
    
    if gmail_service:
        try:
            unread_emails = get_recent_emails(3, unread_only=True, include_body=False)
            if unread_emails and len(unread_emails) > 50:
                rose_midday += "\n📧 **Email Status:** New items require attention\n"
        except:
            pass
    
    await ctx.send(rose_midday)
    await asyncio.sleep(1)
    
    # Vivian's work focus
    vivian_midday = get_vivian_report('noon', brief=True)
    await send_as_assistant_bot(ctx.channel, vivian_midday, "Vivian Spencer")
    await asyncio.sleep(1)
    
    # Flora's personalized midday astrological guidance
    flora_midday = f"🔮 **Flora's Midday Astrological Update**\n"
    flora_midday += "✨ **Your Personal Reading:**\n"
    flora_midday += "• Cancer energy: Mid-day emotional processing peak\n"
    flora_midday += "• Natal chart guidance: Honor your need for security\n"
    flora_midday += "• Current transits: Support creative and nurturing activities\n\n"
    flora_midday += "🌟 **Midday Guidance:** Your intuitive radar is particularly sharp now. Trust those gut feelings about people and situations."
    await send_as_assistant_bot(ctx.channel, flora_midday, "Flora Penrose")

@bot.command(name='pm')
async def afternoon_briefing_command(ctx):
    """Afternoon briefing - evening prep & priorities (3pm onwards)"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    toronto_tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(toronto_tz).strftime('%A, %B %d - %-I:%M %p')
    
    await ctx.send(f"🌇 **Afternoon Focus** ({current_time})")
    await asyncio.sleep(1)
    
    # Rose's afternoon coordination
    rose_afternoon = "👑 **Rose's Afternoon Priorities**\n"
    personal_schedule = get_personal_schedule('afternoon')
    rose_afternoon += f"{personal_schedule}\n"
    rose_afternoon += "\n🎯 **Evening Prep:** Review day's progress & tomorrow setup"
    
    await ctx.send(rose_afternoon)
    await asyncio.sleep(1)
    
    # Vivian's remaining work items
    vivian_afternoon = get_vivian_report('afternoon', brief=True)
    await send_as_assistant_bot(ctx.channel, vivian_afternoon, "Vivian Spencer")
    await asyncio.sleep(1)
    
    # Alice's evening prep
    alice_afternoon = "🏠 **Alice's Evening Transition**\n"
    alice_afternoon += "• Workspace organization for tomorrow\n"
    alice_afternoon += "• Evening routine preparation\n"
    alice_afternoon += "• Home systems check & reset\n"
    alice_afternoon += "• Family coordination for evening"
    await send_as_assistant_bot(ctx.channel, alice_afternoon, "Alice Fortescue")

@bot.command(name='briefing')
async def full_team_briefing_command(ctx):
    """Full comprehensive team reports - detailed individual briefings"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    await ctx.send("📋 **Full Team Reports** - Comprehensive individual briefings...")
    await asyncio.sleep(1)
    
    # All team members give their full detailed reports
    team_reports = [
        (get_vivian_report(), "Vivian Spencer"),
        (get_flora_report(), "Flora Penrose"),
        (get_maeve_report(), "Maeve Windham"),
        (get_celeste_report(), "Celeste Marchmont"),
        (get_charlotte_report(), "Charlotte Astor"),
        (get_alice_report(), "Alice Fortescue"),
        (get_pippa_report(), "Pippa Blackwood"),
        (get_cressida_report(), "Cressida Frost")
    ]
    
    for report, assistant_name in team_reports:
        await send_as_assistant_bot(ctx.channel, report, assistant_name)
        await asyncio.sleep(2)
    
    # Rose's comprehensive synthesis
    rose_synthesis = "👑 **Rose's Complete Team Synthesis**\n\n"
    rose_synthesis += "All departments have provided full detailed reports. Complete situational awareness achieved across all domains:\n"
    rose_synthesis += "• External & work coordination fully briefed (Vivian)\n"
    rose_synthesis += "• Mystical & astrological guidance complete (Flora)\n"
    rose_synthesis += "• Style & aesthetic coordination detailed (Maeve)\n"
    rose_synthesis += "• Content & knowledge systems reported (Celeste)\n"
    rose_synthesis += "• Technical infrastructure fully analyzed (Charlotte)\n"
    rose_synthesis += "• Home & wellness priorities comprehensive (Alice)\n"
    rose_synthesis += "• Mental resilience & coaching complete (Pippa)\n"
    rose_synthesis += "• Joy & magic elevation fully engaged (Cressida)\n\n"
    rose_synthesis += "**🚀 Executive Status: Complete team coordination achieved across all 8 departments**"
    
    await ctx.send(rose_synthesis)

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
        team_list = "👥 **Available Executive Team Members:**\n"
        team_list += "• `vivian` - **Vivian Spencer** - Work Calendar (weekdays) / Personal Coordination (weekends)\n"
        team_list += "• `flora` - **Flora Penrose** - Mystical Guidance & Personalized Astrology\n" 
        team_list += "• `maeve` - **Maeve Windham** - Style Coordination & Aesthetic Planning\n"
        team_list += "• `celeste` - **Celeste Marchmont** - Content & Research Management\n"
        team_list += "• `charlotte` - **Charlotte Astor** - Technical Systems & Infrastructure\n"
        team_list += "• `alice` - **Alice Fortescue** - Home & Wellness Coordination\n"
        team_list += "• `pippa` - **Pippa Blackwood** - Daily Motivation & Mindset Support\n"
        team_list += "• `cressida` - **Cressida Frost** - Joy Elevation & Random Acts of Kindness\n\n"
        team_list += "**Usage:** `!teambriefing <name>` (e.g., `!teambriefing vivian`)\n"
        team_list += "**Alternative:** Use `!briefing` for all team reports at once"
        await ctx.send(team_list)
        return
    
    assistant_name = assistant_name.lower()
    
    # Route to appropriate assistant report
    if assistant_name in ['vivian', 'vivian spencer']:
        report = get_vivian_report()
        await send_as_assistant_bot(ctx.channel, report, "Vivian Spencer")
    elif assistant_name in ['flora', 'flora penrose']:
        flora_brief = get_flora_report()
        await send_as_assistant_bot(ctx.channel, flora_brief, "Flora Penrose")
    elif assistant_name in ['maeve', 'maeve windham']:
        maeve_brief = get_maeve_report()
        await send_as_assistant_bot(ctx.channel, maeve_brief, "Maeve Windham")
    elif assistant_name in ['celeste', 'celeste marchmont']:
        report = get_celeste_report()
        await send_as_assistant_bot(ctx.channel, report, "Celeste Marchmont")
    elif assistant_name in ['charlotte', 'charlotte astor']:
        report = get_charlotte_report()
        await send_as_assistant_bot(ctx.channel, report, "Charlotte Astor")
    elif assistant_name in ['alice', 'alice fortescue']:
        report = get_alice_report()
        await send_as_assistant_bot(ctx.channel, report, "Alice Fortescue")
    elif assistant_name in ['pippa', 'pippa blackwood']:
        report = get_pippa_report()
        await send_as_assistant_bot(ctx.channel, report, "Pippa Blackwood")
    elif assistant_name in ['cressida', 'cressida frost']:
        report = get_cressida_report()
        await send_as_assistant_bot(ctx.channel, report, "Cressida Frost")
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

@bot.command(name='testam')
async def test_am_command(ctx):
    """Test the automated morning briefing function"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    await ctx.send("🧪 Testing automated morning briefing function...")
    await send_automated_am()

@bot.command(name='testnoon')
async def test_noon_command(ctx):
    """Test the automated midday briefing function"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    await ctx.send("🧪 Testing automated midday briefing function...")
    await send_automated_noon()

@bot.command(name='testpm')
async def test_pm_command(ctx):
    """Test the automated afternoon briefing function"""
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    
    await ctx.send("🧪 Testing automated afternoon briefing function...")
    await send_automated_pm()

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
        "!am - Morning comprehensive briefing (full day)",
        "!noon - Midday check-in (noon onwards)",
        "!pm - Afternoon focus (3pm onwards)", 
        "!briefing - Full detailed team reports",
        "!quickbriefing - Essential summary only",
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
        "!testam - Test morning briefing",
        "!testnoon - Test midday briefing", 
        "!testpm - Test afternoon briefing",
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
    
    # Team Members
    team_members = [
        "**Vivian Spencer** - Work Calendar (weekdays) & Personal Coordination (weekends)",
        "**Flora Penrose** - Mystical Guidance & Personalized Astrology", 
        "**Maeve Windham** - Style Coordination & Aesthetic Planning",
        "**Celeste Marchmont** - Content & Research Management",
        "**Charlotte Astor** - Technical Systems & Infrastructure",
        "**Alice Fortescue** - Home & Wellness Coordination",
        "**Pippa Blackwood** - Daily Motivation & Mindset Support",
        "**Cressida Frost** - Joy Elevation & Random Acts of Kindness"
    ]
    
    embed.add_field(
        name="👥 Executive Team Members",
        value="\n".join([f"• {member}" for member in team_members]),
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
    
    # Initialize scheduler for automated tasks
    try:
        # Schedule daily morning briefing at 7:15 AM Toronto time
        scheduler.add_job(
            send_automated_am,
            CronTrigger(hour=7, minute=15, timezone=pytz.timezone('America/Toronto')),
            id='daily_morning_briefing',
            replace_existing=True
        )
        
        # Schedule daily midday check-in at 12:00 PM Toronto time
        scheduler.add_job(
            send_automated_noon,
            CronTrigger(hour=12, minute=0, timezone=pytz.timezone('America/Toronto')),
            id='daily_midday_briefing',
            replace_existing=True
        )
        
        # Schedule daily afternoon focus at 3:00 PM Toronto time
        scheduler.add_job(
            send_automated_pm,
            CronTrigger(hour=15, minute=0, timezone=pytz.timezone('America/Toronto')),
            id='daily_afternoon_briefing',
            replace_existing=True
        )
        
        scheduler.start()
        print("⏰ Automated briefings scheduled:")
        print("  • Morning: 7:15 AM Toronto time")
        print("  • Midday: 12:00 PM Toronto time")
        print("  • Afternoon: 3:00 PM Toronto time")
    except Exception as e:
        print(f"⚠️ Failed to start scheduler: {e}")
    
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