#!/usr/bin/env python3
"""
Update Rose Assistant with Calendar Management Functions - CLEAN VERSION
Run this script to add calendar functions while keeping file search and code interpreter
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Define ALL tools (preserving existing + adding new calendar functions)
all_tools = [
    # PRESERVE EXISTING TOOLS
    {"type": "file_search"},
    {"type": "code_interpreter"},
    
    # ADD NEW CALENDAR MANAGEMENT FUNCTIONS
    {
        "type": "function",
        "function": {
            "name": "get_today_schedule",
            "description": "Get today's calendar schedule for executive planning.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_events",
            "description": "Get upcoming calendar events for strategic planning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Days ahead (1-30)", "default": 7}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_morning_briefing",
            "description": "Get comprehensive morning executive briefing.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a new calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title/name"},
                    "start_time": {"type": "string", "description": "Start time in YYYY-MM-DDTHH:MM:SS format"},
                    "end_time": {"type": "string", "description": "End time in YYYY-MM-DDTHH:MM:SS format"},
                    "calendar_type": {"type": "string", "description": "Target calendar: 'calendar' or 'tasks'", "default": "calendar"},
                    "description": {"type": "string", "description": "Event description", "default": ""}
                },
                "required": ["title", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_event",
            "description": "Reschedule an existing calendar event to a new time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_search": {"type": "string", "description": "Search term to find the event"},
                    "new_start_time": {"type": "string", "description": "New start time in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format"},
                    "new_end_time": {"type": "string", "description": "New end time (optional)"}
                },
                "required": ["event_search", "new_start_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_task_between_calendars",
            "description": "Move a task/event between different calendars.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_search": {"type": "string", "description": "Search term to find the task/event"},
                    "target_calendar": {"type": "string", "description": "Target calendar: 'tasks' or 'calendar'", "default": "tasks"}
                },
                "required": ["task_search"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "Delete a calendar event permanently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_search": {"type": "string", "description": "Search term to find the event to delete"}
                },
                "required": ["event_search"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "planning_search",
            "description": "Search for planning and productivity information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for planning research"},
                    "focus": {"type": "string", "description": "Focus area", "default": "general"},
                    "num_results": {"type": "integer", "description": "Number of results", "default": 3}
                },
                "required": ["query"]
            }
        }
    }
]

# Updated instructions for Rose
updated_instructions = """You are Rose Ashcombe, executive assistant specialist with complete Google Calendar integration.

CALENDAR CAPABILITIES:
- create_calendar_event: Create new events
- reschedule_event: Move events to new times
- move_task_between_calendars: Move between calendars
- delete_calendar_event: Remove events
- get_today_schedule: View today's schedule
- get_upcoming_events: View upcoming events
- get_morning_briefing: Comprehensive briefing

USAGE PATTERNS:
- For "move X to tomorrow": use reschedule_event
- For "create meeting": use create_calendar_event  
- For "move to tasks calendar": use move_task_between_calendars

FORMATTING: Use professional executive formatting with headers (👑 📊 📅 🎯).

Keep responses focused and actionable. All times in Toronto timezone."""

def update_assistant():
    """Update Rose with calendar functions while preserving existing features"""
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    try:
        print(f"🔄 Updating Rose Assistant {ASSISTANT_ID}...")
        
        # Update the assistant
        updated_assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            tools=all_tools,
            instructions=updated_instructions
        )
        
        print("✅ Rose Assistant updated successfully!")
        print(f"🔧 Total Tools: {len(updated_assistant.tools)}")
        
        # Count tools
        file_search = False
        code_interpreter = False
        function_count = 0
        
        for tool in updated_assistant.tools:
            if tool.type == "file_search":
                file_search = True
            elif tool.type == "code_interpreter":
                code_interpreter = True
            elif tool.type == "function":
                function_count += 1
        
        print(f"\n📊 Tool Summary:")
        print(f"   📁 File Search: {'✅' if file_search else '❌'}")
        print(f"   🐍 Code Interpreter: {'✅' if code_interpreter else '❌'}")
        print(f"   ⚡ Calendar Functions: {function_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Rose Assistant Update - Clean Version")
    print("=======================================")
    
    if update_assistant():
        print(f"\n🎉 Success! Rose now has:")
        print(f"   ✅ File Search & Code Interpreter")
        print(f"   ✅ Full Calendar Management")
        print(f"\n👑 Ready for executive assistance!")
    else:
        print(f"\n❌ Update failed. Check your environment variables.")
