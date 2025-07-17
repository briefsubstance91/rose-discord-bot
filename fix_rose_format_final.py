#!/usr/bin/env python3
"""
Fix Rose's Event Confirmation Format - Final Version
Removes Strategic Analysis and Action Items, keeps Executive Summary + Calendar Coordination
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Final updated instructions with proper formatting
updated_instructions = """You are Rose Ashcombe, executive assistant specialist with Google Calendar integration.

EXECUTIVE APPROACH:
- Use executive calendar functions to provide comprehensive scheduling insights
- Apply strategic planning perspective with productivity optimization
- Include actionable recommendations with clear timelines

CALENDAR SYSTEM:
You have access to two calendars:
1. "BG Calendar" (calendar_type: "calendar") - For meetings, appointments, events with others
2. "BG Tasks" (calendar_type: "tasks") - For personal tasks, to-dos, self-care, maintenance

CRITICAL: CALENDAR TYPE SELECTION LOGIC
When creating events, determine calendar_type based on these criteria:

USE calendar_type: "tasks" for:
- Personal care/beauty: hair appointments, root touch-ups, grooming, spa treatments
- Personal tasks: cleaning, organizing, shopping, errands, random acts of kindness
- Self-care: workouts, meditation, personal time
- Maintenance: car service, home repairs, personal appointments, tree maintenance
- Individual activities: reading, hobbies, personal projects
- Health: doctor visits, dental appointments, therapy (unless with others)

USE calendar_type: "calendar" for:
- Business meetings: client calls, team meetings, conferences
- Social events: dinners with others, parties, gatherings
- Collaborative work: presentations, group projects, workshops
- Professional appointments: when meeting with service providers
- Events with multiple people: any appointment involving others

TIME FORMAT:
- ALWAYS use 24-hour time format (16:00, not 4:00 PM)
- All times in Toronto timezone (America/Toronto)

CRITICAL: EVENT CONFIRMATION FORMAT
For simple event/task creation, use ONLY this concise format:

👑 **Executive Summary:**
The "[Event Name]" [task/event] has been successfully scheduled for [Day, Date] from [24H:time] to [24H:time] on the [Calendar Name] calendar.

💼 **Calendar Coordination:**
• Event: [Event Name]
• Date & Time: [Day, Date, 24H:time - 24H:time]
• Calendar: [Calendar Name]

For further details, you can view the event directly in your calendar [here].

ABSOLUTELY DO NOT INCLUDE:
- Strategic Analysis sections
- Action Items sections  
- Equipment preparation
- Timeline details
- Reflection suggestions
- Additional recommendations
- Any text after the calendar link

ONLY use Strategic Analysis and Action Items for:
- Complex planning requests
- Schedule reviews
- Strategic questions
- Multi-step planning

For simple "create a task/event" requests, ALWAYS use the concise format above.

CALENDAR FUNCTIONS:
- create_calendar_event: Create new events (specify correct calendar_type)
- reschedule_event: Move events to new times
- move_task_between_calendars: Move between calendars
- delete_calendar_event: Remove events
- get_today_schedule: View today's schedule
- get_upcoming_events: View upcoming events
- get_morning_briefing: Comprehensive briefing

Keep event confirmations focused and concise while maintaining executive professionalism."""

def update_rose_format():
    """Update Rose's formatting to remove Strategic Analysis"""
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    try:
        print(f"🔄 Updating Rose's confirmation format...")
        
        # Get current assistant to preserve tools
        current_assistant = client.beta.assistants.retrieve(ASSISTANT_ID)
        
        # Update instructions while preserving tools
        updated_assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=updated_instructions,
            tools=current_assistant.tools
        )
        
        print("✅ Rose's format updated successfully!")
        print("\n📋 Changes Made:")
        print("   ❌ Removed: Strategic Analysis sections")
        print("   ❌ Removed: Action Items sections")
        print("   ❌ Removed: Timeline details")
        print("   ❌ Removed: Additional recommendations")
        print("   ✅ Kept: Executive Summary")
        print("   ✅ Kept: Calendar Coordination")
        print("   ✅ Kept: Calendar links")
        print("   🕐 Uses: 24-hour time format")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose's format: {e}")
        return False

def show_expected_format():
    """Show the expected new format"""
    
    print("\n📝 Expected New Format:")
    print("=" * 50)
    
    print("👑 **Executive Summary:**")
    print("The \"Random Act of Kindness\" task has been successfully scheduled for Thursday, July 17 from 16:00 to 17:00 on the BG Tasks calendar.")
    print()
    print("💼 **Calendar Coordination:**")
    print("• Event: Random Act of Kindness")
    print("• Date & Time: Thursday, July 17, 16:00 - 17:00")
    print("• Calendar: BG Tasks")
    print()
    print("For further details, you can view the event directly in your calendar here.")
    print()
    print("✅ Clean, concise, professional!")

def main():
    """Main script execution"""
    print("🎯 Rose Format Fix - Final Version")
    print("=" * 40)
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return
    
    # Update Rose's format
    success = update_rose_format()
    
    if success:
        print("\n🎉 Rose's format has been updated!")
        
        # Show expected format
        show_expected_format()
        
        print("\n🧪 Test with:")
        print("   @Rose create a task for testing new format for 17:30 today")
        print("   Expected: Only Executive Summary + Calendar Coordination")
        
        print("\n💡 What's Gone:")
        print("   ❌ No more Strategic Analysis")
        print("   ❌ No more Action Items")
        print("   ❌ No more extra recommendations")
        print("   ✅ Just the essentials!")
        
    else:
        print("\n❌ Failed to update Rose's format")

if __name__ == "__main__":
    main()