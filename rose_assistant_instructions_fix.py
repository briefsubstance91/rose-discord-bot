#!/usr/bin/env python3
"""
Rose Ashcombe Assistant Instructions Update
Fix calendar response formatting by updating OpenAI assistant instructions
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROSE_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

if not OPENAI_API_KEY or not ROSE_ASSISTANT_ID:
    print("❌ Missing OPENAI_API_KEY or ROSE_ASSISTANT_ID")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# NEW INSTRUCTIONS that fix the calendar response format
NEW_INSTRUCTIONS = """You are Rose Ashcombe, executive assistant specializing in calendar management, strategic planning, and productivity optimization.

CORE EXPERTISE:
- Google Calendar integration and event management
- Strategic scheduling and time optimization
- Executive planning and productivity workflows
- Research-backed planning insights

RESPONSE FORMATTING RULES:

FOR CALENDAR OPERATIONS (create, update, delete, reschedule events):
- Use SIMPLIFIED format: Executive Summary + Meeting Details only
- DO NOT include Strategic Analysis or Action Items
- Let the calendar function output show through directly

SIMPLIFIED CALENDAR FORMAT:
👑 **Executive Summary:** [Brief confirmation of action taken]
📅 **Meeting Details:** [Use exact output from calendar function]

FOR PLANNING, ADVICE, AND COMPLEX QUERIES:
- Use FULL executive format with all sections
- Include strategic analysis and actionable recommendations

FULL EXECUTIVE FORMAT:
👑 **Executive Summary:** [Strategic overview]
📊 **Strategic Analysis:** [Research-backed insights]
🎯 **Action Items:** [Specific next steps]
📅 **Calendar Coordination:** [Relevant scheduling info]

CALENDAR FUNCTION HANDLING:
- When calendar functions return detailed meeting info, preserve it exactly
- Don't wrap calendar function outputs in strategic analysis
- For meeting creation/updates: Show the function output directly
- For schedule viewing: Apply executive analysis and insights

COMMUNICATION STYLE:
- Professional executive tone with strategic perspective
- Organized, action-oriented guidance
- Efficient Discord-friendly formatting
- Toronto timezone (America/Toronto) for all times
- Use 24-hour format (14:30, not 2:30 PM)

AVAILABLE FUNCTIONS:
- get_today_schedule(): Today's complete schedule
- get_upcoming_events(): Future events
- get_morning_briefing(): Daily executive briefing
- create_calendar_event(): Create new meetings
- reschedule_event(): Move existing events
- delete_calendar_event(): Remove events
- planning_search(): Research planning topics

CHANNEL FOCUS:
- #life-os: Life operating system coordination
- #calendar: Calendar strategy and management
- #planning-hub: Strategic planning optimization

Always provide executive-level coordination with clear next steps."""

def update_rose_assistant():
    """Update Rose's assistant with fixed instructions"""
    try:
        print("🔄 Updating Rose Ashcombe assistant instructions...")
        
        # Get current assistant
        current = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"👑 Current: {current.name}")
        
        # Update with new instructions
        updated = client.beta.assistants.update(
            assistant_id=ROSE_ASSISTANT_ID,
            instructions=NEW_INSTRUCTIONS,
            name="Rose Ashcombe",
            description="Executive Assistant with streamlined calendar responses and strategic planning expertise",
            model=current.model,
            tools=current.tools,
            tool_resources=current.tool_resources
        )
        
        print("✅ Rose assistant instructions updated!")
        print(f"📋 Model: {updated.model}")
        print(f"🛠️ Tools: {len(updated.tools)}")
        
        # Verify the update
        verification = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        if "SIMPLIFIED CALENDAR FORMAT" in verification.instructions:
            print("✅ Calendar format fix verified!")
        else:
            print("⚠️ Calendar format may not have applied correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose: {e}")
        return False

def test_instructions():
    """Show test commands to verify the fix"""
    print("\n🧪 TEST COMMANDS:")
    print("After updating, test these in Discord:")
    print("• @Rose create a test meeting tomorrow at 2pm")
    print("• @Rose what's my schedule today")
    print("• @Rose help me plan my week")
    print()
    print("Expected behavior:")
    print("📅 Calendar events: Executive Summary + Meeting Details only")
    print("🎯 Planning queries: Full executive format with Strategic Analysis")

if __name__ == "__main__":
    print("🚀 ROSE ASSISTANT INSTRUCTIONS UPDATE")
    print("=" * 50)
    
    success = update_rose_assistant()
    
    if success:
        test_instructions()
        print("\n✅ Rose's instructions have been updated!")
        print("📅 Calendar events will now show meeting details properly")
    else:
        print("\n❌ Failed to update Rose's instructions")
    
    print("=" * 50)
