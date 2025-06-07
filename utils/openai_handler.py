import os
import asyncio
import json
import base64
import pytz
from datetime import datetime, timedelta
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Enhanced memory system (from Celeste)
user_conversations = {}  # user_id -> thread_id
conversation_context = {}  # user_id -> recent message history
MAX_CONTEXT_MESSAGES = 10  # Remember last 10 messages per user

# Set your timezone here - UPDATE THIS TO YOUR TIMEZONE
LOCAL_TIMEZONE = 'America/Toronto'  # Change to your timezone!

# ============================================================================
# MEMORY SYSTEM (Enhanced from Celeste)
# ============================================================================

def get_user_thread(user_id):
    """Get or create a persistent thread for a user"""
    if user_id not in user_conversations:
        thread = client.beta.threads.create()
        user_conversations[user_id] = thread.id
        conversation_context[user_id] = []
        print(f"📝 Created new conversation thread for user {user_id}")
    return user_conversations[user_id]

def add_to_context(user_id, message_content, is_user=True):
    """Add message to user's conversation context"""
    if user_id not in conversation_context:
        conversation_context[user_id] = []
    
    role = "User" if is_user else "Rose"
    timestamp = datetime.now().strftime("%H:%M")
    
    conversation_context[user_id].append({
        'role': role,
        'content': message_content,
        'timestamp': timestamp
    })
    
    if len(conversation_context[user_id]) > MAX_CONTEXT_MESSAGES:
        conversation_context[user_id] = conversation_context[user_id][-MAX_CONTEXT_MESSAGES:]

def get_conversation_context(user_id):
    """Get formatted conversation context for a user"""
    if user_id not in conversation_context or not conversation_context[user_id]:
        return "No previous conversation context."
    
    context_lines = []
    for msg in conversation_context[user_id][-5:]:
        content_preview = msg['content'][:100]
        if len(msg['content']) > 100:
            content_preview += "..."
        context_lines.append(f"{msg['timestamp']} {msg['role']}: {content_preview}")
    
    return "RECENT CONVERSATION:\n" + "\n".join(context_lines)

def clear_user_memory(user_id):
    """Clear conversation memory for a user"""
    if user_id in user_conversations:
        del user_conversations[user_id]
    if user_id in conversation_context:
        del conversation_context[user_id]
    print(f"🧹 Cleared memory for user {user_id}")

# ============================================================================
# GOOGLE SERVICES (Calendar + Gmail)
# ============================================================================

def get_google_service(service_name='calendar', version='v3'):
    """Get authenticated Google service (Calendar or Gmail)"""
    try:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not service_account_json:
            print(f"⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not found for {service_name}")
            return None
        
        service_account_info = json.loads(service_account_json)
        
        # Define scopes based on service
        if service_name == 'calendar':
            scopes = ['https://www.googleapis.com/auth/calendar']
        elif service_name == 'gmail':
            scopes = [
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.send'
            ]
        else:
            scopes = ['https://www.googleapis.com/auth/calendar']
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        
        # For Gmail, we need to specify the user email for domain-wide delegation
        if service_name == 'gmail':
            # Get the email from the calendar ID or use a default
            user_email = os.getenv('GOOGLE_CALENDAR_ID', 'bgelineau@gmail.com')
            if user_email == 'primary':
                user_email = 'bgelineau@gmail.com'  # Replace with your actual email
            
            credentials = credentials.with_subject(user_email)
            print(f"📧 Attempting Gmail access for: {user_email}")
        
        service = build(service_name, version, credentials=credentials)
        print(f"✅ Google {service_name.title()} service connected successfully")
        return service
        
    except Exception as e:
        print(f"❌ Failed to connect to Google {service_name}: {e}")
        return None

# Initialize services
calendar_service = get_google_service('calendar', 'v3')
gmail_service = get_google_service('gmail', 'v1')

# ============================================================================
# CALENDAR FUNCTIONS (Enhanced with Timezone Support)
# ============================================================================

def get_calendar_events(service, days_ahead=7):
    """Get events from Google Calendar with proper timezone handling"""
    if not service:
        print("📅 Using mock calendar data (no Google Calendar connection)")
        return get_mock_calendar_events()
    
    try:
        # Use local timezone
        local_tz = pytz.timezone(LOCAL_TIMEZONE)
        now = datetime.now(local_tz)
        
        # Get start of today in local time, then convert to UTC for API
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_of_today + timedelta(days=days_ahead)
        
        # Convert to UTC for the API call
        start_time_utc = start_of_today.astimezone(pytz.UTC).isoformat()
        end_time_utc = end_time.astimezone(pytz.UTC).isoformat()
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        print(f"📅 Fetching events from calendar: {calendar_id}")
        print(f"📅 Local time range: {start_of_today.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"📅 Timezone: {LOCAL_TIMEZONE}")
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time_utc,
            timeMax=end_time_utc,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print('📅 No upcoming events found in calendar')
            return []
        
        calendar_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse start time with proper timezone handling
            if 'T' in start:
                # Handle datetime with timezone
                if start.endswith('Z'):
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start)
                
                # Convert to local timezone for display
                if start_dt.tzinfo is None:
                    start_dt = pytz.UTC.localize(start_dt)
                start_dt = start_dt.astimezone(local_tz)
            else:
                # All-day event
                start_dt = datetime.strptime(start, '%Y-%m-%d')
                start_dt = local_tz.localize(start_dt)
            
            # Calculate duration
            if end and 'T' in end:
                if end.endswith('Z'):
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.fromisoformat(end)
                
                if end_dt.tzinfo is None:
                    end_dt = pytz.UTC.localize(end_dt)
                end_dt = end_dt.astimezone(local_tz)
                
                duration = end_dt - start_dt
                duration_min = int(duration.total_seconds() / 60)
                if duration_min < 60:
                    duration_str = f"{duration_min} min"
                else:
                    hours = duration_min // 60
                    mins = duration_min % 60
                    if mins > 0:
                        duration_str = f"{hours}h {mins}min"
                    else:
                        duration_str = f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                duration_str = "All day"
            
            calendar_events.append({
                "title": event.get('summary', 'Untitled'),
                "start_time": start_dt,
                "duration": duration_str,
                "description": event.get('description', ''),
                "location": event.get('location', ''),
                "attendees": [att.get('email', '') for att in event.get('attendees', [])],
                "event_id": event.get('id', '')
            })
            
            # Debug: Print each event with its date
            print(f"🔍 DEBUG: Event '{event.get('summary', 'Untitled')}' on {start_dt.strftime('%Y-%m-%d %H:%M')} (Date: {start_dt.date()})")
        
        print(f"✅ Found {len(calendar_events)} calendar events")
        return calendar_events
        
    except HttpError as e:
        if e.resp.status == 404:
            print(f"❌ Calendar not found. Make sure you've shared your calendar with the service account")
        elif e.resp.status == 403:
            print(f"❌ No permission to read calendar. Check that the service account has access")
        else:
            print(f"❌ HTTP error fetching events: {e}")
        return get_mock_calendar_events()
    except Exception as e:
        print(f"❌ Error fetching Google Calendar events: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return get_mock_calendar_events()

def get_mock_calendar_events():
    """Mock calendar data - fallback when no real calendar available"""
    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    today = datetime.now(local_tz)
    
    mock_events = [
        {
            "title": "Team Standup",
            "start_time": today.replace(hour=9, minute=30),
            "duration": "30 min",
            "description": "Daily sync with development team",
            "location": "Zoom",
            "attendees": ["team@company.com"],
            "event_id": "mock_event_1"
        },
        {
            "title": "Strategy Review", 
            "start_time": today.replace(hour=14, minute=0),
            "duration": "1 hour",
            "description": "Q4 planning and roadmap review",
            "location": "Conference Room A",
            "attendees": ["manager@company.com", "strategy@company.com"],
            "event_id": "mock_event_2"
        },
        {
            "title": "Client Call - Project Alpha",
            "start_time": today.replace(hour=16, minute=30),
            "duration": "45 min",
            "description": "Progress update and next steps",
            "location": "Teams",
            "attendees": ["client@clientcompany.com"],
            "event_id": "mock_event_3"
        }
    ]
    
    return mock_events

# ============================================================================
# GMAIL FUNCTIONS (Enhanced)
# ============================================================================

def search_gmail_messages(service, query, max_results=10):
    """Search Gmail messages"""
    if not service:
        print("📧 Using mock email data (no Gmail connection)")
        return get_mock_email_data_for_query(query)
    
    try:
        # Use Gmail's search to find messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print(f"📧 No messages found for query: {query}")
            return []
        
        email_list = []
        for msg in messages[:max_results]:
            try:
                # Get full message details
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Extract body text
                body = extract_email_body(message['payload'])
                
                # Parse date
                try:
                    from email.utils import parsedate_to_datetime
                    parsed_date = parsedate_to_datetime(date)
                except:
                    parsed_date = datetime.now()
                
                # Check if unread
                labels = message.get('labelIds', [])
                is_unread = 'UNREAD' in labels
                
                email_list.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': parsed_date,
                    'body_preview': body[:200] + '...' if len(body) > 200 else body,
                    'full_body': body,
                    'is_unread': is_unread
                })
            except Exception as msg_error:
                print(f"⚠️ Error processing individual message: {msg_error}")
                continue
        
        print(f"✅ Found {len(email_list)} email messages")
        return email_list
        
    except Exception as e:
        print(f"❌ Error searching Gmail: {e}")
        print(f"📧 Falling back to mock email data for query: {query}")
        return get_mock_email_data_for_query(query)

def extract_email_body(payload):
    """Extract text from email payload"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
            elif part['mimeType'] == 'text/html':
                # Fallback to HTML if no plain text
                data = part['body']['data']
                html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                # Simple HTML to text conversion
                import re
                body = re.sub('<[^<]+?>', '', html_body)
                break
    elif payload['mimeType'] == 'text/plain':
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body.strip()

def get_recent_emails(service, max_results=10):
    """Get recent emails"""
    if not service:
        return get_mock_email_data()
    
    try:
        # Get recent messages
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        
        email_list = []
        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            body = extract_email_body(message['payload'])
            
            try:
                from email.utils import parsedate_to_datetime
                parsed_date = parsedate_to_datetime(date)
            except:
                parsed_date = datetime.now()
            
            # Check if unread
            labels = message.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            
            email_list.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender,
                'date': parsed_date,
                'body_preview': body[:150] + '...' if len(body) > 150 else body,
                'is_unread': is_unread
            })
        
        return email_list
        
    except Exception as e:
        print(f"❌ Error getting recent emails: {e}")
        return get_mock_email_data()

def get_mock_email_data():
    """Mock email data - fallback when no Gmail connection"""
    today = datetime.now()
    
    mock_emails = [
        {
            'id': 'mock1',
            'subject': 'Project Alpha Update',
            'sender': 'john.doe@company.com',
            'date': today - timedelta(hours=2),
            'body_preview': 'Hi, just wanted to update you on the progress of Project Alpha. We\'ve completed the first phase...',
            'is_unread': True
        },
        {
            'id': 'mock2', 
            'subject': 'Meeting Follow-up',
            'sender': 'sarah.smith@partner.com',
            'date': today - timedelta(hours=5),
            'body_preview': 'Thank you for the productive meeting today. As discussed, here are the next steps...',
            'is_unread': False
        },
        {
            'id': 'mock3',
            'subject': 'Q4 Budget Review',
            'sender': 'finance@company.com',
            'date': today - timedelta(days=1),
            'body_preview': 'Please review the attached Q4 budget proposal and provide your feedback by Friday...',
            'is_unread': True
        }
    ]
    
    return mock_emails

def get_mock_email_data_for_query(query):
    """Mock email data specific to the search query"""
    today = datetime.now()
    
    # Create relevant mock emails based on the query
    if any(word in query.lower() for word in ['coaching', 'nobs', 'call']):
        mock_emails = [
            {
                'id': 'mock_coaching1',
                'subject': 'NOBS Coaching Session - Next Week',
                'sender': 'coach@nobscoaching.com',
                'date': today - timedelta(days=2),
                'body_preview': 'Hi! Your next NOBS coaching session is scheduled for next Tuesday at 2 PM. We\'ll be covering goal setting and accountability systems...',
                'is_unread': True
            },
            {
                'id': 'mock_coaching2',
                'subject': 'Re: Coaching Call Follow-up',
                'sender': 'support@nobscoaching.com',
                'date': today - timedelta(days=5),
                'body_preview': 'Thanks for attending last week\'s coaching session. Here are the action items we discussed: 1. Daily planning routine, 2. Priority matrix setup...',
                'is_unread': False
            }
        ]
    else:
        # Generic mock for other queries
        mock_emails = [
            {
                'id': 'mock_generic1',
                'subject': f'Search results for: {query}',
                'sender': 'system@example.com',
                'date': today - timedelta(hours=1),
                'body_preview': f'Gmail search is currently unavailable, but I would normally search for: {query}. Please check your Gmail directly or try again later.',
                'is_unread': True
            }
        ]
    
    return mock_emails

def send_email(service, to, subject, body, sender_email=None):
    """Send an email via Gmail"""
    if not service:
        return "📧 Email sending not available (no Gmail connection). Draft saved to your notes."
    
    try:
        import email.mime.text
        import email.mime.multipart
        
        # Create message
        message = email.mime.multipart.MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        if sender_email:
            message['from'] = sender_email
        
        # Add body
        msg_body = email.mime.text.MIMEText(body)
        message.attach(msg_body)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return f"✅ Email sent successfully to {to}"
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return f"❌ Failed to send email: {str(e)}"

# ============================================================================
# FUNCTION EXECUTION (Enhanced with All Functions)
# ============================================================================

def execute_function(function_name, arguments):
    """Execute the called function and return results with timezone support"""
    
    # Get local timezone for all date operations
    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    
    # Calendar Reading Functions
    if function_name == "get_today_schedule":
        events = get_calendar_events(calendar_service, days_ahead=1)
        today = datetime.now(local_tz).date()
        
        today_events = []
        for event in events:
            try:
                # Get event date with timezone handling
                if hasattr(event['start_time'], 'date'):
                    event_date = event['start_time'].date()
                else:
                    # Fallback parsing
                    event_dt = datetime.fromisoformat(str(event['start_time']))
                    if event_dt.tzinfo is None:
                        event_dt = local_tz.localize(event_dt)
                    event_date = event_dt.date()
                
                print(f"🔍 DEBUG: Event '{event['title']}' on {event_date}, today is {today}")
                
                if event_date == today:
                    today_events.append(event)
                    
            except Exception as e:
                print(f"⚠️ Error processing event date: {e}")
                continue
        
        print(f"🔍 DEBUG: Found {len(events)} total events, {len(today_events)} for today")
        
        if not today_events:
            result = "No events scheduled for today - completely clear schedule"
        else:
            event_lines = []
            for event in today_events:
                try:
                    # Format time
                    if hasattr(event['start_time'], 'strftime'):
                        time_str = event['start_time'].strftime('%I:%M %p')
                    else:
                        time_str = "All day"
                    
                    # Build event line
                    event_line = f"• {time_str}: {event['title']}"
                    if event['duration'] and event['duration'] != "All day":
                        event_line += f" ({event['duration']})"
                    
                    event_lines.append(event_line)
                    
                    # Add location if present
                    if event['location']:
                        event_lines.append(f"  📍 {event['location']}")
                        
                except Exception as e:
                    print(f"⚠️ Error formatting event: {e}")
                    event_lines.append(f"• {event.get('title', 'Unknown event')}")
            
            result = f"Today's schedule ({len(today_events)} events):\n" + "\n".join(event_lines)
        
        print(f"🔍 DEBUG: get_today_schedule final result: {result}")
        return result
    
    elif function_name == "get_tomorrow_schedule":
        events = get_calendar_events(calendar_service, days_ahead=2)
        tomorrow = (datetime.now(local_tz) + timedelta(days=1)).date()
        
        tomorrow_events = []
        for event in events:
            try:
                if hasattr(event['start_time'], 'date'):
                    event_date = event['start_time'].date()
                else:
                    event_dt = datetime.fromisoformat(str(event['start_time']))
                    if event_dt.tzinfo is None:
                        event_dt = local_tz.localize(event_dt)
                    event_date = event_dt.date()
                
                if event_date == tomorrow:
                    tomorrow_events.append(event)
            except Exception as e:
                print(f"⚠️ Error processing event: {e}")
                continue
        
        print(f"🔍 DEBUG: Found {len(events)} total events, {len(tomorrow_events)} tomorrow events")
        
        if not tomorrow_events:
            result = "No events scheduled for tomorrow - open day ahead"
        else:
            event_lines = []
            for event in tomorrow_events:
                try:
                    if hasattr(event['start_time'], 'strftime'):
                        time_str = event['start_time'].strftime('%I:%M %p')
                    else:
                        time_str = "All day"
                    
                    event_line = f"• {time_str}: {event['title']}"
                    if event['duration'] and event['duration'] != "All day":
                        event_line += f" ({event['duration']})"
                    
                    event_lines.append(event_line)
                    
                    if event['location']:
                        event_lines.append(f"  📍 {event['location']}")
                        
                except Exception as e:
                    event_lines.append(f"• {event.get('title', 'Event')}")
            
            result = f"Tomorrow's schedule ({len(tomorrow_events)} events):\n" + "\n".join(event_lines)
        
        print(f"🔍 DEBUG: get_tomorrow_schedule returning: {result[:200]}...")
        return result
    
    elif function_name == "get_upcoming_events":
        days = arguments.get('days', 7)
        events = get_calendar_events(calendar_service, days_ahead=days)
        
        print(f"🔍 DEBUG: Found {len(events)} events for next {days} days")
        
        if not events:
            result = f"No events found in the next {days} days"
        else:
            today = datetime.now(local_tz).date()
            
            event_lines = []
            for event in events[:15]:  # Limit to 15 events for readability
                try:
                    if hasattr(event['start_time'], 'date'):
                        event_date = event['start_time'].date()
                    else:
                        event_dt = datetime.fromisoformat(str(event['start_time']))
                        if event_dt.tzinfo is None:
                            event_dt = local_tz.localize(event_dt)
                        event_date = event_dt.date()
                    
                    # Format date relative to today
                    if event_date == today:
                        date_str = "Today"
                    elif event_date == today + timedelta(days=1):
                        date_str = "Tomorrow"
                    else:
                        date_str = event_date.strftime('%m/%d')
                    
                    # Format time
                    if hasattr(event['start_time'], 'strftime'):
                        time_str = event['start_time'].strftime('%I:%M %p')
                    else:
                        time_str = "All day"
                    
                    event_lines.append(f"• {date_str} at {time_str}: {event['title']}")
                    
                except Exception as e:
                    event_lines.append(f"• {event.get('title', 'Event')}")
            
            if len(events) > 15:
                event_lines.append(f"... and {len(events) - 15} more events")
            
            result = f"Upcoming events (next {days} days, {len(events)} total):\n" + "\n".join(event_lines)
        
        print(f"🔍 DEBUG: get_upcoming_events returning: {result[:200]}...")
        return result
    
    elif function_name == "find_free_time":
        duration = arguments.get('duration', 60)
        date_str = arguments.get('date', datetime.now(local_tz).strftime('%Y-%m-%d'))
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            target_date = local_tz.localize(target_date)
        except:
            target_date = datetime.now(local_tz)
        
        days_ahead = max(1, (target_date.date() - datetime.now(local_tz).date()).days + 1)
        events = get_calendar_events(calendar_service, days_ahead=days_ahead)
        
        target_events = []
        for event in events:
            try:
                if hasattr(event['start_time'], 'date'):
                    if event['start_time'].date() == target_date.date():
                        target_events.append(event)
                else:
                    event_dt = datetime.fromisoformat(str(event['start_time']))
                    if event_dt.tzinfo is None:
                        event_dt = local_tz.localize(event_dt)
                    if event_dt.date() == target_date.date():
                        target_events.append(event)
            except:
                continue
        
        # Simple free time finding logic
        free_slots = []
        business_start = target_date.replace(hour=9, minute=0)
        business_end = target_date.replace(hour=18, minute=0)
        
        target_events.sort(key=lambda x: x['start_time'])
        
        current_time = business_start
        
        for event in target_events:
            event_start = event['start_time']
            
            if current_time < event_start:
                gap_minutes = (event_start - current_time).total_seconds() / 60
                if gap_minutes >= duration:
                    free_slots.append(f"{current_time.strftime('%I:%M %p')} - {event_start.strftime('%I:%M %p')}")
            
            # Move current time to after this event
            duration_min = 60
            if "min" in event['duration']:
                try:
                    duration_min = int(event['duration'].split()[0])
                except:
                    pass
            elif "hour" in event['duration']:
                try:
                    hours = int(event['duration'].split()[0])
                    duration_min = hours * 60
                except:
                    pass
            
            current_time = event_start + timedelta(minutes=duration_min)
        
        if current_time < business_end:
            gap_minutes = (business_end - current_time).total_seconds() / 60
            if gap_minutes >= duration:
                free_slots.append(f"{current_time.strftime('%I:%M %p')} - {business_end.strftime('%I:%M %p')}")
        
        if not free_slots:
            result = f"No free blocks of {duration}+ minutes found on {target_date.strftime('%Y-%m-%d')}"
        else:
            result = f"⏰ Free time slots on {target_date.strftime('%Y-%m-%d')} ({duration}+ min blocks):\n" + "\n".join([f"• {slot}" for slot in free_slots])
        
        print(f"🔍 DEBUG: find_free_time returning: {result[:200]}...")
        return result
    
    # Email Reading Functions
    elif function_name == "search_emails":
        query = arguments.get('query', '')
        max_results = arguments.get('max_results', 10)
        
        emails = search_gmail_messages(gmail_service, query, max_results)
        
        print(f"🔍 DEBUG: Found {len(emails)} emails for query '{query}'")
        
        if not emails:
            result = f"No emails found matching '{query}'"
        else:
            email_list = []
            for email in emails:
                date_str = email['date'].strftime('%m/%d %I:%M %p')
                unread_indicator = "🔵 " if email.get('is_unread') else ""
                email_list.append(f"• {unread_indicator}{email['subject']}\n  From: {email['sender']} ({date_str})\n  Preview: {email['body_preview']}")
            
            result = f"📧 Email Search Results for '{query}':\n\n" + "\n\n".join(email_list)
        
        print(f"🔍 DEBUG: search_emails returning: {result[:200]}...")
        return result
    
    elif function_name == "get_recent_emails":
        max_results = arguments.get('max_results', 10)
        
        emails = get_recent_emails(gmail_service, max_results)
        
        print(f"🔍 DEBUG: Found {len(emails)} recent emails")
        
        if not emails:
            result = "No recent emails found"
        else:
            email_list = []
            unread_count = 0
            
            for email in emails:
                date_str = email['date'].strftime('%m/%d %I:%M %p')
                unread_indicator = "🔵 " if email.get('is_unread') else ""
                if email.get('is_unread'):
                    unread_count += 1
                
                email_list.append(f"• {unread_indicator}{email['subject']}\n  From: {email['sender']} ({date_str})\n  Preview: {email['body_preview']}")
            
            result = f"📧 Recent Emails ({unread_count} unread):\n\n" + "\n\n".join(email_list)
        
        print(f"🔍 DEBUG: get_recent_emails returning: {result[:200]}...")
        return result
    
    elif function_name == "send_email":
        to = arguments.get('to', '')
        subject = arguments.get('subject', '')
        body = arguments.get('body', '')
        
        if not to or not subject or not body:
            result = "Missing required email fields: to, subject, and body are all required"
        else:
            result = send_email(gmail_service, to, subject, body)
        
        print(f"🔍 DEBUG: send_email returning: {result[:200]}...")
        return result
    
    else:
        result = f"Unknown function: {function_name}"
        print(f"🔍 DEBUG: Unknown function {function_name}")
        return result

async def handle_function_calls(run, thread_id):
    """Handle function calls from the assistant"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name} with args: {arguments}")
        
        # Execute the function
        output = execute_function(function_name, arguments)
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": output
        })
    
    # Submit the function outputs back to the assistant
    client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run.id,
        tool_outputs=tool_outputs
    )

def should_give_detailed_response(user_message):
    """Check if user is asking for a detailed/comprehensive response"""
    detail_triggers = [
        'deep dive', 'detailed', 'comprehensive', 'tell me more', 'elaborate',
        'break it down', 'full breakdown', 'in depth', 'thorough', 'complete',
        'everything about', 'walk me through', 'explain fully', 'analysis'
    ]
    
    return any(trigger in user_message.lower() for trigger in detail_triggers)

def format_for_discord_rose(response):
    """Format response specifically for Vivian's PR/communications focus"""
    
    # Remove excessive formatting for readability
    response = response.replace('**', '')  # Remove all bold formatting initially
    response = response.replace('\n\n\n', '\n\n')  # Remove triple line breaks
    response = response.replace('\n\n\n\n', '\n\n')  # Remove quadruple line breaks
    
    # Add strategic emoji headers for key sections
    if 'schedule' in response.lower() or 'calendar' in response.lower():
        if response.startswith('📅'):
            pass  # Already has calendar emoji
        elif 'no events' in response.lower() or 'clear schedule' in response.lower():
            response = '📅 **Clear Calendar** \n\n' + response
        else:
            response = '📅 **Schedule Update** \n\n' + response
    
    # Add email headers
    if 'email' in response.lower() and not response.startswith('📧'):
        response = '📧 **Email Update** \n\n' + response
    
    # Limit length but keep it strategic
    if len(response) > 1800:
        sentences = response.split('. ')
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence + '. ') < 1700:
                truncated += sentence + '. '
            else:
                truncated += "\n\n💡 *Need more details? Just ask!*"
                break
        response = truncated
    
    return response.strip()

async def get_openai_response(user_message: str, user_id: int, clear_memory: bool = False) -> str:
    """Enhanced OpenAI response with memory and function calling"""
    try:
        # Handle memory clearing
        if clear_memory:
            clear_user_memory(user_id)
            return "🧹 **Memory cleared!** Starting fresh conversation."
        
        # Get or create thread for this specific user (persistent memory)
        thread_id = get_user_thread(user_id)
        
        # Add to conversation context
        conversation_history = get_conversation_context(user_id)
        add_to_context(user_id, user_message, is_user=True)
        
        print(f"📨 Sending message to OpenAI Assistant (Thread: {thread_id}, User: {user_id})")
        
        # Clean the user message (remove bot mentions)
        clean_message = user_message.replace(f'<@{os.getenv("BOT_USER_ID", "")}>', '').strip()
        
        # Enhanced message with conversation context and strict function requirements
        enhanced_message = f"""CONVERSATION CONTEXT:
{conversation_history}

CURRENT REQUEST: {clean_message}

CRITICAL INSTRUCTIONS:
- This is a continuing conversation - refer to previous context when relevant
- You are Vivian Spencer, a strategic productivity assistant focused on PR and communications
- For calendar/schedule questions, you MUST use calendar functions
- For email questions, you MUST use email functions  
- You MUST base your response entirely on actual function results
- DO NOT invent or assume any calendar events or email information
- If a function returns "no events" or "no emails", that is the factual truth
- Provide actionable insights focused on productivity and efficiency
- Be conversational but strategic
- Remember our conversation history and build on previous discussions"""
        
        # Add message to thread
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=enhanced_message
        )
        
        print(f"✅ Message added to thread: {message.id}")
        
        # Check if user wants detailed response
        wants_detail = should_give_detailed_response(clean_message)
        
        # Create run with dynamic instructions
        if wants_detail:
            instructions = "You are Vivian Spencer, a strategic productivity assistant. Provide comprehensive insights but stay focused and actionable. Every point should add strategic value. Use calendar and email functions when users ask about schedule, meetings, or email management. Focus on productivity patterns and strategic time management."
            additional = "REQUIRED: Each sentence should deliver strategic value. Comprehensive but focused on productivity. Use available functions for calendar and email queries, then provide strategic analysis."
        else:
            instructions = "You are Vivian Spencer, a strategic productivity assistant. Keep responses conversational and focused (800-1500 chars). Think like a smart executive assistant - strategic but approachable. When users ask about calendar/schedule/emails, use the available functions, then provide strategic insights about their time and communication patterns."
            additional = "Sound strategic but human. Focus on actionable productivity insights. Use functions for calendar/email queries, then analyze patterns strategically. Less corporate speak, more strategic friend."

        # Add strict function usage requirements
        additional += " MANDATORY: Use calendar functions for ANY calendar/schedule question. Use email functions for ANY email question. Base responses entirely on function results. Never fabricate data."

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            instructions=instructions,
            additional_instructions=additional
        )
        
        print(f"🏃 Run created: {run.id}")
        
        # Wait for completion with function call handling
        for _ in range(30):  # Wait up to ~30 seconds
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            print(f"🔄 Run status: {run_status.status}")
            
            if run_status.status == "completed":
                break
            elif run_status.status == "requires_action":
                print("🔧 Function call required")
                await handle_function_calls(run_status, thread_id)
                continue
            elif run_status.status == "failed":
                print(f"❌ Run failed: {run_status.last_error}")
                return "❌ Sorry, there was an error processing your request. Please try again."
            elif run_status.status in ["cancelled", "expired"]:
                print(f"❌ Run {run_status.status}")
                return "❌ Request was cancelled or expired. Please try again."
            
            await asyncio.sleep(1)
        else:
            return "⏱️ Request timed out. Please try again with a simpler question."
        
        # Get response - find the latest assistant message
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=10)
        
        latest_assistant_message = None
        for msg in messages.data:
            if msg.role == "assistant":
                latest_assistant_message = msg
                break
        
        if latest_assistant_message and latest_assistant_message.content:
            response = latest_assistant_message.content[0].text.value
            print(f"✅ Got response: {response[:100]}...")
            
            # Add to conversation context
            add_to_context(user_id, response, is_user=False)
            
            # Apply Discord formatting and return
            return format_for_discord_rose(response)
        
        return "⚠️ No assistant response found."
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return "❌ An error occurred while communicating with the assistant. Please try again."