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

# Rose's updated configuration to match other assistants
ASSISTANT_CONFIG = {
    "name": "Rose Ashcombe",
    "role": "Executive Assistant",
    "description": "Strategic planning specialist with calendar integration, email management, and productivity optimization",
    "emoji": "👑",
    "color": 0xDC2626,  # Red color (Tailwind red-600)
    "specialties": [
        "📅 Executive Planning",
        "🗓️ Calendar Management", 
        "📊 Productivity Systems",
        "📧 Email Management",
        "⚡ Time Optimization",
        "🎯 Life OS"
    ],
    "capabilities": [
        "Gmail Integration - Read, send, organize, and batch delete emails",
        "Calendar Management - Multi-calendar coordination with timezone handling",
        "Strategic Planning - Research-backed productivity and planning insights",
        "Morning Briefings - Comprehensive executive briefings with email and calendar data",
        "Batch Email Cleanup - Process 25-200 emails per operation"
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
        "!briefing / !daily / !morning - Morning executive briefing",
        "!schedule / !today - Today's executive schedule",
        "!upcoming [days] - Upcoming events (default: 7 days)",
        "!emails [count] - Recent emails (default: 10)",
        "!unread [count] - Unread emails only",
        "!emailstats - Email dashboard overview",
        "!quickemails [count] - Concise email view",
        "!emailcount - Just email counts",
        "!cleansender <email> [count] - Delete emails from sender",
        "!plan [query] / !research [query] - Planning research",
        "!ping - Test connectivity",
        "!status - System status",
        "!help - This help message"
    ],
    "channels": ["life-os", "calendar", "planning-hub", "general"]
}

def batch_delete_by_subject(subject_text, count=25):
    """Delete multiple emails containing specific text in subject line"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
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
        return f"📧 **Batch Cleanup:** Deleted emails with '{subject_text}'\n📊 **Processed:** {deleted_count} emails deleted\n🎯 **Status:** {status}"
        
    except Exception as e:
        print(f"❌ Error in batch_delete_by_subject: {e}")
        return f"❌ Error in batch cleanup: {str(e)}"

def batch_archive_old_emails(days_old, query_filter="", count=50):
    """Archive emails older than specified days"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Build query for old emails
        query = f"older_than:{days_old}d"
        if query_filter:
            query += f" {query_filter}"
        
        search_result = gmail_service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=min(count, 200)  # Cap at 200 for bulk operations
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 **Batch Cleanup:** No emails found older than {days_old} days"
        
        archived_count = 0
        failed_count = 0
        
        for message in messages:
            try:
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
        return f"📧 **Batch Cleanup:** Archived emails older than {days_old} days\n📊 **Processed:** {archived_count} emails archived\n🎯 **Status:** {status}"
        
    except Exception as e:
        print(f"❌ Error in batch_archive_old_emails: {e}")
        return f"❌ Error in batch archive: {str(e)}"

def cleanup_promotional_emails(action="archive", count=50):
    """Clean up promotional/marketing emails in bulk"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
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
        
        action_word = "deleted" if action == "delete" else "archived"
        status = "Success" if failed_count == 0 else f"Partial ({failed_count} failed)"
        return f"📧 **Batch Cleanup:** {action_word.title()} promotional emails\n📊 **Processed:** {processed_count} emails {action_word}\n🎯 **Status:** {status}"
        
    except Exception as e:
        print(f"❌ Error in cleanup_promotional_emails: {e}")
        return f"❌ Error in promotional cleanup: {str(e)}"

def get_recent_emails_large(count=50, query="in:inbox"):
    """Get large number of recent emails for review (up to 100)"""
    try:
        if not gmail_service:
            return "📧 Gmail integration not available"
        
        # Cap the count at 100 for performance
        safe_count = min(count, 100)
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=safe_count
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📧 No emails found for query: {query}"
        
        email_list = []
        for msg in messages[:safe_count]:
            email_data = get_email_details(msg['id'])
            if email_data:
                email_list.append(format_email_concise(email_data))
        
        if email_list:
            total_size = results.get('resultSizeEstimate', len(email_list))
            return f"📧 **Large Email Review** ({len(email_list)} of {total_size} emails):\n\n" + "\n\n".join(email_list)
        else:
            return "📧 No emails retrieved"
            
    except Exception as e:
        print(f"❌ Error getting large email list: {e}")
        return f"❌ Error retrieving emails: {str(e)}"

# ============================================================================
# BRIEFING AND PLANNING FUNCTIONS
# ============================================================================

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
        
        # Get tomorrow's events
        tomorrow_events = get_upcoming_events(1)
        
        # Add email stats if Gmail is available
        email_summary = ""
        if gmail_service:
            try:
                stats = get_email_stats()
                email_summary = f"\n\n📧 **Email Overview:**\n{stats}"
            except Exception as e:
                print(f"❌ Error getting email stats for briefing: {e}")
        
        # Combine into morning briefing with correct Toronto date
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        briefing = f"🌅 **Good Morning! Executive Briefing for {current_time}**\n\n{today_schedule}\n\n{tomorrow_events}{email_summary}\n\n💼 **Executive Focus:** Prioritize high-impact activities during peak energy hours"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        print(f"📋 Morning briefing traceback: {traceback.format_exc()}")
        return "🌅 **Morning Briefing:** Error generating briefing - please check calendar apps manually"

async def planning_search(query, focus_area="general"):
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

# ============================================================================
# GOOGLE SERVICES INITIALIZATION WITH OAUTH2 FOR GMAIL
# ============================================================================

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
        
        #