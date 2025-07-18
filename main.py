#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE FIXED VERSION
Executive Assistant with Full Google Calendar + Gmail Integration
FIXES: All incomplete code sections, missing imports, broken function calls
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
from typing import Dict, List, Optional, Tuple, Union

# Email-specific imports
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

# Load environment variables
load_dotenv()

# Rose's executive configuration
ASSISTANT_NAME = "Rose Ashcombe"
ASSISTANT_ROLE = "Executive Assistant with Email & Calendar"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Enhanced integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
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

# ============================================================================
# STANDARDIZED ERROR HANDLING CLASS
# ============================================================================

class RoseErrorHandler:
    """Centralized error handling for consistent user experience"""
    
    @staticmethod
    def handle_discord_error(error: Exception, context: str = "Discord operation") -> str:
        """Handle Discord-related errors with user-friendly messages"""
        error_str = str(error).lower()
        error_msg = f"❌ {context}: {str(error)[:100]}"
        print(f"{error_msg}\nFull traceback: {traceback.format_exc()}")
        
        if "rate limit" in error_str or "429" in error_str:
            return "⏳ Rose is handling multiple requests. Please try again in a moment."
        elif "timeout" in error_str:
            return "⏱️ Request timed out. Please try a more specific query."
        elif "permission" in error_str or "403" in error_str:
            return "🔐 Permission issue detected. Contact administrator if this persists."
        elif "not found" in error_str or "404" in error_str:
            return "🔍 Requested resource not found. Please check your request."
        else:
            return "👑 Executive assistance temporarily unavailable. Please try again."
    
    @staticmethod
    def handle_api_error(error: Exception, service: str = "API") -> str:
        """Handle API-related errors"""
        error_str = str(error).lower()
        
        if "quota" in error_str or "limit" in error_str:
            return f"📊 {service} quota reached. Executive capabilities temporarily reduced."
        elif "unauthorized" in error_str or "authentication" in error_str:
            return f"🔐 {service} authentication issue. Contact administrator."
        elif "timeout" in error_str:
            return f"⏱️ {service} timeout. Please try again."
        else:
            return f"🔧 {service} temporarily unavailable. ({str(error)[:50]})"
    
    @staticmethod
    def handle_calendar_error(error: Exception, operation: str = "Calendar operation") -> str:
        """Handle calendar-specific errors"""
        if isinstance(error, HttpError):
            status_code = error.resp.status
            if status_code == 404:
                return "📅 Calendar not found. Please check calendar permissions."
            elif status_code == 403:
                return "🔐 Calendar access denied. Share calendar with service account."
            elif status_code == 400:
                return "⚠️ Invalid calendar request. Please check your query."
            else:
                return f"📅 Calendar error ({status_code}). Please try again."
        else:
            return RoseErrorHandler.handle_api_error(error, "Calendar")
    
    @staticmethod
    def log_error(error: Exception, context: str, details: Dict = None):
        """Log detailed error information for debugging"""
        print(f"❌ ERROR in {context}:")
        print(f"   Type: {type(error).__name__}")
        print(f"   Message: {str(error)}")
        if details:
            print(f"   Details: {details}")
        print(f"   Traceback: {traceback.format_exc()}")

# ============================================================================
# RESPONSE FORMATTING CLASS
# ============================================================================

class ResponseFormatter:
    """Clean, structured response formatting"""
    
    @classmethod
    def format_response(cls, response_text: str, response_type: str = "general") -> str:
        """Main formatting method"""
        try:
            if not response_text or not response_text.strip():
                return "👑 Executive response processing... Please try again."
            
            # Clean up response text
            cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', response_text)
            
            # Ensure proper Discord character limits
            if len(cleaned) > 1900:
                cleaned = cleaned[:1900] + "\n\n👑 *(Executive insights continue)*"
            
            return cleaned.strip()
                
        except Exception as e:
            RoseErrorHandler.log_error(e, "Response formatting")
            return "👑 Executive message formatting... Please try again."

# ============================================================================
# DISCORD BOT INITIALIZATION
# ============================================================================

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

# Google Services setup (Calendar + Gmail)
calendar_service = None
gmail_service = None
accessible_calendars = []

# Updated scopes for both Calendar and Gmail
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=GOOGLE_SCOPES
        )
        
        # Initialize Calendar service
        calendar_service = build('calendar', 'v3', credentials=credentials)
        calendar_list = calendar_service.calendarList().list().execute()
        for calendar in calendar_list.get('items', []):
            accessible_calendars.append((calendar['id'], calendar.get('summary', 'Unnamed')))
        
        print(f"✅ Google Calendar initialized with {len(accessible_calendars)} calendars")
        
        # Initialize Gmail service
        gmail_service = build('gmail', 'v1', credentials=credentials)
        print("✅ Gmail service initialized")
        
except Exception as e:
    print(f"⚠️ Google services initialization failed: {e}")
    calendar_service = None
    gmail_service = None

# Global state management
user_conversations = {}
active_runs = {}
last_response_time = {}
processing_messages = set()

# ============================================================================
# CALENDAR FUNCTIONS
# ============================================================================

async def get_calendar_events_unified(timeframe="today", max_results=10, calendar_filter=None):
    """Unified calendar function"""
    if not calendar_service:
        return "📅 Calendar integration not available"
    
    try:
        # Get time range
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        
        if timeframe == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif timeframe == "week":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif timeframe == "month":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=30)
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        time_min = start.isoformat()
        time_max = end.isoformat()
        
        all_events = []
        
        for calendar_id, calendar_name in accessible_calendars:
            try:
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                for event in events:
                    event['calendar_source'] = calendar_name
                
                all_events.extend(events)
                
            except HttpError as e:
                print(f"❌ Calendar error for {calendar_name}: {e}")
                continue
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
        
        # Format events
        if not all_events:
            return f"📅 No events found for {timeframe}"
        
        event_lines = []
        for event in all_events[:max_results]:
            try:
                summary = event.get('summary', 'Untitled Event')
                start = event.get('start', {})
                calendar_source = event.get('calendar_source', 'Unknown')
                
                if start.get('dateTime'):
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    if start_dt.tzinfo:
                        start_dt = start_dt.astimezone(toronto_tz)
                    time_str = start_dt.strftime('%I:%M %p').lower().lstrip('0')
                elif start.get('date'):
                    time_str = "All day"
                else:
                    time_str = "Unknown time"
                
                event_lines.append(f"• **{time_str}** - {summary} *({calendar_source})*")
                
            except Exception as e:
                print(f"❌ Event formatting error: {e}")
                continue
        
        header = f"📅 **{timeframe.title()} Schedule** ({len(all_events)} event{'s' if len(all_events) != 1 else ''})"
        return "\n".join([header] + event_lines)
        
    except Exception as e:
        return RoseErrorHandler.handle_calendar_error(e, "Calendar events retrieval")

# Restored calendar helper functions -------------------------------------------------

def get_calendar_events(calendar_id, start_time, end_time, max_results=100):
    """Retrieve events from a specific calendar."""
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

        return events_result.get('items', [])
    except Exception as e:
        print(f"❌ Error getting events from {calendar_id}: {e}")
        return []


def find_calendar_event(search_term, days_range=30):
    """Locate a calendar event across accessible calendars."""
    if not calendar_service or not accessible_calendars:
        return None, None, None

    try:
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        past_search = now - timedelta(days=7)
        future_search = now + timedelta(days=days_range)

        for calendar_id, calendar_name in accessible_calendars:
            events = get_calendar_events(calendar_id, past_search, future_search, max_results=200)
            for event in events:
                title = event.get('summary', '').lower()
                if search_term.lower() in title:
                    return event, calendar_id, calendar_name

        return None, None, None
    except Exception as e:
        print(f"❌ Error finding event: {e}")
        return None, None, None


def create_calendar_event(title, start_time, end_time, calendar_type="calendar", description=""):
    """Create a new calendar event."""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"

    try:
        target_calendar_id = None
        target_calendar_name = None

        # Basic name matching against available calendars
        for cal_id, cal_name in accessible_calendars:
            if calendar_type.lower() in cal_name.lower():
                target_calendar_id = cal_id
                target_calendar_name = cal_name
                break

        if not target_calendar_id:
            target_calendar_id, target_calendar_name = accessible_calendars[0]

        toronto_tz = pytz.timezone('America/Toronto')

        if "T" not in start_time:
            start_time = f"{start_time}T15:00:00"
        if "T" not in end_time:
            end_time = f"{end_time}T16:00:00"

        start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
        end_dt = datetime.fromisoformat(end_time.replace('Z', ''))

        if start_dt.tzinfo is None:
            start_dt = toronto_tz.localize(start_dt)
        if end_dt.tzinfo is None:
            end_dt = toronto_tz.localize(end_dt)

        event = {
            'summary': title,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Toronto',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Toronto',
            },
            'description': description,
        }

        created_event = calendar_service.events().insert(
            calendarId=target_calendar_id,
            body=event
        ).execute()

        display_start = start_dt.astimezone(toronto_tz)
        display_end = end_dt.astimezone(toronto_tz)
        day_date = display_start.strftime('%A, %B %d, %Y')
        start_24 = display_start.strftime('%H:%M')
        end_24 = display_end.strftime('%H:%M')

        return (
            f"✅ **{title}** created\n"
            f"📅 {day_date}, {start_24} - {end_24}\n"
            f"🗓️ {target_calendar_name}\n"
            f"🔗 [View Event]({created_event.get('htmlLink', '#')})"
        )
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
        return f"❌ Failed to create '{title}': {str(e)}"


def update_calendar_event(event_search, new_title=None, new_start_time=None, new_end_time=None, new_description=None):
    """Update an existing calendar event."""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"

    try:
        found_event, calendar_id, calendar_name = find_calendar_event(event_search)

        if not found_event:
            return f"❌ '{event_search}' not found"

        updated_fields = []

        if new_title:
            found_event['summary'] = new_title
            updated_fields.append(f"Title → {new_title}")

        toronto_tz = pytz.timezone('America/Toronto')

        if new_start_time:
            if "T" not in new_start_time and 'dateTime' in found_event['start']:
                new_start_time = f"{new_start_time}T{found_event['start']['dateTime'].split('T')[1]}"
            new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', ''))
            if new_start_dt.tzinfo is None:
                new_start_dt = toronto_tz.localize(new_start_dt)
            found_event['start'] = {
                'dateTime': new_start_dt.isoformat(),
                'timeZone': 'America/Toronto',
            }
            updated_fields.append(f"Start → {new_start_dt.strftime('%m/%d %H:%M')}")

        if new_end_time:
            if "T" not in new_end_time and 'dateTime' in found_event['end']:
                new_end_time = f"{new_end_time}T{found_event['end']['dateTime'].split('T')[1]}"
            new_end_dt = datetime.fromisoformat(new_end_time.replace('Z', ''))
            if new_end_dt.tzinfo is None:
                new_end_dt = toronto_tz.localize(new_end_dt)
            found_event['end'] = {
                'dateTime': new_end_dt.isoformat(),
                'timeZone': 'America/Toronto',
            }
            updated_fields.append(f"End → {new_end_dt.strftime('%m/%d %H:%M')}")

        if new_description is not None:
            found_event['description'] = new_description
            updated_fields.append("Description updated")

        updated_event = calendar_service.events().update(
            calendarId=calendar_id,
            eventId=found_event['id'],
            body=found_event
        ).execute()

        return (
            f"✅ **{updated_event['summary']}** updated\n"
            f"🔄 {', '.join(updated_fields)}\n"
            f"🗓️ {calendar_name}\n"
            f"🔗 [View Event]({updated_event.get('htmlLink', '#')})"
        )
    except Exception as e:
        print(f"❌ Error updating event: {e}")
        return f"❌ Failed to update '{event_search}': {str(e)}"


def reschedule_event(event_search, new_start_time, new_end_time=None):
    """Reschedule an existing calendar event."""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"

    try:
        found_event, calendar_id, calendar_name = find_calendar_event(event_search)

        if not found_event:
            return f"❌ '{event_search}' not found"

        toronto_tz = pytz.timezone('America/Toronto')

        if "T" not in new_start_time:
            original_time = found_event['start'].get('dateTime', 'T15:00:00').split('T')[1]
            new_start_time = f"{new_start_time}T{original_time}"

        new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', ''))
        if new_start_dt.tzinfo is None:
            new_start_dt = toronto_tz.localize(new_start_dt)

        if new_end_time:
            if "T" not in new_end_time:
                original_end = found_event['end'].get('dateTime', 'T16:00:00').split('T')[1]
                new_end_time = f"{new_end_time}T{original_end}"
            new_end_dt = datetime.fromisoformat(new_end_time.replace('Z', ''))
            if new_end_dt.tzinfo is None:
                new_end_dt = toronto_tz.localize(new_end_dt)
        else:
            start_orig = datetime.fromisoformat(found_event['start']['dateTime'].replace('Z', '+00:00'))
            end_orig = datetime.fromisoformat(found_event['end']['dateTime'].replace('Z', '+00:00'))
            duration = end_orig - start_orig
            new_end_dt = new_start_dt + duration

        found_event['start'] = {
            'dateTime': new_start_dt.isoformat(),
            'timeZone': 'America/Toronto',
        }
        found_event['end'] = {
            'dateTime': new_end_dt.isoformat(),
            'timeZone': 'America/Toronto',
        }

        updated_event = calendar_service.events().update(
            calendarId=calendar_id,
            eventId=found_event['id'],
            body=found_event
        ).execute()

        display_start = new_start_dt.astimezone(toronto_tz)
        display_end = new_end_dt.astimezone(toronto_tz)
        day_date = display_start.strftime('%A, %B %d')
        start_24 = display_start.strftime('%H:%M')
        end_24 = display_end.strftime('%H:%M')

        return (
            f"✅ **{updated_event['summary']}** rescheduled\n"
            f"📅 {day_date}, {start_24} - {end_24}\n"
            f"🗓️ {calendar_name}\n"
            f"🔗 [View Event]({updated_event.get('htmlLink', '#')})"
        )
    except Exception as e:
        print(f"❌ Error rescheduling event: {e}")
        return f"❌ Failed to reschedule '{event_search}': {str(e)}"


def move_task_between_calendars(task_search, target_calendar="tasks"):
    """Move a task/event to a different calendar."""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"

    try:
        found_event, found_calendar_id, found_calendar_name = find_calendar_event(task_search)

        if not found_event:
            return f"❌ '{task_search}' not found"

        target_calendar_id = None
        target_calendar_name = None

        for cal_id, cal_name in accessible_calendars:
            if target_calendar.lower() in cal_name.lower():
                target_calendar_id = cal_id
                target_calendar_name = cal_name
                break

        if not target_calendar_id:
            target_calendar_id, target_calendar_name = accessible_calendars[0]

        if found_calendar_id == target_calendar_id:
            return f"📅 '{found_event['summary']}' already in {target_calendar_name}"

        event_copy = {
            'summary': found_event.get('summary'),
            'description': found_event.get('description', ''),
            'start': found_event.get('start'),
            'end': found_event.get('end'),
            'location': found_event.get('location', ''),
        }

        for field in ['id', 'htmlLink', 'iCalUID', 'created', 'updated', 'creator', 'organizer']:
            event_copy.pop(field, None)

        created_event = calendar_service.events().insert(
            calendarId=target_calendar_id,
            body=event_copy
        ).execute()

        calendar_service.events().delete(
            calendarId=found_calendar_id,
            eventId=found_event['id']
        ).execute()

        return (
            f"✅ **{found_event['summary']}** moved\n"
            f"📍 {found_calendar_name} → {target_calendar_name}\n"
            f"🔗 [View Event]({created_event.get('htmlLink', '#')})"
        )
    except HttpError as e:
        return f"❌ Calendar error: {e.resp.status}"
    except Exception as e:
        print(f"❌ Error moving task: {e}")
        return f"❌ Failed to move '{task_search}': {str(e)}"


def delete_calendar_event(event_search):
    """Delete a calendar event."""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"

    try:
        found_event, calendar_id, calendar_name = find_calendar_event(event_search)

        if not found_event:
            return f"❌ '{event_search}' not found"

        event_title = found_event.get('summary', 'Unknown Event')

        calendar_service.events().delete(
            calendarId=calendar_id,
            eventId=found_event['id']
        ).execute()

        return f"✅ **{event_title}** deleted from {calendar_name}"
    except Exception as e:
        print(f"❌ Error deleting event: {e}")
        return f"❌ Failed to delete '{event_search}': {str(e)}"


# ============================================================================
# EMAIL FUNCTIONS
# ============================================================================

async def get_recent_emails(count=10, query="in:inbox"):
    """Get recent emails"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        messages_result = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=count
        ).execute()
        
        messages = messages_result.get('messages', [])
        if not messages:
            return f'📭 No emails found for query: "{query}"'
        
        email_lines = []
        for message in messages[:count]:
            try:
                email_detail = gmail_service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata'
                ).execute()
                
                headers = {}
                payload = email_detail.get('payload', {})
                for header in payload.get('headers', []):
                    headers[header['name'].lower()] = header['value']
                
                sender = headers.get('from', 'Unknown sender')
                subject = headers.get('subject', 'No subject')
                date_str = headers.get('date', 'Unknown date')[:16]
                
                is_unread = 'UNREAD' in email_detail.get('labelIds', [])
                status = "🔵" if is_unread else "⚪"
                
                # Extract sender name
                if '<' in sender:
                    sender_name = sender.split('<')[0].strip(' "')[:30]
                else:
                    sender_name = sender[:30]
                
                email_lines.append(f"{status} **{sender_name}**\n   *{subject[:50]}*\n   📅 {date_str}")
                
            except Exception as e:
                print(f"❌ Email processing error: {e}")
                continue
        
        header = f"📧 **Email Summary** ({len(messages)} total)"
        return "\n\n".join([header] + email_lines)
        
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail")

async def get_unread_emails(count=10):
    """Get unread emails"""
    return await get_recent_emails(count, "is:unread in:inbox")

async def get_email_stats_function():
    """Get email statistics"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        unread = gmail_service.users().messages().list(
            userId='me',
            q='is:unread in:inbox',
            maxResults=1
        ).execute()
        
        today_emails = gmail_service.users().messages().list(
            userId='me',
            q='in:inbox newer_than:1d',
            maxResults=1
        ).execute()
        
        unread_count = unread.get('resultSizeEstimate', 0)
        today_count = today_emails.get('resultSizeEstimate', 0)
        
        stats = f"📊 **Email Dashboard**\n"
        stats += f"📥 Unread: {unread_count}\n"
        stats += f"📅 Today: {today_count}"
        
        return stats
        
    except Exception as e:
        return RoseErrorHandler.handle_api_error(e, "Gmail Stats")

# ============================================================================
# SEARCH FUNCTION
# ============================================================================

async def planning_search_enhanced(query, max_results=5):
    """Enhanced search with better error handling"""
    if not BRAVE_API_KEY:
        return "🔍 Search not available - API key not configured", []
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            params = {
                'q': query,
                'count': max_results,
                'mkt': 'en-CA',
                'safesearch': 'moderate'
            }
            
            headers = {
                'X-Subscription-Token': BRAVE_API_KEY,
                'Accept': 'application/json'
            }
            
            async with session.get('https://api.search.brave.com/res/v1/web/search', 
                                 params=params, headers=headers) as response:
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return "🔍 No search results found for your query", []
                    
                    formatted_results = []
                    sources = []
                    
                    for i, result in enumerate(results[:max_results]):
                        title = result.get('title', 'No title')[:80]
                        snippet = result.get('description', 'No description')[:150]
                        url = result.get('url', '')
                        
                        formatted_results.append(f"**{i+1}. {title}**\n{snippet}")
                        sources.append({
                            'number': i+1,
                            'title': title,
                            'url': url
                        })
                    
                    return "\n\n".join(formatted_results), sources
                    
                elif response.status == 429:
                    return "⏳ Search rate limit reached. Please try again later.", []
                else:
                    return f"🔍 Search service error (HTTP {response.status})", []
                    
    except asyncio.TimeoutError:
        return "⏱️ Search request timed out. Please try again.", []
    except Exception as e:
        error_msg = RoseErrorHandler.handle_api_error(e, "Search")
        return error_msg, []

# ============================================================================
# FUNCTION HANDLING
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with calendar and email functions"""
    
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
            # Calendar functions
            if function_name in ["get_today_schedule", "get_upcoming_events", "get_calendar_events_detailed"]:
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                
                if function_name == "get_today_schedule":
                    timeframe = "today"
                elif function_name == "get_upcoming_events":
                    timeframe = "week"
                else:
                    timeframe = args.get('timeframe', 'today')
                
                max_results = args.get('max_results', 10)
                result = await get_calendar_events_unified(timeframe, max_results)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            # Email functions
            elif function_name == "get_recent_emails":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                count = args.get('count', 10)
                query = args.get('query', 'in:inbox')
                
                result = await get_recent_emails(count, query)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "get_unread_emails":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                count = args.get('count', 10)
                
                result = await get_unread_emails(count)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "get_email_stats":
                result = await get_email_stats_function()
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            # Calendar modification functions
            elif function_name == "create_calendar_event":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                title = args.get('title', '')
                start_time = args.get('start_time', '')
                end_time = args.get('end_time', '')
                calendar_type = args.get('calendar_type', 'calendar')
                description = args.get('description', '')

                if title and start_time and end_time:
                    result = create_calendar_event(title, start_time, end_time, calendar_type, description)
                else:
                    result = "❌ Missing required parameters: title, start_time, end_time"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "update_calendar_event":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                event_search = args.get('event_search', '')
                new_title = args.get('new_title')
                new_start_time = args.get('new_start_time')
                new_end_time = args.get('new_end_time')
                new_description = args.get('new_description')

                if event_search:
                    result = update_calendar_event(event_search, new_title, new_start_time, new_end_time, new_description)
                else:
                    result = "❌ Missing required parameter: event_search"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "reschedule_event":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                event_search = args.get('event_search', '')
                new_start_time = args.get('new_start_time', '')
                new_end_time = args.get('new_end_time')

                if event_search and new_start_time:
                    result = reschedule_event(event_search, new_start_time, new_end_time)
                else:
                    result = "❌ Missing required parameters: event_search, new_start_time"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "move_task_between_calendars":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                task_search = args.get('task_search', '')
                target_calendar = args.get('target_calendar', 'tasks')

                if task_search:
                    result = move_task_between_calendars(task_search, target_calendar)
                else:
                    result = "❌ Missing required parameter: task_search"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })

            elif function_name == "delete_calendar_event":
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                event_search = args.get('event_search', '')

                if event_search:
                    result = delete_calendar_event(event_search)
                else:
                    result = "❌ Missing required parameter: event_search"

                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            elif function_name == "planning_search":
                args = json.loads(tool_call.function.arguments)
                query = args.get('query', '')
                max_results = args.get('max_results', 5)
                
                if not query:
                    result = "🔍 Search query required"
                else:
                    result, sources = await planning_search_enhanced(query, max_results)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": result
                })
            
            else:
                # Handle unknown functions gracefully
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": f"⚠️ Function '{function_name}' not recognized"
                })
        
        except json.JSONDecodeError as e:
            error_msg = "⚠️ Invalid function arguments format"
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": error_msg
            })
        
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, f"Function {function_name}")
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": error_msg
            })
    
    # Submit tool outputs
    if tool_outputs:
        try:
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        except Exception as e:
            error_msg = RoseErrorHandler.handle_api_error(e, "OpenAI tool outputs")
            print(f"❌ Failed to submit tool outputs: {error_msg}")

# ============================================================================
# MAIN RESPONSE FUNCTION
# ============================================================================

async def get_rose_response(message, user_id):
    """Main response function with enhanced formatting and error handling"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Rate limiting check
        current_time = time.time()
        if user_id in last_response_time:
            if current_time - last_response_time[user_id] < 3:
                return "⏳ Please wait a moment between requests."
        
        # Check for active runs
        if user_id in active_runs and active_runs[user_id]:
            return "⏳ Executive analysis in progress. Please wait..."
        
        # Mark user as having active run
        active_runs[user_id] = True
        
        try:
            # Get user's thread
            if user_id not in user_conversations:
                thread = client.beta.threads.create()
                user_conversations[user_id] = thread.id
                print(f"👑 Created executive thread for user {user_id}")
            
            thread_id = user_conversations[user_id]
            
            # Clean message
            clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
            
            # Enhanced message with executive planning and email focus
            enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- SMART DETECTION: Automatically detect calendar, email, or planning queries
- EMAIL QUERIES: Use email functions for inbox management, sending, searching
- CALENDAR QUERIES: Use calendar functions for scheduling and coordination
- PLANNING QUERIES: Use research functions for strategic insights
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📧 **Email Management:** or 📅 **Calendar Coordination:**
- IMPORTANT: Always provide strategic context and actionable next steps
- All times are in Toronto timezone (America/Toronto)
- For executive briefings, include both calendar and email statistics"""
            
            # Create message
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
                    raise e
            
            # Create and run assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )
            
            # Wait for completion with timeout
            start_time = time.time()
            timeout = 45
            
            while run.status in ['queued', 'in_progress', 'requires_action']:
                if time.time() - start_time > timeout:
                    return "⏱️ Executive analysis taking longer than expected. Please try again."
                
                if run.status == 'requires_action':
                    await handle_rose_functions_enhanced(run, thread_id)
                
                await asyncio.sleep(1)
                try:
                    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                except Exception as e:
                    print(f"❌ Error retrieving run status: {e}")
                    break
            
            # Handle run completion
            if run.status == 'completed':
                # Get messages
                messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                
                if messages.data:
                    assistant_message = messages.data[0]
                    if hasattr(assistant_message, 'content') and assistant_message.content:
                        response_text = assistant_message.content[0].text.value
                        
                        # Apply improved formatting
                        formatted_response = ResponseFormatter.format_response(response_text)
                        return formatted_response
                    else:
                        return "👑 Executive response processing... Please try again."
                else:
                    return "👑 Executive analysis complete. Please try again for results."
            
            elif run.status == 'failed':
                error_info = getattr(run, 'last_error', None)
                if error_info:
                    return RoseErrorHandler.handle_api_error(Exception(str(error_info)), "OpenAI Assistant")
                else:
                    return "❌ Executive analysis failed. Please try again."
            
            else:
                return f"⚠️ Executive analysis status: {run.status}. Please try again."
                
        finally:
            # Always clear active run status
            active_runs[user_id] = False
            last_response_time[user_id] = current_time
            
    except Exception as e:
        # Clear active run status on error
        active_runs[user_id] = False
        error_msg = RoseErrorHandler.handle_api_error(e, "Rose Assistant")
        RoseErrorHandler.log_error(e, "get_rose_response", {'user_id': user_id, 'message': message[:100]})
        return error_msg

# ============================================================================
# MESSAGE HANDLING
# ============================================================================

async def send_long_message(original_message, response):
    """Send response with improved length handling and error recovery"""
    try:
        if len(response) <= 2000:
            await original_message.reply(response)
        else:
            # Smart chunking that preserves formatting
            chunks = []
            current_chunk = ""
            
            # Split on double newlines first to preserve sections
            sections = response.split('\n\n')
            
            for section in sections:
                if len(current_chunk + section + '\n\n') > 1900:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = section + '\n\n'
                else:
                    current_chunk += section + '\n\n'
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Send chunks
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await original_message.reply(chunk)
                else:
                    await original_message.channel.send(chunk)
                    
    except discord.HTTPException as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Message sending")
        try:
            await original_message.reply(error_msg)
        except:
            pass
    except Exception as e:
        RoseErrorHandler.log_error(e, "send_long_message")

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
        print(f"📧 Gmail Status: {'Enabled' if gmail_service else 'Disabled'}")
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
        RoseErrorHandler.log_error(e, "Bot startup")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f"❌ Discord error in {event}: {traceback.format_exc()}")

@bot.event
async def on_message(message):
    """Enhanced message handling with improved error handling"""
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
                error_msg = RoseErrorHandler.handle_discord_error(e, "Message processing")
                try:
                    await message.reply(error_msg)
                except:
                    pass
            finally:
                processing_messages.discard(message_key)
                    
    except Exception as e:
        RoseErrorHandler.log_error(e, "on_message event")

# ============================================================================
# ROSE'S EXECUTIVE COMMANDS
# ============================================================================

@bot.command(name='ping')
async def ping_command(ctx):
    """Test Rose's connectivity with executive flair"""
    try:
        latency = round(bot.latency * 1000)
        await ctx.send(f"👑 Pong! Executive response time: {latency}ms")
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Ping command")
        await ctx.send(error_msg)

@bot.command(name='schedule')
async def schedule_command(ctx):
    """Get today's calendar schedule"""
    try:
        async with ctx.typing():
            schedule = await get_calendar_events_unified("today", 10)
            
        embed = discord.Embed(
            title="📅 Today's Executive Schedule",
            description=schedule,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Schedule command")
        await ctx.send(error_msg)

@bot.command(name='upcoming')
async def upcoming_command(ctx, days: int = 7):
    """View upcoming events (default: 7 days)"""
    try:
        async with ctx.typing():
            if days <= 7:
                timeframe = "week"
            elif days <= 30:
                timeframe = "month"
            else:
                timeframe = "month"
                days = 30
            
            events = await get_calendar_events_unified(timeframe, 15)
            
        embed = discord.Embed(
            title=f"📋 Upcoming Events ({days} days)",
            description=events,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Upcoming command")
        await ctx.send(error_msg)

@bot.command(name='plan')
async def plan_command(ctx, *, query):
    """Planning research for strategic insights"""
    try:
        async with ctx.typing():
            if not query:
                await ctx.send("👑 Please provide a planning topic to research.")
                return
            
            search_results, sources = await planning_search_enhanced(query, 5)
            
        embed = discord.Embed(
            title="📊 Strategic Planning Research",
            description=f"**Query:** {query}\n\n{search_results}",
            color=0x9932CC
        )
        
        if sources:
            source_list = "\n".join([f"{s['number']}. {s['title'][:50]}..." for s in sources[:3]])
            embed.add_field(name="🔗 Sources", value=source_list, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Plan command")
        await ctx.send(error_msg)

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Executive briefing with calendar, email, and insights"""
    try:
        async with ctx.typing():
            # Get today's schedule
            today_schedule = await get_calendar_events_unified("today", 8)
            
            # Get upcoming events
            upcoming_events = await get_calendar_events_unified("week", 5)
            
            # Get email statistics
            email_stats = await get_email_stats_function()
            
            # Build executive briefing
            briefing_parts = [
                "👑 **Executive Briefing**",
                f"📅 **Today's Priority Schedule:**\n{today_schedule}",
                f"📧 **Email Status:**\n{email_stats}",
                f"📋 **Week Ahead Preview:**\n{upcoming_events}",
                "🎯 **Strategic Focus:** Optimize time blocks, manage inbox, and maintain executive productivity"
            ]
            
            briefing = "\n\n".join(briefing_parts)
        
        # Send as embed or long message depending on length
        if len(briefing) <= 4000:
            embed = discord.Embed(
                title="📊 Executive Briefing",
                description=briefing,
                color=0x9932CC
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(briefing)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Briefing command")
        await ctx.send(error_msg)

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    try:
        async with ctx.typing():
            emails = await get_recent_emails(count)
            
        embed = discord.Embed(
            title="📧 Recent Emails",
            description=emails,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Emails command")
        await ctx.send(error_msg)

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Get unread emails"""
    try:
        async with ctx.typing():
            emails = await get_unread_emails(count)
            
        embed = discord.Embed(
            title="🔵 Unread Emails",
            description=emails,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Unread command")
        await ctx.send(error_msg)

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Get email statistics"""
    try:
        async with ctx.typing():
            stats = await get_email_stats_function()
            
        embed = discord.Embed(
            title="📊 Email Statistics",
            description=stats,
            color=0x9932CC
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Email stats command")
        await ctx.send(error_msg)

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Status",
            description="Complete executive assistance system status",
            color=0x9932CC
        )
        
        # System status
        embed.add_field(
            name="🤖 System Status",
            value=f"✅ Online\n📡 Latency: {round(bot.latency * 1000)}ms",
            inline=True
        )
        
        # Calendar status
        calendar_status = "✅ Active" if calendar_service else "❌ Unavailable"
        embed.add_field(
            name="📅 Calendar Integration",
            value=f"{calendar_status}\n📋 Calendars: {len(accessible_calendars)}",
            inline=True
        )
        
        # Gmail status
        gmail_status = "✅ Active" if gmail_service else "❌ Unavailable"
        embed.add_field(
            name="📧 Gmail Integration",
            value=gmail_status,
            inline=True
        )
        
        # Search capability
        search_status = "✅ Available" if BRAVE_API_KEY else "❌ Not configured"
        embed.add_field(
            name="🔍 Research Capability",
            value=search_status,
            inline=True
        )
        
        # Active conversations
        embed.add_field(
            name="📊 Executive Metrics",
            value=f"👥 Active Threads: {len(user_conversations)}\n🏃 Processing: {len(processing_messages)}",
            inline=False
        )
        
        # Channels
        embed.add_field(
            name="🏢 Monitored Channels",
            value=f"• {', '.join([f'#{ch}' for ch in ALLOWED_CHANNELS])}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Status command")
        await ctx.send(error_msg)

@bot.command(name='help')
async def help_command(ctx):
    """Show Rose's executive capabilities and usage"""
    try:
        embed = discord.Embed(
            title="👑 Rose Ashcombe - Executive Assistant",
            description="Your strategic planning specialist with calendar integration, email management, and productivity optimization",
            color=0x9932CC
        )
        
        # How to Use Rose
        embed.add_field(
            name="💬 How to Use Rose",
            value="• Mention @Rose Ashcombe for executive planning & productivity advice\n• Ask about time management, scheduling, productivity systems\n• Get strategic insights based on your calendar and goals\n• Manage emails and coordinate communications",
            inline=False
        )
        
        # Executive Commands
        embed.add_field(
            name="🔧 Executive Commands",
            value="• `!schedule` - Get today's calendar\n• `!upcoming [days]` - View upcoming events\n• `!emails [count]` - Recent emails\n• `!unread [count]` - Unread emails\n• `!emailstats` - Email dashboard\n• `!briefing` - Executive briefing\n• `!plan [query]` - Planning research\n• `!ping` - Test connectivity\n• `!status` - Show capabilities",
            inline=False
        )
        
        # Example Requests
        embed.add_field(
            name="👑 Example Requests",
            value="• @Rose help me plan my week strategically\n• @Rose check my unread emails\n• @Rose what's the best time blocking method?\n• @Rose give me my executive briefing\n• @Rose research productivity systems for executives",
            inline=False
        )
        
        # Specialties
        embed.add_field(
            name="📊 Specialties",
            value="👑 Executive Planning • 📅 Calendar Management • 📧 Email Management • 🎯 Productivity Systems • ⚡ Time Optimization • 🏢 Life OS",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = RoseErrorHandler.handle_discord_error(e, "Help command")
        await ctx.send(error_msg)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        print("🚀 Starting Rose Ashcombe - Executive Assistant Bot (Complete Fixed Version)")
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ CRITICAL: Bot startup failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        exit(1)
                