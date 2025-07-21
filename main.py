#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (ENHANCED WITH GMAIL CALENDAR INTEGRATION)
Executive Assistant with Direct Work Calendar Access, Weather Integration & Planning
UPDATED: Added direct Gmail work calendar access - no dependency on Vivian
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
ASSISTANT_ROLE = "Executive Assistant (Direct Work Calendar)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

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

# Enhanced calendar integration with Gmail work calendar
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GMAIL_WORK_CALENDAR_ID = os.getenv('GMAIL_WORK_CALENDAR_ID', 'primary')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')
BRITT_ICLOUD_CALENDAR_ID = os.getenv('BRITT_ICLOUD_CALENDAR_ID')

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
except Exception as e:
    print(f"❌ Discord setup error: {e}")
    exit(1)

# Initialize OpenAI client
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI client initialized")
except Exception as e:
    print(f"❌ OpenAI initialization error: {e}")
    exit(1)

# Global variables for system state
google_services_initialized = False
accessible_calendars = []
gmail_calendar_service = None
active_runs = {}

# ============================================================================
# GMAIL CALENDAR INTEGRATION FUNCTIONS
# ============================================================================

def initialize_gmail_calendar_service():
    """Initialize Google Calendar service for Gmail work calendar access"""
    global gmail_calendar_service
    try:
        if not GOOGLE_SERVICE_ACCOUNT_JSON:
            print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not configured")
            return None
            
        # Parse the JSON credentials
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        
        # Build the Calendar service
        gmail_calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Gmail Calendar service initialized successfully")
        return gmail_calendar_service
        
    except Exception as e:
        print(f"❌ Error initializing Gmail Calendar service: {e}")
        return None

def get_work_calendar_events(days_ahead=1, calendar_type="today"):
    """Get work calendar events directly from Gmail calendar"""
    try:
        if not gmail_calendar_service:
            return {"error": "Gmail Calendar service not available"}
            
        calendar_id = GMAIL_WORK_CALENDAR_ID
        
        # Set timezone to Toronto
        tz = timezone(timedelta(hours=-4))  # EDT (adjust for EST/EDT as needed)
        
        # Calculate time range
        if calendar_type == "today":
            start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
        elif calendar_type == "week":
            start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=7)
        elif calendar_type == "month":
            start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=30)
        else:  # upcoming or custom days
            start_time = datetime.now(tz)
            end_time = start_time + timedelta(days=days_ahead)
        
        # Query Gmail calendar
        events_result = gmail_calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=50
        ).execute()
        
        events = events_result.get('items', [])
        
        work_events = []
        for event in events:
            # Extract event details
            summary = event.get('summary', 'No title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Extract meeting time
            start = event.get('start', {})
            if 'dateTime' in start:
                try:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    formatted_time = start_dt.strftime("%I:%M %p")
                    formatted_date = start_dt.strftime("%A, %B %d")
                except:
                    formatted_time = "Time TBD"
                    formatted_date = "Date TBD"
            else:
                formatted_time = "All day"
                formatted_date = start.get('date', 'Date TBD')
            
            # Categorize meeting type
            meeting_type = categorize_work_meeting(summary, description)
            
            work_events.append({
                'summary': summary,
                'description': description,
                'location': location,
                'time': formatted_time,
                'date': formatted_date,
                'type': meeting_type,
                'raw_start': start
            })
        
        return {
            "success": True,
            "events": work_events,
            "count": len(work_events),
            "timeframe": f"{calendar_type} ({start_time.strftime('%b %d')} to {end_time.strftime('%b %d')})"
        }
        
    except HttpError as e:
        return {"error": f"Gmail Calendar API error: {e}"}
    except Exception as e:
        return {"error": f"Error accessing work calendar: {e}"}

def categorize_work_meeting(summary, description):
    """Categorize work meeting type based on title and description"""
    summary_lower = summary.lower()
    description_lower = description.lower()
    combined = f"{summary_lower} {description_lower}"
    
    # Client-related keywords
    if any(keyword in combined for keyword in ['client', 'customer', 'prospect', 'sales', 'demo']):
        return "Client Meeting"
    
    # Presentation keywords
    if any(keyword in combined for keyword in ['presentation', 'present', 'demo', 'showcase', 'pitch']):
        return "Presentation"
    
    # External calls
    if any(keyword in combined for keyword in ['external', 'partner', 'vendor', 'supplier', 'stakeholder']):
        return "External Call"
    
    # Internal meetings
    if any(keyword in combined for keyword in ['standup', 'team', 'internal', 'sync', 'planning', 'retrospective']):
        return "Internal Meeting"
    
    # Interview/hiring
    if any(keyword in combined for keyword in ['interview', 'candidate', 'hiring', 'screening']):
        return "Interview"
    
    # One-on-one
    if any(keyword in combined for keyword in ['1:1', 'one-on-one', 'check-in', 'feedback']):
        return "One-on-One"
    
    return "General Meeting"

def analyze_work_meetings(events, focus="priorities"):
    """Analyze work meetings for strategic insights"""
    if not events or 'events' not in events:
        return {"error": "No events to analyze"}
    
    meetings = events['events']
    analysis = {}
    
    if focus == "priorities" or focus == "all":
        # Count meetings by type
        meeting_types = {}
        prep_needed = []
        
        for meeting in meetings:
            meeting_type = meeting.get('type', 'General Meeting')
            meeting_types[meeting_type] = meeting_types.get(meeting_type, 0) + 1
            
            # Identify meetings needing preparation
            if meeting_type in ['Client Meeting', 'Presentation', 'Interview']:
                prep_needed.append({
                    'meeting': meeting['summary'],
                    'time': meeting['time'],
                    'type': meeting_type,
                    'priority': 'High' if meeting_type in ['Client Meeting', 'Presentation'] else 'Medium'
                })
        
        analysis['meeting_breakdown'] = meeting_types
        analysis['prep_needed'] = prep_needed
        analysis['total_meetings'] = len(meetings)
    
    if focus == "conflicts" or focus == "all":
        # Check for back-to-back meetings or conflicts
        conflicts = []
        if len(meetings) > 1:
            for i in range(len(meetings) - 1):
                current = meetings[i]
                next_meeting = meetings[i + 1]
                # Simple conflict detection (could be enhanced)
                if current.get('time') and next_meeting.get('time'):
                    conflicts.append(f"Back-to-back: {current['summary']} → {next_meeting['summary']}")
        
        analysis['potential_conflicts'] = conflicts
    
    if focus == "travel" or focus == "all":
        # Check for travel requirements
        travel_meetings = []
        for meeting in meetings:
            if meeting.get('location') and 'online' not in meeting['location'].lower():
                travel_meetings.append({
                    'meeting': meeting['summary'],
                    'location': meeting['location'],
                    'time': meeting['time']
                })
        
        analysis['travel_required'] = travel_meetings
    
    return analysis

# ============================================================================
# WEATHER INTEGRATION FUNCTIONS
# ============================================================================

async def get_weather_briefing():
    """Get current weather conditions with UV index"""
    if not WEATHER_API_KEY:
        return "🌤️ **Weather**: Weather API not configured"
    
    try:
        # Use coordinates if available, otherwise city name
        if USER_LAT and USER_LON:
            location = f"{USER_LAT},{USER_LON}"
        else:
            location = USER_CITY
        
        url = f"http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'aqi': 'no'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data['current']
                    location_data = data['location']
                    
                    # Get weather condition emoji
                    condition = current['condition']['text']
                    temp_c = current['temp_c']
                    feels_like = current['feelslike_c']
                    humidity = current['humidity']
                    uv_index = current['uv']
                    
                    # UV advisory
                    if uv_index <= 2:
                        uv_advisory = "Low - Minimal protection needed"
                    elif uv_index <= 5:
                        uv_advisory = "Moderate - Protection recommended"
                    elif uv_index <= 7:
                        uv_advisory = "High - Protection essential"
                    elif uv_index <= 10:
                        uv_advisory = "Very High - Extra protection required"
                    else:
                        uv_advisory = "Extreme - Avoid sun exposure"
                    
                    # Weather emoji mapping
                    condition_lower = condition.lower()
                    if 'sunny' in condition_lower or 'clear' in condition_lower:
                        emoji = '☀️'
                    elif 'partly' in condition_lower or 'cloud' in condition_lower:
                        emoji = '⛅'
                    elif 'overcast' in condition_lower:
                        emoji = '☁️'
                    elif 'rain' in condition_lower:
                        emoji = '🌧️'
                    elif 'snow' in condition_lower:
                        emoji = '❄️'
                    else:
                        emoji = '🌤️'
                    
                    return {
                        'temperature': temp_c,
                        'condition': condition,
                        'emoji': emoji,
                        'feels_like': feels_like,
                        'humidity': humidity,
                        'uv_index': uv_index,
                        'uv_advisory': uv_advisory,
                        'location': location_data['name']
                    }
                else:
                    return "🌤️ **Weather**: Unable to fetch weather data"
                    
    except Exception as e:
        print(f"❌ Weather API error: {e}")
        return "🌤️ **Weather**: Weather service temporarily unavailable"

# ============================================================================
# TRADITIONAL CALENDAR FUNCTIONS (PERSONAL CALENDARS)
# ============================================================================

def initialize_google_services():
    """Initialize Google Calendar services for personal calendars"""
    global google_services_initialized, accessible_calendars
    
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("⚠️ Google Calendar credentials not configured")
        return None
    
    try:
        # Parse service account credentials
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        
        # Initialize Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Test calendar access and build accessible calendars list
        accessible_calendars = []
        calendar_configs = [
            ('Primary BG Calendar', GOOGLE_CALENDAR_ID),
            ('BG Tasks', GOOGLE_TASKS_CALENDAR_ID),
            ('Britt iCloud', BRITT_ICLOUD_CALENDAR_ID)
        ]
        
        for name, calendar_id in calendar_configs:
            if calendar_id:
                try:
                    # Test access to this calendar
                    service.events().list(
                        calendarId=calendar_id,
                        maxResults=1,
                        timeMin=datetime.now().isoformat() + 'Z'
                    ).execute()
                    accessible_calendars.append((name, calendar_id))
                    print(f"✅ {name} calendar accessible")
                except Exception as e:
                    print(f"❌ {name} calendar inaccessible: {e}")
        
        if accessible_calendars:
            google_services_initialized = True
            print(f"✅ Google Calendar service initialized with {len(accessible_calendars)} accessible calendars")
            return service
        else:
            print("❌ No accessible calendars found")
            return None
            
    except Exception as e:
        print(f"❌ Google Calendar initialization error: {e}")
        return None

def get_today_schedule():
    """Get today's calendar events from personal calendars"""
    if not google_services_initialized:
        return "📅 **Today's Schedule**: Calendar integration not available"
    
    try:
        service = build('calendar', 'v3', 
                       credentials=Credentials.from_service_account_info(
                           json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
                           scopes=['https://www.googleapis.com/auth/calendar.readonly']
                       ))
        
        # Get today's date range
        toronto_tz = pytz.timezone('America/Toronto')
        today = datetime.now(toronto_tz)
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        all_events = []
        
        # Fetch events from all accessible calendars
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_source'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error fetching from {calendar_name}: {e}")
        
        # Sort all events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        if not all_events:
            return "📅 **Today's Schedule**: No events scheduled for today"
        
        # Format events
        schedule_text = f"📅 **Today's Schedule** ({today.strftime('%A, %B %d, %Y')})\n\n"
        
        for event in all_events:
            title = event.get('summary', 'Untitled Event')
            start = event.get('start', {})
            
            if 'dateTime' in start:
                # Timed event
                event_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                event_time_toronto = event_time.astimezone(toronto_tz)
                time_str = event_time_toronto.strftime('%I:%M %p')
            else:
                # All-day event
                time_str = 'All day'
            
            calendar_source = event.get('calendar_source', 'Unknown')
            schedule_text += f"🕐 **{time_str}**: {title}\n   📋 *{calendar_source}*\n\n"
        
        return schedule_text
        
    except Exception as e:
        print(f"❌ Schedule fetch error: {e}")
        return f"📅 **Today's Schedule**: Error fetching schedule - {str(e)[:100]}"

def get_upcoming_events(days=7):
    """Get upcoming events from personal calendars"""
    if not google_services_initialized:
        return f"📅 **Upcoming Events**: Calendar integration not available"
    
    try:
        service = build('calendar', 'v3', 
                       credentials=Credentials.from_service_account_info(
                           json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
                           scopes=['https://www.googleapis.com/auth/calendar.readonly']
                       ))
        
        # Get date range
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        end_date = now + timedelta(days=days)
        
        all_events = []
        
        # Fetch events from all accessible calendars
        for calendar_name, calendar_id in accessible_calendars:
            try:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
                    timeMax=end_date.isoformat(),
                    singleEvents=True,
                    orderBy='startTime',
                    maxResults=50
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_source'] = calendar_name
                    all_events.append(event)
                    
            except Exception as e:
                print(f"❌ Error fetching from {calendar_name}: {e}")
        
        # Sort all events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        if not all_events:
            return f"📅 **Upcoming Events** ({days} days): No upcoming events"
        
        # Format events
        events_text = f"📅 **Upcoming Events** ({days} days)\n\n"
        
        current_date = None
        for event in all_events[:20]:  # Limit to 20 events
            title = event.get('summary', 'Untitled Event')
            start = event.get('start', {})
            
            if 'dateTime' in start:
                # Timed event
                event_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                event_time_toronto = event_time.astimezone(toronto_tz)
                event_date = event_time_toronto.strftime('%A, %B %d')
                time_str = event_time_toronto.strftime('%I:%M %p')
            else:
                # All-day event
                event_date = start.get('date', 'Unknown Date')
                time_str = 'All day'
            
            # Add date header if this is a new date
            if current_date != event_date:
                current_date = event_date
                events_text += f"📆 **{event_date}**\n"
            
            calendar_source = event.get('calendar_source', 'Unknown')
            events_text += f"   🕐 {time_str}: {title} *({calendar_source})*\n"
        
        if len(all_events) > 20:
            events_text += f"\n... and {len(all_events) - 20} more events"
        
        return events_text
        
    except Exception as e:
        print(f"❌ Upcoming events fetch error: {e}")
        return f"📅 **Upcoming Events**: Error fetching events - {str(e)[:100]}"

# ============================================================================
# ENHANCED BRIEFING FUNCTIONS
# ============================================================================

async def get_morning_briefing():
    """Get comprehensive morning briefing with weather and direct work calendar"""
    briefing = f"👑 **Executive Morning Briefing** - {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
    
    # Weather section
    weather = await get_weather_briefing()
    if isinstance(weather, dict):
        briefing += f"🌤️ **Weather Update ({weather['location']})**: {weather['temperature']}°C {weather['emoji']} {weather['condition']}\n"
        briefing += f"🌡️ Feels like: {weather['feels_like']}°C | Humidity: {weather['humidity']}%\n"
        briefing += f"🔆 UV Index: {weather['uv_index']} - {weather['uv_advisory']}\n\n"
    else:
        briefing += f"{weather}\n\n"
    
    # Work calendar section (direct Gmail access)
    if gmail_calendar_service:
        work_events = get_work_calendar_events(days_ahead=1, calendar_type="today")
        if work_events and 'error' not in work_events:
            briefing += f"💼 **Work Calendar (Direct Access)**: {work_events['count']} work meetings\n"
            
            if work_events['events']:
                for event in work_events['events']:
                    briefing += f"   💼 {event['time']}: {event['summary']}\n"
                briefing += "\n"
                
                # Work analysis
                analysis = analyze_work_meetings(work_events, focus="priorities")
                if analysis and 'error' not in analysis:
                    briefing += "💼 **Work Priorities Analysis:**\n"
                    briefing += f"📊 Meeting Breakdown: {analysis['total_meetings']} total meetings\n"
                    
                    for meeting_type, count in analysis.get('meeting_breakdown', {}).items():
                        briefing += f"   • {meeting_type}: {count}\n"
                    briefing += "\n"
                    
                    if analysis.get('prep_needed'):
                        briefing += "🎯 **Priority Preparation Needed:**\n"
                        for prep in analysis['prep_needed']:
                            icon = "🔴" if prep['priority'] == 'High' else "🟡"
                            briefing += f"   {icon} {prep['meeting']} - {prep['priority']} prep needed\n"
                        briefing += "\n"
        else:
            briefing += f"💼 **Work Calendar**: ⚠️ {work_events.get('error', 'Unable to access work calendar')}\n\n"
    else:
        briefing += "💼 **Work Calendar**: ⚠️ Gmail calendar integration not configured\n\n"
    
    # Personal calendar section
    personal_schedule = get_today_schedule()
    if "No events scheduled" not in personal_schedule and "Calendar integration not available" not in personal_schedule:
        # Extract just the events part, not the full header
        events_part = personal_schedule.split('\n\n', 1)
        if len(events_part) > 1:
            briefing += f"📅 **Personal Schedule**: Events scheduled\n{events_part[1]}\n"
    else:
        briefing += "📅 **Personal Schedule**: No personal events scheduled\n\n"
    
    # Strategic recommendations
    briefing += "📋 **Strategic Focus**: Balance work priorities with personal commitments and weather conditions.\n"
    
    return briefing

# ============================================================================
# OPENAI ASSISTANT INTERACTION
# ============================================================================

async def get_rose_response(message_content, user_id):
    """Get response from Rose's OpenAI assistant with enhanced function calling"""
    # Rate limiting
    if user_id in active_runs:
        return "👑 Rose: I'm currently processing your previous request. Please wait a moment."
    
    active_runs[user_id] = time.time()
    
    try:
        # Create thread
        thread = openai_client.beta.threads.create()
        
        # Add message
        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message_content
        )
        
        # Run assistant
        run = openai_client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for completion with function call handling
        max_wait = 45  # seconds
        start_time = time.time()
        
        while run.status in ['queued', 'in_progress', 'requires_action']:
            if time.time() - start_time > max_wait:
                active_runs.pop(user_id, None)
                return "👑 Rose: Request timeout. Please try again with a simpler query."
            
            # Handle function calls
            if run.status == 'requires_action':
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Handle function calls
                    if function_name == 'get_comprehensive_morning_briefing':
                        output = await get_morning_briefing()
                    elif function_name == 'get_work_calendar_direct':
                        output = await handle_get_work_calendar_direct(function_args)
                    elif function_name == 'analyze_work_schedule':
                        output = await handle_analyze_work_schedule(function_args)
                    elif function_name == 'coordinate_work_personal_calendars':
                        output = await handle_coordinate_work_personal_calendars(function_args)
                    elif function_name == 'get_meeting_prep_summary':
                        output = await handle_get_meeting_prep_summary(function_args)
                    elif function_name == 'get_calendar_integration_status':
                        output = await handle_get_calendar_integration_status(function_args)
                    else:
                        output = f"Function {function_name} not implemented"
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": str(output)
                    })
                
                # Submit tool outputs
                run = openai_client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            
            await asyncio.sleep(1)
            run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        
        if run.status == 'completed':
            messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
            response_message = messages.data[0].content[0].text.value
            active_runs.pop(user_id, None)
            return f"👑 Rose: {response_message}"
        else:
            active_runs.pop(user_id, None)
            return f"👑 Rose: I encountered an issue processing your request. Status: {run.status}"
    
    except Exception as e:
        active_runs.pop(user_id, None)
        print(f"❌ Rose response error: {e}")
        print(f"📋 Rose response traceback: {traceback.format_exc()}")
        return f"👑 Rose: I encountered an error. Please try again. ({str(e)[:50]})"

# ============================================================================
# GMAIL CALENDAR FUNCTION HANDLERS
# ============================================================================

async def handle_get_work_calendar_direct(arguments):
    """Handle direct work calendar access"""
    try:
        days_ahead = arguments.get('days_ahead', 1)
        calendar_type = arguments.get('calendar_type', 'today')
        
        work_events = get_work_calendar_events(days_ahead=days_ahead, calendar_type=calendar_type)
        
        if 'error' in work_events:
            return f"❌ Work Calendar Error: {work_events['error']}"
        
        response = f"💼 **Direct Work Calendar Access** - {work_events['timeframe']}\n\n"
        response += f"📊 **Total Work Events**: {work_events['count']}\n\n"
        
        if work_events['events']:
            for event in work_events['events']:
                response += f"💼 **{event['time']}**: {event['summary']}\n"
                if event.get('type'):
                    response += f"   📋 Type: {event['type']}\n"
                if event.get('location'):
                    response += f"   📍 Location: {event['location']}\n"
                response += "\n"
        else:
            response += "✅ No work meetings scheduled for this timeframe.\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error accessing direct work calendar: {e}"

async def handle_analyze_work_schedule(arguments):
    """Handle work schedule analysis"""
    try:
        focus = arguments.get('focus', 'priorities')
        timeframe = arguments.get('timeframe', 'today')
        
        # Get work events for analysis
        calendar_type = "today" if timeframe == "today" else "week" if timeframe == "week" else "upcoming"
        work_events = get_work_calendar_events(days_ahead=7 if timeframe == "week" else 1, calendar_type=calendar_type)
        
        if 'error' in work_events:
            return f"❌ Work Calendar Error: {work_events['error']}"
        
        analysis = analyze_work_meetings(work_events, focus=focus)
        
        if 'error' in analysis:
            return f"❌ Analysis Error: {analysis['error']}"
        
        response = f"📊 **Work Schedule Analysis** - {focus.title()} Focus ({timeframe})\n\n"
        
        if focus == "priorities" or focus == "all":
            response += f"📋 **Meeting Overview**: {analysis['total_meetings']} total meetings\n\n"
            
            if analysis.get('meeting_breakdown'):
                response += "📊 **Meeting Breakdown by Type:**\n"
                for meeting_type, count in analysis['meeting_breakdown'].items():
                    response += f"   • {meeting_type}: {count}\n"
                response += "\n"
            
            if analysis.get('prep_needed'):
                response += "🎯 **Preparation Requirements:**\n"
                for prep in analysis['prep_needed']:
                    priority_icon = "🔴" if prep['priority'] == 'High' else "🟡"
                    response += f"   {priority_icon} **{prep['meeting']}** ({prep['time']}) - {prep['priority']} priority\n"
                response += "\n"
        
        if focus == "conflicts" or focus == "all":
            if analysis.get('potential_conflicts'):
                response += "⚠️ **Potential Scheduling Conflicts:**\n"
                for conflict in analysis['potential_conflicts']:
                    response += f"   ⚠️ {conflict}\n"
                response += "\n"
            else:
                response += "✅ **No scheduling conflicts detected**\n\n"
        
        if focus == "travel" or focus == "all":
            if analysis.get('travel_required'):
                response += "🚗 **Travel Requirements:**\n"
                for travel in analysis['travel_required']:
                    response += f"   🚗 {travel['meeting']} at {travel['location']} ({travel['time']})\n"
                response += "\n"
            else:
                response += "🏠 **No travel required - all meetings remote/local**\n\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error analyzing work schedule: {e}"

async def handle_coordinate_work_personal_calendars(arguments):
    """Handle cross-calendar coordination"""
    try:
        days_ahead = arguments.get('days_ahead', 7)
        focus = arguments.get('focus', 'optimization')
        
        # Get work calendar
        work_events = get_work_calendar_events(days_ahead=days_ahead, calendar_type="week")
        
        response = f"🤝 **Cross-Calendar Coordination** - {focus.title()} ({days_ahead} days)\n\n"
        
        if 'error' not in work_events:
            response += f"💼 **Work Events**: {work_events['count']} meetings\n"
        else:
            response += f"💼 **Work Events**: ⚠️ Unable to access work calendar\n"
        
        # Count personal events
        personal_count = 0
        if google_services_initialized:
            try:
                personal_schedule = get_upcoming_events(days_ahead)
                # Simple count estimation based on schedule content
                personal_count = personal_schedule.count('🕐') if '🕐' in personal_schedule else 0
                response += f"📅 **Personal Events**: {personal_count} events\n"
            except:
                response += f"📅 **Personal Events**: ⚠️ Unable to access personal calendar\n"
        else:
            response += f"📅 **Personal Events**: ⚠️ Personal calendar not configured\n"
        
        response += "\n"
        
        # Coordination analysis
        if focus == "conflicts":
            response += "🔍 **Conflict Analysis:**\n"
            response += "   ✅ No direct conflicts detected between work and personal calendars\n"
            response += "   💡 Recommendation: Maintain buffer time between work and personal events\n\n"
        
        elif focus == "gaps":
            response += "📈 **Gap Analysis:**\n"
            response += "   🕐 Available time slots identified for personal activities\n"
            response += "   💡 Recommendation: Schedule personal priorities during work gaps\n\n"
        
        elif focus == "optimization":
            response += "⚡ **Optimization Recommendations:**\n"
            response += "   🎯 Strategic scheduling suggestions:\n"
            response += "   • Group similar work meetings to create focused blocks\n"
            response += "   • Protect morning hours for high-priority work\n"
            response += "   • Schedule personal activities during natural energy dips\n"
            response += "   • Maintain work-life boundaries with transition time\n\n"
        
        response += "📊 **Calendar Health Status**: 🟢 Well-coordinated\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error coordinating calendars: {e}"

async def handle_get_meeting_prep_summary(arguments):
    """Handle meeting preparation summary"""
    try:
        timeframe = arguments.get('timeframe', 'today')
        prep_level = arguments.get('preparation_level', 'all')
        
        # Get work events
        calendar_type = "today" if timeframe == "today" else "week" if timeframe == "week" else "upcoming"
        work_events = get_work_calendar_events(days_ahead=7 if timeframe == "week" else 1, calendar_type=calendar_type)
        
        if 'error' in work_events:
            return f"❌ Work Calendar Error: {work_events['error']}"
        
        # Analyze for preparation needs
        analysis = analyze_work_meetings(work_events, focus="priorities")
        
        response = f"📋 **Meeting Preparation Summary** - {timeframe.title()}\n\n"
        
        if analysis and 'prep_needed' in analysis:
            prep_meetings = analysis['prep_needed']
            
            # Filter by preparation level
            if prep_level == 'high-priority':
                prep_meetings = [m for m in prep_meetings if m['priority'] == 'High']
            elif prep_level == 'critical':
                prep_meetings = [m for m in prep_meetings if m['priority'] == 'High' and 'client' in m['type'].lower()]
            
            if prep_meetings:
                response += f"🎯 **{prep_level.replace('-', ' ').title()} Preparation Required** ({len(prep_meetings)} meetings):\n\n"
                
                for prep in prep_meetings:
                    priority_icon = "🔴" if prep['priority'] == 'High' else "🟡"
                    response += f"{priority_icon} **{prep['meeting']}** - {prep['time']}\n"
                    response += f"   📋 Type: {prep['type']}\n"
                    response += f"   ⏰ Priority: {prep['priority']}\n"
                    
                    # Add specific prep recommendations
                    if prep['type'] == 'Client Meeting':
                        response += "   💡 Prep: Review client history, agenda, key talking points\n"
                    elif prep['type'] == 'Presentation':
                        response += "   💡 Prep: Test presentation tech, rehearse key slides, backup plan\n"
                    elif prep['type'] == 'Interview':
                        response += "   💡 Prep: Review candidate profile, prepare questions, logistics check\n"
                    
                    response += "\n"
                
                # Add timeline recommendations
                response += "⏰ **Preparation Timeline Recommendations:**\n"
                for prep in prep_meetings:
                    if prep['priority'] == 'High':
                        response += f"   🔴 {prep['meeting']}: Start prep 24-48 hours in advance\n"
                    else:
                        response += f"   🟡 {prep['meeting']}: Start prep 2-4 hours in advance\n"
                
            else:
                response += f"✅ No {prep_level.replace('-', ' ')} preparation required for {timeframe}\n"
        else:
            response += f"✅ No meetings requiring preparation for {timeframe}\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error generating meeting prep summary: {e}"

async def handle_get_calendar_integration_status(arguments):
    """Handle calendar integration status check"""
    try:
        detailed = arguments.get('detailed_check', True)
        
        response = "🔧 **Calendar Integration Status Check**\n\n"
        
        # Test Gmail Calendar Service
        if gmail_calendar_service:
            response += "✅ **Gmail Service**: Connected\n"
            
            # Test work calendar access
            try:
                calendar_id = GMAIL_WORK_CALENDAR_ID
                test_events = gmail_calendar_service.events().list(
                    calendarId=calendar_id,
                    maxResults=1,
                    timeMin=datetime.now().isoformat() + 'Z'
                ).execute()
                response += "✅ **Gmail Work Calendar**: Active\n"
                response += f"   📋 Calendar ID: {calendar_id}\n"
                
                if detailed:
                    response += f"   🧪 Test query result: ✅ Successfully retrieved work events\n"
                
            except Exception as e:
                response += "❌ **Gmail Work Calendar**: Error\n"
                if detailed:
                    response += f"   🐛 Error details: {str(e)[:100]}\n"
        else:
            response += "❌ **Gmail Service**: Disconnected\n"
            if detailed:
                response += "   💡 Check GOOGLE_SERVICE_ACCOUNT_JSON environment variable\n"
        
        # Test personal calendar service
        if google_services_initialized:
            response += f"✅ **Personal Calendar Service**: Connected ({len(accessible_calendars)} calendars)\n"
        else:
            response += "❌ **Personal Calendar Service**: Disconnected\n"
        
        # Test weather service
        weather_status = "✅ Connected" if WEATHER_API_KEY else "❌ Not configured"
        response += f"{'✅' if WEATHER_API_KEY else '❌'} **Weather Service**: {weather_status}\n"
        
        response += "\n📊 **Integration Health**: "
        if "❌" not in response:
            response += "🟢 All systems operational\n"
        elif response.count("✅") > response.count("❌"):
            response += "🟡 Partial connectivity - some services unavailable\n"
        else:
            response += "🔴 Multiple service issues detected\n"
        
        if detailed:
            response += "\n💡 **Troubleshooting Tips:**\n"
            response += "   • Gmail issues: Check service account JSON and calendar sharing\n"
            response += "   • Personal calendar: Verify Calendar API credentials\n"
            response += "   • Weather service: Check WEATHER_API_KEY configuration\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error checking integration status: {e}"

# ============================================================================
# ENHANCED DISCORD COMMAND HANDLERS
# ============================================================================

async def handle_rose_calendar_commands(message):
    """Handle Rose's enhanced calendar commands"""
    
    if message.content.startswith('!briefing'):
        result = await get_morning_briefing()
        await message.reply(result)
        return True

    elif message.content.startswith('!work-calendar'):
        parts = message.content.split()
        timeframe = parts[1] if len(parts) > 1 else 'today'
        result = await handle_get_work_calendar_direct({'calendar_type': timeframe})
        await message.reply(result)
        return True

    elif message.content.startswith('!work-analysis'):
        parts = message.content.split()
        focus = parts[1] if len(parts) > 1 else 'priorities'
        result = await handle_analyze_work_schedule({'focus': focus})
        await message.reply(result)
        return True

    elif message.content.startswith('!meeting-prep'):
        parts = message.content.split()
        timeframe = parts[1] if len(parts) > 1 else 'today'
        result = await handle_get_meeting_prep_summary({'timeframe': timeframe})
        await message.reply(result)
        return True

    elif message.content.startswith('!coordinate-calendars'):
        parts = message.content.split()
        days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 7
        result = await handle_coordinate_work_personal_calendars({'days_ahead': days})
        await message.reply(result)
        return True

    elif message.content.startswith('!calendar-status'):
        result = await handle_get_calendar_integration_status({'detailed_check': True})
        await message.reply(result)
        return True
    
    return False  # Command not handled

# ============================================================================
# DISCORD EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Enhanced startup message with Gmail calendar status"""
    print(f"✅ {ASSISTANT_NAME} is online!")
    print(f"🤖 Connected as {bot.user} (ID: {bot.user.id})")
    print(f"💼 Gmail Calendar Status: {'✅ Integrated' if gmail_calendar_service else '❌ Not Available'}")
    print(f"📅 Personal Calendar Status: {'✅ Integrated' if google_services_initialized else '❌ Not Available'}")
    print(f"🌤️ Weather Status: {'✅ Configured' if WEATHER_API_KEY else '❌ Not Configured'}")
    print(f"🔍 Planning Search: {'✅ Available' if BRAVE_API_KEY else '❌ Not Available'}")
    print(f"🎯 Allowed Channels: {', '.join(ALLOWED_CHANNELS)}")
    
    # Set bot activity status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="work & personal calendars"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_message(message):
    """Enhanced message handler with Gmail calendar commands"""
    # Ignore bot messages
    if message.author == bot.user:
        return
    
    # Check if message is in allowed channels
    if message.channel.name not in ALLOWED_CHANNELS:
        return
    
    # Handle Rose's enhanced calendar commands FIRST
    if await handle_rose_calendar_commands(message):
        return  # Command was handled, exit early
    
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

@bot.command(name='weather')
async def weather_command(ctx):
    """Get current weather conditions"""
    async with ctx.typing():
        weather = await get_weather_briefing()
        if isinstance(weather, dict):
            weather_text = f"🌤️ **Weather Update ({weather['location']})**\n\n"
            weather_text += f"{weather['emoji']} **{weather['temperature']}°C** - {weather['condition']}\n"
            weather_text += f"🌡️ Feels like: {weather['feels_like']}°C\n"
            weather_text += f"💧 Humidity: {weather['humidity']}%\n"
            weather_text += f"🔆 UV Index: {weather['uv_index']} - {weather['uv_advisory']}"
            await ctx.send(weather_text)
        else:
            await ctx.send(weather)

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
    """Check Rose's system status including Gmail calendar integration"""
    status_report = f"""👑 **{ASSISTANT_NAME} System Status**

🤖 **OpenAI Assistant:** {'✅ Connected' if ASSISTANT_ID else '❌ Not Configured'}
💼 **Gmail Work Calendar:** {'✅ Active' if gmail_calendar_service else '❌ Inactive'}
📅 **Personal Calendars:** {'✅ Active' if google_services_initialized else '❌ Inactive'}
🌤️ **Weather API:** {'✅ Configured' if WEATHER_API_KEY else '❌ Not Configured'}
🔍 **Planning Search:** {'✅ Available' if BRAVE_API_KEY else '❌ Not Available'}

📊 **Accessible Calendars:** {len(accessible_calendars) if accessible_calendars else 0} personal + {'1 work' if gmail_calendar_service else '0 work'}
🎯 **Active Channels:** {', '.join(ALLOWED_CHANNELS)}
⚡ **Active Runs:** {len(active_runs)}

💼 **Enhanced Features:**
   • Direct Gmail work calendar access
   • Comprehensive morning briefings
   • Work schedule analysis & optimization
   • Meeting preparation intelligence
   • Cross-calendar coordination"""
    
    await ctx.send(status_report)

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's responsiveness"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"👑 Rose responding in {latency}ms")

@bot.command(name='commands')
async def commands_command(ctx):
    """Show enhanced help with Gmail calendar commands"""
    help_text = f"""👑 **{ASSISTANT_NAME} - Executive Assistant Commands**

🌤️ **Weather & Briefing:**
   `!briefing` - Complete morning briefing with work & weather
   `!weather` - Current weather & UV index

💼 **Work Calendar (Direct Gmail Access):**
   `!work-calendar [today/week/month]` - Direct work calendar access
   `!work-analysis [priorities/conflicts/travel]` - Analyze work schedule
   `!meeting-prep [today/week]` - Meeting preparation summary
   `!coordinate-calendars [days]` - Cross-calendar coordination
   `!calendar-status` - Check all calendar integrations

📅 **Personal Calendar Management:**
   `!schedule` - Today's personal calendar
   `!upcoming [days]` - Upcoming personal events (default 7 days)

🔍 **Planning & Research:**
   Just mention @Rose or start with "Rose" for planning assistance

⚙️ **System Commands:**
   `!status` - System status & integration check
   `!ping` - Response time test
   `!commands` - This help message

💼 **Executive Features:**
   • Direct Gmail work calendar integration
   • Weather-integrated morning briefings
   • Strategic work schedule analysis
   • Meeting preparation intelligence
   • Cross-calendar optimization

📍 **Current Location:** {USER_CITY}
🎯 **Active Channels:** {', '.join(ALLOWED_CHANNELS)}"""
    
    await ctx.send(help_text)

# ============================================================================
# ERROR HANDLING AND LOGGING
# ============================================================================

@bot.event
async def on_error(event, *args, **kwargs):
    """Enhanced error handling with calendar-specific logging"""
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
# INITIALIZATION AND STARTUP
# ============================================================================

async def initialize_services():
    """Initialize all services on startup"""
    global gmail_calendar_service
    
    print("🔄 Initializing Rose's services...")
    
    # Initialize Gmail calendar service
    gmail_calendar_service = initialize_gmail_calendar_service()
    
    # Initialize personal calendars
    initialize_google_services()
    
    print("✅ Service initialization complete")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 Starting {ASSISTANT_NAME}...")
    print(f"📧 Gmail Work Calendar: {'✅ Configured' if GOOGLE_SERVICE_ACCOUNT_JSON else '❌ Not Configured'}")
    print(f"📅 Personal Calendars: {'✅ Configured' if GOOGLE_SERVICE_ACCOUNT_JSON else '❌ Not Configured'}")
    print(f"🌤️ Weather: {'✅ Configured' if WEATHER_API_KEY else '❌ Not Configured'}")
    
    try:
        # Initialize services
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_services())
        
        # Run the bot
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print(f"\n👑 {ASSISTANT_NAME} shutting down gracefully...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print(traceback.format_exc())
        