#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (ENHANCED WITH WEATHER INTEGRATION)
Executive Assistant with Enhanced Error Handling, Planning, Calendar & Weather Functions
UPDATED: Added WeatherAPI.com integration to morning briefings
UPDATED: Added Gmail Work Calendar integration
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
import requests
from dotenv import load_dotenv
from openai import OpenAI
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
import pickle
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

# Weather API configuration (NEW)
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
USER_CITY = os.getenv('USER_CITY', 'Toronto')  # Default to Toronto
USER_LAT = os.getenv('USER_LAT')  # Optional coordinates for precision
USER_LON = os.getenv('USER_LON')

# Enhanced calendar integration with better error handling
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')  # Primary BG Calendar
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')  # BG Tasks
BRITT_ICLOUD_CALENDAR_ID = os.getenv('BRITT_ICLOUD_CALENDAR_ID')  # Britt iCloud
GMAIL_WORK_CALENDAR_ID = os.getenv('GMAIL_WORK_CALENDAR_ID')  # Gmail Work Calendar

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

# Discord setup with error handling - DISABLE DEFAULT HELP
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)  # Disable default help
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Active runs tracking for rate limiting
    active_runs = {}
    
    # Memory management variables (fixed location)
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
# WEATHER INTEGRATION FUNCTIONS (NEW)
# ============================================================================

def get_uv_advice(uv_index):
    """Convert UV index number to actionable advice for executive briefing"""
    try:
        uv = float(uv_index)
        if uv <= 2:
            return "Low - Minimal protection needed"
        elif uv <= 5:
            return "Moderate - Seek shade during midday"
        elif uv <= 7:
            return "High - Protection essential (sunscreen, hat)"
        elif uv <= 10:
            return "Very High - Extra precautions required"
        else:
            return "Extreme - Avoid outdoor exposure"
    except (ValueError, TypeError):
        return "Monitor conditions throughout day"

def get_weather_emoji(condition_text):
    """Convert weather condition to appropriate emoji for briefing"""
    condition = condition_text.lower()
    
    if 'sunny' in condition or 'clear' in condition:
        return "☀️"
    elif 'partly cloudy' in condition or 'partly' in condition:
        return "⛅"
    elif 'cloudy' in condition or 'overcast' in condition:
        return "☁️"
    elif 'rain' in condition or 'drizzle' in condition:
        return "🌧️"
    elif 'snow' in condition:
        return "❄️"
    elif 'storm' in condition or 'thunder' in condition:
        return "⛈️"
    elif 'fog' in condition or 'mist' in condition:
        return "🌫️"
    else:
        return "🌤️"  # Default weather emoji

async def get_weather_briefing():
    """
    Get comprehensive weather briefing for Rose's executive summary
    Returns formatted weather section for the morning briefing
    """
    if not WEATHER_API_KEY:
        return "🌤️ **Weather:** Configure WEATHER_API_KEY for weather updates"
    
    try:
        # Determine location parameter (coordinates preferred for accuracy)
        if USER_LAT and USER_LON:
            location = f"{USER_LAT},{USER_LON}"
            location_display = f"{USER_CITY} ({USER_LAT}, {USER_LON})"
        else:
            location = USER_CITY
            location_display = USER_CITY
        
        # WeatherAPI.com current weather endpoint (includes UV index)
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'aqi': 'no'  # We don't need air quality for basic briefing
        }
        
        print(f"🌍 Fetching weather for {location_display}...")
        
        # Make API request with timeout
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract weather data
            current = data['current']
            location_data = data['location']
            
            temp_c = current['temp_c']
            feels_like_c = current['feelslike_c']
            humidity = current['humidity']
            condition = current['condition']['text']
            uv_index = current['uv']
            wind_kph = current['wind_kph']
            wind_dir = current['wind_dir']
            
            # Get weather emoji and UV advice
            weather_emoji = get_weather_emoji(condition)
            uv_advice = get_uv_advice(uv_index)
            
            # Format local time
            local_time = location_data['localtime']
            
            # Create comprehensive weather briefing
            weather_briefing = f"""🌤️ **Weather Update** ({local_time})
📍 **{location_data['name']}, {location_data['country']}:** {temp_c}°C {weather_emoji} {condition}
🌡️ **Feels like:** {feels_like_c}°C | **Humidity:** {humidity}%
🌬️ **Wind:** {wind_kph} km/h {wind_dir}
🔆 **UV Index:** {uv_index} - {uv_advice}"""
            
            print(f"✅ Weather data retrieved successfully: {temp_c}°C, UV: {uv_index}")
            return weather_briefing
            
        elif response.status_code == 401:
            return "🌤️ **Weather:** Invalid API key - check WEATHER_API_KEY configuration"
        elif response.status_code == 400:
            return f"🌤️ **Weather:** Location '{location}' not found - check USER_CITY setting"
        else:
            return f"🌤️ **Weather:** Service temporarily unavailable (Status: {response.status_code})"
            
    except requests.exceptions.Timeout:
        return "🌤️ **Weather:** Request timeout - service may be slow"
    except requests.exceptions.ConnectionError:
        return "🌤️ **Weather:** Connection error - check internet connectivity"
    except KeyError as e:
        print(f"❌ Weather API response missing key: {e}")
        return f"🌤️ **Weather:** Data format error - missing {e}"
    except Exception as e:
        print(f"❌ Weather briefing error: {e}")
        print(f"📋 Weather briefing traceback: {traceback.format_exc()}")
        return f"🌤️ **Weather:** Error retrieving conditions - {str(e)[:50]}"

# ============================================================================
# ENHANCED GOOGLE CALENDAR INTEGRATION
# ============================================================================

# Initialize Google Calendar service
calendar_service = None
gmail_service = None
accessible_calendars = []


def initialize_oauth_gmail_service():
    """
    Initialize Gmail service using OAuth2 token with full permissions
    This is Rose's PRIMARY Gmail authentication method
    """
    global gmail_service
    
    # Get OAuth token from environment
    gmail_token_json = os.getenv('GMAIL_TOKEN_JSON')
    
    if not gmail_token_json:
        print("❌ GMAIL_TOKEN_JSON not found - Gmail features disabled")
        return False
    
    try:
        # Parse token JSON
        token_data = json.loads(gmail_token_json)
        
        # Ensure we have the required scopes
        required_scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.compose'
        ]
        
        current_scopes = token_data.get('scopes', [])
        
        # Check if we have sufficient permissions
        if not all(scope in current_scopes for scope in required_scopes[:2]):
            print("❌ Gmail token lacks required modify permissions")
            print(f"   Current scopes: {current_scopes}")
            print(f"   Required scopes: {required_scopes}")
            print("   Please regenerate OAuth token with gmail.modify scope")
            return False
        
        # Create OAuth credentials
        creds = OAuthCredentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=current_scopes
        )
        
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            print("🔄 Refreshing Gmail token...")
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        
        # Build Gmail service
        gmail_service = build('gmail', 'v1', credentials=creds)
        
        print("✅ OAuth Gmail service initialized with modify permissions")
        return True
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON in GMAIL_TOKEN_JSON")
        return False
    except Exception as e:
        print(f"❌ OAuth Gmail initialization error: {e}")
        return False


def initialize_google_services():
    """Initialize Google Calendar service with enhanced error handling"""
    global calendar_service, accessible_calendars
    
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("❌ No Google service account JSON found - calendar features disabled")
        return False
    
    try:
        # Parse service account JSON
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        
        # Build Calendar service
        calendar_service = build('calendar', 'v3', credentials=credentials)
        
        print(f"✅ Google services initialized")
        print(f"📧 Service Account: {service_account_info.get('client_email', 'Unknown')}")
        
        # Test calendar access and build accessible calendars list
        test_calendar_access()
        
        return True
        
    except json.JSONDecodeError:
        print("❌ Invalid Google service account JSON format")
        return False
    except Exception as e:
        print(f"❌ Google Calendar initialization error: {e}")
        print(f"📋 Google Calendar traceback: {traceback.format_exc()}")
        return False

def test_calendar_access():
    """Test access to configured calendars and populate accessible_calendars"""
    global accessible_calendars
    
    calendars_to_test = [
        ('🐝 BG Personal', GOOGLE_CALENDAR_ID, 'personal'),
        ('📋 BG Tasks', GOOGLE_TASKS_CALENDAR_ID, 'tasks'),
        ('🍎 Britt iCloud', BRITT_ICLOUD_CALENDAR_ID, 'icloud'),
        ('💼 BG Work', GMAIL_WORK_CALENDAR_ID, 'work')
    ]
    
    accessible_calendars = []
    
    for calendar_name, calendar_id, calendar_type in calendars_to_test:
        if not calendar_id:
            print(f"⚠️ {calendar_name}: No calendar ID configured")
            continue
            
        try:
            # Test calendar access
            calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
            accessible_calendars.append((calendar_name, calendar_id, calendar_type))
            print(f"✅ {calendar_name} accessible: {calendar_info.get('summary', 'Unknown')}")
            
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

def get_calendar_events(calendar_id, time_min, time_max, max_results=25):
    """Get events from a specific calendar with enhanced error handling"""
    if not calendar_service:
        return []
    
    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
        
    except HttpError as e:
        print(f"❌ Calendar API error for {calendar_id}: HTTP {e.resp.status}")
        return []
    except Exception as e:
        print(f"❌ Calendar error for {calendar_id}: {e}")
        return []

def format_event(event, calendar_type, timezone_obj):
    """Format a calendar event for display with enhanced timezone handling"""
    try:
        summary = event.get('summary', 'Untitled Event')
        
        # Handle different start time formats
        start = event.get('start', {})
        if 'dateTime' in start:
            # Timed event
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            local_start = start_dt.astimezone(timezone_obj)
            time_str = local_start.strftime('%-I:%M %p')
        elif 'date' in start:
            # All-day event
            time_str = 'All day'
        else:
            time_str = 'Time TBD'
        
        # Add calendar type indicator
        type_emoji = {
            'personal': '🐝',
            'tasks': '📋',
            'icloud': '🍎',
            'work': '💼'
        }.get(calendar_type, '📅')
        
        return f"   {type_emoji} **{time_str}** - {summary}"
        
    except Exception as e:
        print(f"❌ Event formatting error: {e}")
        return f"   📅 **Event formatting error** - {event.get('summary', 'Unknown')}"

# Initialize Google services on startup
print("🔧 Initializing Google Calendar integration...")
google_services_initialized = initialize_google_services()

print("🔧 Initializing Gmail OAuth2 integration...")
oauth_gmail_initialized = initialize_oauth_gmail_service()

print(f"📅 Calendar Service: {'✅ Ready' if google_services_initialized else '❌ Failed'}")
print(f"📧 Gmail Service: {'✅ Ready' if oauth_gmail_initialized else '❌ Failed'}")

# ============================================================================
# ENHANCED CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's complete schedule from all accessible calendars with Toronto timezone handling"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Today's Schedule:** Calendar integration not available\n\n🎯 **Manual Planning:** Check your calendar apps and prioritize high-impact activities"
    
    try:
        # Use Toronto timezone for proper date calculation
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today's date range in Toronto timezone
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto + timedelta(days=1)
        
        # Convert to UTC for API calls
        today_utc = today_toronto.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from all accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, today_utc, tomorrow_utc)
            for event in events:
                formatted = format_event(event, calendar_type, toronto_tz)
                all_events.append((event, formatted, calendar_type, calendar_name))
        
        if not all_events:
            return "📅 **Today's Schedule:** No events scheduled\n\n🎯 **Strategic Focus:** Perfect day for deep work and planning"
        
        # Sort events by start time
        def get_event_time(event_tuple):
            event = event_tuple[0]
            start = event.get('start', {})
            
            try:
                if 'dateTime' in start:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    return start_dt.astimezone(toronto_tz)
                else:
                    return datetime.fromisoformat(start)
            except:
                return datetime.now(toronto_tz)
        
        all_events.sort(key=get_event_time)
        
        # Format response
        formatted_events = [event_tuple[1] for event_tuple in all_events]
        
        # Count by type
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
        
        return header + "\n\n" + "\n".join(formatted_events[:15])  # Limit for Discord
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        print(f"📋 Calendar traceback: {traceback.format_exc()}")
        return "📅 **Today's Schedule:** Error retrieving calendar data\n\n🎯 **Backup Plan:** Check your calendar apps directly"

def get_upcoming_events(days=7):
    """Get upcoming events from all accessible calendars with Toronto timezone handling"""
    if not calendar_service or not accessible_calendars:
        return f"📅 **Upcoming {days} Days:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps for the next {days} days"
    
    try:
        # Use Toronto timezone
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get date range in Toronto timezone then convert to UTC
        start_toronto = datetime.now(toronto_tz)
        end_toronto = start_toronto + timedelta(days=days)
        
        start_utc = start_toronto.astimezone(pytz.UTC)
        end_utc = end_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from all accessible calendars
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, start_utc, end_utc)
            for event in events:
                all_events.append((event, calendar_type, calendar_name))
        
        if not all_events:
            return f"📅 **Upcoming {days} Days:** No events scheduled\n\n🎯 **Strategic Planning:** Great opportunity for proactive scheduling"
        
        # Group events by date
        events_by_date = defaultdict(list)
        
        for event, calendar_type, calendar_name in all_events:
            try:
                start = event.get('start', {})
                if 'dateTime' in start:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    local_start = start_dt.astimezone(toronto_tz)
                    date_key = local_start.strftime('%Y-%m-%d')
                elif 'date' in start:
                    date_key = start['date']
                else:
                    continue
                
                formatted = format_event(event, calendar_type, toronto_tz)
                events_by_date[date_key].append(formatted)
                
            except Exception as e:
                print(f"❌ Event processing error: {e}")
                continue
        
        # Format output
        formatted = []
        for date_key in sorted(events_by_date.keys())[:days]:  # Limit to requested days
            try:
                date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                date_str = date_obj.strftime('%A, %B %d')
                events_for_date = events_by_date[date_key][:5]  # Limit events per day
                
                formatted.append(f"**{date_str}:**")
                formatted.extend(events_for_date)
                formatted.append("")  # Empty line between dates
            except:
                continue
        
        header = f"📅 **Upcoming {days} Days:** {len(all_events)} total events"
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        print(f"📋 Calendar traceback: {traceback.format_exc()}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

async def get_morning_briefing():
    """ENHANCED morning briefing with WEATHER at the top + calendar integration"""
    try:
        # Use Toronto timezone for proper date calculation
        toronto_tz = pytz.timezone('America/Toronto')
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        
        # 1. GET WEATHER FIRST (NEW - at the top!)
        weather_section = await get_weather_briefing()
        
        # 2. Get today's schedule
        if calendar_service and accessible_calendars:
            today_schedule = get_today_schedule()
        else:
            today_schedule = "📅 **Today's Schedule:** Calendar integration not available\n\n📋 **Manual Planning:** Review your calendar apps and prioritize your day"
        
        # 3. Get tomorrow's preview
        if calendar_service and accessible_calendars:
            # Get tomorrow's events using Toronto timezone
            today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_toronto = today_toronto + timedelta(days=1)
            day_after_toronto = tomorrow_toronto + timedelta(days=1)
            
            # Convert to UTC for API calls
            tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
            day_after_utc = day_after_toronto.astimezone(pytz.UTC)
            
            tomorrow_events = []
            
            # Get tomorrow's events from all accessible calendars
            for calendar_name, calendar_id, calendar_type in accessible_calendars:
                events = get_calendar_events(calendar_id, tomorrow_utc, day_after_utc)
                tomorrow_events.extend([(event, calendar_type, calendar_name) for event in events])
            
            # Format tomorrow's preview
            if tomorrow_events:
                tomorrow_formatted = []
                for event, calendar_type, calendar_name in tomorrow_events[:4]:  # Limit to 4 for briefing
                    formatted = format_event(event, calendar_type, toronto_tz)
                    tomorrow_formatted.append(formatted)
                tomorrow_preview = "📅 **Tomorrow Preview:**\n" + "\n".join(tomorrow_formatted)
            else:
                tomorrow_preview = "📅 **Tomorrow Preview:** Clear schedule - great for strategic planning"
        else:
            tomorrow_preview = "📅 **Tomorrow Preview:** Calendar integration not available"
        
        # 4. Combine into executive briefing with WEATHER AT THE TOP
        briefing = f"""👑 **Executive Briefing for {current_time}**

{weather_section}

{today_schedule}

{tomorrow_preview}

💼 **Executive Focus:** Consider weather conditions when planning outdoor meetings and commute timing"""
        
        print("✅ Enhanced morning briefing generated with weather data")
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        print(f"📋 Morning briefing traceback: {traceback.format_exc()}")
        return "🌅 **Morning Briefing:** Error generating briefing - please check calendar apps manually"

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
# GMAIL INTEGRATION FUNCTIONS (ADDED BY SCRIPT)
# ============================================================================



def search_emails(query, max_results=10, include_body=False):
    """Search Gmail messages with query"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        # Search for messages
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Gmail Search:** No emails found for '{query}'"
        
        email_list = []
        
        for msg in messages[:max_results]:
            try:
                # Get message details
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full' if include_body else 'metadata'
                ).execute()
                
                # Extract headers
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Format email entry
                email_entry = f"📧 **{subject}**\nFrom: {sender}\nDate: {date}"
                
                if include_body:
                    # Extract body (simplified)
                    body = extract_email_body(message['payload'])
                    if body:
                        email_entry += f"\n{body[:200]}..."
                
                email_list.append(email_entry)
                
            except Exception as e:
                print(f"❌ Error processing email {msg['id']}: {e}")
                continue
        
        header = f"📧 **Gmail Search Results:** '{query}' ({len(email_list)} found)"
        return header + "\n\n" + "\n\n".join(email_list)
        
    except Exception as e:
        print(f"❌ Gmail search error: {e}")
        return f"📧 **Gmail Search Error:** {str(e)[:100]}"

def get_recent_emails(count=10, unread_only=False, include_body=False):
    """Get recent Gmail messages"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        query = "is:unread" if unread_only else ""
        
        # Get messages
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            status = "unread emails" if unread_only else "emails"
            return f"📧 **Recent Emails:** No {status} found"
        
        email_list = []
        
        for msg in messages[:count]:
            try:
                # Get message details
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full' if include_body else 'metadata'
                ).execute()
                
                # Extract headers
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                
                # Check if unread
                unread_indicator = "🆕 " if 'UNREAD' in message.get('labelIds', []) else ""
                
                email_entry = f"{unread_indicator}📧 **{subject}**\nFrom: {sender}"
                email_list.append(email_entry)
                
            except Exception as e:
                print(f"❌ Error processing email {msg['id']}: {e}")
                continue
        
        email_type = "Unread" if unread_only else "Recent"
        header = f"📧 **{email_type} Emails:** {len(email_list)} found"
        return header + "\n\n" + "\n\n".join(email_list)
        
    except Exception as e:
        print(f"❌ Gmail recent emails error: {e}")
        return f"📧 **Gmail Error:** {str(e)[:100]}"

def get_email_stats(days=7):
    """Get Gmail statistics"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread'
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get recent count
        recent_results = gmail_service.users().messages().list(
            userId='me',
            maxResults=100
        ).execute()
        recent_count = len(recent_results.get('messages', []))
        
        # Get inbox label info
        try:
            labels = gmail_service.users().labels().list(userId='me').execute()
            inbox_label = next((l for l in labels['labels'] if l['id'] == 'INBOX'), None)
            inbox_total = inbox_label.get('messagesTotal', 0) if inbox_label else 0
        except:
            inbox_total = "Unknown"
        
        stats = f"""📊 **Gmail Dashboard Overview:**
📧 **Unread Messages:** {unread_count}
📥 **Inbox Total:** {inbox_total}
🔄 **Recent Activity:** {recent_count} messages

🎯 **Quick Actions:**
• Use `!unread` to see unread emails
• Use `!emails 20` to see recent emails
• Use `@Rose search emails from [sender]`"""
        
        return stats
        
    except Exception as e:
        print(f"❌ Gmail stats error: {e}")
        return f"📊 **Gmail Stats Error:** {str(e)[:100]}"

def delete_emails_from_sender(sender_email, max_delete=50, confirm=False):
    """Delete emails from specific sender"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    if not confirm:
        return f"⚠️ **Email Deletion:** Use `confirm=True` to delete emails from {sender_email}"
    
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
            return f"📧 **No emails found** from {sender_email}"
        
        deleted_count = 0
        
        for msg in messages[:max_delete]:
            try:
                gmail_service.users().messages().delete(
                    userId='me',
                    id=msg['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {msg['id']}: {e}")
                continue
        
        return f"🗑️ **Deleted {deleted_count} emails** from {sender_email}"
        
    except Exception as e:
        print(f"❌ Gmail delete error: {e}")
        return f"🗑️ **Delete Error:** {str(e)[:100]}"

def mark_emails_read(query, max_emails=50):
    """Mark emails as read based on query"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        # Search for emails
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_emails
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **No emails found** matching '{query}'"
        
        marked_count = 0
        
        for msg in messages[:max_emails]:
            try:
                gmail_service.users().messages().modify(
                    userId='me',
                    id=msg['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                marked_count += 1
            except Exception as e:
                print(f"❌ Error marking email {msg['id']} as read: {e}")
                continue
        
        return f"✅ **Marked {marked_count} emails as read** matching '{query}'"
        
    except Exception as e:
        print(f"❌ Gmail mark read error: {e}")
        return f"✅ **Mark Read Error:** {str(e)[:100]}"

def archive_emails(query, max_emails=50):
    """Archive emails based on query"""
    if not gmail_service:
        return "📧 Gmail service not available"
    
    try:
        # Search for emails
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_emails
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **No emails found** matching '{query}'"
        
        archived_count = 0
        
        for msg in messages[:max_emails]:
            try:
                gmail_service.users().messages().modify(
                    userId='me',
                    id=msg['id'],
                    body={'removeLabelIds': ['INBOX']}
                ).execute()
                archived_count += 1
            except Exception as e:
                print(f"❌ Error archiving email {msg['id']}: {e}")
                continue
        
        return f"📦 **Archived {archived_count} emails** matching '{query}'"
        
    except Exception as e:
        print(f"❌ Gmail archive error: {e}")
        return f"📦 **Archive Error:** {str(e)[:100]}"

def extract_email_body(payload):
    """Extract email body from payload (simplified)"""
    try:
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    import base64
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        elif payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            import base64
            return base64.urlsafe_b64decode(data).decode('utf-8')
        return ""
    except:
        return ""

# ============================================================================
# BATCH EMAIL FUNCTIONS
# ============================================================================

def batch_delete_by_subject(subject_text, count=25):
    """Delete multiple emails containing specific text in subject line"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Search for emails with subject text
        query = f"subject:{subject_text}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=min(count, 100)  # Cap at 100 for safety
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 **Batch Cleanup:** No emails found with '{subject_text}' in subject"
        
        deleted_count = 0
        failed_count = 0
        
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me',
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
                failed_count += 1
        
        status = "Success" if failed_count == 0 else f"Partial ({failed_count} failed)"
        return f"📧 **Batch Cleanup:** Deleted emails with '{subject_text}' in subject\n🗑️ **Deleted:** {deleted_count} emails\n🎯 **Status:** {status}"
        
    except Exception as e:
        print(f"❌ Error in batch_delete_by_subject: {e}")
        return f"❌ Error in batch delete: {str(e)}"

def batch_archive_old_emails(days_old, query_filter='', count=50):
    """Archive emails older than specified days"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Calculate the date threshold
        from datetime import datetime, timedelta
        date_threshold = datetime.now() - timedelta(days=days_old)
        date_str = date_threshold.strftime('%Y/%m/%d')
        
        # Build search query
        base_query = f"before:{date_str}"
        if query_filter:
            full_query = f"{base_query} {query_filter}"
        else:
            full_query = base_query
        
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=full_query, 
            maxResults=min(count, 200)  # Cap at 200
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 **Batch Archive:** No emails found older than {days_old} days"
        
        archived_count = 0
        failed_count = 0
        
        for message in messages:
            try:
                # Archive by removing INBOX label
                gmail_service.users().messages().modify(
                    userId='me',
                    id=message['id'],
                    body={'removeLabelIds': ['INBOX']}
                ).execute()
                archived_count += 1
            except Exception as e:
                print(f"❌ Error archiving email {message['id']}: {e}")
                failed_count += 1
        
        status = "Success" if failed_count == 0 else f"Partial ({failed_count} failed)"
        return f"📧 **Batch Archive:** Archived emails older than {days_old} days\n📦 **Archived:** {archived_count} emails\n🎯 **Status:** {status}"
        
    except Exception as e:
        print(f"❌ Error in batch_archive_old_emails: {e}")
        return f"❌ Error in batch archive: {str(e)}"

def cleanup_promotional_emails(action="archive", count=50):
    """Clean up promotional/marketing emails in bulk"""
    if not gmail_service:
        return "❌ Gmail service not available"
    
    try:
        # Search for promotional emails using common patterns
        promotional_queries = [
            "category:promotions",
            "unsubscribe OR newsletter OR marketing OR promotion",
            "from:noreply OR from:no-reply"
        ]
        
        all_messages = []
        for query in promotional_queries:
            try:
                search_result = gmail_service.users().messages().list(
                    userId='me', 
                    q=query, 
                    maxResults=count // len(promotional_queries)  # Distribute across queries
                ).execute()
                all_messages.extend(search_result.get('messages', []))
            except Exception as e:
                print(f"❌ Error searching with query '{query}': {e}")
        
        # Remove duplicates
        unique_messages = {msg['id']: msg for msg in all_messages}.values()
        messages_to_process = list(unique_messages)[:count]
        
        if not messages_to_process:
            return f"📧 **Batch Cleanup:** No promotional emails found"
        
        processed_count = 0
        failed_count = 0
        
        for message in messages_to_process:
            try:
                if action == "delete":
                    gmail_service.users().messages().trash(
                        userId='me',
                        id=message['id']
                    ).execute()
                else:  # archive
                    gmail_service.users().messages().modify(
                        userId='me',
                        id=message['id'],
                        body={'removeLabelIds': ['INBOX']}
                    ).execute()
                processed_count += 1
            except Exception as e:
                print(f"❌ Error processing email {message['id']}: {e}")
                failed_count += 1
        
        action_word = "Deleted" if action == "delete" else "Archived"
        status = "Success" if failed_count == 0 else f"Partial ({failed_count} failed)"
        return f"📧 **Batch Cleanup:** {action_word} promotional emails\n📊 **Processed:** {processed_count} emails\n🎯 **Status:** {status}"
        
    except Exception as e:
        print(f"❌ Error in cleanup_promotional_emails: {e}")
        return f"❌ Error in promotional cleanup: {str(e)}"

def get_recent_emails_large(count=50, query="in:inbox"):
    """Get a larger batch of recent emails for comprehensive review"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Cap at 200 for performance
        count = min(count, 200)
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        total_size = results.get('resultSizeEstimate', 0)
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for i, msg in enumerate(messages):
            try:
                # Get basic info without full details for performance
                msg_data = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = msg_data.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                
                # Format sender
                if '<' in sender:
                    sender = sender.split('<')[0].strip()
                
                # Truncate long subjects
                if len(subject) > 60:
                    subject = subject[:57] + "..."
                
                email_list.append(f"{i+1}. **{subject}** - {sender}")
                
            except Exception as e:
                print(f"❌ Error formatting email {msg['id']}: {e}")
                continue
        
        if email_list:
            return f"📧 **Large Email Review** ({len(email_list)} of {total_size} emails):\n\n" + "\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting large email list: {e}")
        return f"❌ Error retrieving emails: {str(e)}"


# ============================================================================
# ENHANCED FUNCTION HANDLING WITH FIXED OPENAI API CALLS
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with fixed OpenAI API calls"""
    
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
                output = await get_morning_briefing()
                
            
            # GMAIL FUNCTIONS
            elif function_name == "search_emails":
                query = arguments.get('query', '')
                max_results = arguments.get('max_results', 10)
                include_body = arguments.get('include_body', False)
                
                if query:
                    output = search_emails(query, max_results, include_body)
                else:
                    output = "📧 No search query provided"
                    
            elif function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                unread_only = arguments.get('unread_only', False)
                include_body = arguments.get('include_body', False)
                
                output = get_recent_emails(count, unread_only, include_body)
                
            elif function_name == "get_email_stats":
                days = arguments.get('days', 7)
                output = get_email_stats(days)
                
            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                max_delete = arguments.get('max_delete', 50)
                confirm = arguments.get('confirm', False)
                
                if sender_email:
                    output = delete_emails_from_sender(sender_email, max_delete, confirm)
                else:
                    output = "📧 No sender email provided"
                    
            elif function_name == "mark_emails_read":
                query = arguments.get('query', '')
                max_emails = arguments.get('max_emails', 50)
                
                if query:
                    output = mark_emails_read(query, max_emails)
                else:
                    output = "📧 No query provided for marking emails as read"
                    
            elif function_name == "archive_emails":
                query = arguments.get('query', '')
                max_emails = arguments.get('max_emails', 50)
                
                if query:
                    output = archive_emails(query, max_emails)
                else:
                    output = "📧 No query provided for archiving emails"
                    
            # Batch email management functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

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
# MEMORY MANAGEMENT FUNCTIONS (AUTO-ADDED)
# ============================================================================

def get_or_create_user_thread(user_id, channel_id=None):
    """Get existing thread for user or create new one"""
    try:
        # Try user-specific thread first
        if user_id in user_conversations:
            thread_id = user_conversations[user_id]
            
            # Verify thread still exists
            try:
                client.beta.threads.retrieve(thread_id)
                print(f"✅ Reusing existing thread for user {user_id}: {thread_id}")
                return thread_id
            except Exception as e:
                print(f"⚠️ Thread {thread_id} no longer exists, creating new one")
                del user_conversations[user_id]
        
        # Create new thread
        thread = client.beta.threads.create()
        thread_id = thread.id
        
        # Store thread for user
        user_conversations[user_id] = thread_id
        
        # Store metadata
        conversation_metadata[thread_id] = {
            'user_id': user_id,
            'channel_id': channel_id,
            'created_at': time.time(),
            'message_count': 0
        }
        
        print(f"✅ Created new thread for user {user_id}: {thread_id}")
        return thread_id
        
    except Exception as e:
        print(f"❌ Error managing user thread: {e}")
        # Fallback: create new thread
        thread = client.beta.threads.create()
        return thread.id

def clear_user_memory(user_id):
    """Clear conversation memory for specific user"""
    if user_id in user_conversations:
        thread_id = user_conversations[user_id]
        del user_conversations[user_id]
        if thread_id in conversation_metadata:
            del conversation_metadata[thread_id]
        print(f"✅ Cleared memory for user {user_id}")
        return True
    return False

def get_memory_stats():
    """Get memory usage statistics"""
    return {
        'user_conversations': len(user_conversations),
        'channel_conversations': len(channel_conversations),
        'total_threads': len(conversation_metadata),
        'active_runs': len(active_runs)
    }
# ============================================================================
# MAIN CONVERSATION HANDLER WITH FIXED OPENAI API CALLS
# ============================================================================

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with MEMORY ENABLED"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Check if user already has an active run
        if user_id in active_runs:
            return "👑 Rose is currently analyzing your executive strategy. Please wait for completion."
        
        # GET OR CREATE THREAD WITH MEMORY (FIXED!)
        thread_id = get_or_create_user_thread(user_id)
        
        # Add message to EXISTING thread (preserves conversation history)
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        # Update metadata
        if thread_id in conversation_metadata:
            conversation_metadata[thread_id]['message_count'] += 1
            conversation_metadata[thread_id]['last_activity'] = time.time()
        
        # Mark user as having active run
        active_runs[user_id] = thread_id
        
        # Create run with assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        print(f"👑 Rose run created: {run.id} on thread: {thread_id}")
        
        # Wait for completion with timeout
        max_wait = 30  # seconds
        wait_time = 0
        
        while wait_time < max_wait:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run.status == 'completed':
                break
            elif run.status == 'requires_action':
                await handle_rose_functions_enhanced(run, thread_id)
                await asyncio.sleep(1)
            elif run.status in ['failed', 'cancelled', 'expired']:
                active_runs.pop(user_id, None)
                return f"👑 Rose: Analysis failed with status: {run.status}"
            
            await asyncio.sleep(1)
            wait_time += 1
        
        # Remove user from active runs
        active_runs.pop(user_id, None)
        
        if wait_time >= max_wait:
            return "👑 Rose: Analysis is taking longer than expected. Please try again."
        
        # Get the response (most recent assistant message)
        messages = client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=5  # Get recent messages for context
        )
        
        if messages.data:
            # Find the most recent assistant response
            for message in messages.data:
                if message.role == "assistant":
                    response = message.content[0].text.value
                    print(f"✅ Rose response retrieved from thread {thread_id}")
                    return response
            
            return "👑 Rose: I generated a response but couldn't retrieve it. Please try again."
        else:
            return "👑 Rose: I apologize, but I couldn't generate a response. Please try again."
            
    except Exception as e:
        active_runs.pop(user_id, None)
        print(f"❌ Rose response error: {e}")
        print(f"📋 Rose response traceback: {traceback.format_exc()}")
        return f"👑 Rose: I encountered an error. Please try again. ({str(e)[:50]})"


@bot.event
async def on_ready():
    """Enhanced startup message with weather status"""
    print(f"✅ {ASSISTANT_NAME} is online!")
    print(f"🤖 Connected as {bot.user} (ID: {bot.user.id})")
    print(f"📅 Calendar Status: {'✅ Integrated' if google_services_initialized else '❌ Not Available'}")
    print(f"🌤️ Weather Status: {'✅ Configured' if WEATHER_API_KEY else '❌ Not Configured'}")
    print(f"🔍 Planning Search: {'✅ Available' if BRAVE_API_KEY else '❌ Not Available'}")
    print(f"🎯 Allowed Channels: {', '.join(ALLOWED_CHANNELS)}")
    
    # Set bot activity status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="executive schedules & weather"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_message(message):
    """Enhanced message handler with weather-aware responses"""
    # Ignore bot messages
    if message.author == bot.user:
        return
    
    # Check if message is in allowed channels
    if message.channel.name not in ALLOWED_CHANNELS:
        return
    
    # Check if bot is mentioned or message starts with Rose
    is_mentioned = bot.user in message.mentions
    is_rose_message = message.content.lower().startswith('rose') or message.content.lower().startswith('@rose')
    
    if is_mentioned or is_rose_message:
        async with message.channel.typing():
            response = await get_rose_response(message.content, message.author.id)
            
            # Split long responses if needed
            if len(response) <= 2000:
                await message.channel.send(response)
            else:
                # Split into chunks
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
                    await asyncio.sleep(0.5)  # Brief pause between chunks
    
    # Process other commands
    await bot.process_commands(message)

# ============================================================================
# ENHANCED DISCORD COMMANDS
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
    """Universal status command - Rose's enhanced version"""
    try:
        config = ASSISTANT_CONFIG
        
        embed = discord.Embed(
            title=f"{config['emoji']} {config['name']} - {config['role']}",
            description=config['description'],
            color=config['color']
        )
        
        # Connection status
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        # Calendar Access
        embed.add_field(
            name="📅 Calendar Access", 
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        # Gmail Access (if configured)
        embed.add_field(
            name="📧 Gmail Access",
            value="🔧 Email functions pending" if not globals().get('gmail_service') else "✅ Connected",
            inline=True
        )
        
        # Weather capability
        embed.add_field(
            name="🌤️ Weather API",
            value="✅ Available" if WEATHER_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Search capability
        embed.add_field(
            name="🔍 Web Search",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Accessible calendars detail
        calendars_detail = f"{len(accessible_calendars)} calendars"
        if accessible_calendars:
            calendar_types = [cal[0] for cal in accessible_calendars]
            calendars_detail = "\n".join(calendar_types[:5])  # Limit to 5 for space
        
        embed.add_field(
            name="📊 Accessible Calendars",
            value=calendars_detail,
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
            value=f"👥 Active Runs: {len(active_runs)}\n📍 Location: {USER_CITY}\n🎯 Channels: {len(ALLOWED_CHANNELS)}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("❌ Error generating status report")

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
            value=f"• Mention @{config['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in config['channels']])}",
            inline=False
        )
        
        # Commands - Split into sections for better organization
        calendar_commands = [
            "!briefing - Complete morning briefing",
            "!schedule - Today's calendar", 
            "!upcoming [days] - Upcoming events",
            "!weather - Current weather & UV"
        ]
        
        email_commands = [
            "!emails [count] - Recent emails",
            "!unread [count] - Unread only",
            "!emailstats - Email dashboard",
            "!cleansender <email> - Delete from sender"
        ]
        
        system_commands = [
            "!status - System status",
            "!ping - Test response",
            "!help - This message"
        ]
        
        embed.add_field(
            name="📅 Calendar & Briefing",
            value="\n".join([f"• {cmd}" for cmd in calendar_commands]),
            inline=False
        )
        
        embed.add_field(
            name="📧 Email Management",
            value="\n".join([f"• {cmd}" for cmd in email_commands]) + "\n*(Email functions coming soon)*",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ System",
            value="\n".join([f"• {cmd}" for cmd in system_commands]),
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in config['example_requests'][:4]])  # Limit to 4
        embed.add_field(
            name="✨ Example Requests",
            value=examples_text,
            inline=False
        )
        
        # Capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in config['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("❌ Error generating help information")



# ============================================================================
# GMAIL DISCORD COMMANDS (ADDED BY SCRIPT)
# ============================================================================

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 50))
            emails = get_recent_emails(count)
            
            if len(emails) <= 2000:
                await ctx.send(emails)
            else:
                chunks = [emails[i:i+2000] for i in range(0, len(emails), 2000)]
                for chunk in chunks:
                    await ctx.send(chunk)
                    await asyncio.sleep(0.5)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Error retrieving emails. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Get unread emails only"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 50))
            emails = get_recent_emails(count, unread_only=True)
            
            if len(emails) <= 2000:
                await ctx.send(emails)
            else:
                chunks = [emails[i:i+2000] for i in range(0, len(emails), 2000)]
                for chunk in chunks:
                    await ctx.send(chunk)
                    await asyncio.sleep(0.5)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Error retrieving unread emails. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Get Gmail statistics dashboard"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📊 Error retrieving email statistics. Please try again.")

@bot.command(name='quickemails')
async def quickemails_command(ctx, count: int = 5):
    """Get concise email view"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count, include_body=False)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Error retrieving quick emails. Please try again.")

@bot.command(name='emailcount')
async def emailcount_command(ctx):
    """Get just email counts"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            # Extract just the count lines
            lines = stats.split('\n')
            count_lines = [line for line in lines if ('Unread' in line or 'Inbox' in line or 'Recent' in line)]
            await ctx.send('\n'.join(count_lines))
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📊 Error retrieving email counts. Please try again.")

@bot.command(name='cleansender')
async def cleansender_command(ctx, sender_email: str, count: int = 50):
    """Delete emails from a specific sender (requires confirmation)"""
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
                    result = delete_emails_from_sender(sender_email, count, confirm=True)
                    await ctx.send(result)
                else:
                    await ctx.send("❌ Email deletion cancelled.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Email deletion confirmation timed out. Cancelled for safety.")
                
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send("🗑️ Error with email deletion. Please try again.")


# ============================================================================
# ERROR HANDLING AND LOGGING
# ============================================================================

@bot.event
async def on_error(event, *args, **kwargs):
    """Enhanced error handling with weather-specific logging"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_command_error(ctx, error):
    """Enhanced command error handling"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("👑 Rose: I don't recognize that command. Use `!commands` for available commands.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("👑 Rose: Invalid argument. Please check the command format.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("👑 Rose: Missing required argument. Use `!commands` for command details.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("👑 Rose: I encountered an error processing your command. Please try again.")

# ============================================================================
# ENHANCED TESTING FUNCTIONS
# ============================================================================

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


# ============================================================================
# MEMORY MANAGEMENT COMMANDS (AUTO-ADDED)
# ============================================================================

@bot.command(name='memory-stats')
async def memory_stats_command(ctx):
    """Show memory usage statistics"""
    stats = get_memory_stats()
    
    embed = discord.Embed(
        title="👑 Rose Memory Statistics",
        color=0xE91E63
    )
    
    embed.add_field(name="User Conversations", value=stats['user_conversations'], inline=True)
    embed.add_field(name="Total Threads", value=stats['total_threads'], inline=True)
    embed.add_field(name="Active Runs", value=stats['active_runs'], inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='clear-my-memory')
async def clear_user_memory_command(ctx):
    """Clear conversation memory for the requesting user"""
    user_id = str(ctx.author.id)
    if clear_user_memory(user_id):
        await ctx.send("👑 Rose: Your conversation memory has been cleared. We'll start fresh!")
    else:
        await ctx.send("👑 Rose: You don't have any stored conversation memory to clear.")
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

# === Restored Email Functions from main-email_2.py ===

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


@bot.command(name='briefing')
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def format_email_concise(email_data):
    """Format email data concisely"""
    try:
        subject = email_data.get('subject', 'No Subject')[:50]
        sender = email_data.get('sender', 'Unknown Sender')
        snippet = email_data.get('snippet', '')[:80]
        
        # Extract just the name from sender if it's in "Name <email>" format
        if '<' in sender and '>' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        elif '@' in sender:
            sender = sender.split('@')[0]
        
        # Shorten long subjects
        if len(subject) >= 50:
            subject = subject[:47] + "..."
        
        return f"• **{subject}** - {sender}\n  {snippet}..."
        
    except Exception as e:
        print(f"❌ Error formatting email: {e}")
        return "• Email formatting error"

def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails with Gmail query support"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for msg in messages[:count]:
            email_data = get_email_details(msg['id'])
            if email_data:
                email_list.append(format_email_concise(email_data))
        
        if email_list:
            return f"📧 {len(email_list)} emails found:\n\n" + "\n\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting recent emails: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


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
            
            print(f"   • {summary} (ID: {cal_id[:20]}...)")
            calendars.append((summary, cal_id, access_role))
        
        return calendars
        
    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return []

def setup_gmail_oauth():
    """Setup Gmail with OAuth authentication"""
    try:
        creds = None
        
        # First try to load token from environment variable (for Railway)
        if GMAIL_TOKEN_JSON:
            try:
                token_info = json.loads(GMAIL_TOKEN_JSON)
                creds = OAuthCredentials.from_authorized_user_info(token_info, GMAIL_SCOPES)
                print("📧 Found Gmail token from environment variable")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in GMAIL_TOKEN_JSON: {e}")
                creds = None
        
        # Fallback to token file (for local development)
        elif os.path.exists(GMAIL_TOKEN_FILE):
            creds = OAuthCredentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
            print("📧 Found existing Gmail token file")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing Gmail credentials...")
                creds.refresh(Request())
                
                # Save refreshed token back to file (local) or print for env var (Railway)
                if os.path.exists(GMAIL_TOKEN_FILE):
                    with open(GMAIL_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                        print("💾 Gmail token refreshed and saved to file")
                else:
                    print("💡 Token refreshed - update GMAIL_TOKEN_JSON environment variable with:")
                    print(creds.to_json())
            else:
                print("🔑 Getting new Gmail credentials...")
                
                if not GMAIL_OAUTH_JSON:
                    print("❌ GMAIL_OAUTH_JSON not found in environment variables")
                    print("💡 Set GMAIL_OAUTH_JSON with your OAuth client JSON content")
                    return None
                
                # Parse OAuth JSON from environment variable
                try:
                    oauth_info = json.loads(GMAIL_OAUTH_JSON)
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in GMAIL_OAUTH_JSON: {e}")
                    return None
                
                # Create flow from OAuth info
                flow = InstalledAppFlow.from_client_config(oauth_info, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ Gmail authentication completed")
                
                # Save credentials for next run
                with open(GMAIL_TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                    print("💾 Gmail token saved to file")
                    print("💡 For Railway deployment, add this as GMAIL_TOKEN_JSON environment variable:")
                    print(creds.to_json())
        
        # Build Gmail service
        gmail_service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail OAuth service initialized")
        
        # Test Gmail access
        try:
            profile = gmail_service.users().getProfile(userId='me').execute()
            print(f"📧 Gmail account: {profile.get('emailAddress', 'Unknown')}")
            return gmail_service
        except Exception as test_error:
            print(f"❌ Gmail test failed: {test_error}")
            return None
        
    except Exception as e:
        print(f"❌ Gmail OAuth setup error: {e}")
        return None

# Initialize Google Services
try:
    # Initialize Calendar with Service Account
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        calendar_credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar'
            ]
        )
        
        calendar_service = build('calendar', 'v3', credentials=calendar_credentials)
        print("✅ Google Calendar service initialized with service account")
        
        # Get service account email for sharing instructions
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account Email: {service_account_email}")
        
    else:
        print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not found - calendar features disabled")
        calendar_service = None
    
    # Initialize Gmail with OAuth2
    gmail_service = setup_gmail_oauth()
    
    if calendar_service:
        # List all accessible calendars first
        all_calendars = get_all_accessible_calendars()
        
        # Test specific calendars
        calendars_to_test = [
            ("BG Calendar", GOOGLE_CALENDAR_ID),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID),
            ("Britt iCloud", BRITT_ICLOUD_CALENDAR_ID)
        ]
        
        for name, calendar_id in calendars_to_test:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id))
        
        # If no calendars work, try primary as fallback
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _ in accessible_calendars:
            print(f"   ✅ {name}")
        
        if not accessible_calendars:
            print("❌ No accessible calendars found")
    
except Exception as e:
    print(f"❌ Google services setup error: {e}")
    calendar_service = None
    gmail_service = None

# ============================================================================
# EMAIL FUNCTIONS
# ============================================================================

def get_email_details(message_id):
    """Get detailed email information"""
    try:
        message = gmail_service.users().messages().get(
            userId='me', 
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Get email body snippet
        snippet = message.get('snippet', '')
        
        return {
            'id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': snippet
        }
    except Exception as e:
        print(f"❌ Error getting email details: {e}")
        return None

def format_email_concise(email_data):
    """Format email data concisely"""
    try:
        subject = email_data.get('subject', 'No Subject')[:50]
        sender = email_data.get('sender', 'Unknown Sender')
        snippet = email_data.get('snippet', '')[:80]
        
        # Extract just the name from sender if it's in "Name <email>" format
        if '<' in sender and '>' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        elif '@' in sender:
            sender = sender.split('@')[0]
        
        # Shorten long subjects
        if len(subject) >= 50:
            subject = subject[:47] + "..."
        
        return f"• **{subject}** - {sender}\n  {snippet}..."
        
    except Exception as e:
        print(f"❌ Error formatting email: {e}")
        return "• Email formatting error"

def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails with Gmail query support"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for msg in messages[:count]:
            email_data = get_email_details(msg['id'])
            if email_data:
                email_list.append(format_email_concise(email_data))
        
        if email_list:
            return f"📧 {len(email_list)} emails found:\n\n" + "\n\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting recent emails: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def get_email_details(message_id):
    """Get detailed email information"""
    try:
        message = gmail_service.users().messages().get(
            userId='me', 
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Get email body snippet
        snippet = message.get('snippet', '')
        
        return {
            'id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': snippet
        }
    except Exception as e:
        print(f"❌ Error getting email details: {e}")
        return None

def format_email_concise(email_data):
    """Format email data concisely"""
    try:
        subject = email_data.get('subject', 'No Subject')[:50]
        sender = email_data.get('sender', 'Unknown Sender')
        snippet = email_data.get('snippet', '')[:80]
        
        # Extract just the name from sender if it's in "Name <email>" format
        if '<' in sender and '>' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        elif '@' in sender:
            sender = sender.split('@')[0]
        
        # Shorten long subjects
        if len(subject) >= 50:
            subject = subject[:47] + "..."
        
        return f"• **{subject}** - {sender}\n  {snippet}..."
        
    except Exception as e:
        print(f"❌ Error formatting email: {e}")
        return "• Email formatting error"

def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails with Gmail query support"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for msg in messages[:count]:
            email_data = get_email_details(msg['id'])
            if email_data:
                email_list.append(format_email_concise(email_data))
        
        if email_list:
            return f"📧 {len(email_list)} emails found:\n\n" + "\n\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting recent emails: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def planning_search(query, focus_area="general"):
    """Research planning topics using Brave Search"""
    if not BRAVE_API_KEY:
        return "🔍 Research capability not available (missing API key)"
    
    try:
        # Enhance query for planning content
        planning_query = f"{query} {focus_area} productivity executive planning time management 2025"
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        params = {
            "q": planning_query,
            "count": 5,
            "search_lang": "en",
            "country": "ca"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = data.get('web', {}).get('results', [])
                    if not results:
                        return f"🔍 No research results found for: {query}"
                    
                    formatted_results = []
                    for i, result in enumerate(results[:3]):
                        title = result.get('title', 'No title')
                        description = result.get('description', 'No description')
                        url_link = result.get('url', '')
                        
                        # Extract domain for credibility
                        domain = url_link.split('/')[2] if len(url_link.split('/')) > 2 else 'Unknown'
                        
                        formatted_results.append(f"**{i+1}. {title}** ({domain})\n{description[:150]}...\n{url_link}")
                    
                    return f"🔍 **Planning Research: '{query}'**\n\n" + "\n\n".join(formatted_results)
                else:
                    return f"🔍 Research error: HTTP {response.status}"
                    
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Research error: {str(e)}"

# ============================================================================
# GOOGLE SERVICES INITIALIZATION
# ============================================================================

def test_calendar_access(calendar_id, calendar_name):
    """Test access to a specific calendar with detailed error reporting"""
    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=datetime.utcnow().isoformat() + 'Z',
            maxResults=1,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        print(f"✅ {calendar_name}: Accessible")
        return True
        
    except HttpError as e:
        error_code = e.resp.status
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        
        print(f"❌ {calendar_name} HTTP Error {error_code}: {error_details}")
        
        if error_code == 404:
            print(f"💡 {calendar_name}: Calendar not found - check ID format")
        elif error_code == 403:
            print(f"💡 {calendar_name}: Permission denied")
        elif error_code == 400:
            print(f"💡 {calendar_name}: Bad request - malformed calendar ID")
        
        return False
        
    except Exception as e:
        print(f"❌ {calendar_name} unexpected error: {e}")
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
            
            print(f"   • {summary} (ID: {cal_id[:20]}...)")
            calendars.append((summary, cal_id, access_role))
        
        return calendars
        
    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return []

def setup_gmail_oauth():
    """Setup Gmail with OAuth authentication"""
    try:
        creds = None
        
        # First try to load token from environment variable (for Railway)
        if GMAIL_TOKEN_JSON:
            try:
                token_info = json.loads(GMAIL_TOKEN_JSON)
                creds = OAuthCredentials.from_authorized_user_info(token_info, GMAIL_SCOPES)
                print("📧 Found Gmail token from environment variable")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in GMAIL_TOKEN_JSON: {e}")
                creds = None
        
        # Fallback to token file (for local development)
        elif os.path.exists(GMAIL_TOKEN_FILE):
            creds = OAuthCredentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
            print("📧 Found existing Gmail token file")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing Gmail credentials...")
                creds.refresh(Request())
                
                # Save refreshed token back to file (local) or print for env var (Railway)
                if os.path.exists(GMAIL_TOKEN_FILE):
                    with open(GMAIL_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                        print("💾 Gmail token refreshed and saved to file")
                else:
                    print("💡 Token refreshed - update GMAIL_TOKEN_JSON environment variable with:")
                    print(creds.to_json())
            else:
                print("🔑 Getting new Gmail credentials...")
                
                if not GMAIL_OAUTH_JSON:
                    print("❌ GMAIL_OAUTH_JSON not found in environment variables")
                    print("💡 Set GMAIL_OAUTH_JSON with your OAuth client JSON content")
                    return None
                
                # Parse OAuth JSON from environment variable
                try:
                    oauth_info = json.loads(GMAIL_OAUTH_JSON)
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in GMAIL_OAUTH_JSON: {e}")
                    return None
                
                # Create flow from OAuth info
                flow = InstalledAppFlow.from_client_config(oauth_info, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ Gmail authentication completed")
                
                # Save credentials for next run
                with open(GMAIL_TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                    print("💾 Gmail token saved to file")
                    print("💡 For Railway deployment, add this as GMAIL_TOKEN_JSON environment variable:")
                    print(creds.to_json())
        
        # Build Gmail service
        gmail_service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail OAuth service initialized")
        
        # Test Gmail access
        try:
            profile = gmail_service.users().getProfile(userId='me').execute()
            print(f"📧 Gmail account: {profile.get('emailAddress', 'Unknown')}")
            return gmail_service
        except Exception as test_error:
            print(f"❌ Gmail test failed: {test_error}")
            return None
        
    except Exception as e:
        print(f"❌ Gmail OAuth setup error: {e}")
        return None

# Initialize Google Services
try:
    # Initialize Calendar with Service Account
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        calendar_credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar'
            ]
        )
        
        calendar_service = build('calendar', 'v3', credentials=calendar_credentials)
        print("✅ Google Calendar service initialized with service account")
        
        # Get service account email for sharing instructions
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account Email: {service_account_email}")
        
    else:
        print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not found - calendar features disabled")
        calendar_service = None
    
    # Initialize Gmail with OAuth2
    gmail_service = setup_gmail_oauth()
    
    if calendar_service:
        # List all accessible calendars first
        all_calendars = get_all_accessible_calendars()
        
        # Test specific calendars
        calendars_to_test = [
            ("BG Calendar", GOOGLE_CALENDAR_ID),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID),
            ("Britt iCloud", BRITT_ICLOUD_CALENDAR_ID)
        ]
        
        for name, calendar_id in calendars_to_test:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id))
        
        # If no calendars work, try primary as fallback
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _ in accessible_calendars:
            print(f"   ✅ {name}")
        
        if not accessible_calendars:
            print("❌ No accessible calendars found")
    
except Exception as e:
    print(f"❌ Google services setup error: {e}")
    calendar_service = None
    gmail_service = None

# ============================================================================
# EMAIL FUNCTIONS
# ============================================================================

def get_email_details(message_id):
    """Get detailed email information"""
    try:
        message = gmail_service.users().messages().get(
            userId='me', 
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Get email body snippet
        snippet = message.get('snippet', '')
        
        return {
            'id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': snippet
        }
    except Exception as e:
        print(f"❌ Error getting email details: {e}")
        return None

def format_email_concise(email_data):
    """Format email data concisely"""
    try:
        subject = email_data.get('subject', 'No Subject')[:50]
        sender = email_data.get('sender', 'Unknown Sender')
        snippet = email_data.get('snippet', '')[:80]
        
        # Extract just the name from sender if it's in "Name <email>" format
        if '<' in sender and '>' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        elif '@' in sender:
            sender = sender.split('@')[0]
        
        # Shorten long subjects
        if len(subject) >= 50:
            subject = subject[:47] + "..."
        
        return f"• **{subject}** - {sender}\n  {snippet}..."
        
    except Exception as e:
        print(f"❌ Error formatting email: {e}")
        return "• Email formatting error"

def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails with Gmail query support"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for msg in messages[:count]:
            email_data = get_email_details(msg['id'])
            if email_data:
                email_list.append(format_email_concise(email_data))
        
        if email_list:
            return f"📧 {len(email_list)} emails found:\n\n" + "\n\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting recent emails: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def send_long_message(original_message, response):
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def setup_gmail_oauth():
    """Setup Gmail with OAuth authentication"""
    try:
        creds = None
        
        # First try to load token from environment variable (for Railway)
        if GMAIL_TOKEN_JSON:
            try:
                token_info = json.loads(GMAIL_TOKEN_JSON)
                creds = OAuthCredentials.from_authorized_user_info(token_info, GMAIL_SCOPES)
                print("📧 Found Gmail token from environment variable")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in GMAIL_TOKEN_JSON: {e}")
                creds = None
        
        # Fallback to token file (for local development)
        elif os.path.exists(GMAIL_TOKEN_FILE):
            creds = OAuthCredentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
            print("📧 Found existing Gmail token file")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing Gmail credentials...")
                creds.refresh(Request())
                
                # Save refreshed token back to file (local) or print for env var (Railway)
                if os.path.exists(GMAIL_TOKEN_FILE):
                    with open(GMAIL_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                        print("💾 Gmail token refreshed and saved to file")
                else:
                    print("💡 Token refreshed - update GMAIL_TOKEN_JSON environment variable with:")
                    print(creds.to_json())
            else:
                print("🔑 Getting new Gmail credentials...")
                
                if not GMAIL_OAUTH_JSON:
                    print("❌ GMAIL_OAUTH_JSON not found in environment variables")
                    print("💡 Set GMAIL_OAUTH_JSON with your OAuth client JSON content")
                    return None
                
                # Parse OAuth JSON from environment variable
                try:
                    oauth_info = json.loads(GMAIL_OAUTH_JSON)
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in GMAIL_OAUTH_JSON: {e}")
                    return None
                
                # Create flow from OAuth info
                flow = InstalledAppFlow.from_client_config(oauth_info, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ Gmail authentication completed")
                
                # Save credentials for next run
                with open(GMAIL_TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                    print("💾 Gmail token saved to file")
                    print("💡 For Railway deployment, add this as GMAIL_TOKEN_JSON environment variable:")
                    print(creds.to_json())
        
        # Build Gmail service
        gmail_service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail OAuth service initialized")
        
        # Test Gmail access
        try:
            profile = gmail_service.users().getProfile(userId='me').execute()
            print(f"📧 Gmail account: {profile.get('emailAddress', 'Unknown')}")
            return gmail_service
        except Exception as test_error:
            print(f"❌ Gmail test failed: {test_error}")
            return None
        
    except Exception as e:
        print(f"❌ Gmail OAuth setup error: {e}")
        return None

# Initialize Google Services
try:
    # Initialize Calendar with Service Account
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        calendar_credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar'
            ]
        )
        
        calendar_service = build('calendar', 'v3', credentials=calendar_credentials)
        print("✅ Google Calendar service initialized with service account")
        
        # Get service account email for sharing instructions
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account Email: {service_account_email}")
        
    else:
        print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not found - calendar features disabled")
        calendar_service = None
    
    # Initialize Gmail with OAuth2
    gmail_service = setup_gmail_oauth()
    
    if calendar_service:
        # List all accessible calendars first
        all_calendars = get_all_accessible_calendars()
        
        # Test specific calendars
        calendars_to_test = [
            ("BG Calendar", GOOGLE_CALENDAR_ID),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID),
            ("Britt iCloud", BRITT_ICLOUD_CALENDAR_ID)
        ]
        
        for name, calendar_id in calendars_to_test:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id))
        
        # If no calendars work, try primary as fallback
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _ in accessible_calendars:
            print(f"   ✅ {name}")
        
        if not accessible_calendars:
            print("❌ No accessible calendars found")
    
except Exception as e:
    print(f"❌ Google services setup error: {e}")
    calendar_service = None
    gmail_service = None

# ============================================================================
# EMAIL FUNCTIONS
# ============================================================================

def get_email_details(message_id):
    """Get detailed email information"""
    try:
        message = gmail_service.users().messages().get(
            userId='me', 
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Get email body snippet
        snippet = message.get('snippet', '')
        
        return {
            'id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': snippet
        }
    except Exception as e:
        print(f"❌ Error getting email details: {e}")
        return None

def format_email_concise(email_data):
    """Format email data concisely"""
    try:
        subject = email_data.get('subject', 'No Subject')[:50]
        sender = email_data.get('sender', 'Unknown Sender')
        snippet = email_data.get('snippet', '')[:80]
        
        # Extract just the name from sender if it's in "Name <email>" format
        if '<' in sender and '>' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        elif '@' in sender:
            sender = sender.split('@')[0]
        
        # Shorten long subjects
        if len(subject) >= 50:
            subject = subject[:47] + "..."
        
        return f"• **{subject}** - {sender}\n  {snippet}..."
        
    except Exception as e:
        print(f"❌ Error formatting email: {e}")
        return "• Email formatting error"

def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails with Gmail query support"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for msg in messages[:count]:
            email_data = get_email_details(msg['id'])
            if email_data:
                email_list.append(format_email_concise(email_data))
        
        if email_list:
            return f"📧 {len(email_list)} emails found:\n\n" + "\n\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting recent emails: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

def get_unread_emails(count=10):
    """Get unread emails only"""
    return get_recent_emails(count, "is:unread")

def search_emails(query, count=10):
    """Search emails using Gmail search syntax"""
    return get_recent_emails(count, query)

def send_email(to_email, subject, body):
    """Send email through Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"📧 Email sent to {to_email}\n📝 Subject: {subject}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread count
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        # Get today's emails
        today_results = gmail_service.users().messages().list(
            userId='me',
            q='newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        # Get important emails
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"📧 **Email Dashboard**\n🔴 Unread: {unread_count}\n📅 Today: {today_count}\n⭐ Important: {important_count}"
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

def delete_email(email_id):
    """Move email to trash"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().trash(
            userId='me',
            id=email_id
        ).execute()
        
        return f"📧 Email deleted"
        
    except Exception as e:
        print(f"❌ Delete email error: {e}")
        return f"❌ Failed to delete email: {str(e)}"

def archive_email(email_id):
    """Archive email (remove from inbox)"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        return f"📧 Email archived"
        
    except Exception as e:
        print(f"❌ Archive email error: {e}")
        return f"❌ Failed to archive email: {str(e)}"

def delete_emails_from_sender(sender_email, count=10):
    """Delete multiple emails from a specific sender"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=count
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 No emails found from {sender_email}"
        
        deleted_count = 0
        for message in messages:
            try:
                gmail_service.users().messages().trash(
                    userId='me', 
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
        
        return f"📧 Deleted {deleted_count} emails from {sender_email}"
        
    except Exception as e:
        print(f"❌ Error in delete_emails_from_sender: {e}")
        return f"❌ Error deleting emails from {sender_email}: {str(e)}"

def mark_email_as_read(email_id):
    """Mark an email as read"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return f"📧 Marked email as read"
        
    except Exception as e:
        print(f"❌ Error marking email as read: {e}")
        return f"❌ Error marking email as read: {str(e)}"

def mark_email_as_important(email_id):
    """Mark an email as important"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['IMPORTANT']}
        ).execute()
        
        return f"📧 Marked email as important"
        
    except Exception as e:
        print(f"❌ Error marking email as important: {e}")
        return f"❌ Error marking email as important: {str(e)}"

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

def get_today_schedule():
    """Get today's calendar events"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
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
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_name'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error getting events from {calendar_name}: {e}")
        
        if not all_events:
            return "📅 No events scheduled for today"
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        formatted_events = []
        for event in all_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            calendar_name = event.get('calendar_name', 'Unknown')
            
            if 'T' in start:
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%I:%M %p')
            else:
                time_str = "All day"
            
            formatted_events.append(f"• {time_str} - {summary} ({calendar_name})")
        
        return f"📅 **Today's Schedule ({now.strftime('%A, %B %d')}):**\n\n" + "\n".join(formatted_events)
        
    except Exception as e:
        print(f"❌ Error getting today's schedule: {e}")
        return f"❌ Error retrieving today's schedule: {str(e)}"

def get_upcoming_events(days=7):
    """Get upcoming events for specified number of days"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_time = now + timedelta(days=days)
        
        all_events = []
        
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
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

# ============================================================================
# FUNCTION EXECUTION HANDLER
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        try:
            # Email functions
            if function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails(count, query)

            elif function_name == "get_unread_emails":
                count = arguments.get('count', 10)
                output = get_unread_emails(count)

            elif function_name == "search_emails":
                query = arguments.get('query', '')
                count = arguments.get('count', 10)
                if query:
                    output = search_emails(query, count)
                else:
                    output = "❌ Missing required parameter: query"

            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"

            elif function_name == "get_email_stats":
                output = get_email_stats()

            elif function_name == "delete_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = delete_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "archive_email":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = archive_email(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                count = arguments.get('count', 10)
                if sender_email:
                    output = delete_emails_from_sender(sender_email, count)
                else:
                    output = "❌ Missing required parameter: sender_email"

            elif function_name == "mark_email_as_read":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_read(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            elif function_name == "mark_email_as_important":
                email_id = arguments.get('email_id', '')
                if email_id:
                    output = mark_email_as_important(email_id)
                else:
                    output = "❌ Missing required parameter: email_id"

            # Batch cleanup functions
            elif function_name == "batch_delete_by_subject":
                subject_text = arguments.get('subject_text', '')
                count = arguments.get('count', 25)
                if subject_text:
                    output = batch_delete_by_subject(subject_text, count)
                else:
                    output = "❌ Missing required parameter: subject_text"

            elif function_name == "batch_archive_old_emails":
                days_old = arguments.get('days_old', 0)
                query_filter = arguments.get('query_filter', '')
                count = arguments.get('count', 50)
                if days_old > 0:
                    output = batch_archive_old_emails(days_old, query_filter, count)
                else:
                    output = "❌ Missing or invalid parameter: days_old (must be > 0)"

            elif function_name == "cleanup_promotional_emails":
                action = arguments.get('action', 'archive')
                count = arguments.get('count', 50)
                output = cleanup_promotional_emails(action, count)

            elif function_name == "get_recent_emails_large":
                count = arguments.get('count', 50)
                query = arguments.get('query', 'in:inbox')
                output = get_recent_emails_large(count, query)

            # Briefing and planning functions
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()

            elif function_name == "planning_search":
                query = arguments.get('query', '')
                focus_area = arguments.get('focus_area', 'general')
                if query:
                    # Run async function in sync context
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        output = loop.run_until_complete(planning_search(query, focus_area))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        output = asyncio.run(planning_search(query, focus_area))
                else:
                    output = "❌ Missing required parameter: query"

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Limit output length
        })
    
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

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"📝 Created new thread for user {user_id}: {thread.id}")
        
        thread_id = user_conversations[user_id]
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                handle_rose_functions_enhanced(run_status, thread_id)
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run failed with status: {run_status.status}")
                return "❌ Executive consultation encountered an issue. Please try again in a moment."
            
            await asyncio.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Run timeout - attempting to retrieve last response")
            return "👑 Executive analysis taking longer than expected. Please try again in a moment."
        
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

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Rose startup confirmation"""
    try:
        print(f"\n🌹 ======================================")
        print(f"👑 ROSE ASHCOMBE - EXECUTIVE ASSISTANT")
        print(f"🌹 ======================================")
        print(f"✅ Discord: Connected as {bot.user}")
        print(f"📧 Gmail: {'✅ Connected' if gmail_service else '❌ Not available'}")
        print(f"📅 Calendar: {'✅ Connected' if calendar_service else '❌ Not available'}")
        print(f"🛠️  Assistant: {'✅ Connected' if ASSISTANT_ID else '❌ Not configured'}")
        print(f"🔍 Research: {'✅ Connected' if BRAVE_API_KEY else '❌ Not available'}")
        print(f"📋 Channels: {', '.join(ALLOWED_CHANNELS)}")
        
        if accessible_calendars:
            print(f"📅 Accessible Calendars: {len(accessible_calendars)}")
            for name, _ in accessible_calendars:
                print(f"   • {name}")
        
        print(f"🌹 ======================================")
        print(f"👑 Ready for executive assistance!")
        print(f"🌹 ======================================\n")
        
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
            pass  # auto-fixed to prevent syntax error
            
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
# DISCORD COMMANDS WITH NEW VISUAL IDENTITY
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Latency: {latency}ms - Executive operations running smoothly!")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")


def status_command(ctx):
    """Show Rose's comprehensive status with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # Connection statuses
        embed.add_field(
            name="🔗 OpenAI Assistant",
            value="✅ Connected" if ASSISTANT_ID else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📧 Gmail Access",
            value="✅ Connected" if gmail_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="📅 Calendar Access",
            value="✅ Connected" if calendar_service else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Research Capability",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([f"• {spec}" for spec in ASSISTANT_CONFIG['specialties']])
        embed.add_field(
            name="🎯 Executive Specialties",
            value=specialties_text,
            inline=False
        )
        
        # Calendar status if available
        if accessible_calendars:
            calendar_list = "\n".join([f"• {name}" for name, _ in accessible_calendars])
            embed.add_field(
                name="📅 Accessible Calendars",
                value=calendar_list,
                inline=False
            )
        
        # Active status
        embed.add_field(
            name="📊 Executive Status",
            value=f"👥 Active Conversations: {len(user_conversations)}\n📋 Monitored Channels: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's comprehensive help information with new visual identity"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0xDC2626  # Red color
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Work with Rose",
            value=f"• Mention @{ASSISTANT_CONFIG['name']} for executive assistance and strategic planning\n• Use commands below for specific functions\n• I monitor: {', '.join([f'#{ch}' for ch in ASSISTANT_CONFIG['channels']])}",
            inline=False
        )
        
        # All commands organized by category
        embed.add_field(
            name="📧 Email Commands",
            value="• `!emails [count]` - Recent emails (default: 10)\n• `!unread [count]` - Unread emails only\n• `!emailstats` - Email dashboard overview\n• `!quickemails [count]` - Concise email view\n• `!emailcount` - Just email counts\n• `!cleansender <email> [count]` - Delete emails from sender",
            inline=False
        )
        
        embed.add_field(
            name="📅 Calendar Commands",
            value="• `!briefing` / `!daily` / `!morning` - Morning executive briefing\n• `!schedule` / `!today` - Today's executive schedule\n• `!upcoming [days]` - Upcoming events (default: 7 days)",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Planning & Research Commands",
            value="• `!plan [query]` / `!research [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - System status\n• `!help` - This help message",
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([f"• {ex}" for ex in ASSISTANT_CONFIG['example_requests']])
        embed.add_field(
            name="✨ Example Executive Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([f"• {cap}" for cap in ASSISTANT_CONFIG['capabilities']])
        embed.add_field(
            name="🎯 Executive Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Executive help experiencing issues.")

# Email-specific Discord commands
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Recent emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Unread emails command"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 20))
            emails = get_unread_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread emails unavailable. Please try again.")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Email statistics command"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email stats command error: {e}")
        await ctx.send("📧 Email statistics unavailable. Please try again.")

@bot.command(name='quickemails')
async def quick_emails_command(ctx, count: int = 5):
    """Quick email overview with minimal formatting"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 10))
            emails = get_recent_emails(count)
            await ctx.send(emails)
    except Exception as e:
        print(f"❌ Quick emails command error: {e}")
        await ctx.send("📧 Quick email check unavailable")

@bot.command(name='emailcount')
async def email_count_command(ctx):
    """Just show email counts without details"""
    try:
        async with ctx.typing():
            stats = get_email_stats()
            await ctx.send(stats)
    except Exception as e:
        print(f"❌ Email count command error: {e}")
        await ctx.send("📧 Email count unavailable")

@bot.command(name='cleansender')
async def clean_sender_command(ctx, sender_email: str, count: int = 5):
    """Clean emails from a specific sender"""
    try:
        async with ctx.typing():
            if '@' not in sender_email:
                await ctx.send("❌ Please provide a valid email address")
                return
            
            count = max(1, min(count, 20))
            result = delete_emails_from_sender(sender_email, count)
            await ctx.send(result)
    except Exception as e:
        print(f"❌ Clean sender command error: {e}")
        await ctx.send(f"❌ Error cleaning emails from {sender_email}")

# Briefing-specific Discord commands
@bot.command(name='briefing', aliases=['daily', 'morning'])
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await send_long_message(ctx.message, briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("🌅 Morning briefing unavailable. Please try again.")

@bot.command(name='plan', aliases=['research'])
async def plan_command(ctx, *, query: str = ""):
    """Planning research command"""
    try:
        if not query:
            await ctx.send("🔍 Please provide a planning research query. Example: `!plan time blocking strategies`")
            return
        
        async with ctx.typing():
            research = await planning_search(query)
            await send_long_message(ctx.message, research)
    except Exception as e:
        print(f"❌ Plan command error: {e}")
        await ctx.send("🔍 Planning research unavailable. Please try again.")

# Calendar-specific Discord commands
@bot.command(name='schedule', aliases=['today'])
async def schedule_command(ctx):
    """Today's schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await send_long_message(ctx.message, schedule)
    except Exception as e:
        print(f"❌ Schedule command error: {e}")
        await ctx.send("📅 Schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await send_long_message(ctx.message, events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("📅 Upcoming events unavailable. Please try again.")

# ============================================================================
# ERROR HANDLING AND STARTUP
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `!help` for command usage.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🌹 Starting Rose Ashcombe Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n👑 Rose Ashcombe shutting down gracefully...")
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")

