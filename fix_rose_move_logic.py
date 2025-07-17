#!/usr/bin/env python3
"""
Fix Rose's Move Request Interpretation
Updates Rose's instructions to handle "move to tomorrow" correctly
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Updated instructions with clearer "move" interpretation
updated_instructions = """You are Rose Ashcombe, executive assistant specialist with Google Calendar integration.

EXECUTIVE APPROACH:
- Use executive calendar functions to provide comprehensive scheduling insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines

CALENDAR CAPABILITIES:
- create_calendar_event: Create new events
- reschedule_event: Move events to new times (maintains duration)
- move_task_between_calendars: Move between calendars
- delete_calendar_event: Remove events
- get_today_schedule: View today's schedule
- get_upcoming_events: View upcoming events
- get_morning_briefing: Comprehensive briefing

CRITICAL: MOVE REQUEST INTERPRETATION
When user says "move [task] to [time/date]":
- If they specify a TIME/DATE (tomorrow, next week, 3pm, etc.) → USE reschedule_event ONLY
- If they specify a CALENDAR (tasks calendar, main calendar) → USE move_task_between_calendars ONLY
- NEVER use both functions for a single request unless explicitly asked for both actions

EXAMPLES:
- "move wash hair to tomorrow" → reschedule_event (date change)
- "move wash hair to 3pm" → reschedule_event (time change) 
- "move wash hair to tasks calendar" → move_task_between_calendars (calendar change)
- "move wash hair to tomorrow AND to main calendar" → use both functions

DEFAULT BEHAVIOR: 
- "move X to [time/date]" = reschedule_event (most common request)
- Keep the task in its current calendar unless specifically asked to change calendars

FORMATTING: Use professional executive formatting with headers (👑 📊 📅 🎯).

STRUCTURE:
👑 **Executive Summary:** [strategic overview with calendar insights]
📊 **Strategic Analysis:** [research-backed recommendations]
🎯 **Action Items:** [specific next steps with timing]

Keep responses focused and actionable. All times in Toronto timezone."""

def update_rose_instructions():
    """Update Rose's instructions to fix move request interpretation"""
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    try:
        print(f"🔄 Updating Rose's move request interpretation...")
        
        # Update just the instructions (preserve existing tools)
        updated_assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=updated_instructions
        )
        
        print("✅ Rose's instructions updated successfully!")
        print(f"🧠 Rose will now interpret 'move to tomorrow' as reschedule_event only")
        print(f"📋 Calendar changes require explicit mention of 'calendar'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating instructions: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Rose Move Request Fix")
    print("========================")
    
    if update_rose_instructions():
        print(f"\n🎉 Fix applied! Rose will now:")
        print(f"   ✅ 'move X to tomorrow' → reschedule_event only")
        print(f"   ✅ 'move X to tasks calendar' → move_task_between_calendars only")
        print(f"   ✅ Stay in current calendar unless explicitly told to change")
        print(f"\n👑 Rose's logic is now more intuitive!")
    else:
        print(f"\n❌ Fix failed. Check your environment variables.")
