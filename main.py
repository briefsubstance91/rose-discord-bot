#!/usr/bin/env python3
"""
ROSE ASHCOMBE - DISCORD BOT (COMPLETE FIXED VERSION)
Executive Assistant with Full Google Calendar API Integration & Gmail Integration
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
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parsedate_to_datetime
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
ASSISTANT_ROLE = "Executive Assistant (Complete Enhanced)"
ALLOWED_CHANNELS = ['life-os', 'calendar', 'planning-hub', 'general']

# Environment variables with fallbacks
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("ROSE_DISCORD_TOKEN")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Calendar integration
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_TASKS_CALENDAR_ID = os.getenv('GOOGLE_TASKS_CALENDAR_ID')

# Gmail integration
GMAIL_USER_EMAIL = os.getenv('GMAIL_USER_EMAIL')  # Your main email address
GMAIL_DELEGATE_EMAIL = os.getenv('GMAIL_DELEGATE_EMAIL', GMAIL_USER_EMAIL)  # Email to impersonate

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

# Google Calendar setup
calendar_service = None
accessible_calendars = []
service_account_email = None

# Gmail setup
gmail_service = None
gmail_user_email = None

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

# Initialize Google Calendar and Gmail services
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
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
        )
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized")
        
        service_account_email = credentials_info.get('client_email')
        print(f"📧 Service Account: {service_account_email}")
        
        # Initialize Gmail service with domain-wide delegation
        if GMAIL_USER_EMAIL:
            delegated_credentials = credentials.with_subject(GMAIL_DELEGATE_EMAIL or GMAIL_USER_EMAIL)
            gmail_service = build('gmail', 'v1', credentials=delegated_credentials)
            gmail_user_email = GMAIL_DELEGATE_EMAIL or GMAIL_USER_EMAIL
            print(f"✅ Gmail service initialized for: {gmail_user_email}")
        else:
            print("⚠️ GMAIL_USER_EMAIL not configured - Gmail features disabled")
        
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
            
    else:
        print("⚠️ Google services credentials not found")
        
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

def create_calendar_event(title, start_time, end_time, calendar_type="calendar", description=""):
    """Create a new calendar event in specified Google Calendar with concise confirmation"""
    if not calendar_service or not accessible_calendars:
        return "📅 Calendar integration not available"
    
    try:
        # Enhanced calendar selection logic
        target_calendar_id = None
        target_calendar_name = None
        
        # First, try exact calendar type match
        for name, cal_id, cal_type in accessible_calendars:
            if calendar_type == cal_type:
                target_calendar_id = cal_id
                target_calendar_name = name
                break
        
        # If no exact match, try keyword matching
        if not target_calendar_id:
            for name, cal_id, cal_type in accessible_calendars:
                if calendar_type.lower() in name.lower() or calendar_type.lower() in cal_type.lower():
                    target_calendar_id = cal_id
                    target_calendar_name = name
                    break
        
        # Final fallback to first available
        if not target_calendar_id and accessible_calendars:
            target_calendar_id = accessible_calendars[0][1]
            target_calendar_name = accessible_calendars[0][0]
        
        if not target_calendar_id:
            return "❌ No suitable calendar found"
        
        # Parse times
        toronto_tz = pytz.timezone('America/Toronto')
        
        try:
            # Handle different time formats
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
            
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
            
        except ValueError as e:
            return f"❌ Invalid time format: {e}"
        
        # Create event object
        event = {
            'summary': title,
            'start': {
                'dateTime': start_iso,
                'timeZone': 'America/Toronto',
            },
            'end': {
                'dateTime': end_iso,
                'timeZone': 'America/Toronto',
            },
            'description': description,
        }
        
        # Create the event
        created_event = calendar_service.events().insert(
            calendarId=target_calendar_id,
            body=event
        ).execute()
        
        # CONCISE CONFIRMATION with 24-hour time format
        display_start_dt = start_dt.astimezone(toronto_tz)
        display_end_dt = end_dt.astimezone(toronto_tz)
        
        # Format day and date
        day_date = display_start_dt.strftime('%A, %B %d, %Y')
        start_time_24h = display_start_dt.strftime('%H:%M')
        end_time_24h = display_end_dt.strftime('%H:%M')
        
        return f"✅ **{title}** created\n📅 {day_date}, {start_time_24h} - {end_time_24h}\n🗓️ {target_calendar_name}\n🔗 [View Event]({created_event.get('htmlLink', '#')})"
        
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
        return f"❌ Failed to create '{title}': {str(e)}"

# ============================================================================
# GMAIL FUNCTIONS
# ============================================================================

def get_recent_emails(max_results=10, query=""):
    """Get recent emails from Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Build query for recent emails
        search_query = query if query else "in:inbox"
        
        # Get message IDs
        results = gmail_service.users().messages().list(
            userId='me',
            q=search_query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 **Recent Emails:** No emails found"
        
        formatted_emails = []
        
        for msg in messages[:max_results]:
            try:
                # Get full message
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                
                # Extract email details
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Parse date for better formatting
                try:
                    parsed_date = parsedate_to_datetime(date)
                    toronto_tz = pytz.timezone('America/Toronto')
                    local_date = parsed_date.astimezone(toronto_tz)
                    formatted_date = local_date.strftime('%m/%d %H:%M')
                except:
                    formatted_date = date[:16] if len(date) > 16 else date
                
                # Check if unread
                labels = message.get('labelIds', [])
                unread_indicator = "🔴" if 'UNREAD' in labels else "📧"
                
                # Format sender (extract name/email)
                if '<' in from_email:
                    sender = from_email.split('<')[0].strip().strip('"')
                    if not sender:
                        sender = from_email.split('<')[1].split('>')[0]
                else:
                    sender = from_email
                
                formatted_emails.append(f"{unread_indicator} **{subject[:50]}{'...' if len(subject) > 50 else ''}**\n   From: {sender[:30]}{'...' if len(sender) > 30 else ''} | {formatted_date}")
                
            except Exception as e:
                print(f"❌ Error processing email {msg['id']}: {e}")
                continue
        
        header = f"📧 **Recent Emails:** {len(formatted_emails)} messages"
        return header + "\n\n" + "\n\n".join(formatted_emails)
        
    except Exception as e:
        print(f"❌ Error getting emails: {e}")
        return f"📧 **Email Error:** {str(e)}"

def send_email(to_email, subject, body, cc_email=None, bcc_email=None):
    """Send an email via Gmail"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Create message
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = subject
        message['From'] = gmail_user_email
        
        if cc_email:
            message['Cc'] = cc_email
        if bcc_email:
            message['Bcc'] = bcc_email
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send email
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ **Email Sent Successfully**\n📧 To: {to_email}\n📝 Subject: {subject}\n🕐 Sent at: {datetime.now(pytz.timezone('America/Toronto')).strftime('%H:%M')}"
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return f"❌ **Failed to send email:** {str(e)}"

def get_unread_count():
    """Get count of unread emails"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get unread emails count
        results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread in:inbox',
            maxResults=1
        ).execute()
        
        # Get the estimated total count
        unread_count = results.get('resultSizeEstimate', 0)
        
        if unread_count == 0:
            return "📧 **Inbox Status:** All caught up! No unread emails"
        elif unread_count == 1:
            return "📧 **Inbox Status:** 1 unread email"
        else:
            return f"📧 **Inbox Status:** {unread_count} unread emails"
        
    except Exception as e:
        print(f"❌ Error getting unread count: {e}")
        return f"📧 **Inbox Status Error:** {str(e)}"

def get_inbox_summary():
    """Get a comprehensive inbox summary"""
    if not gmail_service:
        return "📧 Gmail integration not available"
    
    try:
        # Get recent emails
        recent_emails = get_recent_emails(5, "in:inbox")
        
        # Get unread count
        unread_status = get_unread_count()
        
        # Combine into summary
        summary = f"""📧 **Inbox Executive Summary**

{unread_status}

**Recent Emails:**
{recent_emails.split('📧 **Recent Emails:** 5 messages')[1] if '📧 **Recent Emails:** 5 messages' in recent_emails else recent_emails}"""
        
        return summary
        
    except Exception as e:
        print(f"❌ Error getting inbox summary: {e}")
        return f"📧 **Inbox Summary Error:** {str(e)}"

# ============================================================================
# ENHANCED FUNCTION HANDLING
# ============================================================================

async def handle_rose_functions_enhanced(run, thread_id):
    """Enhanced function handling with complete calendar and Gmail management"""
    
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
            # CALENDAR FUNCTIONS
            if function_name == "get_today_schedule":
                output = get_today_schedule()
                    
            elif function_name == "create_calendar_event":
                title = arguments.get('title', '')
                start_time = arguments.get('start_time', '')
                end_time = arguments.get('end_time', '')
                calendar_type = arguments.get('calendar_type', 'calendar')
                description = arguments.get('description', '')
                
                if title and start_time and end_time:
                    output = create_calendar_event(title, start_time, end_time, calendar_type, description)
                else:
                    output = "❌ Missing required parameters: title, start_time, end_time"
            
            # GMAIL FUNCTIONS
            elif function_name == "get_recent_emails":
                max_results = arguments.get('max_results', 10)
                query = arguments.get('query', '')
                output = get_recent_emails(max_results, query)
                
            elif function_name == "send_email":
                to_email = arguments.get('to_email', '')
                subject = arguments.get('subject', '')
                body = arguments.get('body', '')
                cc_email = arguments.get('cc_email', None)
                bcc_email = arguments.get('bcc_email', None)
                
                if to_email and subject and body:
                    output = send_email(to_email, subject, body, cc_email, bcc_email)
                else:
                    output = "❌ Missing required parameters: to_email, subject, body"
                    
            elif function_name == "get_unread_count":
                output = get_unread_count()
                
            elif function_name == "get_inbox_summary":
                output = get_inbox_summary()
                
            else:
                output = f"❓ Function {function_name} not implemented yet"
                
        except Exception as e:
            print(f"❌ Function execution error: {e}")
            output = f"❌ Error executing {function_name}: {str(e)}"
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output[:1500]  # Keep within reasonable limits
        })
    
    # Submit tool outputs
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

def format_calendar_response_simple(response_text):
    """Simplify calendar responses by removing Strategic Analysis and Action Items"""
    import re
    
    # Check if this is a calendar-related response
    calendar_keywords = ["calendar", "meeting", "event", "scheduled", "appointment", "briefing"]
    is_calendar_response = any(keyword in response_text.lower() for keyword in calendar_keywords)
    
    if not is_calendar_response:
        return response_text  # Return unchanged for non-calendar responses
    
    # Extract Executive Summary
    executive_summary = ""
    summary_match = re.search(r'👑\s*\*\*Executive Summary:\*\*\s*([^👑📊🎯📅💼🗓️]*)', response_text, re.DOTALL)
    if summary_match:
        executive_summary = summary_match.group(1).strip()
    
    # Extract Meeting Details section (look for the original format)
    meeting_details = ""
    
    # Look for Meeting Details section with Google Calendar link
    meeting_details_match = re.search(r'💼\s*\*\*Meeting Details:\*\*\s*(.*?)(?=🔗|$)', response_text, re.DOTALL)
    if meeting_details_match:
        meeting_details = meeting_details_match.group(1).strip()
    
    # Look for the Google Calendar link section
    calendar_link = ""
    link_match = re.search(r'🔗\s*View Event.*?Google Calendar.*?(?:\n.*?)*', response_text, re.DOTALL)
    if link_match:
        calendar_link = link_match.group(0).strip()
    
    # If no Meeting Details found, try to extract from other sections
    if not meeting_details:
        # Try Calendar Coordination section
        coord_match = re.search(r'📅\s*\*\*Calendar Coordination:\*\*\s*([^👑📊🎯📅💼🗓️]*)', response_text, re.DOTALL)
        if coord_match:
            meeting_details = coord_match.group(1).strip()
        
        # If still nothing, extract basic meeting info
        if not meeting_details:
            detail_lines = []
            for line in response_text.split('\n'):
                if any(word in line.lower() for word in ['title:', 'date & time:', 'location:', 'calendar:', 'description:']):
                    detail_lines.append(f"• {line.strip()}")
            meeting_details = "\n".join(detail_lines) if detail_lines else "Meeting details confirmed"
    
    # Build the response with Meeting Details header
    simplified_response = f"""👑 **Executive Summary:**
{executive_summary}

💼 **Meeting Details:**
{meeting_details}"""
    
    # Add the calendar link if found
    if calendar_link:
        simplified_response += f"\n\n{calendar_link}"
    
    return simplified_response.strip()

async def get_rose_response(message, user_id):
    """Get response from Rose's enhanced OpenAI assistant with fixed API calls"""
    try:
        if not ASSISTANT_ID:
            return "⚠️ Rose not configured - check ROSE_ASSISTANT_ID environment variable"
        
        # Create user thread if needed
        if user_id not in user_conversations:
            thread = client.beta.threads.create()
            user_conversations[user_id] = thread.id
            print(f"👑 Created executive thread for user {user_id}")
        
        thread_id = user_conversations[user_id]
        
        # Clean message
        clean_message = message.replace(f'<@{bot.user.id}>', '').strip() if hasattr(bot, 'user') and bot.user else message.strip()
        
        # Get current date context for Rose
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
- GMAIL STATUS: {'Enabled' if gmail_service else 'Disabled'}
        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

CURRENT DATE & TIME CONTEXT:
- TODAY: {today_formatted} ({today_date})
- TOMORROW: {tomorrow_formatted} ({tomorrow_date})
- TIMEZONE: America/Toronto

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- AVAILABLE CALENDARS: {[name for name, _, _ in accessible_calendars]}
- GMAIL STATUS: {'Enabled' if gmail_service else 'Disabled'}
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
- Use executive calendar and email functions to provide comprehensive scheduling and communication insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines

FORMATTING: Use professional executive formatting with strategic headers (👑 📊 📅 🎯 💼 📧) and provide organized, action-oriented guidance.

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
                    
                    # NEW: Apply calendar response simplification
                    response = format_calendar_response_simple(response)
                    
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
        print(f"📧 Gmail Status: {'Connected' if gmail_service else 'Not configured'}")
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
# STANDARDIZED COMMANDS
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
    """Enhanced help command"""
    try:
        help_text = f"""👑 **{ASSISTANT_NAME} - Executive Assistant Commands**

**📅 Calendar & Scheduling:**
• `!today` - Today's executive schedule
• `!briefing` / `!daily` / `!morning` - Morning executive briefing

**📧 Gmail & Email:**
• `!inbox` - Recent inbox summary
• `!emails [count]` - Recent emails (default 10)
• `!unread` - Count of unread emails

**💼 Executive Functions:**
• `!status` - System and calendar status
• `!ping` - Test connectivity
• `!help` - This command menu

**📱 Usage:**
• Mention @{bot.user.name if bot.user else 'Rose'} in any message
• Available in: {', '.join(ALLOWED_CHANNELS)}

**💡 Example Commands:**
• `!briefing` - Get comprehensive morning briefing
• `!today` - See today's complete schedule
• `!inbox` - Check recent emails and unread count
• `@Rose send an email to john@example.com about meeting`
• `@Rose create a meeting tomorrow at 2pm`"""
        
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
        
        gmail_status = "❌ Not configured"
        if gmail_service and gmail_user_email:
            gmail_status = f"✅ Connected: {gmail_user_email}"
        
        assistant_status = "✅ Connected" if ASSISTANT_ID else "❌ Not configured"
        
        sa_info = "Not configured"
        if service_account_email:
            sa_info = f"✅ {service_account_email}"
        
        status_text = f"""👑 **{ASSISTANT_NAME} Executive Status**

**🤖 Core Systems:**
• Discord: ✅ Connected as {bot.user.name if bot.user else 'Unknown'}
• OpenAI Assistant: {assistant_status}
• Service Account: {sa_info}

**📅 Calendar Integration:**
• Status: {calendar_status}
• Timezone: 🇨🇦 Toronto (America/Toronto)

**📧 Gmail Integration:**
• Status: {gmail_status}

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

@bot.command(name='briefing')
async def briefing_command(ctx):
    """Morning executive briefing command"""
    try:
        async with ctx.typing():
            user_id = str(ctx.author.id)
            briefing_query = "morning executive briefing with calendar and email summary"
            response = await get_rose_response(briefing_query, user_id)
            await send_long_message(ctx.message, response)
    except Exception as e:
        print(f"❌ Briefing command error: {e}")
        await ctx.send("👑 Executive briefing unavailable. Please try again.")

@bot.command(name='inbox')
async def inbox_command(ctx):
    """Get inbox summary"""
    try:
        async with ctx.typing():
            summary = get_inbox_summary()
            await ctx.send(summary)
    except Exception as e:
        print(f"❌ Inbox command error: {e}")
        await ctx.send("📧 Inbox summary unavailable. Please try again.")

@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails"""
    try:
        async with ctx.typing():
            count = max(1, min(count, 25))  # Limit between 1-25
            emails = get_recent_emails(count)
            await send_long_message(ctx.message, emails)
    except Exception as e:
        print(f"❌ Emails command error: {e}")
        await ctx.send("📧 Recent emails unavailable. Please try again.")

@bot.command(name='unread')
async def unread_command(ctx):
    """Get unread email count"""
    try:
        async with ctx.typing():
            unread_status = get_unread_count()
            await ctx.send(unread_status)
    except Exception as e:
        print(f"❌ Unread command error: {e}")
        await ctx.send("📧 Unread count unavailable. Please try again.")

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
        print(f"📧 Gmail API: {bool(gmail_service)} gmail integration")
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