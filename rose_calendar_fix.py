#!/usr/bin/env python3
"""
ROSE ASHCOMBE - CALENDAR RESPONSE FORMAT FIX
Updates Rose's assistant instructions to streamline calendar event responses
Removes Strategic Analysis and Action Items sections from calendar events
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROSE_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in environment variables")
    exit(1)

if not ROSE_ASSISTANT_ID:
    print("❌ ROSE_ASSISTANT_ID not found in environment variables")
    exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Updated instructions with streamlined calendar response format
UPDATED_INSTRUCTIONS = """You are Rose Ashcombe, executive assistant specializing in calendar management, planning, and strategic coordination. You excel at Google Calendar integration, scheduling optimization, and executive productivity.

CORE EXPERTISE:
- Executive calendar management and strategic scheduling
- Meeting coordination and appointment optimization  
- Task planning and productivity workflows
- Research-backed planning insights and time management
- Life OS coordination and quarterly business reviews (QBR)

CALENDAR RESPONSE FORMATTING:
For calendar events (creation, updates, scheduling):
- Use SIMPLIFIED format with Executive Summary and Calendar Coordination only
- DO NOT include Strategic Analysis or Action Items sections for calendar events
- Focus on clear confirmation and essential details

SIMPLIFIED CALENDAR FORMAT:
👑 **Executive Summary:** [Brief confirmation of calendar action]
📅 **Calendar Coordination:** [Event details, timing, and calendar location]

FULL STRATEGIC FORMAT (for planning, advice, complex queries):
👑 **Executive Summary:** [Strategic overview with insights]
📊 **Strategic Analysis:** [Research-backed recommendations] 
🎯 **Action Items:** [Specific next steps with timing]
📅 **Calendar Coordination:** [Relevant scheduling information]

COMMUNICATION STYLE:
- Professional executive tone with strategic perspective
- Organized, action-oriented guidance
- Efficient Discord-friendly formatting (under 1500 characters)
- Toronto timezone (America/Toronto) for all scheduling
- Use strategic headers with appropriate emojis

CALENDAR FUNCTIONS:
- get_today_schedule(): Current day's events
- get_upcoming_events(days): Events in specified timeframe  
- create_calendar_event(): Add new events
- planning_search(): Research for strategic planning

CHANNEL OWNERSHIP:
- #life-os: Life operating system and quarterly reviews
- #calendar: Calendar management and scheduling strategy  
- #planning-hub: Strategic planning and productivity optimization

Always provide executive-level insights with practical scheduling coordination."""

def update_rose_assistant():
    """Update Rose's assistant instructions to fix calendar response formatting"""
    
    try:
        print("🔄 Updating Rose Ashcombe assistant instructions...")
        
        # Get current assistant details
        current_assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"📋 Current Assistant: {current_assistant.name}")
        print(f"🎯 Current Model: {current_assistant.model}")
        
        # Update the assistant with new instructions
        updated_assistant = client.beta.assistants.update(
            assistant_id=ROSE_ASSISTANT_ID,
            instructions=UPDATED_INSTRUCTIONS,
            name="Rose Ashcombe",
            description="Executive Assistant specializing in calendar management, strategic planning, and productivity optimization with streamlined calendar responses",
            model=current_assistant.model,  # Preserve current model
            tools=current_assistant.tools,  # Preserve existing tools
            tool_resources=current_assistant.tool_resources  # Preserve tool resources
        )
        
        print("✅ Rose assistant updated successfully!")
        print(f"📝 Instructions updated: {len(UPDATED_INSTRUCTIONS)} characters")
        print(f"🛠️ Tools preserved: {len(updated_assistant.tools)}")
        
        # Verify the update
        verification = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        if "SIMPLIFIED CALENDAR FORMAT" in verification.instructions:
            print("✅ Calendar format fix verified in instructions")
        else:
            print("⚠️ Calendar format fix may not have applied correctly")
            
        print("\n📋 CHANGES MADE:")
        print("• ✅ Added simplified calendar response format")
        print("• ✅ Removed Strategic Analysis from calendar events")
        print("• ✅ Removed Action Items from calendar events") 
        print("• ✅ Kept full format for planning and complex queries")
        print("• ✅ Preserved all existing tools and capabilities")
        
        print("\n🎯 EXPECTED BEHAVIOR:")
        print("Calendar events will now show:")
        print("👑 Executive Summary + 📅 Calendar Coordination only")
        print("\nPlanning queries will still show:")
        print("👑 Executive Summary + 📊 Strategic Analysis + 🎯 Action Items")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose assistant: {e}")
        return False

def test_calendar_response_format():
    """Test if the calendar response format has been updated correctly"""
    print("\n🧪 TESTING CALENDAR RESPONSE FORMAT...")
    print("Try these commands in Discord to verify the fix:")
    print("• @Rose create a meeting tomorrow at 2pm")
    print("• @Rose what's on my calendar today")
    print("• @Rose schedule a planning session")
    print("\nExpected: Only Executive Summary + Calendar Coordination")
    print("No Strategic Analysis or Action Items for calendar events")

if __name__ == "__main__":
    print("🚀 ROSE CALENDAR RESPONSE FIX SCRIPT")
    print("=" * 50)
    
    success = update_rose_assistant()
    
    if success:
        test_calendar_response_format()
        print("\n✅ Rose calendar response format has been fixed!")
        print("📅 Calendar events will now have streamlined responses")
    else:
        print("\n❌ Failed to update Rose assistant")
        print("Please check your environment variables and try again")
    
    print("=" * 50)