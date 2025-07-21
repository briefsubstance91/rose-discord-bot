#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (ENHANCED WITH WEATHER INTEGRATION)
Executive Assistant with Enhanced Error Handling, Planning, Calendar & Weather Functions
UPDATED: Added WeatherAPI.com integration to morning briefings
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
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Active runs tracking for rate limiting
    active_runs = {}
    
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
accessible_calendars = []

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
        ('🍎 Britt iCloud', BRITT_ICLOUD_CALENDAR_ID, 'icloud')
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
# MAIN CONVERSATION HANDLER WITH FIXED OPENAI API CALLS
# ============================================================================

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with fixed API calls"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Check if user already has an active run
        if user_id in active_runs:
            return "👑 Rose is currently analyzing your executive strategy. Please wait for completion."
        
        # Create or get existing thread
        thread = client.beta.threads.create()
        thread_id = thread.id
        
        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        # Mark user as having active run
        active_runs[user_id] = thread_id
        
        # Create run with assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
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
        
        # Get the response
        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )
        
        if messages.data:
            response = messages.data[0].content[0].text.value
            return response
        else:
            return "👑 Rose: I apologize, but I couldn't generate a response. Please try again."
            
    except Exception as e:
        active_runs.pop(user_id, None)
        print(f"❌ Rose response error: {e}")
        print(f"📋 Rose response traceback: {traceback.format_exc()}")
        return f"👑 Rose: I encountered an error. Please try again. ({str(e)[:50]})"

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

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

@bot.command(name='status')
async def status_command(ctx):
    """Check Rose's system status including weather integration"""
    status_report = f"""👑 **{ASSISTANT_NAME} System Status**

🤖 **OpenAI Assistant:** {'✅ Connected' if ASSISTANT_ID else '❌ Not Configured'}
📅 **Calendar Integration:** {'✅ Active' if google_services_initialized else '❌ Inactive'}
🌤️ **Weather API:** {'✅ Configured' if WEATHER_API_KEY else '❌ Not Configured'}
🔍 **Planning Search:** {'✅ Available' if BRAVE_API_KEY else '❌ Not Available'}

📊 **Accessible Calendars:** {len(accessible_calendars) if accessible_calendars else 0}
🎯 **Active Channels:** {', '.join(ALLOWED_CHANNELS)}
⚡ **Active Runs:** {len(active_runs)}

💼 **Executive Features:**
   • Morning briefing with weather
   • Calendar integration & scheduling
   • Planning research & productivity
   • UV index & weather advisory"""
    
    await ctx.send(status_report)

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's responsiveness"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"👑 Rose responding in {latency}ms")

@bot.command(name='commands')
async def commands_command(ctx):
    """Show enhanced help with weather commands (renamed from 'help' to avoid conflict)"""
    help_text = f"""👑 **{ASSISTANT_NAME} - Executive Assistant Commands**

🌤️ **Weather & Briefing:**
   `!briefing` - Complete morning briefing with weather
   `!weather` - Current weather & UV index

📅 **Calendar Management:**
   `!schedule` - Today's calendar
   `!upcoming [days]` - Upcoming events (default 7 days)

🔍 **Planning & Research:**
   Just mention @Rose or start with "Rose" for planning assistance

⚙️ **System Commands:**
   `!status` - System status & integration check
   `!ping` - Response time test
   `!commands` - This help message

💼 **Executive Features:**
   • Weather-integrated morning briefings
   • Multi-calendar schedule optimization  
   • UV index & outdoor planning advice
   • Strategic planning research

📍 **Current Location:** {USER_CITY}
🎯 **Active Channels:** {', '.join(ALLOWED_CHANNELS)}"""
    
    await ctx.send(help_text)

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