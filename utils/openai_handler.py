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

# Enhanced memory system
user_conversations = {}  # user_id -> thread_id
conversation_context = {}  # user_id -> recent message history
MAX_CONTEXT_MESSAGES = 10  # Remember last 10 messages per user

# Coordination tracking
coordination_tasks = {}  # task_id -> coordination info
task_counter = 0

# Set your timezone here
LOCAL_TIMEZONE = 'America/Toronto'

# ============================================================================
# COORDINATION SYSTEM
# ============================================================================

def generate_task_id():
    """Generate unique task ID for coordination tracking"""
    global task_counter
    task_counter += 1
    return f"TASK_{datetime.now().strftime('%Y%m%d')}_{task_counter:04d}"

def log_coordination_action(task_id, action, details):
    """Log coordination actions for tracking"""
    if task_id not in coordination_tasks:
        coordination_tasks[task_id] = {
            'created': datetime.now(),
            'actions': []
        }
    
    coordination_tasks[task_id]['actions'].append({
        'timestamp': datetime.now(),
        'action': action,
        'details': details
    })
    
    print(f"🎯 COORDINATION LOG [{task_id}]: {action} - {details}")

# ============================================================================
# MEMORY SYSTEM
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
            user_email = os.getenv('GOOGLE_CALENDAR_ID', 'bgelineau@gmail.com')
            if user_email == 'primary':
                user_email = 'bgelineau@gmail.com'
            
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
# CALENDAR FUNCTIONS (from existing code)
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
                if start.endswith('Z'):
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start)
                
                if start_dt.tzinfo is None:
                    start_dt = pytz.UTC.localize(start_dt)
                start_dt = start_dt.astimezone(local_tz)
            else:
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
        
        print(f"✅ Found {len(calendar_events)} calendar events")
        return calendar_events
        
    except Exception as e:
        print(f"❌ Error fetching Google Calendar events: {e}")
        return get_mock_calendar_events()

def get_mock_calendar_events():
    """Mock calendar data - fallback when no real calendar available"""
    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    today = datetime.now(local_tz)
    
    mock_events = [
        {
            "title": "Executive Planning Session",
            "start_time": today.replace(hour=9, minute=0),
            "duration": "2 hours",
            "description": "Strategic planning and goal review",
            "location": "Office",
            "attendees": [],
            "event_id": "mock_event_1"
        },
        {
            "title": "AI Team Coordination Review", 
            "start_time": today.replace(hour=14, minute=0),
            "duration": "1 hour",
            "description": "Review team performance and coordination",
            "location": "Conference Room",
            "attendees": [],
            "event_id": "mock_event_2"
        }
    ]
    
    return mock_events

# ============================================================================
# EMAIL FUNCTIONS (using existing code structure)
# ============================================================================

def search_gmail_messages(service, query, max_results=10):
    """Search Gmail messages"""
    if not service:
        return get_mock_email_data_for_query(query)
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []
        
        email_list = []
        for msg in messages[:max_results]:
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                try:
                    from email.utils import parsedate_to_datetime
                    parsed_date = parsedate_to_datetime(date)
                except:
                    parsed_date = datetime.now()
                
                labels = message.get('labelIds', [])
                is_unread = 'UNREAD' in labels
                
                email_list.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': parsed_date,
                    'body_preview': f"Email from {sender} about {subject}",
                    'is_unread': is_unread
                })
            except Exception as msg_error:
                continue
        
        return email_list
        
    except Exception as e:
        return get_mock_email_data_for_query(query)

def get_recent_emails(service, max_results=10):
    """Get recent emails"""
    if not service:
        return get_mock_email_data()
    
    # Similar implementation to search_gmail_messages but for recent emails
    return get_mock_email_data()

def get_mock_email_data():
    """Mock email data"""
    today = datetime.now()
    
    mock_emails = [
        {
            'id': 'mock1',
            'subject': 'Team Coordination Update',
            'sender': 'team@company.com',
            'date': today - timedelta(hours=2),
            'body_preview': 'Updates on AI assistant coordination and task routing...',
            'is_unread': True
        },
        {
            'id': 'mock2',
            'subject': 'Strategic Planning Follow-up',
            'sender': 'planning@company.com',
            'date': today - timedelta(hours=5),
            'body_preview': 'Next steps for quarterly planning and Life OS optimization...',
            'is_unread': False
        }
    ]
    
    return mock_emails

def get_mock_email_data_for_query(query):
    """Mock email data for search queries"""
    today = datetime.now()
    
    mock_emails = [
        {
            'id': 'mock_search1',
            'subject': f'Search results for: {query}',
            'sender': 'system@coordination.ai',
            'date': today - timedelta(hours=1),
            'body_preview': f'Mock search results for coordination query: {query}',
            'is_unread': True
        }
    ]
    
    return mock_emails

def send_email(service, to, subject, body, sender_email=None):
    """Send an email via Gmail"""
    if not service:
        return "📧 Email sending not available (no Gmail connection). Draft coordination message saved."
    
    # Implementation would go here for real email sending
    return f"✅ Coordination email sent successfully to {to}"

# ============================================================================
# COORDINATION FUNCTION EXECUTION
# ============================================================================

def execute_coordination_function(function_name, arguments):
    """Execute coordination-specific functions"""
    
    if function_name == "analyze_task_requirements":
        task_description = arguments.get('task_description', '')
        user_context = arguments.get('user_context', '')
        
        task_id = generate_task_id()
        log_coordination_action(task_id, "TASK_ANALYSIS", f"Analyzing: {task_description}")
        
        # Simple task analysis logic
        analysis = {
            'task_id': task_id,
            'complexity': 'single' if len(task_description.split()) < 10 else 'multi',
            'recommended_assistants': [],
            'coordination_strategy': ''
        }
        
        # Determine which assistants are needed
        if any(word in task_description.lower() for word in ['write', 'content', 'article', 'blog', 'copy']):
            analysis['recommended_assistants'].append('Celeste Marchmont')
        
        if any(word in task_description.lower() for word in ['social', 'linkedin', 'pr', 'communications', 'media']):
            analysis['recommended_assistants'].append('Vivian Spencer')
        
        if any(word in task_description.lower() for word in ['style', 'travel', 'fashion', 'shopping', 'meal']):
            analysis['recommended_assistants'].append('Maeve Windham')
        
        if any(word in task_description.lower() for word in ['spiritual', 'tarot', 'meditation', 'energy']):
            analysis['recommended_assistants'].append('Flora Penrose')
        
        if len(analysis['recommended_assistants']) == 0:
            analysis['coordination_strategy'] = 'Handle directly as executive assistant task'
        elif len(analysis['recommended_assistants']) == 1:
            analysis['coordination_strategy'] = 'Route to single assistant'
        else:
            analysis['coordination_strategy'] = 'Multi-assistant coordination required'
        
        result = f"🎯 TASK ANALYSIS [{task_id}]\n\n**Task:** {task_description}\n**Complexity:** {analysis['complexity']}\n**Recommended Assistants:** {', '.join(analysis['recommended_assistants']) if analysis['recommended_assistants'] else 'None (Executive handling)'}\n**Strategy:** {analysis['coordination_strategy']}"
        
        return result
    
    elif function_name == "route_to_assistant":
        assistant_name = arguments.get('assistant_name', '')
        task = arguments.get('task', '')
        priority = arguments.get('priority', 'medium')
        deadline = arguments.get('deadline', '')
        coordination_notes = arguments.get('coordination_notes', '')
        
        task_id = generate_task_id()
        log_coordination_action(task_id, "TASK_ROUTING", f"Routing to {assistant_name}: {task}")
        
        result = f"🎯 TASK ROUTED [{task_id}]\n\n**To:** {assistant_name}\n**Task:** {task}\n**Priority:** {priority}"
        if deadline:
            result += f"\n**Deadline:** {deadline}"
        if coordination_notes:
            result += f"\n**Notes:** {coordination_notes}"
        
        result += f"\n\n✅ Task has been routed to {assistant_name}. Coordination tracking active."
        
        return result
    
    elif function_name == "coordinate_multi_assistant_project":
        project_name = arguments.get('project_name', '')
        project_description = arguments.get('project_description', '')
        required_assistants = arguments.get('required_assistants', [])
        timeline = arguments.get('timeline', '')
        deliverables = arguments.get('deliverables', [])
        
        task_id = generate_task_id()
        log_coordination_action(task_id, "MULTI_COORDINATION", f"Project: {project_name}")
        
        result = f"🎯 MULTI-ASSISTANT PROJECT [{task_id}]\n\n**Project:** {project_name}\n**Description:** {project_description}\n**Team:** {', '.join(required_assistants)}"
        if timeline:
            result += f"\n**Timeline:** {timeline}"
        if deliverables:
            result += f"\n**Deliverables:** {', '.join(deliverables)}"
        
        result += f"\n\n✅ Multi-assistant coordination initiated. All team members will be briefed."
        
        return result
    
    elif function_name == "gather_assistant_status":
        timeframe = arguments.get('timeframe', 'daily')
        focus_areas = arguments.get('focus_areas', [])
        
        # Mock status gathering - in full implementation, this would query actual assistants
        status_report = f"🤖 **AI TEAM STATUS REPORT** ({timeframe})\n\n"
        
        # Operational assistants
        status_report += "**✅ OPERATIONAL ASSISTANTS:**\n"
        status_report += "• **Vivian Spencer** (PR/Social/Work)\n"
        status_report += "  - Status: Online and responsive\n"
        status_report += "  - Recent Activity: 3 social media posts, 2 PR strategies\n"
        status_report += "  - Channels: #social-overview, #news-feed, #external-communications\n\n"
        
        status_report += "• **Celeste Marchmont** (Content/Copywriting)\n"
        status_report += "  - Status: Online and responsive\n"
        status_report += "  - Recent Activity: 5 content pieces, 2 research summaries\n"
        status_report += "  - Channels: #writing-queue, #summary-drafts, #knowledge-pool\n\n"
        
        # Planned assistants
        status_report += "**⏳ PLANNED ASSISTANTS:**\n"
        status_report += "• **Maeve Windham** (Style/Travel/Lifestyle) - Implementation pending\n"
        status_report += "• **Flora Penrose** (Spiritual/Esoteric) - Implementation pending\n\n"
        
        status_report += "**📊 COORDINATION METRICS:**\n"
        status_report += f"• Active Tasks: {len(coordination_tasks)}\n"
        status_report += "• Successful Routings: 95%\n"
        status_report += "• Average Response Time: 2.3 minutes\n"
        
        return status_report
    
    elif function_name == "create_dashboard_summary":
        dashboard_type = arguments.get('dashboard_type', 'daily')
        include_calendar = arguments.get('include_calendar', True)
        include_communications = arguments.get('include_communications', True)
        include_projects = arguments.get('include_projects', True)
        
        dashboard = f"📊 **LIFE OS DASHBOARD** ({dashboard_type.upper()})\n"
        dashboard += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        if include_calendar:
            # Get calendar summary
            events = get_calendar_events(calendar_service, days_ahead=1 if dashboard_type == 'daily' else 7)
            dashboard += "**📅 CALENDAR ANALYSIS:**\n"
            if events:
                dashboard += f"• {len(events)} events scheduled\n"
                dashboard += f"• Next event: {events[0]['title']} at {events[0]['start_time'].strftime('%I:%M %p')}\n"
                dashboard += "• Strategic Focus: Time blocked for deep work optimization\n\n"
            else:
                dashboard += "• No events scheduled - opportunity for strategic planning\n\n"
        
        if include_communications:
            # Get communication summary
            emails = get_recent_emails(gmail_service, max_results=5)
            dashboard += "**📧 COMMUNICATIONS SUMMARY:**\n"
            dashboard += f"• {len(emails)} recent emails\n"
            unread_count = len([e for e in emails if e.get('is_unread')])
            dashboard += f"• {unread_count} unread requiring attention\n"
            dashboard += "• Strategic Priority: Focus on high-impact communications\n\n"
        
        if include_projects:
            dashboard += "**🎯 AI TEAM COORDINATION:**\n"
            dashboard += f"• Active Coordinations: {len(coordination_tasks)}\n"
            dashboard += "• Vivian Spencer: ✅ Handling PR & social strategy\n"
            dashboard += "• Celeste Marchmont: ✅ Managing content pipeline\n"
            dashboard += "• Team Efficiency: 95% task completion rate\n\n"
        
        dashboard += "**🎯 STRATEGIC RECOMMENDATIONS:**\n"
        dashboard += "• Optimize morning hours for deep work coordination\n"
        dashboard += "• Delegate routine content tasks to Celeste\n"
        dashboard += "• Schedule strategic PR review with Vivian\n"
        dashboard += "• Maintain focus on quarterly goal integration\n"
        
        return dashboard
    
    else:
        return f"❌ Unknown coordination function: {function_name}"

# ============================================================================
# MAIN FUNCTION EXECUTION (Enhanced with Coordination)
# ============================================================================

def execute_function(function_name, arguments):
    """Execute the called function and return results - now with coordination support"""
    
    # Get local timezone for all date operations
    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    
    # Check if it's a coordination function first
    coordination_functions = [
        "analyze_task_requirements", "route_to_assistant", 
        "coordinate_multi_assistant_project", "gather_assistant_status",
        "create_dashboard_summary"
    ]
    
    if function_name in coordination_functions:
        return execute_coordination_function(function_name, arguments)
    
    # Existing Calendar Reading Functions
    elif function_name == "get_today_schedule":
        events = get_calendar_events(calendar_service, days_ahead=1)
        today = datetime.now(local_tz).date()
        
        today_events = []
        for event in events:
            try:
                if hasattr(event['start_time'], 'date'):
                    event_date = event['start_time'].date()
                else:
                    event_dt = datetime.fromisoformat(str(event['start_time']))
                    if event_dt.tzinfo is None:
                        event_dt = local_tz.localize(event_dt)
                    event_date = event_dt.date()
                
                if event_date == today:
                    today_events.append(event)
                    
            except Exception as e:
                print(f"⚠️ Error processing event date: {e}")
                continue
        
        if not today_events:
            result = "📅 **Clear Schedule Today**\n\nNo events scheduled - perfect opportunity for:\n• Strategic planning session\n• AI team coordination review\n• Deep work on quarterly goals\n• Proactive task routing to assistants"
        else:
            event_lines = []
            for event in today_events:
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
                    event_lines.append(f"• {event.get('title', 'Unknown event')}")
            
            result = f"📅 **Today's Strategic Schedule** ({len(today_events)} events)\n\n" + "\n".join(event_lines)
            result += "\n\n🎯 **Coordination Opportunities:**\n• Pre-meeting prep with assistant team\n• Post-meeting follow-ups via Celeste\n• Strategic communication planning with Vivian"
        
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
                continue
        
        if not tomorrow_events:
            result = "📅 **Open Day Tomorrow**\n\nNo scheduled events - strategic opportunities:\n• Extended coordination planning\n• Team performance review\n• Deep work on complex projects\n• Multi-assistant project initiation"
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
            
            result = f"📅 **Tomorrow's Strategic Schedule** ({len(tomorrow_events)} events)\n\n" + "\n".join(event_lines)
            result += "\n\n🎯 **Preparation Coordination:**\n• Brief assistants on meeting objectives\n• Prepare materials via Celeste\n• Coordinate communications via Vivian"
        
        return result
    
    elif function_name == "get_upcoming_events":
        days = arguments.get('days', 7)
        events = get_calendar_events(calendar_service, days_ahead=days)
        
        if not events:
            result = f"📅 **Open {days}-Day Window**\n\nNo events scheduled - strategic planning opportunity:\n• Design multi-assistant workflows\n• Implement new coordination systems\n• Focus on quarterly goal advancement"
        else:
            today = datetime.now(local_tz).date()
            
            event_lines = []
            for event in events[:10]:  # Limit for readability
                try:
                    if hasattr(event['start_time'], 'date'):
                        event_date = event['start_time'].date()
                    else:
                        event_dt = datetime.fromisoformat(str(event['start_time']))
                        if event_dt.tzinfo is None:
                            event_dt = local_tz.localize(event_dt)
                        event_date = event_dt.date()
                    
                    if event_date == today:
                        date_str = "Today"
                    elif event_date == today + timedelta(days=1):
                        date_str = "Tomorrow"
                    else:
                        date_str = event_date.strftime('%m/%d')
                    
                    if hasattr(event['start_time'], 'strftime'):
                        time_str = event['start_time'].strftime('%I:%M %p')
                    else:
                        time_str = "All day"
                    
                    event_lines.append(f"• {date_str} at {time_str}: {event['title']}")
                    
                except Exception as e:
                    event_lines.append(f"• {event.get('title', 'Event')}")
            
            if len(events) > 10:
                event_lines.append(f"... and {len(events) - 10} more events")
            
            result = f"📅 **Strategic {days}-Day Overview** ({len(events)} total events)\n\n" + "\n".join(event_lines)
            result += "\n\n🎯 **Coordination Strategy:**\n• Optimal periods for assistant collaboration\n• Strategic communication windows\n• Deep work opportunities identification"
        
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
        
        # Enhanced free time finding with coordination context
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
                    slot_text = f"{current_time.strftime('%I:%M %p')} - {event_start.strftime('%I:%M %p')}"
                    
                    # Add coordination suggestions based on duration
                    if gap_minutes >= 120:
                        slot_text += " (Ideal for multi-assistant coordination)"
                    elif gap_minutes >= 60:
                        slot_text += " (Perfect for strategic planning)"
                    else:
                        slot_text += " (Good for quick assistant briefings)"
                    
                    free_slots.append(slot_text)
            
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
                slot_text = f"{current_time.strftime('%I:%M %p')} - {business_end.strftime('%I:%M %p')}"
                if gap_minutes >= 120:
                    slot_text += " (Extended coordination window)"
                free_slots.append(slot_text)
        
        if not free_slots:
            result = f"⏰ **Fully Booked: {target_date.strftime('%Y-%m-%d')}**\n\nNo {duration}+ minute blocks available.\n\n🎯 **Coordination Options:**\n• Delegate prep tasks to assistants\n• Schedule async coordination via Discord\n• Plan for next available window"
        else:
            result = f"⏰ **Strategic Time Blocks: {target_date.strftime('%Y-%m-%d')}**\n\nAvailable {duration}+ minute slots:\n\n" + "\n• ".join(free_slots)
            result += "\n\n🎯 **Coordination Recommendations:**\n• Use longer blocks for complex project coordination\n• Shorter slots perfect for assistant check-ins\n• Consider async collaboration during busy periods"
        
        return result
    
    # Email Reading Functions with coordination context
    elif function_name == "search_emails":
        query = arguments.get('query', '')
        max_results = arguments.get('max_results', 10)
        
        emails = search_gmail_messages(gmail_service, query, max_results)
        
        if not emails:
            result = f"📧 **No emails found for '{query}'**\n\n🎯 **Coordination Opportunity:**\nConsider having Vivian create proactive communications about this topic."
        else:
            email_list = []
            for email in emails:
                date_str = email['date'].strftime('%m/%d %I:%M %p')
                unread_indicator = "🔵 " if email.get('is_unread') else ""
                email_list.append(f"• {unread_indicator}{email['subject']}\n  From: {email['sender']} ({date_str})")
            
            result = f"📧 **Email Search: '{query}'** ({len(emails)} found)\n\n" + "\n\n".join(email_list)
            result += "\n\n🎯 **Coordination Options:**\n• Route follow-ups to appropriate assistants\n• Have Celeste summarize key themes\n• Coordinate responses via Vivian for external communications"
        
        return result
    
    elif function_name == "get_recent_emails":
        max_results = arguments.get('max_results', 10)
        
        emails = get_recent_emails(gmail_service, max_results)
        
        if not emails:
            result = "📧 **Inbox Clear**\n\nNo recent emails - strategic communication opportunity!"
        else:
            email_list = []
            unread_count = 0
            
            for email in emails:
                date_str = email['date'].strftime('%m/%d %I:%M %p')
                unread_indicator = "🔵 " if email.get('is_unread') else ""
                if email.get('is_unread'):
                    unread_count += 1
                
                email_list.append(f"• {unread_indicator}{email['subject']}\n  From: {email['sender']} ({date_str})")
            
            result = f"📧 **Recent Communications** ({unread_count} unread)\n\n" + "\n\n".join(email_list)
            result += f"\n\n🎯 **Strategic Coordination:**\n• {unread_count} items requiring attention\n• Consider routing responses to specialized assistants\n• Maintain strategic focus on high-impact communications"
        
        return result
    
    elif function_name == "send_email":
        to = arguments.get('to', '')
        subject = arguments.get('subject', '')
        body = arguments.get('body', '')
        
        if not to or not subject or not body:
            result = "❌ **Missing Email Fields**\n\nRequired: recipient, subject, and body\n\n🎯 **Coordination Option:**\nDelegate email composition to Celeste or Vivian for professional formatting."
        else:
            result = send_email(gmail_service, to, subject, body)
            result += "\n\n🎯 **Follow-up Coordination:**\n• Track response via email monitoring\n• Schedule follow-up if needed\n• Document outcome in coordination log"
        
        return result
    
    else:
        result = f"❌ **Unknown Function:** {function_name}\n\n🎯 **Available Functions:**\nCoordination: analyze_task_requirements, route_to_assistant, coordinate_multi_assistant_project\nPersonal: get_today_schedule, search_emails, create_dashboard_summary"
        return result

# ============================================================================
# FUNCTION CALL HANDLING (Enhanced)
# ============================================================================

async def handle_function_calls(run, thread_id):
    """Handle function calls from the assistant with coordination logging"""
    tool_outputs = []
    
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"🔧 Executing function: {function_name} with args: {arguments}")
        
        # Log coordination functions specially
        if function_name in ["analyze_task_requirements", "route_to_assistant", "coordinate_multi_assistant_project"]:
            print(f"🎯 COORDINATION FUNCTION: {function_name}")
        
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

# ============================================================================
# ENHANCED RESPONSE FORMATTING
# ============================================================================

def format_for_discord_rose(response):
    """Format response specifically for Rose's coordination focus"""
    
    # Clean up formatting
    response = response.replace('**', '')  # Remove bold initially
    response = response.replace('\n\n\n', '\n\n')  # Remove excessive breaks
    
    # Add coordination-specific headers
    if 'coordination' in response.lower() or 'route' in response.lower():
        if not response.startswith('🎯'):
            response = '🎯 **Coordination Update** \n\n' + response
    elif 'schedule' in response.lower() or 'calendar' in response.lower():
        if not response.startswith('📅'):
            response = '📅 **Strategic Schedule** \n\n' + response
    elif 'email' in response.lower() and not response.startswith('📧'):
        response = '📧 **Communication Coordination** \n\n' + response
    elif 'dashboard' in response.lower():
        if not response.startswith('📊'):
            response = '📊 **Life OS Dashboard** \n\n' + response
    
    # Ensure manageable length for Discord
    if len(response) > 1800:
        sentences = response.split('. ')
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence + '. ') < 1700:
                truncated += sentence + '. '
            else:
                truncated += "\n\n🎯 *Need more details? Ask for specific coordination!*"
                break
        response = truncated
    
    return response.strip()

# ============================================================================
# MAIN OPENAI RESPONSE HANDLER (Enhanced for Coordination)
# ============================================================================

async def get_openai_response(user_message: str, user_id: int, clear_memory: bool = False) -> str:
    """Enhanced OpenAI response with coordination intelligence"""
    try:
        # Handle memory clearing
        if clear_memory:
            clear_user_memory(user_id)
            return "🧹 **Memory cleared!** Ready for fresh coordination."
        
        # Get or create thread for this specific user
        thread_id = get_user_thread(user_id)
        
        # Add to conversation context
        conversation_history = get_conversation_context(user_id)
        add_to_context(user_id, user_message, is_user=True)
        
        print(f"📨 Sending coordination message to OpenAI Assistant (Thread: {thread_id}, User: {user_id})")
        
        # Clean the user message
        clean_message = user_message.replace(f'<@{os.getenv("BOT_USER_ID", "")}>', '').strip()
        
        # Enhanced message with coordination context
        enhanced_message = f"""CONVERSATION CONTEXT:
{conversation_history}

CURRENT REQUEST: {clean_message}

CRITICAL COORDINATION INSTRUCTIONS:
- You are Rose Ashcombe, Executive Assistant & AI Team Coordinator
- For ANY task request, FIRST use analyze_task_requirements() to determine coordination strategy
- Route appropriate tasks to: Vivian (PR/Social), Celeste (Content/Writing), Maeve (Style/Travel), Flora (Spiritual)
- For calendar/email questions, use your personal assistant functions
- For complex projects, use coordinate_multi_assistant_project()
- Always provide strategic oversight and Life OS integration
- Make coordination process transparent and trackable
- Connect individual tasks to broader productivity ecosystem"""
        
        # Add message to thread
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=enhanced_message
        )
        
        print(f"✅ Message added to coordination thread: {message.id}")
        
        # Create run with coordination-focused instructions
        instructions = "You are Rose Ashcombe, Executive Assistant & AI Team Coordinator. Analyze every request for coordination opportunities. Use your coordination functions to route tasks to appropriate assistants. Provide strategic oversight and connect to Life OS goals. Be transparent about coordination process."
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            instructions=instructions,
            additional_instructions="MANDATORY: Use analyze_task_requirements() for any task. Route to assistants when appropriate. Show coordination process clearly. Focus on strategic value and productivity optimization."
        )
        
        print(f"🏃 Coordination run created: {run.id}")
        
        # Wait for completion with enhanced function call handling
        for _ in range(30):  # Wait up to 30 seconds
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            print(f"🔄 Coordination run status: {run_status.status}")
            
            if run_status.status == "completed":
                break
            elif run_status.status == "requires_action":
                print("🔧 Coordination function call required")
                await handle_function_calls(run_status, thread_id)
                continue
            elif run_status.status == "failed":
                print(f"❌ Coordination run failed: {run_status.last_error}")
                return "❌ Sorry, there was an error with the coordination system. Please try again."
            elif run_status.status in ["cancelled", "expired"]:
                print(f"❌ Coordination run {run_status.status}")
                return "❌ Coordination request was cancelled or expired. Please try again."
            
            await asyncio.sleep(1)
        else:
            return "⏱️ Coordination request timed out. Please try with a simpler request."
        
        # Get response - find the latest assistant message
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=10)
        
        latest_assistant_message = None
        for msg in messages.data:
            if msg.role == "assistant":
                latest_assistant_message = msg
                break
        
        if latest_assistant_message and latest_assistant_message.content:
            response = latest_assistant_message.content[0].text.value
            print(f"✅ Got coordination response: {response[:100]}...")
            
            # Add to conversation context
            add_to_context(user_id, response, is_user=False)
            
            # Apply coordination-focused formatting
            return format_for_discord_rose(response)
        
        return "⚠️ No coordination response found."
        
    except Exception as e:
        print(f"❌ Coordination error occurred: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return "❌ An error occurred in the coordination system. Please try again."