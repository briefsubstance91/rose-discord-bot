#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE DISCORD BOT WITH CALENDAR INTEGRATION
Executive Assistant with Calendar Management, Email Management, and Strategic Planning
FIXED VERSION - All syntax errors resolved
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
ASSISTANT_ROLE = "Executive Assistant"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Enhanced calendar and email integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')
BRITT_ICLOUD_CALENDAR_ID = os.getenv('BRITT_ICLOUD_CALENDAR_ID')

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

# Weather API configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

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

def initialize_google_services():
    """Initialize Google Calendar and Gmail services"""
    global calendar_service, gmail_service
    
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
    if not calendar_service:
        return
    
    calendars_to_test = [
        ('primary', '🐝 BG Personal'),
        (GOOGLE_CALENDAR_ID, '📆 BG Calendar'),
        (GOOGLE_TASKS_CALENDAR_ID, '✅ BG Tasks'),
        (BRITT_ICLOUD_CALENDAR_ID, 'Britt'),
        ('brittgelineau@gmail.com', '💼 BG Work')
    ]
    
    accessible_calendars = []
    
    for calendar_id, calendar_name in calendars_to_test:
        if not calendar_id:
            continue
            
        try:
            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=datetime.utcnow().isoformat() + 'Z',
                maxResults=1,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            accessible_calendars.append((calendar_id, calendar_name))
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
# ENHANCED FUNCTION HANDLING WITH CALENDAR SUPPORT
# ============================================================================

def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handler for Rose's capabilities including calendar functions"""
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
            
            # Web search function
            elif function_name == "web_search":
                query = arguments.get('query', '')
                result = web_search(query) if BRAVE_API_KEY else "Web search not available - API key missing"
            
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
                await message.reply(response)
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
# DISCORD BOT COMMANDS
# ============================================================================

@bot.command(name='ping')
async def ping(ctx):
    """Test bot connectivity and response time"""
    try:
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Status",
            description="Executive Assistant operational status",
            color=0xE91E63
        )
        embed.add_field(name="🏓 Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="📅 Calendar", value="✅ Ready" if calendar_service else "❌ Offline", inline=True)
        embed.add_field(name="🔍 Search", value="✅ Ready" if BRAVE_API_KEY else "❌ Offline", inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Ping command error: {e}")

@bot.command(name='status')
async def status(ctx):
    """Show comprehensive Rose status"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration",
            color=0xE91E63
        )
        
        # Core capabilities
        embed.add_field(
            name="📅 Calendar Management",
            value="✅ Create, update, delete events" if calendar_service else "❌ Not available",
            inline=True
        )
        
        embed.add_field(
            name="🔍 Planning Research",
            value="✅ Available" if BRAVE_API_KEY else "❌ Not configured",
            inline=True
        )
        
        embed.add_field(
            name="🌤️ Weather Integration",
            value="✅ Available" if WEATHER_API_KEY else "❌ Not configured",
            inline=True
        )
        
        # Specialties
        specialties_text = "\n".join([
            "• 📅 Executive Planning",
            "• 🗓️ Calendar Management", 
            "• 📊 Productivity Systems",
            "• ⚡ Time Optimization",
            "• 🎯 Life OS Strategy"
        ])
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
    """Show Rose's help information"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Strategic planning specialist with calendar integration and productivity optimization",
            color=0xE91E63
        )
        
        # How to use
        embed.add_field(
            name="💬 How to Use",
            value="• Mention @Rose Ashcombe for executive assistance\n• Use commands below for specific functions\n• I monitor: #life-os, #calendar, #planning-hub, #general",
            inline=False
        )
        
        # Commands
        commands_text = "\n".join([
            "• !ping - Test connectivity",
            "• !status - Show comprehensive status",
            "• !help - Show this help message"
        ])
        embed.add_field(
            name="🔧 Commands",
            value=commands_text,
            inline=False
        )
        
        # Example requests
        examples_text = "\n".join([
            "• @Rose help me plan my week strategically",
            "• @Rose create a meeting for tomorrow at 2pm",
            "• @Rose what's the best time blocking method?",
            "• @Rose schedule a planning session"
        ])
        embed.add_field(
            name="✨ Example Requests",
            value=examples_text,
            inline=False
        )
        
        # Core capabilities
        capabilities_text = "\n".join([
            "• Calendar event creation and management",
            "• Strategic planning and productivity research",
            "• Time blocking and scheduling optimization",
            "• Executive workflow coordination",
            "• Life OS strategy implementation"
        ])
        embed.add_field(
            name="🎯 Core Capabilities",
            value=capabilities_text,
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"❌ Help command error: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 Starting {ASSISTANT_NAME} Enhanced Executive Assistant...")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        exit(1)