#!/usr/bin/env python3
"""
ROSE TIMEZONE FIX - TORONTO/EASTERN TIME
Fixes the timezone issue where Rose thinks today is tomorrow
Based on your timezone: America/Toronto
"""

from datetime import datetime, timezone, timedelta
import pytz

# Add this import at the top of Rose's main.py
# import pytz

# Replace the timezone handling in Rose's calendar functions with this:

def get_today_schedule():
    """Get today's schedule from both calendars with PROPER timezone handling"""
    if not calendar_service:
        return "📅 **Today's Schedule:** Calendar integration not configured\n\n🎯 **Planning Tip:** Set up your calendar integration for automated schedule management"
    
    try:
        # FIXED: Use Toronto timezone instead of UTC
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get today in Toronto timezone
        today_toronto = datetime.now(toronto_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_toronto = today_toronto.replace(hour=23, minute=59, second=59)
        
        # Convert to UTC for Google Calendar API (Google expects UTC)
        today_utc = today_toronto.astimezone(pytz.UTC)
        tomorrow_utc = tomorrow_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from primary calendar
        if GOOGLE_CALENDAR_ID:
            calendar_events = get_calendar_events(GOOGLE_CALENDAR_ID, today_utc, tomorrow_utc)
            for event in calendar_events:
                formatted = format_event(event, "calendar", toronto_tz)
                all_events.append((event, formatted, "calendar"))
        
        # Get events from tasks calendar
        if GOOGLE_TASKS_CALENDAR_ID:
            task_events = get_calendar_events(GOOGLE_TASKS_CALENDAR_ID, today_utc, tomorrow_utc)
            for event in task_events:
                formatted = format_event(event, "tasks", toronto_tz)
                all_events.append((event, formatted, "tasks"))
        
        # If no specific calendars configured, try primary
        if not GOOGLE_CALENDAR_ID and not GOOGLE_TASKS_CALENDAR_ID:
            primary_events = get_calendar_events('primary', today_utc, tomorrow_utc)
            for event in primary_events:
                formatted = format_event(event, "calendar", toronto_tz)
                all_events.append((event, formatted, "calendar"))
        
        if not all_events:
            return "📅 **Today's Schedule:** No scheduled events\n\n🎯 **Executive Opportunity:** Perfect day for deep work and strategic planning"
        
        # Sort all events by start time
        def get_event_time(event_tuple):
            event = event_tuple[0]
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                if 'T' in start:
                    # Parse and convert to Toronto timezone
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
        calendar_count = len([e for e in all_events if e[2] == "calendar"])
        tasks_count = len([e for e in all_events if e[2] == "tasks"])
        
        header = f"📅 **Today's Executive Schedule:** {len(all_events)} events"
        if calendar_count > 0 and tasks_count > 0:
            header += f" ({calendar_count} appointments, {tasks_count} tasks)"
        elif calendar_count > 0:
            header += f" ({calendar_count} appointments)"
        elif tasks_count > 0:
            header += f" ({tasks_count} tasks)"
        
        return header + "\n\n" + "\n".join(formatted_events[:10])  # Limit for Discord
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return "📅 **Today's Schedule:** Error retrieving calendar data\n\n🎯 **Backup Plan:** Use manual schedule review"

def format_event(event, calendar_type="", user_timezone=None):
    """Helper function to format a single event with proper timezone"""
    if user_timezone is None:
        user_timezone = pytz.timezone('America/Toronto')
    
    start = event['start'].get('dateTime', event['start'].get('date'))
    title = event.get('summary', 'Untitled Event')
    
    # Add calendar indicator
    if calendar_type == "tasks":
        title = f"✅ {title}"
    elif calendar_type == "calendar":
        title = f"📅 {title}"
    
    if 'T' in start:  # Has time
        try:
            # Parse UTC time and convert to user timezone
            utc_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            local_time = utc_time.astimezone(user_timezone)
            time_str = local_time.strftime('%I:%M %p')
            return f"• {time_str}: {title}"
        except:
            return f"• {title}"
    else:  # All day event
        return f"• All Day: {title}"

def get_upcoming_events(days=7):
    """Get upcoming events from both calendars with PROPER timezone handling"""
    if not calendar_service:
        return f"📅 **Upcoming {days} Days:** Calendar integration not configured\n\n🎯 **Planning Tip:** Manual weekly planning recommended"
    
    try:
        # FIXED: Use Toronto timezone
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Get date range in Toronto timezone then convert to UTC
        start_toronto = datetime.now(toronto_tz)
        end_toronto = start_toronto + timedelta(days=days)
        
        start_utc = start_toronto.astimezone(pytz.UTC)
        end_utc = end_toronto.astimezone(pytz.UTC)
        
        all_events = []
        
        # Get events from primary calendar
        if GOOGLE_CALENDAR_ID:
            calendar_events = get_calendar_events(GOOGLE_CALENDAR_ID, start_utc, end_utc)
            for event in calendar_events:
                all_events.append((event, "calendar"))
        
        # Get events from tasks calendar
        if GOOGLE_TASKS_CALENDAR_ID:
            task_events = get_calendar_events(GOOGLE_TASKS_CALENDAR_ID, start_utc, end_utc)
            for event in task_events:
                all_events.append((event, "tasks"))
        
        # If no specific calendars configured, try primary
        if not GOOGLE_CALENDAR_ID and not GOOGLE_TASKS_CALENDAR_ID:
            primary_events = get_calendar_events('primary', start_utc, end_utc)
            for event in primary_events:
                all_events.append((event, "calendar"))
        
        if not all_events:
            return f"📅 **Upcoming {days} Days:** No scheduled events\n\n🎯 **Strategic Opportunity:** Focus on long-term planning and goal setting"
        
        # Group by date using Toronto timezone
        events_by_date = defaultdict(list)
        
        for event, calendar_type in all_events:
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
        calendar_count = len([e for e in all_events if e[1] == "calendar"])
        tasks_count = len([e for e in all_events if e[1] == "tasks"])
        
        for date, day_events in list(events_by_date.items())[:7]:  # Limit to 7 days for Discord
            formatted.append(f"**{date}**")
            formatted.extend(day_events[:5])  # Limit events per day for readability
        
        header = f"📅 **Upcoming {days} Days:** {total_events} total events"
        if calendar_count > 0 and tasks_count > 0:
            header += f" ({calendar_count} appointments, {tasks_count} tasks)"
        elif calendar_count > 0:
            header += f" ({calendar_count} appointments)"
        elif tasks_count > 0:
            header += f" ({tasks_count} tasks)"
        
        return header + "\n\n" + "\n".join(formatted)
        
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return f"📅 **Upcoming {days} Days:** Error retrieving calendar data"

def get_morning_briefing():
    """Comprehensive morning briefing with PROPER timezone handling"""
    if not calendar_service:
        return "🌅 **Morning Briefing:** Calendar integration needed for full briefing\n\n📋 **Manual Planning:** Review your calendar and prioritize your day"
    
    try:
        # FIXED: Use Toronto timezone for proper date calculation
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
        
        # Get tomorrow's events from both calendars
        if GOOGLE_CALENDAR_ID:
            calendar_events = get_calendar_events(GOOGLE_CALENDAR_ID, tomorrow_utc, day_after_utc)
            tomorrow_events.extend([(event, "calendar") for event in calendar_events])
        
        if GOOGLE_TASKS_CALENDAR_ID:
            task_events = get_calendar_events(GOOGLE_TASKS_CALENDAR_ID, tomorrow_utc, day_after_utc)
            tomorrow_events.extend([(event, "tasks") for event in task_events])
        
        # If no specific calendars configured, try primary
        if not GOOGLE_CALENDAR_ID and not GOOGLE_TASKS_CALENDAR_ID:
            primary_events = get_calendar_events('primary', tomorrow_utc, day_after_utc)
            tomorrow_events.extend([(event, "calendar") for event in primary_events])
        
        # Format tomorrow's preview
        if tomorrow_events:
            tomorrow_formatted = []
            for event, calendar_type in tomorrow_events[:3]:  # Limit to 3 for briefing
                formatted = format_event(event, calendar_type, toronto_tz)
                tomorrow_formatted.append(formatted)
            tomorrow_preview = "📅 **Tomorrow Preview:**\n" + "\n".join(tomorrow_formatted)
        else:
            tomorrow_preview = "📅 **Tomorrow Preview:** Clear schedule - great for strategic planning"
        
        # Combine into morning briefing with CORRECT date
        current_time = datetime.now(toronto_tz).strftime('%A, %B %d')
        briefing = f"🌅 **Good Morning! Executive Briefing for {current_time}**\n\n{today_schedule}\n\n{tomorrow_preview}\n\n💼 **Executive Focus:** Prioritize high-impact activities during peak energy hours"
        
        return briefing
        
    except Exception as e:
        print(f"❌ Morning briefing error: {e}")
        return "🌅 **Morning Briefing:** Error generating briefing - please check calendar manually"

# IMPLEMENTATION INSTRUCTIONS:
"""
1. Add 'import pytz' to the top of Rose's main.py file
2. Add 'pytz>=2023.3' to requirements.txt if not already there
3. Replace the three functions above in Rose's main.py:
   - get_today_schedule()
   - get_upcoming_events() 
   - get_morning_briefing()
   - format_event()
4. Deploy to Railway

This should fix Rose showing Wednesday when it's Tuesday!
"""