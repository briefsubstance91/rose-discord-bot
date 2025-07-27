#!/usr/bin/env python3
"""
DEPLOY ROSE CALENDAR FIX
Complete script to fix Rose's create_gcal_event function
- Updates backend main.py with working calendar creation
- Updates OpenAI Assistant function definition
- Preserves all existing functionality
"""

import os
import re
import shutil
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Rose's Assistant ID
ROSE_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")

def backup_main_file():
    """Create a backup of the current main.py file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"main_backup_{timestamp}.py"
    
    if os.path.exists("main.py"):
        shutil.copy2("main.py", backup_filename)
        print(f"✅ Backup created: {backup_filename}")
        return backup_filename
    else:
        print("❌ main.py not found in current directory")
        return None

def get_fixed_create_gcal_event_function():
    """Return the corrected create_gcal_event function"""
    return '''def create_gcal_event(calendar_id="primary", summary=None, description=None, 
                     start_time=None, end_time=None, location=None, attendees=None):
    """Create a new Google Calendar event - FIXED VERSION"""
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
        
        # **CRITICAL FIX - ACTUALLY CREATE THE EVENT**
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
        return error_msg'''

def fix_main_py_file():
    """Fix the create_gcal_event function in main.py"""
    if not os.path.exists("main.py"):
        print("❌ main.py not found in current directory")
        return False
    
    print("🔧 Reading main.py file...")
    with open("main.py", "r", encoding="utf-8") as file:
        content = file.read()
    
    # Pattern to match the existing create_gcal_event function
    # This will match from def create_gcal_event to the next def or end of file
    pattern = r'def create_gcal_event\([^)]*\):.*?(?=\ndef|\Z)'
    
    fixed_function = get_fixed_create_gcal_event_function()
    
    # Replace the broken function with the fixed one
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, fixed_function, content, flags=re.DOTALL)
        
        # Write the fixed content back to main.py
        with open("main.py", "w", encoding="utf-8") as file:
            file.write(new_content)
        
        print("✅ Successfully updated create_gcal_event function in main.py")
        return True
    else:
        print("❌ Could not find create_gcal_event function in main.py")
        print("🔍 Searching for function patterns...")
        
        # Try to find any calendar-related functions
        calendar_functions = re.findall(r'def [a-zA-Z_]*cal[a-zA-Z_]*\([^)]*\):', content)
        if calendar_functions:
            print("🔍 Found calendar functions:")
            for func in calendar_functions:
                print(f"   - {func}")
        
        return False

def update_openai_assistant():
    """Update Rose's OpenAI Assistant function definition"""
    if not ROSE_ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    print("🔧 Updating Rose's OpenAI Assistant configuration...")
    
    try:
        # Get current assistant configuration
        current_assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"✅ Retrieved Rose assistant: {current_assistant.name}")
        
        # Get current tools
        current_tools = current_assistant.tools or []
        print(f"📋 Current tools count: {len(current_tools)}")
        
        # Updated create_gcal_event function definition
        fixed_create_gcal_event = {
            "type": "function",
            "function": {
                "name": "create_gcal_event",
                "description": "Create a new Google Calendar event. Actually creates the event in the calendar and returns real event data.",
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

def verify_fix():
    """Verify that the fix has been applied correctly"""
    print("\n🔍 VERIFICATION CHECKLIST:")
    
    # Check if main.py contains the fixed function
    if os.path.exists("main.py"):
        with open("main.py", "r", encoding="utf-8") as file:
            content = file.read()
        
        if "calendar_service.events().insert(" in content:
            print("✅ main.py contains calendar_service.events().insert() call")
        else:
            print("❌ main.py missing calendar_service.events().insert() call")
        
        if "created_event.get('htmlLink')" in content:
            print("✅ main.py uses real event data from API response")
        else:
            print("❌ main.py missing real event data handling")
    
    # Check environment variables
    if ROSE_ASSISTANT_ID:
        print("✅ ROSE_ASSISTANT_ID found in environment")
    else:
        print("❌ ROSE_ASSISTANT_ID missing from environment")
    
    print("\n📋 NEXT STEPS AFTER RUNNING THIS SCRIPT:")
    print("1. 🧪 Test the fix locally with a test calendar event")
    print("2. 🚀 Deploy to Railway")
    print("3. 🔍 Monitor Railway logs for '📅 Calendar Service: ✅ Ready'")
    print("4. 🎯 Test actual calendar event creation through Discord")
    print("5. ✅ Verify events appear in Google Calendar")

def main():
    """Main deployment function"""
    print("🚀 ROSE CALENDAR FIX DEPLOYMENT")
    print("=" * 50)
    
    # Step 1: Create backup
    print("\n📁 STEP 1: Creating backup...")
    backup_file = backup_main_file()
    if not backup_file:
        print("⚠️  Proceeding without backup...")
    
    # Step 2: Fix main.py
    print("\n🔧 STEP 2: Fixing main.py...")
    main_py_fixed = fix_main_py_file()
    
    # Step 3: Update OpenAI Assistant
    print("\n🤖 STEP 3: Updating OpenAI Assistant...")
    assistant_updated = update_openai_assistant()
    
    # Step 4: Verification
    print("\n🔍 STEP 4: Verification...")
    verify_fix()
    
    # Summary
    print("\n📊 DEPLOYMENT SUMMARY:")
    print("=" * 50)
    if backup_file:
        print(f"✅ Backup created: {backup_file}")
    print(f"{'✅' if main_py_fixed else '❌'} main.py function fix: {'SUCCESS' if main_py_fixed else 'FAILED'}")
    print(f"{'✅' if assistant_updated else '❌'} Assistant update: {'SUCCESS' if assistant_updated else 'FAILED'}")
    
    if main_py_fixed and assistant_updated:
        print("\n🎉 DEPLOYMENT SUCCESSFUL!")
        print("🌹 Rose's calendar creation is now fixed!")
        print("\n🚀 Ready for Railway deployment!")
    else:
        print("\n❌ DEPLOYMENT INCOMPLETE")
        if backup_file:
            print(f"🔄 To restore: mv {backup_file} main.py")
        print("🔧 Please check errors above and retry")

if __name__ == "__main__":
    main()