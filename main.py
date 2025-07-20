#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE DISCORD BOT WITH EMAIL INTEGRATION
Executive Assistant with Calendar Management, Email Management, and Strategic Planning
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

# Global services
calendar_service = None
gmail_service = None
accessible_calendars = []
service_account_email = None

# User conversation tracking
user_conversations = {}
processing_messages = set()
last_response_time = {}

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

# Initialize Google Services
try:
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        gmail_service = build('gmail', 'v1', credentials=credentials)
        print("✅ Google Calendar and Gmail services initialized")
        
        # Get service account email for sharing instructions
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account Email: {service_account_email}")
        
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
            
    else:
        print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not found - calendar/email features disabled")
        
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
# PLANNING RESEARCH FUNCTION
# ============================================================================

async def planning_search(query):
    """Research planning topics using Brave Search"""
    if not BRAVE_API_KEY:
        return "🔍 Research capability not available (missing API key)"
    
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        params = {
            "q": f"{query} productivity planning executive",
            "count": 5,
            "search_lang": "en",
            "country": "ca"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = data.get('web', {}).get('results', [])
                    if not results:
                        return f"🔍 No research results found for: {query}"
                    
                    formatted_results = []
                    for result in results[:3]:
                        title = result.get('title', 'No title')
                        description = result.get('description', 'No description')
                        url = result.get('url', '')
                        
                        formatted_results.append(f"**{title}**\n{description[:200]}...\n{url}")
                    
                    return f"🔍 **Research Results for '{query}':**\n\n" + "\n\n".join(formatted_results)
                else:
                    return f"🔍 Research error: HTTP {response.status}"
                    
    except Exception as e:
        print(f"❌ Planning search error: {e}")
        return f"🔍 Research error: {str(e)}"

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

            # Calendar functions
            elif function_name == "get_today_schedule":
                output = get_today_schedule()

            elif function_name == "get_upcoming_events":
                days = arguments.get('days', 7)
                output = get_upcoming_events(days)

            # Planning function
            elif function_name == "planning_search":
                query = arguments.get('query', '')
                if query:
                    output = asyncio.run(planning_search(query))
                else:
                    output = "❌ Missing required parameter: query"

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

@bot.command(name='status')
async def status_command(ctx):
    """Show Rose's comprehensive status"""
    try:
        gmail_status = "✅ Connected" if gmail_service else "❌ Not available"
        calendar_status = "✅ Connected" if calendar_service else "❌ Not available"
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        research_status = "✅ Connected" if BRAVE_API_KEY else "❌ Not available"
        
        calendar_list = ""
        if accessible_calendars:
            calendar_list = "\n📅 **Accessible Calendars:**\n" + "\n".join([f"   • {name}" for name, _ in accessible_calendars])
        
        status_message = f"""👑 **Rose Ashcombe - Executive Assistant Status**

🔧 **Core Systems:**
📧 Gmail: {gmail_status}
📅 Calendar: {calendar_status}
🤖 OpenAI Assistant: {assistant_status}
🔍 Research: {research_status}

📱 **Capabilities:**
• Email management (read, send, organize, delete)
• Calendar coordination and scheduling
• Strategic planning research
• Executive productivity optimization

📋 **Channels:** {', '.join(ALLOWED_CHANNELS)}
{calendar_list}

💡 **Usage:** Mention @Rose or DM for assistance"""

        await ctx.send(status_message)
        
    except Exception as e:
        print(f"❌ Status command error: {e}")
        await ctx.send("👑 Executive status check experiencing issues.")

@bot.command(name='help', aliases=['commands'])
async def help_command(ctx):
    """Show Rose's help information"""
    try:
        help_message = """👑 **Rose Ashcombe - Executive Assistant Commands**

🤖 **Assistant Interaction:**
• Mention @Rose [request] - Full assistant capabilities
• DM Rose directly - Private consultation

📧 **Email Commands:**
• `!emails [count]` - Recent emails (default: 10)
• `!unread [count]` - Unread emails only
• `!emailstats` - Email dashboard
• `!quickemails [count]` - Concise email view
• `!emailcount` - Just email counts
• `!cleansender <email> [count]` - Delete emails from sender

📅 **Calendar Commands:**
• `!schedule` - Today's events
• `!upcoming [days]` - Upcoming events (default: 7 days)

🔧 **System Commands:**
• `!ping` - Test connectivity
• `!status` - System status
• `!help` - This help message

💡 **Examples:**
• @Rose check my unread emails
• @Rose what's my schedule for today?
• @Rose find emails from john@company.com
• @Rose help me plan my week strategically
• !emails 5
• !cleansender newsletter@company.com 10"""

        await ctx.send(help_message)
        
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

# Calendar-specific Discord commands
@bot.command(name='schedule')
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