#!/usr/bin/env python3
"""
FIX ROSE CALENDAR EVENT CREATION
Script to fix Rose's create_gcal_event function so it actually creates calendar events
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Rose's Assistant ID
ROSE_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")

def fix_rose_calendar_creation():
    """Fix Rose's calendar event creation function"""
    
    if not ROSE_ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    print("🔧 Fixing Rose's calendar event creation function...")
    
    # Get current assistant configuration
    try:
        current_assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"✅ Retrieved Rose assistant: {current_assistant.name}")
        
        # Get current tools
        current_tools = current_assistant.tools or []
        print(f"📋 Current tools count: {len(current_tools)}")
        
        # Updated create_gcal_event function with ACTUAL event creation
        fixed_create_gcal_event = {
            "type": "function",
            "function": {
                "name": "create_gcal_event",
                "description": "Create a new Google Calendar event. Actually creates the event in the calendar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (default: 'primary')",
                            "default": "primary"
                        },
                        "summary": {
                            "type": "string",
                            "description": "Event title/summary (required)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description (optional)"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in YYYY-MM-DD HH:MM format or ISO format"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in YYYY-MM-DD HH:MM format or ISO format (optional, defaults to 1 hour after start)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location (optional)"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses (optional)"
                        }
                    },
                    "required": ["summary", "start_time"]
                }
            }
        }
        
        # Find and replace existing create_gcal_event function
        updated_tools = []
        function_found = False
        
        for tool in current_tools:
            if (tool.type == "function" and 
                hasattr(tool, 'function') and 
                tool.function.name == "create_gcal_event"):
                # Replace with fixed version
                updated_tools.append(fixed_create_gcal_event)
                function_found = True
                print("🔄 Replaced existing create_gcal_event function")
            else:
                # Keep existing tool
                updated_tools.append(tool.model_dump() if hasattr(tool, 'model_dump') else tool)
        
        # If function wasn't found, add it
        if not function_found:
            updated_tools.append(fixed_create_gcal_event)
            print("➕ Added create_gcal_event function")
        
        # Update assistant with fixed function
        updated_assistant = client.beta.assistants.update(
            assistant_id=ROSE_ASSISTANT_ID,
            tools=updated_tools
        )
        
        print(f"✅ Rose assistant updated successfully!")
        print(f"🔧 Total tools: {len(updated_assistant.tools)}")
        
        # Verify the function was added/updated
        for tool in updated_assistant.tools:
            if (tool.type == "function" and 
                hasattr(tool, 'function') and 
                tool.function.name == "create_gcal_event"):
                print("✅ create_gcal_event function verified in assistant")
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose assistant: {e}")
        return False

def create_backend_fix_instructions():
    """Create instructions for fixing the backend calendar creation code"""
    
    backend_fix = """
# BACKEND CODE FIX NEEDED FOR ROSE'S main.py

The create_gcal_event function in Rose's main.py needs to be updated to actually call the Google Calendar API.

## Current Problem:
The function formats parameters correctly but never calls calendar_service.events().insert()

## Required Fix:
Replace the existing create_gcal_event function with this corrected version:

```python3
def create_gcal_event(calendar_id="primary", summary=None, description=None, 
                     start_time=None, end_time=None, location=None, attendees=None):
    \"\"\"Create a new Google Calendar event - FIXED VERSION\"\"\"
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
        
        # **THIS IS THE MISSING PIECE - ACTUALLY CREATE THE EVENT**
        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()
        
        print(f"✅ Event created successfully!")
        print(f"   Event ID: {created_event.get('id')}")
        print(f"   HTML Link: {created_event.get('htmlLink')}")
        
        # Format success message
        event_link = created_event.get('htmlLink', '')
        event_id = created_event.get('id', '')
        
        formatted_time = start_dt.strftime('%a %m/%d at %-I:%M %p')
        
        result = "✅ **Event Created Successfully**\\n"
        result += f"📅 **{summary}**\\n"
        result += f"🕐 {formatted_time}\\n"
        if location:
            result += f"📍 {location}\\n"
        if event_link:
            result += f"🔗 [View in Calendar]({event_link})\\n"
        result += f"🆔 Event ID: `{event_id}`"
        
        print(f"📝 Returning result: {result}")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error creating calendar event: {str(e)}"
        print(f"❌ EXCEPTION in create_gcal_event: {e}")
        import traceback
        traceback.print_exc()
        return error_msg
```

## Key Changes:
1. ✅ Added the missing calendar_service.events().insert() call
2. ✅ Proper error handling with try/catch
3. ✅ Real event creation that returns actual Google Calendar event data
4. ✅ Real event links and IDs from Google Calendar API

## Deployment:
1. Update the create_gcal_event function in Rose's main.py
2. Redeploy Rose to Railway
3. Test event creation
"""
    
    return backend_fix

if __name__ == "__main__":
    print("🚀 Starting Rose Calendar Fix...")
    print("=" * 50)
    
    # Fix the assistant function definition
    if fix_rose_calendar_creation():
        print("\n✅ Assistant function updated successfully!")
        
        # Show backend fix instructions
        print("\n📋 BACKEND CODE FIX REQUIRED:")
        print("=" * 50)
        backend_instructions = create_backend_fix_instructions()
        print(backend_instructions)
        
        print("\n🎯 NEXT STEPS:")
        print("1. ✅ Assistant function definition updated")
        print("2. 🔧 Update create_gcal_event function in Rose's main.py (see above)")
        print("3. 🚀 Redeploy Rose to Railway")
        print("4. 🧪 Test calendar event creation")
        
    else:
        print("\n❌ Failed to update assistant function")
    
    print("\n🌹 Rose Calendar Fix Complete!")
