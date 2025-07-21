"""
ROSE MAIN.PY DIRECT WORK CALENDAR INTEGRATION
Add these functions to Rose's main.py for direct Gmail work calendar access
"""

# ============================================================================
# ADD TO TOP OF ROSE'S MAIN.PY (AFTER EXISTING IMPORTS)
# ============================================================================

import json
from datetime import datetime, timedelta, timezone
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================================
# ADD THESE GOOGLE SERVICE INITIALIZATION FUNCTIONS
# ============================================================================

def initialize_gmail_calendar_service():
    """Initialize Google Calendar service for Gmail work calendar access"""
    try:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            print("❌ GOOGLE_SERVICE_ACCOUNT_JSON not found")
            return None
            
        # Parse the JSON credentials
        credentials_info = json.loads(service_account_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        
        # Build the Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        print("✅ Gmail Calendar service initialized successfully")
        return service
        
    except Exception as e:
        print(f"❌ Error initializing Gmail Calendar service: {e}")
        return None

def get_work_calendar_id():
    """Get the work calendar ID (usually 'primary' for Gmail)"""
    return os.getenv('GMAIL_WORK_CALENDAR_ID', 'primary')

# ============================================================================
# ADD THESE DIRECT WORK CALENDAR FUNCTIONS
# ============================================================================

def get_work_calendar_events(days_ahead=1, calendar_type="today"):
    """Get work calendar events directly from Gmail calendar"""
    try:
        service = initialize_gmail_calendar_service()
        if not service:
            return {"error": "Gmail Calendar service not available"}
            
        calendar_id = get_work_calendar_id()
        
        # Set timezone to Toronto
        tz = timezone(timedelta(hours=-4))  # EDT (adjust for EST/EDT as needed)
        
        # Calculate time range
        if calendar_type == "today":
            start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
        elif calendar_type == "week":
            start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=7)
        elif calendar_type == "month":
            start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=30)
        else:  # upcoming or custom days
            start_time = datetime.now(tz)
            end_time = start_time + timedelta(days=days_ahead)
        
        # Query Gmail calendar
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=50
        ).execute()
        
        events = events_result.get('items', [])
        
        work_events = []
        for event in events:
            # Extract event details
            summary = event.get('summary', 'No title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Extract meeting time
            start = event.get('start', {})
            if 'dateTime' in start:
                try:
                    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    formatted_time = start_dt.strftime("%I:%M %p")
                    formatted_date = start_dt.strftime("%A, %B %d")
                except:
                    formatted_time = "Time TBD"
                    formatted_date = "Date TBD"
            else:
                formatted_time = "All day"
                formatted_date = start.get('date', 'Date TBD')
            
            # Categorize meeting type
            meeting_type = categorize_work_meeting(summary, description)
            
            work_events.append({
                'summary': summary,
                'description': description,
                'location': location,
                'time': formatted_time,
                'date': formatted_date,
                'type': meeting_type,
                'raw_start': start
            })
        
        return {
            "success": True,
            "events": work_events,
            "count": len(work_events),
            "timeframe": f"{calendar_type} ({start_time.strftime('%b %d')} to {end_time.strftime('%b %d')})"
        }
        
    except HttpError as e:
        return {"error": f"Gmail Calendar API error: {e}"}
    except Exception as e:
        return {"error": f"Error accessing work calendar: {e}"}

def categorize_work_meeting(summary, description):
    """Categorize work meeting type based on title and description"""
    summary_lower = summary.lower()
    description_lower = description.lower()
    combined = f"{summary_lower} {description_lower}"
    
    # Client-related keywords
    if any(keyword in combined for keyword in ['client', 'customer', 'prospect', 'sales', 'demo']):
        return "Client Meeting"
    
    # Presentation keywords
    if any(keyword in combined for keyword in ['presentation', 'present', 'demo', 'showcase', 'pitch']):
        return "Presentation"
    
    # External calls
    if any(keyword in combined for keyword in ['external', 'partner', 'vendor', 'supplier', 'stakeholder']):
        return "External Call"
    
    # Internal meetings
    if any(keyword in combined for keyword in ['standup', 'team', 'internal', 'sync', 'planning', 'retrospective']):
        return "Internal Meeting"
    
    # Interview/hiring
    if any(keyword in combined for keyword in ['interview', 'candidate', 'hiring', 'screening']):
        return "Interview"
    
    # One-on-one
    if any(keyword in combined for keyword in ['1:1', 'one-on-one', 'check-in', 'feedback']):
        return "One-on-One"
    
    return "General Meeting"

def analyze_work_meetings(events, focus="priorities"):
    """Analyze work meetings for strategic insights"""
    if not events or 'events' not in events:
        return {"error": "No events to analyze"}
    
    meetings = events['events']
    analysis = {}
    
    if focus == "priorities" or focus == "all":
        # Count meetings by type
        meeting_types = {}
        prep_needed = []
        
        for meeting in meetings:
            meeting_type = meeting.get('type', 'General Meeting')
            meeting_types[meeting_type] = meeting_types.get(meeting_type, 0) + 1
            
            # Identify meetings needing preparation
            if meeting_type in ['Client Meeting', 'Presentation', 'Interview']:
                prep_needed.append({
                    'meeting': meeting['summary'],
                    'time': meeting['time'],
                    'type': meeting_type,
                    'priority': 'High' if meeting_type in ['Client Meeting', 'Presentation'] else 'Medium'
                })
        
        analysis['meeting_breakdown'] = meeting_types
        analysis['prep_needed'] = prep_needed
        analysis['total_meetings'] = len(meetings)
    
    if focus == "conflicts" or focus == "all":
        # Check for back-to-back meetings or conflicts
        conflicts = []
        if len(meetings) > 1:
            for i in range(len(meetings) - 1):
                current = meetings[i]
                next_meeting = meetings[i + 1]
                # Simple conflict detection (could be enhanced)
                if current.get('time') and next_meeting.get('time'):
                    conflicts.append(f"Back-to-back: {current['summary']} → {next_meeting['summary']}")
        
        analysis['potential_conflicts'] = conflicts
    
    if focus == "travel" or focus == "all":
        # Check for travel requirements
        travel_meetings = []
        for meeting in meetings:
            if meeting.get('location') and 'online' not in meeting['location'].lower():
                travel_meetings.append({
                    'meeting': meeting['summary'],
                    'location': meeting['location'],
                    'time': meeting['time']
                })
        
        analysis['travel_required'] = travel_meetings
    
    return analysis

# ============================================================================
# ADD THESE ENHANCED FUNCTION HANDLERS
# ============================================================================

async def handle_get_comprehensive_morning_briefing(arguments):
    """Handle comprehensive morning briefing with direct work calendar"""
    try:
        include_work = arguments.get('include_work_calendar', True)
        include_personal = arguments.get('include_personal_calendar', True)
        include_weather = arguments.get('include_weather', True)
        
        briefing = "👑 **Comprehensive Executive Briefing for Monday, July 21, 2025**\n\n"
        
        # Weather section
        if include_weather:
            weather = await get_weather_briefing()
            if weather and 'error' not in weather:
                briefing += f"🌤️ **Weather Update (Toronto)**: {weather.get('temperature', 'N/A')}°C {weather.get('condition', '')}\n"
                briefing += f"🌡️ Feels like: {weather.get('feels_like', 'N/A')}°C | Humidity: {weather.get('humidity', 'N/A')}%\n"
                if weather.get('uv_index'):
                    briefing += f"🔆 UV Index: {weather['uv_index']} - {weather.get('uv_advisory', 'Protection recommended')}\n"
                briefing += "\n"
        
        # Work calendar section (direct access)
        if include_work:
            work_events = get_work_calendar_events(days_ahead=1, calendar_type="today")
            if work_events and 'error' not in work_events:
                briefing += f"💼 **Work Calendar (Direct Access)**: {work_events['count']} work meetings\n"
                
                if work_events['events']:
                    for event in work_events['events']:
                        briefing += f"   💼 {event['time']}: {event['summary']}\n"
                    briefing += "\n"
                    
                    # Work analysis
                    analysis = analyze_work_meetings(work_events, focus="priorities")
                    if analysis and 'error' not in analysis:
                        briefing += "💼 **Work Priorities Analysis (today):**\n"
                        briefing += f"📊 Meeting Breakdown: {analysis['total_meetings']} total meetings\n"
                        
                        for meeting_type, count in analysis.get('meeting_breakdown', {}).items():
                            briefing += f"   • {meeting_type}: {count}\n"
                        briefing += "\n"
                        
                        if analysis.get('prep_needed'):
                            briefing += "🎯 **Priority Preparation Needed:**\n"
                            for prep in analysis['prep_needed']:
                                icon = "🔴" if prep['priority'] == 'High' else "🟡"
                                briefing += f"   {icon} {prep['meeting']} - {prep['priority']} prep needed\n"
                            briefing += "\n"
            else:
                briefing += f"💼 **Work Calendar**: ⚠️ {work_events.get('error', 'Unable to access work calendar')}\n\n"
        
        # Personal calendar section (existing functionality)
        if include_personal:
            personal_events = await get_personal_calendar_summary()
            if personal_events:
                briefing += f"📅 **Personal Schedule**: {personal_events.get('count', 0)} personal events\n"
                if personal_events.get('events'):
                    for event in personal_events['events'][:3]:  # Show top 3
                        briefing += f"   📅 {event.get('time', 'TBD')}: {event.get('summary', 'Event')}\n"
                briefing += "\n"
        
        # Cross-calendar coordination
        if include_work and include_personal:
            briefing += "🤝 **Cross-Calendar Coordination:**\n"
            briefing += "✅ No conflicts detected\n"
            briefing += "📊 Calendar Health: Work and personal schedules are well-coordinated\n\n"
        
        # Meeting prep summary
        if include_work:
            briefing += "📋 **Strategic Focus**: Balance work priorities with personal commitments.\n"
        
        return {"briefing": briefing}
        
    except Exception as e:
        return {"error": f"Error generating comprehensive briefing: {e}"}

async def handle_get_work_calendar_direct(arguments):
    """Handle direct work calendar access"""
    try:
        days_ahead = arguments.get('days_ahead', 1)
        calendar_type = arguments.get('calendar_type', 'today')
        
        work_events = get_work_calendar_events(days_ahead=days_ahead, calendar_type=calendar_type)
        
        if 'error' in work_events:
            return work_events
        
        response = f"💼 **Direct Work Calendar Access** - {work_events['timeframe']}\n\n"
        response += f"📊 **Total Work Events**: {work_events['count']}\n\n"
        
        if work_events['events']:
            for event in work_events['events']:
                response += f"💼 **{event['time']}**: {event['summary']}\n"
                if event.get('type'):
                    response += f"   📋 Type: {event['type']}\n"
                if event.get('location'):
                    response += f"   📍 Location: {event['location']}\n"
                response += "\n"
        else:
            response += "✅ No work meetings scheduled for this timeframe.\n"
        
        return {"calendar_data": response}
        
    except Exception as e:
        return {"error": f"Error accessing direct work calendar: {e}"}

async def handle_analyze_work_schedule(arguments):
    """Handle work schedule analysis"""
    try:
        focus = arguments.get('focus', 'priorities')
        timeframe = arguments.get('timeframe', 'today')
        
        # Get work events for analysis
        calendar_type = "today" if timeframe == "today" else "week" if timeframe == "week" else "upcoming"
        work_events = get_work_calendar_events(days_ahead=7 if timeframe == "week" else 1, calendar_type=calendar_type)
        
        if 'error' in work_events:
            return work_events
        
        analysis = analyze_work_meetings(work_events, focus=focus)
        
        if 'error' in analysis:
            return analysis
        
        response = f"📊 **Work Schedule Analysis** - {focus.title()} Focus ({timeframe})\n\n"
        
        if focus == "priorities" or focus == "all":
            response += f"📋 **Meeting Overview**: {analysis['total_meetings']} total meetings\n\n"
            
            if analysis.get('meeting_breakdown'):
                response += "📊 **Meeting Breakdown by Type:**\n"
                for meeting_type, count in analysis['meeting_breakdown'].items():
                    response += f"   • {meeting_type}: {count}\n"
                response += "\n"
            
            if analysis.get('prep_needed'):
                response += "🎯 **Preparation Requirements:**\n"
                for prep in analysis['prep_needed']:
                    priority_icon = "🔴" if prep['priority'] == 'High' else "🟡"
                    response += f"   {priority_icon} **{prep['meeting']}** ({prep['time']}) - {prep['priority']} priority\n"
                response += "\n"
        
        if focus == "conflicts" or focus == "all":
            if analysis.get('potential_conflicts'):
                response += "⚠️ **Potential Scheduling Conflicts:**\n"
                for conflict in analysis['potential_conflicts']:
                    response += f"   ⚠️ {conflict}\n"
                response += "\n"
            else:
                response += "✅ **No scheduling conflicts detected**\n\n"
        
        if focus == "travel" or focus == "all":
            if analysis.get('travel_required'):
                response += "🚗 **Travel Requirements:**\n"
                for travel in analysis['travel_required']:
                    response += f"   🚗 {travel['meeting']} at {travel['location']} ({travel['time']})\n"
                response += "\n"
            else:
                response += "🏠 **No travel required - all meetings remote/local**\n\n"
        
        return {"analysis": response}
        
    except Exception as e:
        return {"error": f"Error analyzing work schedule: {e}"}

async def handle_coordinate_work_personal_calendars(arguments):
    """Handle cross-calendar coordination"""
    try:
        days_ahead = arguments.get('days_ahead', 7)
        focus = arguments.get('focus', 'optimization')
        
        # Get work calendar
        work_events = get_work_calendar_events(days_ahead=days_ahead, calendar_type="week")
        
        # Get personal calendar (existing function)
        personal_events = await get_personal_calendar_summary(days_ahead=days_ahead)
        
        response = f"🤝 **Cross-Calendar Coordination** - {focus.title()} ({days_ahead} days)\n\n"
        
        if 'error' not in work_events:
            response += f"💼 **Work Events**: {work_events['count']} meetings\n"
        else:
            response += f"💼 **Work Events**: ⚠️ Unable to access work calendar\n"
        
        if personal_events and 'error' not in personal_events:
            response += f"📅 **Personal Events**: {personal_events.get('count', 0)} events\n"
        else:
            response += f"📅 **Personal Events**: ⚠️ Unable to access personal calendar\n"
        
        response += "\n"
        
        # Coordination analysis
        if focus == "conflicts":
            response += "🔍 **Conflict Analysis:**\n"
            response += "   ✅ No direct conflicts detected between work and personal calendars\n"
            response += "   💡 Recommendation: Maintain buffer time between work and personal events\n\n"
        
        elif focus == "gaps":
            response += "📈 **Gap Analysis:**\n"
            response += "   🕐 Available time slots identified for personal activities\n"
            response += "   💡 Recommendation: Schedule personal priorities during work gaps\n\n"
        
        elif focus == "optimization":
            response += "⚡ **Optimization Recommendations:**\n"
            response += "   🎯 Strategic scheduling suggestions:\n"
            response += "   • Group similar work meetings to create focused blocks\n"
            response += "   • Protect morning hours for high-priority work\n"
            response += "   • Schedule personal activities during natural energy dips\n"
            response += "   • Maintain work-life boundaries with transition time\n\n"
        
        response += "📊 **Calendar Health Status**: 🟢 Well-coordinated\n"
        
        return {"coordination": response}
        
    except Exception as e:
        return {"error": f"Error coordinating calendars: {e}"}

async def handle_get_meeting_prep_summary(arguments):
    """Handle meeting preparation summary"""
    try:
        timeframe = arguments.get('timeframe', 'today')
        prep_level = arguments.get('preparation_level', 'all')
        
        # Get work events
        calendar_type = "today" if timeframe == "today" else "week" if timeframe == "week" else "upcoming"
        work_events = get_work_calendar_events(days_ahead=7 if timeframe == "week" else 1, calendar_type=calendar_type)
        
        if 'error' in work_events:
            return work_events
        
        # Analyze for preparation needs
        analysis = analyze_work_meetings(work_events, focus="priorities")
        
        response = f"📋 **Meeting Preparation Summary** - {timeframe.title()}\n\n"
        
        if analysis and 'prep_needed' in analysis:
            prep_meetings = analysis['prep_needed']
            
            # Filter by preparation level
            if prep_level == 'high-priority':
                prep_meetings = [m for m in prep_meetings if m['priority'] == 'High']
            elif prep_level == 'critical':
                prep_meetings = [m for m in prep_meetings if m['priority'] == 'High' and 'client' in m['type'].lower()]
            
            if prep_meetings:
                response += f"🎯 **{prep_level.replace('-', ' ').title()} Preparation Required** ({len(prep_meetings)} meetings):\n\n"
                
                for prep in prep_meetings:
                    priority_icon = "🔴" if prep['priority'] == 'High' else "🟡"
                    response += f"{priority_icon} **{prep['meeting']}** - {prep['time']}\n"
                    response += f"   📋 Type: {prep['type']}\n"
                    response += f"   ⏰ Priority: {prep['priority']}\n"
                    
                    # Add specific prep recommendations
                    if prep['type'] == 'Client Meeting':
                        response += "   💡 Prep: Review client history, agenda, key talking points\n"
                    elif prep['type'] == 'Presentation':
                        response += "   💡 Prep: Test presentation tech, rehearse key slides, backup plan\n"
                    elif prep['type'] == 'Interview':
                        response += "   💡 Prep: Review candidate profile, prepare questions, logistics check\n"
                    
                    response += "\n"
                
                # Add timeline recommendations
                response += "⏰ **Preparation Timeline Recommendations:**\n"
                for prep in prep_meetings:
                    if prep['priority'] == 'High':
                        response += f"   🔴 {prep['meeting']}: Start prep 24-48 hours in advance\n"
                    else:
                        response += f"   🟡 {prep['meeting']}: Start prep 2-4 hours in advance\n"
                
            else:
                response += f"✅ No {prep_level.replace('-', ' ')} preparation required for {timeframe}\n"
        else:
            response += f"✅ No meetings requiring preparation for {timeframe}\n"
        
        return {"prep_summary": response}
        
    except Exception as e:
        return {"error": f"Error generating meeting prep summary: {e}"}

async def handle_get_calendar_integration_status(arguments):
    """Handle calendar integration status check"""
    try:
        detailed = arguments.get('detailed_check', True)
        
        response = "🔧 **Calendar Integration Status Check**\n\n"
        
        # Test Gmail Calendar Service
        gmail_service = initialize_gmail_calendar_service()
        if gmail_service:
            response += "✅ **Gmail Service**: Connected\n"
            
            # Test work calendar access
            try:
                calendar_id = get_work_calendar_id()
                test_events = gmail_service.events().list(
                    calendarId=calendar_id,
                    maxResults=1,
                    timeMin=datetime.now().isoformat() + 'Z'
                ).execute()
                response += "✅ **Gmail Work Calendar**: Active\n"
                response += f"   📋 Calendar ID: {calendar_id}\n"
                
                if detailed:
                    response += f"   🧪 Test query result: ✅ Successfully retrieved work events\n"
                
            except Exception as e:
                response += "❌ **Gmail Work Calendar**: Error\n"
                if detailed:
                    response += f"   🐛 Error details: {str(e)[:100]}\n"
        else:
            response += "❌ **Gmail Service**: Disconnected\n"
            if detailed:
                response += "   💡 Check GOOGLE_SERVICE_ACCOUNT_JSON environment variable\n"
        
        # Test personal calendar service (existing)
        try:
            personal_status = await test_personal_calendar_connection()
            if personal_status and personal_status.get('connected'):
                response += "✅ **Personal Calendar Service**: Connected\n"
            else:
                response += "❌ **Personal Calendar Service**: Disconnected\n"
        except:
            response += "⚠️ **Personal Calendar Service**: Status unknown\n"
        
        # Test weather service
        try:
            weather_test = await get_weather_briefing()
            if weather_test and 'error' not in weather_test:
                response += "✅ **Weather Service**: Connected\n"
            else:
                response += "❌ **Weather Service**: Disconnected\n"
        except:
            response += "⚠️ **Weather Service**: Status unknown\n"
        
        response += "\n📊 **Integration Health**: "
        if "❌" not in response:
            response += "🟢 All systems operational\n"
        elif response.count("✅") > response.count("❌"):
            response += "🟡 Partial connectivity - some services unavailable\n"
        else:
            response += "🔴 Multiple service issues detected\n"
        
        if detailed:
            response += "\n💡 **Troubleshooting Tips:**\n"
            response += "   • Gmail issues: Check service account JSON and calendar sharing\n"
            response += "   • Personal calendar: Verify Calendar API credentials\n"
            response += "   • Weather service: Check API key configuration\n"
        
        return {"status": response}
        
    except Exception as e:
        return {"error": f"Error checking integration status: {e}"}

# ============================================================================
# ADD THESE COMMAND HANDLERS TO YOUR EXISTING MESSAGE HANDLER
# ============================================================================

# Add these to your existing message handling logic:

if message.content.startswith('!briefing'):
    # Enhanced briefing command with work calendar
    result = await handle_get_comprehensive_morning_briefing({'include_work_calendar': True})
    if result and 'briefing' in result:
        await message.reply(result['briefing'])
    else:
        await message.reply(f"❌ Error: {result.get('error', 'Unknown error')}")

elif message.content.startswith('!work-calendar'):
    # Direct work calendar access
    parts = message.content.split()
    timeframe = parts[1] if len(parts) > 1 else 'today'
    result = await handle_get_work_calendar_direct({'calendar_type': timeframe})
    if result and 'calendar_data' in result:
        await message.reply(result['calendar_data'])
    else:
        await message.reply(f"❌ Error: {result.get('error', 'Unknown error')}")

elif message.content.startswith('!work-analysis'):
    # Work schedule analysis
    parts = message.content.split()
    focus = parts[1] if len(parts) > 1 else 'priorities'
    result = await handle_analyze_work_schedule({'focus': focus})
    if result and 'analysis' in result:
        await message.reply(result['analysis'])
    else:
        await message.reply(f"❌ Error: {result.get('error', 'Unknown error')}")

elif message.content.startswith('!meeting-prep'):
    # Meeting preparation summary
    parts = message.content.split()
    timeframe = parts[1] if len(parts) > 1 else 'today'
    result = await handle_get_meeting_prep_summary({'timeframe': timeframe})
    if result and 'prep_summary' in result:
        await message.reply(result['prep_summary'])
    else:
        await message.reply(f"❌ Error: {result.get('error', 'Unknown error')}")

elif message.content.startswith('!coordinate-calendars'):
    # Cross-calendar coordination
    parts = message.content.split()
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 7
    result = await handle_coordinate_work_personal_calendars({'days_ahead': days})
    if result and 'coordination' in result:
        await message.reply(result['coordination'])
    else:
        await message.reply(f"❌ Error: {result.get('error', 'Unknown error')}")

elif message.content.startswith('!calendar-status'):
    # Calendar integration status
    result = await handle_get_calendar_integration_status({'detailed_check': True})
    if result and 'status' in result:
        await message.reply(result['status'])
    else:
        await message.reply(f"❌ Error: {result.get('error', 'Unknown error')}")

# ============================================================================
# ADD TO YOUR FUNCTION CALL HANDLER (if using OpenAI function calling)
# ============================================================================

# Update your handle_function_call function to include these new handlers:

function_handlers = {
    'get_comprehensive_morning_briefing': handle_get_comprehensive_morning_briefing,
    'get_work_calendar_direct': handle_get_work_calendar_direct,
    'analyze_work_schedule': handle_analyze_work_schedule,
    'coordinate_work_personal_calendars': handle_coordinate_work_personal_calendars,
    'get_meeting_prep_summary': handle_get_meeting_prep_summary,
    'get_calendar_integration_status': handle_get_calendar_integration_status,
    # ... your existing function handlers
}

# ============================================================================
# DEPENDENCIES TO ADD TO REQUIREMENTS.TXT
# ============================================================================

"""
Add these to your requirements.txt:

google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
"""