# ============================================================================
# GOOGLE CALENDAR FUNCTIONS - COMPLETE CLEAN VERSION FOR ROSE
# ============================================================================

def create_gcal_event(calendar_id="primary", summary=None, description=None, 
                     start_time=None, end_time=None, location=None, attendees=None):
    """Create a new Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not summary or not start_time:
        return "❌ Missing required fields: summary, start_time"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Parse start time
        if isinstance(start_time, str):
            if 'T' not in start_time:
                start_time = start_time + 'T09:00:00'
            start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
        
        # Parse end time (default to 1 hour after start if not provided)
        if end_time:
            if isinstance(end_time, str):
                if 'T' not in end_time:
                    end_time = end_time + 'T10:00:00'
                end_dt = datetime.fromisoformat(end_time.replace('Z', ''))
                if end_dt.tzinfo is None:
                    end_dt = toronto_tz.localize(end_dt)
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        # Build event object
        event_body = {
            'summary': summary,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Toronto'
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Toronto'
            }
        }
        
        if description:
            event_body['description'] = description
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
        
        print(f"🔧 Creating calendar event: {summary}")
        print(f"📅 Start: {start_dt}")
        print(f"📅 End: {end_dt}")
        print(f"📋 Calendar ID: {calendar_id}")
        
        # ACTUALLY CREATE THE EVENT
        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()
        
        print(f"✅ Event created successfully!")
        print(f"   Event ID: {created_event.get('id')}")
        print(f"   HTML Link: {created_event.get('htmlLink')}")
        
        # Format success message with REAL event data
        event_link = created_event.get('htmlLink', '')
        event_id = created_event.get('id', '')
        
        formatted_time = start_dt.strftime('%a %m/%d at %-I:%M %p')
        
        result = "✅ **Event Created Successfully**\n"
        result += f"📅 **{summary}**\n"
        result += f"🕐 {formatted_time}\n"
        if location:
            result += f"📍 {location}\n"
        if event_link:
            result += f"🔗 [View in Calendar]({event_link})\n"
        result += f"🆔 Event ID: `{event_id}`"
        
        print(f"📝 Returning result: {result}")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error creating calendar event: {str(e)}"
        print(f"❌ EXCEPTION in create_gcal_event: {e}")
        import traceback
        traceback.print_exc()
        return error_msg

def update_gcal_event(calendar_id, event_id, summary=None, description=None, 
                     start_time=None, end_time=None, location=None, attendees=None):
    """Update an existing Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not calendar_id or not event_id:
        return "❌ Missing required fields: calendar_id, event_id"
    
    try:
        # Get existing event
        event = calendar_service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Update fields if provided
        if summary:
            event['summary'] = summary
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        
        # Update start time if provided
        if start_time:
            if isinstance(start_time, str):
                if 'T' not in start_time:
                    start_time = start_time + 'T09:00:00'
                start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
                if start_dt.tzinfo is None:
                    start_dt = toronto_tz.localize(start_dt)
                
                event['start'] = {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'America/Toronto'
                }
        
        # Update end time if provided
        if end_time:
            if isinstance(end_time, str):
                if 'T' not in end_time:
                    end_time = end_time + 'T10:00:00'
                end_dt = datetime.fromisoformat(end_time.replace('Z', ''))
                if end_dt.tzinfo is None:
                    end_dt = toronto_tz.localize(end_dt)
                
                event['end'] = {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/Toronto'
                }
        
        # Update attendees if provided
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        # Update the event
        updated_event = calendar_service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        print(f"✅ Event updated successfully!")
        print(f"   Event ID: {updated_event.get('id')}")
        print(f"   HTML Link: {updated_event.get('htmlLink')}")
        
        # Format success message
        event_link = updated_event.get('htmlLink', '')
        summary = updated_event.get('summary', 'Untitled Event')
        
        result = "✅ **Event Updated Successfully**\n"
        result += f"📅 **{summary}**\n"
        if event_link:
            result += f"🔗 [View in Calendar]({event_link})\n"
        result += f"🆔 Event ID: `{event_id}`"
        
        return result
        
    except Exception as e:
        error_msg = f"❌ Error updating calendar event: {str(e)}"
        print(f"❌ EXCEPTION in update_gcal_event: {e}")
        import traceback
        traceback.print_exc()
        return error_msg

def delete_gcal_event(calendar_id, event_id):
    """Delete a Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not calendar_id or not event_id:
        return "❌ Missing required fields: calendar_id, event_id"
    
    try:
        # Get event details before deletion
        event = calendar_service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        event_title = event.get('summary', 'Untitled Event')
        
        # Delete the event
        calendar_service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        return f"✅ **Event Deleted Successfully**\n📅 **{event_title}**\n🆔 Event ID: `{event_id}`"
        
    except Exception as e:
        print(f"❌ Error deleting calendar event: {e}")
        return f"❌ Error deleting calendar event: {str(e)}"

def list_gcal_events(calendar_id="primary", max_results=25, query=None, 
                    time_min=None, time_max=None):
    """List Google Calendar events"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Set default time range if not provided
        if not time_min:
            time_min = datetime.now(toronto_tz)
        if not time_max:
            time_max = datetime.now(toronto_tz) + timedelta(days=30)
        
        # Build query parameters
        params = {
            'calendarId': calendar_id,
            'timeMin': time_min.isoformat() if hasattr(time_min, 'isoformat') else time_min,
            'timeMax': time_max.isoformat() if hasattr(time_max, 'isoformat') else time_max,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if query:
            params['q'] = query
        
        # Get events
        events_result = calendar_service.events().list(**params).execute()
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No events found for the specified criteria"
        
        # Format events list
        result = f"📅 **Calendar Events ({len(events)} found)**\n\n"
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Untitled')
            event_id = event.get('id', '')
            
            if 'T' in start:
                # Timed event
                event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_time.tzinfo is None:
                    event_time = toronto_tz.localize(event_time)
                else:
                    event_time = event_time.astimezone(toronto_tz)
                time_str = event_time.strftime('%a %m/%d %I:%M %p')
            else:
                # All-day event
                date_obj = datetime.fromisoformat(start)
                time_str = date_obj.strftime('%a %m/%d (All day)')
            
            result += f"• **{time_str}** - {summary}\n"
            result += f"  🆔 `{event_id}`\n\n"
        
        return result
        
    except Exception as e:
        print(f"❌ Error listing calendar events: {e}")
        return f"❌ Error listing calendar events: {str(e)}"

def fetch_gcal_event(calendar_id, event_id):
    """Fetch details of a specific Google Calendar event"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    if not calendar_id or not event_id:
        return "❌ Missing required fields: calendar_id, event_id"
    
    try:
        event = calendar_service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        toronto_tz = pytz.timezone('America/Toronto')
        
        # Extract event details
        summary = event.get('summary', 'Untitled Event')
        description = event.get('description', 'No description')
        location = event.get('location', 'No location specified')
        
        # Format start time
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = toronto_tz.localize(start_dt)
            else:
                start_dt = start_dt.astimezone(toronto_tz)
            time_str = start_dt.strftime('%A, %B %d, %Y at %-I:%M %p')
        else:
            date_obj = datetime.fromisoformat(start)
            time_str = date_obj.strftime('%A, %B %d, %Y (All day)')
        
        # Format attendees
        attendees = event.get('attendees', [])
        attendee_list = [att.get('email', 'Unknown') for att in attendees] if attendees else ['No attendees']
        
        # Build detailed response
        result = "📅 **Event Details**\n\n"
        result += f"**Title:** {summary}\n"
        result += f"**Time:** {time_str}\n"
        result += f"**Location:** {location}\n"
        result += f"**Description:** {description}\n"
        result += f"**Attendees:** {', '.join(attendee_list)}\n"
        result += f"**Event ID:** `{event_id}`\n"
        
        if event.get('htmlLink'):
            result += f"**Calendar Link:** [View Event]({event['htmlLink']})"
        
        return result
        
    except Exception as e:
        print(f"❌ Error fetching calendar event: {e}")
        return f"❌ Error fetching calendar event: {str(e)}"

def find_free_time(calendar_ids, time_min, time_max):
    """Find free time slots across multiple calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        # Parse time parameters
        if isinstance(time_min, str):
            time_min = datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        if isinstance(time_max, str):
            time_max = datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
        # Use Calendar API's freebusy query
        freebusy_query = {
            'timeMin': time_min.isoformat(),
            'timeMax': time_max.isoformat(),
            'items': [{'id': calendar_id} for calendar_id in calendar_ids]
        }
        
        freebusy_result = calendar_service.freebusy().query(body=freebusy_query).execute()
        
        result = "🔍 **Free Time Analysis**\n\n"
        result += f"⏰ **Time Range:** {time_min.strftime('%a %m/%d %I:%M %p')} to {time_max.strftime('%a %m/%d %I:%M %p')}\n"
        result += f"📅 **Calendars Checked:** {len(calendar_ids)}\n\n"
        
        # Analyze busy times
        all_busy_times = []
        for calendar_id in calendar_ids:
            busy_times = freebusy_result['calendars'].get(calendar_id, {}).get('busy', [])
            all_busy_times.extend(busy_times)
        
        if not all_busy_times:
            result += "✅ **Completely Free** - No conflicts found!\n"
        else:
            result += "📅 **Busy Times Found:**\n"
            for busy in all_busy_times:
                start_time = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                result += f"• {start_time.strftime('%a %m/%d %I:%M %p')} - {end_time.strftime('%I:%M %p')}\n"
        
        return result
        
    except Exception as e:
        print(f"❌ Error finding free time: {e}")
        return f"❌ Error finding free time: {str(e)}"

def list_gcal_calendars():
    """List all available Google Calendars"""
    if not calendar_service:
        return "❌ Calendar service not available"
    
    try:
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if not calendars:
            return "📅 No calendars found"
        
        result = f"📅 **Available Calendars ({len(calendars)})**\n\n"
        
        for cal in calendars:
            cal_id = cal.get('id', 'Unknown ID')
            summary = cal.get('summary', 'Untitled Calendar')
            primary = " (Primary)" if cal.get('primary') else ""
            access_role = cal.get('accessRole', 'unknown')
            
            result += f"• **{summary}**{primary}\n"
            result += f"  🔑 Access: {access_role}\n"
            result += f"  🆔 `{cal_id}`\n\n"
        
        return result
        
    except Exception as e:
        print(f"❌ Error listing calendars: {e}")
        return f"❌ Error listing calendars: {str(e)}"