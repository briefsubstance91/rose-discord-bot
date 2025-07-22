#!/usr/bin/env python3
"""
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
ASSISTANT_ROLE = "Executive Assistant (Work + Personal Calendar)"
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

# Enhanced calendar integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

# Work calendar configuration (separate)
GMAIL_WORK_CALENDAR_ID = os.getenv('GMAIL_WORK_CALENDAR_ID', 'primary')

# Personal calendar configuration (preserved as original)
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
work_calendar_service = None  # NEW: Separate work calendar service
active_runs = {}

# ============================================================================
# WORK CALENDAR INTEGRATION FUNCTIONS (NEW)
# ============================================================================

def initialize_work_calendar_service():
    """Initialize work calendar service (separate from personal calendars)"""
    global work_calendar_service
    
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("⚠️ Work calendar credentials not configured")
        return None
    
    try:
        # Parse the JSON credentials for work calendar
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        
        # Build work calendar service
        work_calendar_service = build('calendar', 'v3', credentials=credentials)
        
        # Test work calendar access
        try:
            calendar_id = GMAIL_WORK_CALENDAR_ID
            work_calendar_service.events().list(
                calendarId=calendar_id,
                maxResults=1,
                timeMin=datetime.now().isoformat() + 'Z'
            ).execute()
            print(f"✅ Work Calendar (Gmail) accessible - {calendar_id}")
            return work_calendar_service
        except Exception as e:
            print(f"❌ Work Calendar inaccessible: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Work Calendar initialization error: {e}")
        return None

def get_work_events_for_briefing(days_ahead=1):
    """Get work events specifically for briefings (minimal function)"""
    if not work_calendar_service:
        return {"error": "Work calendar service not available"}
    
    try:
        # Set timezone to Toronto
        tz = timezone(timedelta(hours=-4))  # EDT (adjust for EST/EDT as needed)
        
        # Get today's work events
        start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=days_ahead)
        
        # Query work calendar
        events_result = work_calendar_service.events().list(
            calendarId=GMAIL_WORK_CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=20
        ).execute()
        
        events = events_result.get('items', [])
        
        work_events = []
        for event in events:
            summary = event.get('summary', 'No title')
            start = event.get('start', {})
            
            if 'dateTime' in start:
                try:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    formatted_time = start_dt.strftime("%I:%M %p")
                except:
                    formatted_time = "Time TBD"
            else:
                formatted_time = "All day"
            
            work_events.append({
                'summary': summary,
                'time': formatted_time,
                'raw_start': start
            })
        
        return {
            "success": True,
            "events": work_events,
            "count": len(work_events)
        }
        
    except Exception as e:
        return {"error": f"Error accessing work calendar: {e}"}

# ============================================================================
# WEATHER INTEGRATION FUNCTIONS (PRESERVED)
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
# PERSONAL CALENDAR FUNCTIONS (PRESERVED UNCHANGED)
# ============================================================================

def initialize_google_services():
    """Initialize Google Calendar services for personal calendars (BG Tasks, BG Calendar, Britt iCloud)"""
    global google_services_initialized, accessible_calendars
    
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("⚠️ Personal calendar credentials not configured")
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
            ('BG Calendar', GOOGLE_CALENDAR_ID),
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
            print(f"✅ Personal Calendar service initialized with {len(accessible_calendars)} accessible calendars")
            return service
        else:
            print("❌ No accessible personal calendars found")
            return None
            
    except Exception as e:
        print(f"❌ Personal Calendar initialization error: {e}")
        return None

def get_today_schedule():
    """Get today's calendar events from personal calendars (BG Tasks & BG Calendar)"""
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
        
        # Fetch events from all accessible personal calendars
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
    """Get upcoming events from personal calendars (BG Tasks & BG Calendar)"""
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
        
        # Fetch events from all accessible personal calendars
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
# ENHANCED BRIEFING FUNCTION (PRESERVES EXISTING + ADDS WORK)
# ============================================================================

async def get_morning_briefing():
    """Enhanced morning briefing - preserves personal calendar + adds work calendar"""
    briefing = f"👑 **Executive Morning Briefing** - {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
    
    # Weather section (unchanged)
    weather = await get_weather_briefing()
    if isinstance(weather, dict):
        briefing += f"🌤️ **Weather Update ({weather['location']})**: {weather['temperature']}°C {weather['emoji']} {weather['condition']}\n"
        briefing += f"🌡️ Feels like: {weather['feels_like']}°C | Humidity: {weather['humidity']}%\n"
        briefing += f"🔆 UV Index: {weather['uv_index']} - {weather['uv_advisory']}\n\n"
    else:
        briefing += f"{weather}\n\n"
    
    # NEW: Work calendar section (added functionality)
    if work_calendar_service:
        work_events = get_work_events_for_briefing(days_ahead=1)
        if work_events and 'error' not in work_events:
            briefing += f"💼 **Work Calendar**: {work_events['count']} work meetings\n"
            
            if work_events['events']:
                for event in work_events['events']:
                    briefing += f"   💼 {event['time']}: {event['summary']}\n"
                briefing += "\n"
            else:
                briefing += "   ✅ No work meetings scheduled for today.\n\n"
        else:
            briefing += f"💼 **Work Calendar**: ⚠️ Unable to access work calendar\n\n"
    else:
        briefing += "💼 **Work Calendar**: ⚠️ Not configured\n\n"
    
    # PRESERVED: Personal calendar section (unchanged from original Rose)
    personal_schedule = get_today_schedule()  # This is your existing function
    if "No events scheduled" not in personal_schedule and "Calendar integration not available" not in personal_schedule:
        # Show personal calendar section
        briefing += "📅 **Personal Calendar (BG Tasks & BG Calendar)**: Events scheduled\n"
        # Extract just the events, not the full header
        events_part = personal_schedule.split('\n\n', 1)
        if len(events_part) > 1:
            briefing += f"{events_part[1]}\n"
    else:
        briefing += "📅 **Personal Calendar (BG Tasks & BG Calendar)**: No personal events scheduled\n\n"
    
    # Strategic recommendations (unchanged)
    briefing += "📋 **Strategic Focus**: Balance work priorities with personal commitments and weather conditions.\n"
    
    return briefing

# ============================================================================
# SIMPLE WORK CALENDAR COMMANDS (NEW - OPTIONAL)
# ============================================================================

async def handle_work_calendar_commands(message):
    """Handle simple work calendar commands (optional addition)"""
    
    if message.content.startswith('!work-today'):
        if work_calendar_service:
            work_events = get_work_events_for_briefing(days_ahead=1)
            if work_events and 'error' not in work_events:
                response = f"💼 **Today's Work Calendar**: {work_events['count']} meetings\n\n"
                
                if work_events['events']:
                    for event in work_events['events']:
                        response += f"💼 {event['time']}: {event['summary']}\n"
                else:
                    response += "✅ No work meetings scheduled for today.\n"
                
                await message.reply(response)
            else:
                await message.reply(f"💼 **Work Calendar Error**: {work_events.get('error', 'Unable to access')}")
        else:
            await message.reply("💼 **Work Calendar**: Not configured")
        return True
    
    return False  # Command not handled

# ============================================================================
# OPENAI ASSISTANT INTERACTION (PRESERVED)
# ============================================================================

async def get_rose_response(message_content, user_id):
    """Get response from Rose's OpenAI assistant"""
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
        
        # Wait for completion
        max_wait = 45  # seconds
        start_time = time.time()
        
        while run.status in ['queued', 'in_progress']:
            if time.time() - start_time > max_wait:
                active_runs.pop(user_id, None)
                return "👑 Rose: Request timeout. Please try again with a simpler query."
            
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
# DISCORD EVENT HANDLERS (ENHANCED)
# ============================================================================

@bot.event
async def on_ready():
    """Enhanced startup message with work + personal calendar status"""
    print(f"✅ {ASSISTANT_NAME} is online!")
    print(f"🤖 Connected as {bot.user} (ID: {bot.user.id})")
    print(f"💼 Work Calendar Status: {'✅ Integrated' if work_calendar_service else '❌ Not Available'}")
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
    """Enhanced message handler with work calendar commands"""
    # Ignore bot messages
    if message.author == bot.user:
        return
    
    # Check if message is in allowed channels
    if message.channel.name not in ALLOWED_CHANNELS:
        return
    
    # Handle work calendar commands FIRST (optional)
    if await handle_work_calendar_commands(message):
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

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Enhanced briefing with work calendar integration"""
    async with ctx.typing():
        result = await get_morning_briefing()
        
        if len(result) <= 2000:
            await ctx.send(result)
        else:
            # Split into chunks
            chunks = [result[i:i+2000] for i in range(0, len(result), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
                await asyncio.sleep(0.5)

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

@bot.command(name='work-today')
async def work_today_command(ctx):
    """Get today's work calendar (new command)"""
    async with ctx.typing():
        if work_calendar_service:
            work_events = get_work_events_for_briefing(days_ahead=1)
            if work_events and 'error' not in work_events:
                response = f"💼 **Today's Work Calendar**: {work_events['count']} meetings\n\n"
                
                if work_events['events']:
                    for event in work_events['events']:
                        response += f"💼 {event['time']}: {event['summary']}\n"
                else:
                    response += "✅ No work meetings scheduled for today.\n"
                
                await ctx.send(response)
            else:
                await ctx.send(f"💼 **Work Calendar Error**: {work_events.get('error', 'Unable to access')}")
        else:
            await ctx.send("💼 **Work Calendar**: Not configured")

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's personal calendar schedule"""
    async with ctx.typing():
        schedule = get_today_schedule()
        await ctx.send(schedule)

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Get upcoming personal events (default 7 days)"""
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
    """Enhanced status including work calendar integration"""
    status_report = f"""👑 **{ASSISTANT_NAME} System Status**

🤖 **OpenAI Assistant:** {'✅ Connected' if ASSISTANT_ID else '❌ Not Configured'}
💼 **Work Calendar (Gmail):** {'✅ Active' if work_calendar_service else '❌ Inactive'}
📅 **Personal Calendars (BG):** {'✅ Active' if google_services_initialized else '❌ Inactive'}
🌤️ **Weather API:** {'✅ Configured' if WEATHER_API_KEY else '❌ Not Configured'}
🔍 **Planning Search:** {'✅ Available' if BRAVE_API_KEY else '❌ Not Available'}

📊 **Calendar Access:**
   • Work Calendar: {'✅ Gmail integrated' if work_calendar_service else '❌ Not available'}
   • Personal Calendars: {len(accessible_calendars) if accessible_calendars else 0} (BG Tasks, BG Calendar, Britt iCloud)

🎯 **Active Channels:** {', '.join(ALLOWED_CHANNELS)}
⚡ **Active Runs:** {len(active_runs)}

💼 **Enhanced Features:**
   • Morning briefings with work + personal calendars
   • Weather integration
   • Strategic daily focus
   • Work-life balance optimization"""
    
    await ctx.send(status_report)

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's responsiveness"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"👑 Rose responding in {latency}ms")

@bot.command(name='commands')
async def commands_command(ctx):
    """Enhanced help showing work calendar integration"""
    help_text = f"""👑 **{ASSISTANT_NAME} - Executive Assistant Commands**

🌤️ **Enhanced Briefing:**
   `!briefing` - Complete briefing (weather + work calendar + personal calendar)
   `!weather` - Current weather & UV index

💼 **Work Calendar (New!):**
   `!work-today` - Today's work meetings (direct Gmail access)

📅 **Personal Calendar Management (BG Tasks & BG Calendar):**
   `!schedule` - Today's personal calendar
   `!upcoming [days]` - Upcoming personal events (default 7 days)

🔍 **Planning & Research:**
   Just mention @Rose or start with "Rose" for planning assistance

⚙️ **System Commands:**
   `!status` - System status & integration check
   `!ping` - Response time test
   `!commands` - This help message

💼 **NEW: Work Calendar Integration:**
   • Morning briefings now include work calendar events
   • Direct Gmail calendar access (no Vivian dependency)
   • Work-personal calendar balance in briefings

📅 **Personal Calendar Features (Preserved):**
   • BG Tasks and BG Calendar grouped together
   • Britt iCloud calendar included
   • All existing functionality maintained

📍 **Current Location:** {USER_CITY}
🎯 **Active Channels:** {', '.join(ALLOWED_CHANNELS)}"""
    
    await ctx.send(help_text)

# ============================================================================
# ERROR HANDLING AND LOGGING (PRESERVED)
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
# INITIALIZATION AND STARTUP (ENHANCED)
# ============================================================================

async def initialize_services():
    """Initialize all services on startup - enhanced with work calendar"""
    global work_calendar_service
    
    print("🔄 Initializing Rose's services...")
    
    # KEEP existing personal calendar initialization
    initialize_google_services()  # Your existing function - don't change
    
    # ADD work calendar initialization
    work_calendar_service = initialize_work_calendar_service()
    
    print("✅ Service initialization complete")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 Starting {ASSISTANT_NAME}...")
    print(f"💼 Work Calendar (Gmail): {'✅ Configured' if GOOGLE_SERVICE_ACCOUNT_JSON else '❌ Not Configured'}")
    print(f"📅 Personal Calendars (BG): {'✅ Configured' if GOOGLE_SERVICE_ACCOUNT_JSON else '❌ Not Configured'}")
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