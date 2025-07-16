#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (ENHANCED CALENDAR DEBUG)
Executive Assistant with Enhanced Error Handling, Planning & Calendar Functions
ENHANCED: Better calendar debugging, error handling, and iCloud calendar support
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
ASSISTANT_ROLE = "Executive Assistant (Enhanced Calendar Debug)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

# Enhanced Google Calendar setup with comprehensive error handling
calendar_service = None
accessible_calendars = []
service_account_email = None

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
            
            print(f"   • {summary}")
            print(f"     ID: {cal_id}")
            print(f"     Access: {access_role}")
            
            # Identify imported calendars
            if 'import.calendar.google.com' in cal_id:
                print(f"     🍎 Imported calendar (likely iCloud)")
            elif cal_id == 'primary':
                print(f"     📅 Primary Google Calendar")
            elif '@group.calendar.google.com' in cal_id:
                print(f"     👥 Shared Google Calendar")
            
            calendars.append((summary, cal_id, access_role))
            print()
        
        return calendars
        
    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return []

def test_calendar_access(calendar_id, calendar_name):
    """Enhanced calendar testing with better error messages"""
    if not calendar_service or not calendar_id:
        return False
    
    try:
        # Test calendar metadata
        calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ {calendar_name} metadata retrieved")
        
        # Test event access with recent events
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
        print(f"✅ {calendar_name} events retrieved: {len(events)} events")
        
        # Additional check: try to get calendar's access role
        calendar_list = calendar_service.calendarList().list().execute()
        for cal in calendar_list.get('items', []):
            if cal['id'] == calendar_id:
                access_role = cal.get('accessRole', 'unknown')
                print(f"📋 {calendar_name} access role: {access_role}")
                break
        
        return True
        
    except HttpError as e:
        error_code = e.resp.status
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        
        print(f"❌ {calendar_name} HTTP Error {error_code}: {error_details}")
        
        if error_code == 404:
            print(f"💡 {calendar_name}: Calendar not found - check ID format")
            print(f"   ID used: {calendar_id}")
        elif error_code == 403:
            print(f"💡 {calendar_name}: Permission denied")
            print(f"   Suggestion: Share calendar with service account")
        elif error_code == 400:
            print(f"💡 {calendar_name}: Bad request - malformed calendar ID")
        
        return False
        
    except Exception as e:
        print(f"❌ {calendar_name} unexpected error: {e}")
        print(f"   Exception type: {type(e).__name__}")
        return False

# Initialize Google Calendar service with enhanced debugging
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized")
        
        # Get service account email for sharing instructions
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account Email: {service_account_email}")
        print(f"💡 Share calendars with this email for access")
        
        # List all accessible calendars first
        all_calendars = get_all_accessible_calendars()
        
        # Test specific calendars
        calendars_to_test = [
            ("BG Calendar", GOOGLE_CALENDAR_ID),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID),
            ("Britt iCloud", BRITT_ICLOUD_CALENDAR_ID)
        ]
        
        accessible_calendars = []
        
        for name, calendar_id in calendars_to_test:
            if calendar_id and test_calendar_access(calendar_id, name):
                # Determine calendar type
                if "task" in name.lower():
                    accessible_calendars.append((name, calendar_id, "tasks"))
                elif "britt" in name.lower():
                    accessible_calendars.append((name, calendar_id, "britt"))
                else:
                    accessible_calendars.append((name, calendar_id, "calendar"))
        
        # If no calendars work, try primary as fallback
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary", "calendar"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _, _ in accessible_calendars:
            print(f"   ✅ {name}")
        
        if not accessible_calendars:
            print("❌ No accessible calendars found")
            print("💡 Next steps:")
            print("   1. Check service account email above")
            print("   2. Share calendars with service account")
            print("   3. Verify calendar IDs are correct")
            
    else:
        print("⚠️ Google Calendar credentials not found")
        
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
# ENHANCED CALENDAR FUNCTIONS WITH ROBUST ERROR HANDLING
# ============================================================================

def get_calendar_events(calendar_id, start_time, end_time, max_results=100):
    """Helper function to get events from a specific calendar with comprehensive error handling"""
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
        print(f"📅 Retrieved {len(events)} events from {calendar_id}")
        return events
        
    except HttpError as e:
        print(f"❌ HTTP Error getting events from {calendar_id}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error getting events from {calendar_id}: {e}")
        return []

def format_event(event, calendar_type="", user_timezone=None):
    """Helper function to format a single event with proper Toronto timezone"""
    if user_timezone is None:
        user_timezone = pytz.timezone('America/Toronto')
    
    start = event['start'].get('dateTime', event['start'].get('date'))
    title = event.get('summary', 'Untitled Event')
    
    # Add calendar indicator with better visibility
    if calendar_type == "tasks":
        title = f"✅ {title}"
    elif calendar_type == "britt":
        title = f"🍎 {title}"
    elif calendar_type == "calendar":
        title = f"📅 {title}"
    
    if 'T' in start:  # Has time
        try:
            # Parse UTC time and convert to Toronto timezone
            utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = utc_time.astimezone(user_timezone)
            time_str = local_time.strftime('%I:%M %p')
            return f"• {time_str}: {title}"
        except Exception as e:
            print(f"❌ Error formatting timed event: {e}")
            return f"• {title}"
    else:  # All day event
        return f"• All Day: {title}"

def get_today_schedule():
    """Get today's schedule from all accessible calendars with Toronto timezone handling"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Today's Schedule:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps directly and prioritize your day"
    
    try:
        # Use Toronto timezone
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today in Toronto timezone
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto.replace(hour=23, minute=59, second=59)
        
        # Convert to UTC for Google Calendar API
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
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Today's Schedule:** No events found\n\n🎯 **Executive Opportunity:** Clear schedule across {calendar_list} - perfect for deep work and strategic planning"
        
        # Sort all events by start time
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
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Upcoming {days} Days:** No events found\n\n🎯 **Strategic Opportunity:** Clear schedule across {calendar_list} - focus on long-term planning"
        
        # Group by date using Toronto timezone
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
        
        for date, day_events in list(events_by_date.items())[:7]:  # Limit to 7 days for Discord
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:6])  # Limit events per day for readability
        
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
        print(f"📋 Calendar traceback: {traceback.format_exc()}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Comprehensive morning briefing with Toronto timezone handling"""
    if not calendar_service or not accessible_calendars:
        return "🌅 **Morning Briefing:** Calendar integration not available\n\n📋 **Manual Planning:** Review your calendar apps and prioritize your day"
    
    try:
        # Use Toronto timezone for proper date calculation
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today's full schedule
        today_schedule = get_today_schedule()
        
        # Get tomorrow's preview using Toronto timezone
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
        
        # Combine into morning briefing with correct Toronto date
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        briefing = f"🌅 **Good Morning! Executive Briefing for {current_time}**\n\n{today_schedule}\n\n{tomorrow_preview}\n\n💼 **Executive Focus:** Prioritize high-impact activities during peak energy hours"
        
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
                output = get_morning_briefing()
                
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
        
        # Enhanced message with executive planning focus
        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- SMART CALENDAR DETECTION: Automatically detect if this is a general or specific calendar query
- GENERAL CALENDAR QUERIES (auto-include full schedule): "what's on my calendar", "what's my schedule", "what do I have today", "how does my day look", "what's happening today"
- SPECIFIC CALENDAR QUERIES (answer directly): "what do I have after 5pm", "am I free at 2pm", "what's my first meeting", "when is my next call"
- When using calendar functions, provide insights from accessible calendars
- For planning research, include actionable productivity recommendations
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- IMPORTANT: Always provide strategic context and actionable next steps
- All times are in Toronto timezone (America/Toronto)"""
        
        try:
            # Fixed API call - removed deprecation warning
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