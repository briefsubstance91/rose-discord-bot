#!/usr/bin/env python3
"""
Update Rose Assistant with Calendar Management Functions
Run this script to add the new functions to your OpenAI assistant
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Define the new calendar management functions
calendar_functions = [
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
            "description": "Get comprehensive morning executive briefing with today + tomorrow preview.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_time",
            "description": "Find available time slots in the calendar for scheduling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes", "default": 60},
                    "preferred_days": {"type": "array", "items": {"type": "string"}, "description": "Preferred days of week"},
                    "preferred_hours": {"type": "array", "items": {"type": "integer"}, "description": "Preferred hours (24-hour format)"},
                    "days_ahead": {"type": "integer", "description": "How many days to search ahead", "default": 7}
                },
                "required": []
            }
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
            "name": "update_calendar_event",
            "description": "Update an existing calendar event's details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_search": {"type": "string", "description": "Search term to find the event"},
                    "new_title": {"type": "string", "description": "New event title (optional)"},
                    "new_start_time": {"type": "string", "description": "New start time in YYYY-MM-DDTHH:MM:SS format (optional)"},
                    "new_end_time": {"type": "string", "description": "New end time in YYYY-MM-DDTHH:MM:SS format (optional)"},
                    "new_description": {"type": "string", "description": "New event description (optional)"}
                },
                "required": ["event_search"]
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
                    "new_end_time": {"type": "string", "description": "New end time (optional, will calculate from original duration)"}
                },
                "required": ["event_search", "new_start_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_task_between_calendars",
            "description": "Move a task/event between different calendars (e.g., from BG Calendar to BG Tasks).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_search": {"type": "string", "description": "Search term to find the task/event"},
                    "target_calendar": {"type": "string", "description": "Target calendar: 'tasks', 'calendar', or calendar name", "default": "tasks"}
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
            "description": "Search for planning, productivity, and executive information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for planning/productivity research"},
                    "focus": {"type": "string", "description": "Focus area (e.g., 'time management', 'productivity')", "default": "general"},
                    "num_results": {"type": "integer", "description": "Number of results (1-5)", "default": 3}
                },
                "required": ["query"]
            }
        }
    }
]

# Updated instructions for Rose
updated_instructions = """You are Rose Ashcombe, executive assistant specialist with complete Google Calendar API integration and advanced task management capabilities.

EXECUTIVE APPROACH:
- Use executive calendar functions to provide comprehensive scheduling insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines
- Focus on high-impact activity identification and time management
- Leverage advanced calendar management: create, update, reschedule, move, delete events
- BRIEFING INTELLIGENCE: For briefing requests, automatically use get_morning_briefing() function

CALENDAR CAPABILITIES:
- create_calendar_event: Create new events in any accessible calendar
- update_calendar_event: Modify existing event details
- reschedule_event: Move events to new times (maintains duration)
- move_task_between_calendars: Move between BG Calendar ↔ BG Tasks
- delete_calendar_event: Remove unnecessary events
- find_free_time: Find optimal time slots for scheduling
- Smart conflict detection and availability checking

USAGE PATTERNS:
- For "move X to tomorrow": use reschedule_event
- For "create meeting": use create_calendar_event  
- For "move to tasks calendar": use move_task_between_calendars
- For "delete old event": use delete_calendar_event
- For "when am I free": use find_free_time
- For "change meeting title": use update_calendar_event

FORMATTING: Use professional executive formatting with strategic headers (👑 📊 📅 🎯 💼) and provide organized, action-oriented guidance.

STRUCTURE:
👑 **Executive Summary:** [strategic overview with calendar insights]
📊 **Strategic Analysis:** [research-backed recommendations]
🎯 **Action Items:** [specific next steps with timing]

Keep core content focused and always provide strategic context with calendar coordination. Leverage all available calendar management functions to provide comprehensive executive assistance. All times are in Toronto timezone (America/Toronto)."""

def update_assistant():
    """Update the Rose assistant with new calendar functions"""
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    try:
        print(f"🔄 Updating Rose Assistant {ASSISTANT_ID}...")
        
        # Update the assistant with new tools and instructions
        updated_assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            tools=calendar_functions,
            instructions=updated_instructions
        )
        
        print("✅ Rose Assistant updated successfully!")
        print(f"📋 Functions added: {len(calendar_functions)}")
        print(f"🤖 Assistant ID: {updated_assistant.id}")
        print(f"📝 Name: {updated_assistant.name}")
        
        # List the new functions
        print("\n🔧 New Calendar Functions:")
        for tool in calendar_functions:
            if tool["type"] == "function":
                func_name = tool["function"]["name"]
                func_desc = tool["function"]["description"]
                print(f"  • {func_name}: {func_desc}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Rose Assistant Calendar Function Updater")
    print("==========================================")
    
    if update_assistant():
        print("\n🎉 Update completed! Rose now has full calendar management capabilities.")
        print("\n💡 Rose can now:")
        print("  • Create calendar events")
        print("  • Update existing events") 
        print("  • Reschedule events to new times")
        print("  • Move tasks between calendars")
        print("  • Delete calendar events")
        print("  • Find free time slots")
        print("\n👑 Ready for advanced executive assistance!")
    else:
        print("\n❌ Update failed. Please check your environment variables and try again.")
