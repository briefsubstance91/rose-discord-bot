#!/usr/bin/env python3
"""
Update Rose's Event Confirmation Style
Makes confirmations more concise and switches to 24-hour time format
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Updated instructions with concise confirmations and 24-hour time
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
- Personal tasks: cleaning, organizing, shopping, errands
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

EXAMPLES:
- "Root touch-up appointment" → calendar_type: "tasks" (personal beauty care)
- "Hair appointment" → calendar_type: "tasks" (personal grooming)
- "Tree maintenance" → calendar_type: "tasks" (personal property maintenance)
- "Client meeting" → calendar_type: "calendar" (business with others)
- "Dentist appointment" → calendar_type: "tasks" (personal health)
- "Team presentation" → calendar_type: "calendar" (work with others)

DEFAULT RULE: If unsure, personal/individual activities → "tasks", activities with others → "calendar"

TIME FORMAT:
- ALWAYS use 24-hour time format (14:30, not 2:30 PM)
- All times in Toronto timezone (America/Toronto)

EVENT CONFIRMATION FORMAT:
When confirming calendar events, use this CONCISE format only:

👑 **Executive Summary:**
The "[Event Name]" [task/event] has been successfully scheduled for [Day, Date] from [24H:time] to [24H:time] on the [Calendar Name] calendar.

💼 **Calendar Coordination:**
• Task Details: [Live Link]
• Calendar: [Calendar Name]

DO NOT INCLUDE:
- Strategic Analysis sections
- Action Items sections  
- Extra planning advice
- Equipment preparation lists
- Additional recommendations

ONLY for complex queries or planning requests should you include strategic analysis. For simple event creation, keep confirmations brief and executive.

CALENDAR FUNCTIONS:
- create_calendar_event: Create new events (specify correct calendar_type)
- reschedule_event: Move events to new times
- move_task_between_calendars: Move between calendars
- delete_calendar_event: Remove events
- get_today_schedule: View today's schedule
- get_upcoming_events: View upcoming events
- get_morning_briefing: Comprehensive briefing

For general scheduling inquiries and complex planning, use full executive formatting with strategic headers (👑 📊 📅 🎯 💼) and provide organized, action-oriented guidance.

Keep event confirmations focused and concise while maintaining executive professionalism."""

def update_rose_confirmations():
    """Update Rose's confirmation style and time format"""
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        return False
    
    try:
        print(f"🔄 Updating Rose's confirmation style...")
        
        # Get current assistant to preserve tools
        current_assistant = client.beta.assistants.retrieve(ASSISTANT_ID)
        
        # Update instructions while preserving tools
        updated_assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=updated_instructions,
            tools=current_assistant.tools  # Preserve existing tools
        )
        
        print("✅ Rose's confirmation style updated successfully!")
        print("\n📋 Key Changes:")
        print("   • Concise event confirmations (no extra analysis)")
        print("   • 24-hour time format (14:30 instead of 2:30 PM)")
        print("   • Keeps Executive Summary + Calendar Coordination")
        print("   • Removes Strategic Analysis for simple events")
        print("   • Removes Action Items for confirmations")
        print("   • Maintains live calendar links")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose's instructions: {e}")
        return False

def show_examples():
    """Show examples of the new confirmation format"""
    
    print("\n📝 New Confirmation Format Examples:")
    print("=" * 50)
    
    print("OLD FORMAT (verbose):")
    print("👑 Executive Summary: Task scheduled...")
    print("📊 Strategic Analysis: Allocating time allows...")
    print("🎯 Action Items: Prepare tools, Review health...")
    print("💼 Calendar Coordination: Details + Link")
    print()
    
    print("NEW FORMAT (concise):")
    print("👑 Executive Summary:")
    print("The \"Tree Maintenance\" task has been scheduled for Friday, July 18 from 11:00 to 11:30 on the BG Tasks calendar.")
    print()
    print("💼 Calendar Coordination:")
    print("• Task Details: [View Event]")
    print("• Calendar: BG Tasks")
    print()
    
    print("✅ Much cleaner and more focused!")

def main():
    """Main script execution"""
    print("📝 Rose Confirmation Style Update")
    print("=" * 40)
    
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables")
        print("💡 Make sure your .env file contains ROSE_ASSISTANT_ID")
        return
    
    # Update Rose's confirmation style
    success = update_rose_confirmations()
    
    if success:
        print("\n🎉 Rose's confirmation style has been updated!")
        
        # Show examples
        show_examples()
        
        print("\n🧪 Test the new format:")
        print("   @Rose create a task for grocery shopping tomorrow at 15:30")
        print("   Expected: Concise confirmation with 24-hour time")
        
        print("\n💡 What changed:")
        print("   ✅ Keeps: Executive Summary + Calendar Coordination + Links")
        print("   ❌ Removes: Strategic Analysis + Action Items for simple events")
        print("   🕐 Uses: 24-hour time format (14:30, 15:30, etc.)")
        
    else:
        print("\n❌ Failed to update Rose's confirmation style")
        print("💡 Check your OpenAI API key and assistant ID")

if __name__ == "__main__":
    main()