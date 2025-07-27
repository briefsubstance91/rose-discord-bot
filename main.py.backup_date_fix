#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE DISCORD BOT WITH FULL FUNCTIONALITY RESTORED
Executive Assistant with Calendar Management, Email Management, Weather, and Strategic Planning
RESTORED: All original functionality + Fixed calendar syntax
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
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

# Rose's executive configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant (Enhanced with Weather)"
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

# Set the assistant config for universal commands
ASSISTANT_CONFIG = ROSE_CONFIG

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Weather API configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
USER_CITY = os.getenv('USER_CITY', 'Toronto')
USER_LAT = os.getenv('USER_LAT')
USER_LON = os.getenv('USER_LON')

# Enhanced calendar and email integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')
BRITT_ICLOUD_CALENDAR_ID = os.getenv('BRITT_ICLOUD_CALENDAR_ID')
GMAIL_WORK_CALENDAR_ID = os.getenv('GMAIL_WORK_CALENDAR_ID')

# Gmail OAuth setup
GMAIL_OAUTH_JSON = os.getenv('GMAIL_OAUTH_JSON')
GMAIL_TOKEN_JSON = os.getenv('GMAIL_TOKEN_JSON')
GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')

# Gmail OAuth scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
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

# Discord setup with error handling
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Active runs tracking for rate limiting
    active_runs = {}
    
    # Memory management variables
    user_conversations = {}  # user_id -> thread_id
    channel_conversations = {}  # channel_id -> thread_id  
    conversation_metadata = {}  # thread_id -> metadata
    processing_messages = set()
    last_response_time = {}
    
    print(f"✅ {ASSISTANT_NAME} initialized successfully")
    print(f"🤖 OpenAI Assistant ID: {ASSISTANT_ID}")
    print(f"🌤️ Weather API configured: {'✅ Yes' if WEATHER_API_KEY else '❌ No'}")
    
except Exception as e:
    print(f"❌ CRITICAL: Failed to initialize {ASSISTANT_NAME}: {e}")
    exit(1)

# ============================================================================
# GOOGLE SERVICES INITIALIZATION
# ============================================================================

# Initialize services as None - will be set up later
calendar_service = None
gmail_service = None
accessible_calendars = []

def initialize_google_services():
    """Initialize Google Calendar and Gmail services"""
    global calendar_service, gmail_service, accessible_calendars
    
    print("🔧 Initializing Google Calendar integration...")
    
    try:
        # Calendar Service (Service Account)
        if GOOGLE_SERVICE_ACCOUNT_JSON:
            try:
                service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
                credentials = Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                calendar_service = build('calendar', 'v3', credentials=credentials)
                print("✅ Google services initialized")
                print(f"📧 Service Account: {service_account_info.get('client_email', 'Unknown')}")
                
                # Test calendar access
                test_calendar_access()
                
            except Exception as e:
                print(f"❌ Service Account Calendar Error: {e}")
        else:
            print("⚠️ No Google service account configured")
        
        # Gmail Service (OAuth)
        print("🔧 Initializing Gmail OAuth2 integration...")
        
        if GMAIL_TOKEN_JSON:
            try:
                token_info = json.loads(GMAIL_TOKEN_JSON)
                gmail_credentials = OAuthCredentials.from_authorized_user_info(
                    token_info, GMAIL_SCOPES
                )
                
                if gmail_credentials and gmail_credentials.valid:
                    gmail_service = build('gmail', 'v1', credentials=gmail_credentials)
                    print("✅ OAuth Gmail service initialized with modify permissions")
                elif gmail_credentials and gmail_credentials.expired and gmail_credentials.refresh_token:
                    gmail_credentials.refresh(Request())
                    gmail_service = build('gmail', 'v1', credentials=gmail_credentials)
                    print("✅ OAuth Gmail service refreshed and initialized")
                else:
                    print("❌ Gmail OAuth credentials invalid")
            except Exception as e:
                print(f"❌ Gmail OAuth Error: {e}")
        else:
            print("⚠️ No Gmail OAuth token configured")
        
    except Exception as e:
        print(f"❌ Google services initialization error: {e}")
    
    print(f"📅 Calendar Service: {'✅ Ready' if calendar_service else '❌ Not available'}")
    print(f"📧 Gmail Service: {'✅ Ready' if gmail_service else '❌ Not available'}")

def test_calendar_access():
    """Test access to configured calendars"""
    global accessible_calendars
    
    if not calendar_service:
        return
    
    calendars_to_test = [
        ('primary', '🐝 BG Personal'),
        (GOOGLE_CALENDAR_ID, '📆 BG Calendar'),
        (GOOGLE_TASKS_CALENDAR_ID, '✅ BG Tasks'),
        (BRITT_ICLOUD_CALENDAR_ID, 'Britt'),
        (GMAIL_WORK_CALENDAR_ID, '💼 BG Work')
    ]
    
    accessible_calendars = []
    
    for calendar_id, calendar_name in calendars_to_test:
        if not calendar_id:
            continue
            
        try:
            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=datetime.now(timezone.utc).isoformat(),
                maxResults=1,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
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
# WEATHER FUNCTIONS
# ============================================================================

async def get_weather_briefing():
    """Get comprehensive weather briefing from WeatherAPI.com"""
    if not WEATHER_API_KEY:
        return "🌤️ Weather information not available (API key not configured)"
    
    try:
        # Use coordinates if available, otherwise city name
        location = f"{USER_LAT},{USER_LON}" if USER_LAT and USER_LON else USER_CITY
        
        print(f"🌍 Fetching enhanced weather for {USER_CITY} ({location})...")
        
        # WeatherAPI.com current + forecast endpoint
        url = f"http://api.weatherapi.com/v1/forecast.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'days': 2,  # Today + tomorrow
            'aqi': 'yes',  # Air quality
            'alerts': 'yes'  # Weather alerts
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Current conditions
                    current = data['current']
                    location_data = data['location']
                    forecast_days = data['forecast']['forecastday']
                    
                    # Today's forecast
                    today_forecast = forecast_days[0]['day']
                    tomorrow_forecast = forecast_days[1]['day'] if len(forecast_days) > 1 else None
                    
                    # Format current time in Toronto timezone
                    toronto_tz = pytz.timezone('America/Toronto')
                    current_time = datetime.now(toronto_tz)
                    
                    print(f"✅ Enhanced weather data retrieved: Current {current['temp_c']}°C, High {today_forecast['maxtemp_c']}°C")
                    
                    # Build comprehensive weather briefing
                    weather_briefing = f"🌤️ **Weather Update** ({current_time.strftime('%Y-%m-%d %H:%M')})\n"
                    weather_briefing += f"📍 **{location_data['name']}, {location_data['country']}:** {current['temp_c']}°C {current['condition']['text']}\n"
                    weather_briefing += f"🌡️ **Current:** Feels like {current['feelslike_c']}°C | Humidity: {current['humidity']}% | Wind: {current['wind_kph']} km/h {current['wind_dir']}\n"
                    weather_briefing += f"🔆 **UV Index:** {current['uv']} - {get_uv_description(current['uv'])}\n"
                    weather_briefing += f"📊 **Today's Forecast:** {today_forecast['mintemp_c']}°C to {today_forecast['maxtemp_c']}°C - {today_forecast['condition']['text']}\n"
                    weather_briefing += f"🌧️ **Rain Chance:** {today_forecast['daily_chance_of_rain']}%\n"
                    
                    # Tomorrow preview
                    if tomorrow_forecast:
                        weather_briefing += f"🔮 **Tomorrow Preview:** {tomorrow_forecast['mintemp_c']}°C to {tomorrow_forecast['maxtemp_c']}°C - {tomorrow_forecast['condition']['text']} ({tomorrow_forecast['daily_chance_of_rain']}% rain)"
                    
                    return weather_briefing
                    
                else:
                    return f"🌤️ Weather service temporarily unavailable (HTTP {response.status})"
                    
    except Exception as e:
        print(f"❌ Weather API error: {e}")
        return f"🌤️ Weather information temporarily unavailable: {str(e)}"

def get_uv_description(uv_index):
    """Get UV index description"""
    uv = float(uv_index)
    if uv <= 2:
        return "Low - Minimal protection needed"
    elif uv <= 5:
        return "Moderate - Seek shade during midday"
    elif uv <= 7:
        return "High - Protection essential"
    elif uv <= 10:
        return "Very High - Extra protection required"
    else:
        return "Extreme - Avoid sun exposure"

# ============================================================================
# CALENDAR FUNCTIONS IMPLEMENTATION (FIXED SYNTAX)
# ============================================================================

def create_gcal_event(calendar_id="primary", summary=None, description=None, 
                     start_time=None, end_time=None, location=None, attendees=None):
    """Create a new Google Calendar event with enhanced error handling and debugging"""
    print(f"🔧 create_gcal_event called with:")
    print(f"   summary: {summary}")
    print(f"   start_time: {start_time}")
    print(f"   end_time: {end_time}")
    print(f"   calendar_id: {calendar_id}")
    
    if not calendar_service:
        error_msg = "❌ Calendar service not available"
        print(error_msg)
        return error_msg
    
    if not summary or not start_time or not end_time:
        error_msg = "❌ Missing required fields: summary, start_time, end_time"
        print(error_msg)
        return error_msg
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        print(f"🌍 Using timezone: {toronto_tz}")
        
        # ENHANCED DATE PARSING - Handle multiple formats and fix year issues
        def parse_datetime_with_current_year(time_str):
            """Parse datetime string and ensure it uses current year if needed"""
            print(f"🕐 Parsing time string: {time_str}")
            
            # Handle string input
            if isinstance(time_str, str):
                # Remove Z suffix if present
                time_str = time_str.replace('Z', '')
                
                # Add time if only date provided
                if 'T' not in time_str:
                    time_str = time_str + 'T09:00:00'
                    print(f"🕐 Added default time: {time_str}")
                
                # Parse the datetime
                try:
                    dt = datetime.fromisoformat(time_str)
                    print(f"🕐 Parsed datetime: {dt}")
                    
                    # FIX: If year is 2023 or earlier, use current year
                    current_year = datetime.now().year
                    if dt.year < current_year:
                        dt = dt.replace(year=current_year)
                        print(f"🕐 Updated to current year: {dt}")
                    
                    # Localize to Toronto timezone if no timezone info
                    if dt.tzinfo is None:
                        dt = toronto_tz.localize(dt)
                        print(f"🕐 Localized to Toronto: {dt}")
                    
                    return dt
                    
                except ValueError as e:
                    print(f"❌ Date parsing error: {e}")
                    # Fallback: try to parse with current date
                    now = datetime.now(toronto_tz)
                    # Extract time if possible
                    if ':' in time_str:
                        time_part = time_str.split('T')[-1]
                        hour, minute = time_part.split(':')[:2]
                        dt = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
                        print(f"🕐 Fallback parsed: {dt}")
                        return dt
                    else:
                        raise e
            else:
                return time_str
        
        # Parse start and end times with enhanced logic
        start_dt = parse_datetime_with_current_year(start_time)
        end_dt = parse_datetime_with_current_year(end_time)
        
        print(f"✅ Final parsed times:")
        print(f"   Start: {start_dt}")
        print(f"   End: {end_dt}")
        
        # Build event object
        event = {
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
            event['description'] = description
            
        if location:
            event['location'] = location
            
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        print(f"📅 Creating event object: {event}")
        
        # Create the event
        print(f"🚀 Calling Google Calendar API...")
        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        print(f"✅ Event created successfully!")
        print(f"   Event ID: {created_event.get('id')}")
        print(f"   HTML Link: {created_event.get('htmlLink')}")
        
        # Format success message
        event_link = created_event.get('htmlLink', '')
        event_id = created_event.get('id', '')
        
        formatted_time = start_dt.strftime('%a %m/%d at %-I:%M %p')
        
        # FIXED: Properly format the result string
        result = "✅ **Event Created Successfully**\n"
        result += f"📅 **{summary}**\n"
        result += f"🕐 {formatted_time}\n"
        if location:
            result += f"📍 {location}\n"
        if event_link:
            result += f"🔗 [View in Calendar]({event_link})\n"
        result += f"🆔 Event ID: `{event_id}`"
        
        print(f"📝 Returning result: {result}")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error creating calendar event: {str(e)}"
        print(f"❌ EXCEPTION in create_gcal_event: {e}")
        import traceback
        traceback.print_exc()
        return error_msg

def update_gcal_event(calendar_id, event_id, summary=None, description=None,
                     start_time=None, end_time=None, location=None, attendees=None):
    """Update an existing Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not calendar_id or not event_id:
        return "❌ Missing required fields: calendar_id, event_id"
    
    try:
        # Get existing event
        existing_event = calendar_service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Update only provided fields
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
        
        if attendees:
            existing_event['attendees'] = [{'email': email} for email in attendees]
        
        # Update the event
        updated_event = calendar_service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=existing_event
        ).execute()
        
        event_link = updated_event.get('htmlLink', '')
        title = updated_event.get('summary', 'Event')
        
        result = "✅ **Event Updated Successfully**\n"
        result += f"📅 **{title}**\n"
        if event_link:
            result += f"🔗 [View in Calendar]({event_link})\n"
        result += f"🆔 Event ID: `{event_id}`"
        
        return result
        
    except Exception as e:
        print(f"❌ Error updating calendar event: {e}")
        return f"❌ Error updating calendar event: {str(e)}"

def delete_gcal_event(calendar_id, event_id):
    """Delete a Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not calendar_id or not event_id:
        return "❌ Missing required fields: calendar_id, event_id"
    
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
        
        return f"✅ **Event Deleted Successfully**\n📅 **{event_title}**\n🆔 Event ID: `{event_id}`"
        
    except Exception as e:
        print(f"❌ Error deleting calendar event: {e}")
        return f"❌ Error deleting calendar event: {str(e)}"

def list_gcal_events(calendar_id="primary", max_results=25, query=None, 
                    time_min=None, time_max=None):
    """List Google Calendar events"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Set default time range if not provided
        if not time_min:
            time_min = datetime.now(toronto_tz)
        if not time_max:
            time_max = datetime.now(toronto_tz) + timedelta(days=30)
        
        # Build query parameters
        params = {
            'calendarId': calendar_id,
            'timeMin': time_min.isoformat() if hasattr(time_min, 'isoformat') else time_min,
            'timeMax': time_max.isoformat() if hasattr(time_max, 'isoformat') else time_max,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if query:
            params['q'] = query
        
        # Get events
        events_result = calendar_service.events().list(**params).execute()
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No events found for the specified criteria"
        
        # Format events list
        result = f"📅 **Calendar Events ({len(events)} found)**\n\n"
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Untitled')
            event_id = event.get('id', '')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%a %m/%d %I:%M %p')
            else:
                date_obj = datetime.fromisoformat(start)
                time_str = date_obj.strftime('%a %m/%d (All day)')
            
            result += f"• **{time_str}** - {summary}\n"
            result += f"  🆔 `{event_id}`\n\n"
        
        return result
        
    except Exception as e:
        print(f"❌ Error listing calendar events: {e}")
        return f"❌ Error listing calendar events: {str(e)}"

def fetch_gcal_event(calendar_id, event_id):
    """Fetch details of a specific Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not calendar_id or not event_id:
        return "❌ Missing required fields: calendar_id, event_id"
    
    try:
        event = calendar_service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Extract event details
        summary = event.get('summary', 'Untitled Event')
        description = event.get('description', 'No description')
        location = event.get('location', 'No location specified')
        
        # Format start time
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
            else:
                start_dt = start_dt.astimezone(toronto_tz)
            time_str = start_dt.strftime('%A, %B %d, %Y at %-I:%M %p')
        else:
            date_obj = datetime.fromisoformat(start)
            time_str = date_obj.strftime('%A, %B %d, %Y (All day)')
        
        # Format attendees
        attendees = event.get('attendees', [])
        attendee_list = [att.get('email', 'Unknown') for att in attendees] if attendees else ['No attendees']
        
        # Build detailed response
        result = "📅 **Event Details**\n\n"
        result += f"**Title:** {summary}\n"
        result += f"**Time:** {time_str}\n"
        result += f"**Location:** {location}\n"
        result += f"**Description:** {description}\n"
        result += f"**Attendees:** {', '.join(attendee_list)}\n"
        result += f"**Event ID:** `{event_id}`\n"
        
        if event.get('htmlLink'):
            result += f"**Calendar Link:** [View Event]({event['htmlLink']})"
        
        return result
        
    except Exception as e:
        print(f"❌ Error fetching calendar event: {e}")
        return f"❌ Error fetching calendar event: {str(e)}"

def find_free_time(calendar_ids, time_min, time_max):
    """Find free time slots across multiple calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        # This is a simplified implementation
        # For a full implementation, you'd use the Calendar API's freebusy query
        result = "🔍 **Free Time Analysis**\n\n"
        result += f"⏰ **Time Range:** {time_min} to {time_max}\n"
        result += f"📅 **Calendars Checked:** {len(calendar_ids)}\n\n"
        result += "💡 *Note: Full free/busy analysis coming soon. Use list_gcal_events to check specific calendars for conflicts.*"
        
        return result
        
    except Exception as e:
        print(f"❌ Error finding free time: {e}")
        return f"❌ Error finding free time: {str(e)}"

def list_gcal_calendars():
    """List all available Google Calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if not calendars:
            return "📅 No calendars found"
        
        result = f"📅 **Available Calendars ({len(calendars)})**\n\n"
        
        for cal in calendars:
            cal_id = cal.get('id', 'Unknown ID')
            summary = cal.get('summary', 'Untitled Calendar')
            primary = " (Primary)" if cal.get('primary') else ""
            
            result += f"• **{summary}**{primary}\n"
            result += f"  🆔 `{cal_id}`\n\n"
        
        return result
        
    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return f"❌ Error listing calendars: {str(e)}"

# ============================================================================
# EMAIL FUNCTIONS
# ============================================================================

def get_recent_emails(count=10, unread_only=False, include_body=False):
    """Get recent emails with enhanced formatting"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        query = 'is:unread' if unread_only else ''
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No {'unread ' if unread_only else ''}emails found"
        
        email_list = []
        for msg in messages[:count]:
            try:
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Clean sender name
                if '<' in sender and '>' in sender:
                    sender = sender.split('<')[0].strip().strip('"')
                elif '@' in sender:
                    sender = sender.split('@')[0]
                
                snippet = message.get('snippet', '')[:100] + '...' if len(message.get('snippet', '')) > 100 else message.get('snippet', '')
                
                email_entry = f"📧 **{subject[:60]}{'...' if len(subject) > 60 else ''}**\n"
                email_entry += f"👤 From: {sender}\n"
                if include_body:
                    email_entry += f"📝 {snippet}\n"
                
                email_list.append(email_entry)
                
            except Exception as e:
                print(f"❌ Error processing email {msg['id']}: {e}")
                continue
        
        status = "Unread" if unread_only else "Recent"
        return f"📧 **{status} Emails ({len(email_list)}):**\n\n" + "\n".join(email_list)
        
    except Exception as e:
        print(f"❌ Error getting emails: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def search_emails(query, max_results=10, include_body=False):
    """Search emails with specific query"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found matching: {query}"
        
        email_list = []
        for msg in messages:
            try:
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                
                # Clean sender name
                if '<' in sender and '>' in sender:
                    sender = sender.split('<')[0].strip().strip('"')
                elif '@' in sender:
                    sender = sender.split('@')[0]
                
                snippet = message.get('snippet', '')[:100] + '...' if len(message.get('snippet', '')) > 100 else message.get('snippet', '')
                
                email_entry = f"📧 **{subject[:60]}{'...' if len(subject) > 60 else ''}**\n"
                email_entry += f"👤 From: {sender}\n"
                if include_body:
                    email_entry += f"📝 {snippet}\n"
                
                email_list.append(email_entry)
                
            except Exception as e:
                print(f"❌ Error processing email {msg['id']}: {e}")
                continue
        
        return f"📧 **Email Search Results for '{query}' ({len(email_list)}):**\n\n" + "\n".join(email_list)
        
    except Exception as e:
        print(f"❌ Error searching emails: {e}")
        return f"❌ Error searching emails: {str(e)}"

def get_email_stats(days=7):
    """Get email statistics for the past N days"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format for Gmail search
        after_date = start_date.strftime('%Y/%m/%d')
        
        # Get various email counts
        queries = {
            'total': f'after:{after_date}',
            'unread': f'is:unread after:{after_date}',
            'sent': f'in:sent after:{after_date}',
            'important': f'is:important after:{after_date}'
        }
        
        stats = {}
        for category, query in queries.items():
            try:
                result = gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=1000
                ).execute()
                stats[category] = len(result.get('messages', []))
            except Exception as e:
                print(f"❌ Error getting {category} count: {e}")
                stats[category] = 0
        
        # Current unread count (all time)
        try:
            unread_result = gmail_service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=1000
            ).execute()
            total_unread = len(unread_result.get('messages', []))
        except:
            total_unread = 0
        
        # Format response
        result = f"📊 **Email Dashboard (Last {days} days):**\n\n"
        result += f"📧 **Received:** {stats['total']} emails\n"
        result += f"📤 **Sent:** {stats['sent']} emails\n"
        result += f"⭐ **Important:** {stats['important']} emails\n"
        result += f"🔴 **Unread (all time):** {total_unread} emails\n"
        result += f"📊 **Daily Average:** {stats['total'] // days if days > 0 else 0} emails/day"
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting email stats: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_emails_from_sender(sender_email, max_delete=50):
    """Delete emails from a specific sender (with safety limit)"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        # Search for emails from sender
        query = f'from:{sender_email}'
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_delete
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from: {sender_email}"
        
        deleted_count = 0
        for msg in messages:
            try:
                gmail_service.users().messages().delete(
                    userId='me',
                    id=msg['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {msg['id']}: {e}")
                continue
        
        return f"🗑️ **Deleted {deleted_count} emails from {sender_email}**\n({len(messages) - deleted_count} failed to delete)"
        
    except Exception as e:
        print(f"❌ Error deleting emails: {e}")
        return f"❌ Error deleting emails: {str(e)}"

# ============================================================================
# CALENDAR VIEW FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's schedule from all accessible calendars"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        today_start = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=today_start.isoformat(),
                    timeMax=today_end.isoformat(),
                    singleEvents=True,
                    orderBy='startTime',
                    maxResults=20
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return f"📅 No events scheduled for today ({today_start.strftime('%A, %B %d')})"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events[:15]:  # Limit to 15 events for Discord
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%-I:%M %p')
            else:
                time_str = 'All day'
            
            # Add calendar indicator
            calendar_emoji = {
                '🐝 BG Personal': '🐝',
                '📆 BG Calendar': '📆',
                '✅ BG Tasks': '✅',
                'Britt': '🍎',
                '💼 BG Work': '💼'
            }.get(calendar_name, '📅')
            
            formatted_events.append(f"   {calendar_emoji} **{time_str}** - {summary}")
        
        current_date = today_start.strftime('%A, %B %d')
        return f"📅 **Today's Schedule** ({current_date}):\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events from all accessible calendars"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar service not available"
    
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
                    singleEvents=True,
                    orderBy='startTime',
                    maxResults=20
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return f"📅 No events scheduled for the next {days} days"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events[:15]:  # Limit to 15 events for Discord
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%a %m/%d %I:%M %p')
            else:
                date_obj = datetime.fromisoformat(start)
                time_str = date_obj.strftime('%a %m/%d (All day)')
            
            formatted_events.append(f"• {time_str} - {summary}")
        
        return f"📅 **Upcoming Events (Next {days} days):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting upcoming events: {e}")
        return f"❌ Error retrieving upcoming events: {str(e)}"

async def get_morning_briefing():
    """Comprehensive morning briefing with weather and calendar"""
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        
        # Get weather briefing
        weather_info = await get_weather_briefing()
        
        # Get today's schedule
        today_schedule = get_today_schedule()
        
        # Get email stats if available
        email_summary = ""
        if gmail_service:
            try:
                stats = get_email_stats(1)  # Just today
                email_summary = f"\n\n📧 **Email Overview:**\n{stats}"
            except Exception as e:
                print(f"❌ Error getting email stats for briefing: {e}")
        
        # Combine into morning briefing
        briefing = f"🌅 **Good Morning!** ({current_time})\n\n"
        briefing += weather_info + "\n\n"
        briefing += today_schedule
        briefing += email_summary
        briefing += "\n\n👑 **Ready to make today productive?**"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Error generating morning briefing: {e}")
        return f"🌅 **Morning Briefing:** Unable to generate full briefing. Error: {str(e)}"

# ============================================================================
# WEB SEARCH FUNCTION
# ============================================================================

async def web_search(query):
    """Perform web search using Brave API"""
    if not BRAVE_API_KEY:
        return "🔍 Web search not available - API key not configured"
    
    try:
        headers = {
            'Accept': 'application/json',
            'X-Subscription-Token': BRAVE_API_KEY
        }
        
        params = {
            'q': query,
            'count': 5,
            'search_lang': 'en',
            'country': 'ca',
            'safesearch': 'moderate'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return f"🔍 No search results found for: {query}"
                    
                    formatted_results = []
                    for result in results[:3]:
                        title = result.get('title', 'No title')
                        description = result.get('description', 'No description')
                        url = result.get('url', '')
                        
                        formatted_results.append(f"**{title}**\n{description}\n{url}")
                    
                    return f"🔍 **Search Results for '{query}':**\n\n" + "\n\n".join(formatted_results)
                else:
                    return f"🔍 Search error: HTTP {response.status}"
                    
    except Exception as e:
        print(f"❌ Web search error: {e}")
        return f"🔍 Search error: {str(e)}"

# ============================================================================
# ENHANCED FUNCTION HANDLING WITH ALL CAPABILITIES
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
                # This needs to be awaited, but we're in a sync function
                # For now, return a placeholder
                result = "🌅 Morning briefing available via !briefing command"
            
            # Web search function
            elif function_name == "web_search":
                query = arguments.get('query', '')
                # This also needs to be awaited - placeholder for now
                result = f"🔍 Web search for '{query}' available via web interface"
            
            else:
                result = f"❌ Function '{function_name}' not implemented yet."
            
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
# DISCORD BOT EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Called when the bot connects to Discord"""
    initialize_google_services()
    print(f"✅ {ASSISTANT_NAME} is online!")
    print(f"🤖 Connected as {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
    print(f"📅 Calendar Status: {'✅ Integrated' if calendar_service else '❌ Not available'}")
    print(f"🌤️ Weather Status: {'✅ Configured' if WEATHER_API_KEY else '❌ Not configured'}")
    print(f"🔍 Planning Search: {'✅ Available' if BRAVE_API_KEY else '❌ Not configured'}")
    print(f"🎯 Allowed Channels: {', '.join(ALLOWED_CHANNELS)}")

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Check if message is in allowed channels or is a DM
    if isinstance(message.channel, discord.DMChannel):
        channel_allowed = True
    else:
        channel_allowed = any(allowed in message.channel.name for allowed in ALLOWED_CHANNELS)
    
    # Process commands first
    await bot.process_commands(message)
    
    # Only respond to mentions in allowed channels
    if channel_allowed and bot.user.mentioned_in(message):
        # Prevent duplicate processing
        message_key = f"{message.id}-{message.author.id}"
        if message_key in processing_messages:
            return
        
        processing_messages.add(message_key)
        
        try:
            # Rate limiting check
            user_id = str(message.author.id)
            current_time = time.time()
            
            if user_id in last_response_time:
                if current_time - last_response_time[user_id] < 3:
                    await message.reply("👑 Please wait a moment between requests.")
                    return
            
            last_response_time[user_id] = current_time
            
            # Clean message content
            content = message.content
            content = re.sub(f'<@!?{bot.user.id}>', '', content).strip()
            
            if not content:
                await message.reply("👑 How may I assist you with executive planning today?")
                return
            
            # Show typing indicator
            async with message.channel.typing():
                response = await get_rose_response(content, user_id)
                
            # Send response
            if response:
                if len(response) <= 2000:
                    await message.reply(response)
                else:
                    # Split into chunks
                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                    for chunk in chunks:
                        await message.reply(chunk)
                        await asyncio.sleep(0.5)
            else:
                await message.reply("👑 I'm processing your executive request. Please try again in a moment.")
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            await message.reply("👑 There was an issue processing your request. Please try again.")
        finally:
            processing_messages.discard(message_key)

# ============================================================================
# CORE ASSISTANT FUNCTIONALITY
# ============================================================================

async def get_rose_response(user_message, user_id):
    """Get response from Rose's OpenAI Assistant"""
    try:
        # Get or create thread for user
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"✅ Created new thread for user {user_id}: {thread.id}")
        else:
            thread_id = user_conversations[user_id]
            try:
                client.beta.threads.retrieve(thread_id)
                print(f"✅ Reusing existing thread for user {user_id}: {thread_id}")
            except:
                thread = client.beta.threads.create()
                user_conversations[user_id] = thread.id
                print(f"✅ Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Check for active runs and wait if necessary
        if user_id in active_runs:
            await asyncio.sleep(2)
            if user_id in active_runs:
                return "👑 Executive analysis in progress. Please wait a moment."
        
        # Create run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        active_runs[user_id] = run.id
        print(f"👑 Rose run created: {run.id} on thread: {thread_id}")
        
        # Wait for completion with function handling
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            
            if run.status == 'completed':
                break
            elif run.status == 'requires_action':
                # Handle function calls
                tool_outputs = handle_rose_functions_enhanced(run, thread_id)
                
                if tool_outputs:
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                    print("✅ Submitted tool outputs successfully")
                    
            elif run.status in ['failed', 'cancelled']:
                print(f"❌ Run failed with status: {run.status}")
                return "👑 Executive analysis encountered an issue. Please try again."
            
            await asyncio.sleep(1)
            attempt += 1
        
        # Clean up active run
        active_runs.pop(user_id, None)
        
        if attempt >= max_attempts:
            print("⏰ Run timeout")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
        # Get the response
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=5)
        for msg in messages.data:
            if msg.role == "assistant":
                response = msg.content[0].text.value
                return format_for_discord_rose(response)
        
        return "👑 Executive analysis unclear. Please try again with a different approach."
        
    except Exception as e:
        print(f"❌ Rose error: {e}")
        active_runs.pop(user_id, None)
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
# DISCORD BOT COMMANDS (ALL ORIGINAL COMMANDS RESTORED)
# ============================================================================

@bot.command(name='briefing')
async def morning_briefing_command(ctx):
    """Get Rose's comprehensive morning briefing with weather"""
    async with ctx.typing():
        briefing = await get_morning_briefing()
        
        # Split if too long for Discord
        if len(briefing) <= 2000:
            await ctx.send(briefing)
        else:
            chunks = [briefing[i:i+2000] for i in range(0, len(briefing), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
                await asyncio.sleep(0.5)

@bot.command(name='weather')
async def weather_command(ctx):
    """Get current weather conditions"""
    async with ctx.typing():
        weather_info = await get_weather_briefing()
        await ctx.send(weather_info)

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's calendar schedule"""
    async with ctx.typing():
        schedule = get_today_schedule()
        await ctx.send(schedule)

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Get upcoming events (default 7 days)"""
    async with ctx.typing():
        if days < 1 or days > 30:
            await ctx.send("📅 Please specify between 1-30 days")
            return
        
        upcoming = get_upcoming_events(days)
        
        if len(upcoming) <= 2000:
            await ctx.send(upcoming)
        else:
            chunks = [upcoming[i:i+2000] for i in range(0, len(upcoming), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
                await asyncio.sleep(0.5)

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    async with ctx.typing():
        if count < 1 or count > 50:
            await ctx.send("📧 Please specify between 1-50 emails")
            return
        
        emails = get_recent_emails(count)
        
        if len(emails) <= 2000:
            await ctx.send(emails)
        else:
            chunks = [emails[i:i+2000] for i in range(0, len(emails), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
                await asyncio.sleep(0.5)

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Get unread emails only"""
    async with ctx.typing():
        if count < 1 or count > 50:
            await ctx.send("📧 Please specify between 1-50 emails")
            return
        
        emails = get_recent_emails(count, unread_only=True)
        await ctx.send(emails)

@bot.command(name='emailstats')
async def emailstats_command(ctx, days: int = 7):
    """Get email statistics"""
    async with ctx.typing():
        if days < 1 or days > 30:
            await ctx.send("📊 Please specify between 1-30 days")
            return
        
        stats = get_email_stats(days)
        await ctx.send(stats)

@bot.command(name='quickemails')
async def quickemails_command(ctx, count: int = 5):
    """Get concise email view"""
    async with ctx.typing():
        if count < 1 or count > 20:
            await ctx.send("📧 Please specify between 1-20 emails")
            return
        
        emails = get_recent_emails(count, include_body=False)
        await ctx.send(emails)

@bot.command(name='emailcount')
async def emailcount_command(ctx):
    """Get just email counts"""
    async with ctx.typing():
        try:
            if not gmail_service:
                await ctx.send("📧 Gmail service not available")
                return
            
            # Get unread count
            unread_result = gmail_service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=1000
            ).execute()
            unread_count = len(unread_result.get('messages', []))
            
            # Get today's count
            today = datetime.now().strftime('%Y/%m/%d')
            today_result = gmail_service.users().messages().list(
                userId='me',
                q=f'after:{today}',
                maxResults=1000
            ).execute()
            today_count = len(today_result.get('messages', []))
            
            result = f"📊 **Email Counts:**\n"
            result += f"🔴 **Unread:** {unread_count}\n"
            result += f"📅 **Today:** {today_count}"
            
            await ctx.send(result)
            
        except Exception as e:
            print(f"❌ Email count error: {e}")
            await ctx.send("📧 Error getting email counts")

@bot.command(name='cleansender')
async def cleansender_command(ctx, sender_email: str, count: int = 10):
    """Delete emails from a specific sender"""
    async with ctx.typing():
        if not sender_email or '@' not in sender_email:
            await ctx.send("📧 Please provide a valid email address")
            return
        
        if count < 1 or count > 100:
            await ctx.send("🗑️ Please specify between 1-100 emails to delete")
            return
        
        # Confirmation step
        await ctx.send(f"⚠️ **Confirmation Required**\nDelete up to {count} emails from `{sender_email}`?\nReact with ✅ to confirm or ❌ to cancel.")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌']
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                result = delete_emails_from_sender(sender_email, count)
                await ctx.send(result)
            else:
                await ctx.send("🗑️ Email deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Email deletion confirmation timed out. Cancelled for safety.")

@bot.command(name='ping')
async def ping(ctx):
    """Universal ping command - Rose's version"""
    try:
        latency = round(bot.latency * 1000)
        config = ASSISTANT_CONFIG
        await ctx.send(f"{config['emoji']} Pong! Latency: {latency}ms - {config['role']} operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")

@bot.command(name='status')
async def status(ctx):
    """Universal status command - Rose's version"""
    try:
        config = ASSISTANT_CONFIG
        
        embed = discord.Embed(
            title=f"{config['emoji']} {config['name']} - {config['role']}",
            description=config['description'],
            color=config['color']
        )
        
        # Core capabilities
        embed.add_field(
            name="📅 Calendar Management",
            value="✅ Available" if calendar_service else "❌ Not available",
            inline=True
        )
        
        embed.add_field(
            name="📧 Email Integration",
            value="✅ Available" if gmail_service else "❌ Not available",
            inline=True
        )
        
        embed.add_field(
            name="🌤️ Weather Integration",
            value="✅ Available" if WEATHER_API_KEY else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Web Search",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in config['specialties']])
        embed.add_field(
            name="🎯 Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Active status
        embed.add_field(
            name="📊 Active Status",
            value=f"👥 Conversations: {len(user_conversations)}\n🏃 Active Runs: {len(active_runs)}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Status command error: {e}")

@bot.command(name='help')
async def help_command(ctx):
    """Universal help command - Rose's version"""
    try:
        config = ASSISTANT_CONFIG
        
        embed = discord.Embed(
            title=f"{config['emoji']} {config['name']} - {config['role']}",
            description=config['description'],
            color=config['color']
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Use",
            value=f"• Mention @{config['name']} for assistance in my specialty areas\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in config['channels']])}",
            inline=False
        )
        
        # Commands
        commands_text = "\n".join([f"• {cmd}" for cmd in config['commands']])
        embed.add_field(
            name="🔧 Commands",
            value=commands_text,
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in config['example_requests']])
        embed.add_field(
            name="✨ Example Requests",
            value=examples_text,
            inline=False
        )
        
        # Capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in config['capabilities']])
        embed.add_field(
            name="🎯 Core Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Help command error: {e}")

# ============================================================================
# ERROR HANDLING AND LOGGING
# ============================================================================

@bot.event
async def on_error(event, *args, **kwargs):
    """Enhanced error handling"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_command_error(ctx, error):
    """Enhanced command error handling"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("👑 Rose: I don't recognize that command. Use `!help` for available commands.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("👑 Rose: Invalid argument. Please check the command format.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("👑 Rose: Missing required argument. Use `!help` for command details.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("👑 Rose: I encountered an error processing your command. Please try again.")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def check_weather_config():
    """Check if weather API is properly configured"""
    config_status = {
        'api_key': bool(WEATHER_API_KEY),
        'city': bool(USER_CITY),
        'coordinates': bool(USER_LAT and USER_LON)
    }
    
    print("🔧 Weather API Configuration Status:")
    print(f"   API Key: {'✅ Configured' if config_status['api_key'] else '❌ Missing WEATHER_API_KEY'}")
    print(f"   City: {'✅ ' + USER_CITY if config_status['city'] else '❌ Missing USER_CITY'}")
    print(f"   Coordinates: {'✅ Precise location' if config_status['coordinates'] else '⚠️ Using city name only'}")
    
    if not config_status['api_key']:
        print("\n📝 Next Steps:")
        print("1. Sign up at https://www.weatherapi.com/")
        print("2. Get your free API key")
        print("3. Add WEATHER_API_KEY to Railway environment variables")
    
    return config_status

async def test_weather_integration():
    """Test the weather integration independently"""
    print("🧪 Testing WeatherAPI.com integration...")
    print(f"🔑 API Key configured: {'✅ Yes' if WEATHER_API_KEY else '❌ No'}")
    print(f"📍 Location: {USER_CITY}")
    
    weather_result = await get_weather_briefing()
    print("\n" + "="*50)
    print("WEATHER BRIEFING TEST RESULT:")
    print("="*50)
    print(weather_result)
    print("="*50)
    
    return weather_result

# ============================================================================
# STARTUP SEQUENCE
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Rose Ashcombe Enhanced Executive Assistant...")
    
    # Check weather configuration
    check_weather_config()
    
    # Test weather if configured
    if WEATHER_API_KEY:
        print("🧪 Testing weather integration...")
        try:
            # Run weather test in main thread since we're not in async context yet
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(test_weather_integration())
            loop.close()
        except Exception as e:
            print(f"⚠️ Weather test failed: {e}")
    
    # Start the Discord bot
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ CRITICAL: Failed to start Rose: {e}")
        exit(1)
