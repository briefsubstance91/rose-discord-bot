#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (COMPLETE WITH GMAIL OAUTH INTEGRATION)
Executive Assistant with Full Google Calendar API Integration, Gmail OAuth Management & Advanced Task Management
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
ASSISTANT_ROLE = "Executive Assistant (Complete Enhanced with Gmail OAuth)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Calendar & Gmail integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')

# Gmail OAuth setup
GMAIL_OAUTH_JSON = os.getenv('GMAIL_OAUTH_JSON')
GMAIL_TOKEN_JSON = os.getenv('GMAIL_TOKEN_JSON')  # New: Token from environment variable
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

# Discord setup
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
except Exception as e:
    print(f"❌ CRITICAL: Discord bot initialization failed: {e}")
    exit(1)

# OpenAI setup
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"❌ CRITICAL: OpenAI client initialization failed: {e}")
    exit(1)

# Google Calendar & Gmail setup
calendar_service = None
gmail_service = None
accessible_calendars = []
service_account_email = None

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
        return gmail_service
        
    except Exception as e:
        print(f"❌ Gmail OAuth setup error: {e}")
        return None

def test_calendar_access(calendar_id, calendar_name):
    """Test calendar access with comprehensive error handling"""
    if not calendar_service or not calendar_id:
        return False
    
    try:
        calendar_info = calendar_service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ {calendar_name} accessible")
        
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
        error_code = e.resp.status
        print(f"❌ {calendar_name} HTTP Error {error_code}")
        return False
    except Exception as e:
        print(f"❌ {calendar_name} error: {e}")
        return False

# Initialize Google Calendar & Gmail services
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        # Calendar setup (keep existing service account for calendar)
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar'
                # ✅ Removed Gmail scopes - OAuth handles Gmail separately
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized")
        
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account: {service_account_email}")
        
        working_calendars = [
            ("BG Calendar", GOOGLE_CALENDAR_ID, "calendar"),
            ("BG Tasks", GOOGLE_TASKS_CALENDAR_ID, "tasks")
        ]
        
        for name, calendar_id, calendar_type in working_calendars:
            if calendar_id and test_calendar_access(calendar_id, name):
                accessible_calendars.append((name, calendar_id, calendar_type))
        
        if not accessible_calendars:
            print("⚠️ No configured calendars accessible, testing primary...")
            if test_calendar_access('primary', "Primary"):
                accessible_calendars.append(("Primary", "primary", "calendar"))
        
        print(f"\n📅 Final accessible calendars: {len(accessible_calendars)}")
        for name, _, _ in accessible_calendars:
            print(f"   ✅ {name}")
    
    # Gmail setup (separate OAuth for personal Gmail)
    print("\n📧 Setting up Gmail OAuth...")
    gmail_service = setup_gmail_oauth()
    if gmail_service:
        print("✅ Gmail integration ready")
    else:
        print("⚠️ Gmail integration disabled")
            
except Exception as e:
    print(f"❌ Google services setup error: {e}")
    calendar_service = None
    gmail_service = None
    accessible_calendars = []

# Memory and duplicate prevention systems
user_conversations = {}
processing_messages = set()
last_response_time = {}

print(f"👑 Starting {ASSISTANT_NAME} - {ASSISTANT_ROLE}...")

# ============================================================================
# CORE CALENDAR FUNCTIONS
# ============================================================================

def get_calendar_events(calendar_id, start_time, end_time, max_results=100):
    """Get events from a specific calendar"""
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
    
    if calendar_type == "tasks":
        title = f"✅ {title}"
    elif calendar_type == "calendar":
        title = f"📅 {title}"
    
    if 'T' in start:  # Has time
        try:
            utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = utc_time.astimezone(user_timezone)
            time_str = local_time.strftime('%H:%M')  # 24-hour format
            return f"• {time_str}: {title}"
        except Exception as e:
            print(f"❌ Error formatting event: {e}")
            return f"• {title}"
    else:  # All day event
        return f"• All Day: {title}"

def get_today_schedule():
    """Get today's schedule with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return "📅 **Today's Schedule:** Calendar integration not available\n\n🎯 **Manual Planning:** Review your calendar apps directly"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto.replace(hour=23, minute=59, second=59)
        
        today_utc = today_toronto.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, today_utc, tomorrow_utc)
            for event in events:
                formatted = format_event(event, calendar_type, toronto_tz)
                all_events.append((event, formatted, calendar_type, calendar_name))
        
        if not all_events:
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Today's Schedule:** No events found\n\n🎯 **Executive Opportunity:** Clear schedule across {calendar_list}"
        
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
        
        formatted_events = [event_tuple[1] for event_tuple in all_events]
        
        calendar_counts = {}
        for _, _, calendar_type, calendar_name in all_events:
            calendar_counts[calendar_name] = calendar_counts.get(calendar_name, 0) + 1
        
        header = f"📅 **Today's Executive Schedule:** {len(all_events)} events"
        
        if calendar_counts:
            breakdown = []
            for calendar_name, count in calendar_counts.items():
                breakdown.append(f"{count} {calendar_name}")
            header += f" ({', '.join(breakdown)})"
        
        return header + "\n\n" + "\n".join(formatted_events[:15])
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data"

def get_upcoming_events(days=7):
    """Get upcoming events with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return f"📅 **Upcoming {days} Days:** Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        start_toronto = datetime.now(toronto_tz)
        end_toronto = start_toronto + timedelta(days=days)
        
        start_utc = start_toronto.astimezone(pytz.UTC)
        end_utc = end_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, start_utc, end_utc)
            for event in events:
                all_events.append((event, calendar_type, calendar_name))
        
        if not all_events:
            calendar_list = ", ".join([name for name, _, _ in accessible_calendars])
            return f"📅 **Upcoming {days} Days:** No events found"
        
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
        
        formatted = []
        total_events = len(all_events)
        
        for date, day_events in list(events_by_date.items())[:7]:
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:6])
        
        header = f"📅 **Upcoming {days} Days:** {total_events} total events"
        
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Morning briefing with enhanced formatting"""
    if not calendar_service or not accessible_calendars:
        return "🌅 **Morning Briefing:** Calendar integration not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        today_schedule = get_today_schedule()
        
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto + timedelta(days=1)
        day_after_toronto = tomorrow_toronto + timedelta(days=1)
        
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        day_after_utc = day_after_toronto.astimezone(pytz.UTC)
        
        tomorrow_events = []
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, tomorrow_utc, day_after_utc)
            tomorrow_events.extend([(event, calendar_type, calendar_name) for event in events])
        
        if tomorrow_events:
            tomorrow_formatted = []
            for event, calendar_type, calendar_name in tomorrow_events[:4]:
                formatted = format_event(event, calendar_type, toronto_tz)
                tomorrow_formatted.append(formatted)
            tomorrow_preview = "📅 **Tomorrow Preview:**\n" + "\n".join(tomorrow_formatted)
        else:
            tomorrow_preview = "📅 **Tomorrow Preview:** Clear schedule - strategic planning day"
        
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        briefing = f"🌅 **Good Morning! Executive Briefing for {current_time}**\n\n{today_schedule}\n\n{tomorrow_preview}\n\n💼 **Executive Focus:** Prioritize high-impact activities"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        return "🌅 **Morning Briefing:** Error generating briefing"

def reschedule_event(event_search, new_start_time, new_end_time=None):
    """Reschedule an existing calendar event to new time"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Find the event
        found_event, found_calendar_id, found_calendar_name = find_calendar_event(event_search)
        
        if not found_event:
            return f"❌ '{event_search}' not found"
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Parse new start time
        try:
            if "T" not in new_start_time:
                original_time = found_event['start']['dateTime'].split('T')[1] if 'dateTime' in found_event['start'] else '15:00:00'
                new_start_time = f"{new_start_time}T{original_time}"
            
            new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', ''))
            if new_start_dt.tzinfo is None:
                new_start_dt = toronto_tz.localize(new_start_dt)
                
        except ValueError:
            return "❌ Invalid time format"
        
        # Calculate new end time
        if new_end_time:
            try:
                if "T" not in new_end_time:
                    original_time = found_event['end']['dateTime'].split('T')[1] if 'dateTime' in found_event['end'] else '16:00:00'
                    new_end_time = f"{new_end_time}T{original_time}"
                new_end_dt = datetime.fromisoformat(new_end_time.replace('Z', ''))
                if new_end_dt.tzinfo is None:
                    new_end_dt = toronto_tz.localize(new_end_dt)
            except ValueError:
                return "❌ Invalid end time format"
        else:
            # Calculate duration from original event
            original_start = datetime.fromisoformat(found_event['start']['dateTime'].replace('Z', '+00:00'))
            original_end = datetime.fromisoformat(found_event['end']['dateTime'].replace('Z', '+00:00'))
            duration = original_end - original_start
            new_end_dt = new_start_dt + duration
        
        # Update the event
        found_event['start'] = {
            'dateTime': new_start_dt.isoformat(),
            'timeZone': 'America/Toronto',
        }
        found_event['end'] = {
            'dateTime': new_end_dt.isoformat(),
            'timeZone': 'America/Toronto',
        }
        
        updated_event = calendar_service.events().update(
            calendarId=found_calendar_id,
            eventId=found_event['id'],
            body=found_event
        ).execute()
        
        # Concise confirmation with 24-hour time
        display_start_dt = new_start_dt.astimezone(toronto_tz)
        display_end_dt = new_end_dt.astimezone(toronto_tz)
        
        day_date = display_start_dt.strftime('%A, %B %d')
        start_time_24h = display_start_dt.strftime('%H:%M')
        end_time_24h = display_end_dt.strftime('%H:%M')
        
        return f"✅ **{updated_event['summary']}** rescheduled\n📅 {day_date}, {start_time_24h} - {end_time_24h}\n🗓️ {found_calendar_name}\n🔗 [View Event]({updated_event.get('htmlLink', '#')})"
        
    except Exception as e:
        print(f"❌ Error rescheduling event: {e}")
        return f"❌ Failed to reschedule '{event_search}': {str(e)}"

def find_calendar_event(search_term, days_range=30):
    """Find calendar events matching a search term"""
    if not calendar_service or not accessible_calendars:
        return None, None, None
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        past_search = now - timedelta(days=7)
        future_search = now + timedelta(days=days_range)
        
        for calendar_name, calendar_id, calendar_type in accessible_calendars:
            events = get_calendar_events(calendar_id, past_search, future_search, max_results=200)
            for event in events:
                event_title = event.get('summary', '').lower()
                if search_term.lower() in event_title:
                    return event, calendar_id, calendar_name
        
        return None, None, None
        
    except Exception as e:
        print(f"❌ Error finding event: {e}")
        return None, None, None

# ============================================================================
# CORE GMAIL FUNCTIONS
# ============================================================================

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
            return f"📧 **Recent Emails:** No emails found for query: {query}"
        
        formatted_emails = []
        
        for message in messages[:count]:
            msg = gmail_service.users().messages().get(
                userId='me',
                id=message['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            
            from_email = headers.get('From', 'Unknown')
            subject = headers.get('Subject', 'No Subject')
            date_str = headers.get('Date', '')
            
            try:
                if date_str:
                    date_obj = parsedate_to_datetime(date_str)
                    toronto_tz = pytz.timezone('America/Toronto')
                    local_date = date_obj.astimezone(toronto_tz)
                    formatted_date = local_date.strftime('%m/%d %H:%M')
                else:
                    formatted_date = 'Unknown'
            except:
                formatted_date = 'Unknown'
            
            labels = msg.get('labelIds', [])
            unread_indicator = "🔴 " if 'UNREAD' in labels else ""
            
            formatted_emails.append(f"{unread_indicator}**{formatted_date}** | {from_email}\n📝 {subject}")
        
        return f"📧 **Recent Emails ({len(formatted_emails)}):**\n\n" + "\n\n".join(formatted_emails)
        
    except Exception as e:
        print(f"❌ Gmail error: {e}")
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
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ **Email Sent Successfully**\n📧 To: {to_email}\n📝 Subject: {subject}\n🆔 Message ID: {sent_message['id']}"
        
    except Exception as e:
        print(f"❌ Send email error: {e}")
        return f"❌ Failed to send email: {str(e)}"

def get_email_stats():
    """Get email dashboard statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        unread_results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = unread_results.get('resultSizeEstimate', 0)
        
        toronto_tz = pytz.timezone('America/Toronto')
        today_results = gmail_service.users().messages().list(
            userId='me',
            q=f'newer_than:1d',
            maxResults=1
        ).execute()
        today_count = today_results.get('resultSizeEstimate', 0)
        
        important_results = gmail_service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()
        important_count = important_results.get('resultSizeEstimate', 0)
        
        return f"""📧 **Executive Email Dashboard**

🔴 **Unread:** {unread_count} emails
📅 **Today:** {today_count} emails received
⭐ **Important & Unread:** {important_count} emails

💡 **Quick Actions:**
• Use `!unread` for unread emails
• Use `!emails` for recent inbox
• Mention @Rose to process specific emails"""
        
    except Exception as e:
        print(f"❌ Email stats error: {e}")
        return f"❌ Error retrieving email statistics: {str(e)}"

# ============================================================================
# ENHANCED FUNCTION HANDLING
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with complete calendar and email management"""
    
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
            # CALENDAR VIEWING FUNCTIONS
            if function_name == "get_today_schedule":
                output = get_today_schedule()
                    
            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)
                
            elif function_name == "get_morning_briefing":
                output = get_morning_briefing()
            
            # EMAIL MANAGEMENT FUNCTIONS
            elif function_name == "get_recent_emails":
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
                
            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]
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
            print(f"👑 Created executive thread for user {user_id}")
        
        thread_id = user_conversations[user_id]
        
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
        
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        today_formatted = now.strftime('%A, %B %d, %Y')
        today_date = now.strftime('%Y-%m-%d')
        tomorrow = now + timedelta(days=1)
        tomorrow_formatted = tomorrow.strftime('%A, %B %d, %Y') 
        tomorrow_date = tomorrow.strftime('%Y-%m-%d')

        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

CURRENT DATE & TIME CONTEXT:
- TODAY: {today_formatted} ({today_date})
- TOMORROW: {tomorrow_formatted} ({tomorrow_date})
- TIMEZONE: America/Toronto

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- AVAILABLE CALENDARS: {[name for name, _, _ in accessible_calendars]}
- GMAIL INTEGRATION: {'Available' if gmail_service else 'Not available'}
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- When user says "tomorrow" use {tomorrow_date} ({tomorrow_formatted})
- When user says "today" use {today_date} ({today_formatted})
- All times are in Toronto timezone (America/Toronto)
- Use 24-hour time format (14:30, not 2:30 PM)"""
        
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
        
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID,
                instructions="""You are Rose Ashcombe, executive assistant specialist with Google Calendar and Gmail integration.

EXECUTIVE APPROACH:
- Use executive calendar and email functions to provide comprehensive insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines

FORMATTING: Use professional executive formatting with strategic headers (👑 📧 📅 🎯 💼) and provide organized, action-oriented guidance.

STRUCTURE:
👑 **Executive Summary:** [strategic overview with calendar and email insights]
📊 **Strategic Analysis:** [research-backed recommendations]
🎯 **Action Items:** [specific next steps with timing]

Keep core content focused and always provide strategic context with calendar and email coordination."""
            )
        except Exception as e:
            print(f"❌ Run creation error: {e}")
            return "❌ Error starting executive analysis. Please try again."
        
        print(f"👑 Rose run created: {run.id}")
        
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
                return "❌ Executive analysis interrupted. Please try again."
            
            await asyncio.sleep(2)
        else:
            print("⏱️ Run timed out")
            return "⏱️ Executive office is busy. Please try again in a moment."
        
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
    except Exception as e:
        print(f"❌ Message sending error: {e}")

# ============================================================================
# DISCORD BOT EVENT HANDLERS
# ============================================================================

@bot.event
async def on_ready():
    """Bot startup with comprehensive initialization"""
    try:
        print(f"✅ {ASSISTANT_NAME} has awakened!")
        print(f"🤖 Connected as: {bot.user.name} (ID: {bot.user.id})")
        print(f"🎯 Role: {ASSISTANT_ROLE}")
        print(f"📅 Calendar Status: {len(accessible_calendars)} accessible calendars")
        print(f"📧 Gmail Status: {'Available' if gmail_service else 'Not available'}")
        print(f"🔍 Research: {'Enabled' if BRAVE_API_KEY else 'Disabled'}")
        print(f"🏢 Allowed channels: {', '.join(ALLOWED_CHANNELS)}")
        
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📅📧 Executive Calendar & Email Management"
            )
        )
        print("👑 Rose is ready for complete executive assistance!")
        
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
# DISCORD COMMANDS
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Executive response time: {latency}ms")
    except Exception as e:
        print(f"❌ Ping command error: {e}")
        await ctx.send("👑 Executive ping experiencing issues.")

@bot.command(name='help')
async def help_command(ctx):
    """Enhanced help command with email functions"""
    try:
        help_text = f"""👑 **{ASSISTANT_NAME} - Executive Assistant Commands**

**📅 Calendar & Scheduling:**
• `!today` - Today's executive schedule
• `!upcoming [days]` - Upcoming events (default 7 days)
• `!briefing` / `!daily` / `!morning` - Morning executive briefing

**📧 Email Management:**
• `!emails [count]` - Recent emails (default 10)
• `!unread [count]` - Unread emails only
• `!emailstats` - Email dashboard overview

**💼 Executive Functions:**
• `!status` - System status (calendar, email, research)
• `!ping` - Test connectivity
• `!help` - This command menu

**📱 Usage:**
• Mention @{bot.user.name if bot.user else 'Rose'} in any message
• Available in: {', '.join(ALLOWED_CHANNELS)}

**💬 Natural Language Examples:**
• "@Rose check my unread emails"
• "@Rose send email to [person] about [topic]"
• "@Rose what's my schedule today?"
• "@Rose what emails came in today?"
• "@Rose help me plan my week strategically"
"""
        
        await ctx.send(help_text)
        
    except Exception as e:
        print(f"❌ Help command error: {e}")
        await ctx.send("👑 Help system needs calibration. Please try again.")

@bot.command(name='status')
async def status_command(ctx):
    """Executive system status with comprehensive diagnostics"""
    try:
        calendar_status = "❌ No calendars accessible"
        if accessible_calendars:
            calendar_names = [name for name, _, _ in accessible_calendars]
            calendar_status = f"✅ {len(accessible_calendars)} calendars: {', '.join(calendar_names)}"
        
        gmail_status = "✅ OAuth Available" if gmail_service else "❌ Not available"
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        
        oauth_info = "Not configured"
        if GMAIL_OAUTH_JSON:
            oauth_info = "✅ OAuth JSON configured"
        
        status_text = f"""👑 **{ASSISTANT_NAME} Executive Status**

**🤖 Core Systems:**
• Discord: ✅ Connected as {bot.user.name if bot.user else 'Unknown'}
• OpenAI Assistant: {assistant_status}
• Service Account: ✅ {service_account_email or 'Not configured'}

**📅 Calendar Integration:**
• Status: {calendar_status}
• Timezone: 🇨🇦 Toronto (America/Toronto)

**📧 Gmail Integration:**
• Status: {gmail_status}
• OAuth Setup: {oauth_info}
• Features: Read, Send, Search, Statistics

**💼 Executive Features:**
• Active conversations: {len(user_conversations)}
• Channels: {', '.join(ALLOWED_CHANNELS)}

**⚡ Performance:**
• Uptime: Ready for executive assistance
• Memory: {len(processing_messages)} processing"""
        
        await ctx.send(status_text)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Status diagnostics experiencing issues. Please try again.")

@bot.command(name='today')
async def today_command(ctx):
    """Today's executive schedule command"""
    try:
        async with ctx.typing():
            schedule = get_today_schedule()
            await ctx.send(schedule)
    except Exception as e:
        print(f"❌ Today command error: {e}")
        await ctx.send("👑 Today's schedule unavailable. Please try again.")

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """Upcoming events command"""
    try:
        async with ctx.typing():
            days = max(1, min(days, 30))
            events = get_upcoming_events(days)
            await ctx.send(events)
    except Exception as e:
        print(f"❌ Upcoming command error: {e}")
        await ctx.send("👑 Upcoming events unavailable. Please try again.")

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            briefing = get_morning_briefing()
            await ctx.send(briefing)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("👑 Executive briefing unavailable. Please try again.")

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

# ============================================================================
# ERROR HANDLING
# ============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling for all commands"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required information. Use `!help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `!help` for command usage.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"👑 Executive office is busy. Please wait {error.retry_after:.1f} seconds.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send("❌ Command error occurred. Please try again.")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print(f"🚀 Launching {ASSISTANT_NAME}...")
        print(f"📅 Google Calendar API: {bool(accessible_calendars)} calendars accessible")
        print(f"📧 Gmail API: {bool(gmail_service)} OAuth service available")
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