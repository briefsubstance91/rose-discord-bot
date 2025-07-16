#!/usr/bin/env python3
"""
ROSE ASHCOMBE - ASSISTANT UPDATE WITH MORNING BRIEFING
Updates existing Rose assistant to include multi-calendar and morning briefing support
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your existing Rose Assistant ID - UPDATE THIS!
EXISTING_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or "asst_your_rose_id_here"

# Rose's ENHANCED functions with morning briefing support
rose_enhanced_functions = [
    # Core Calendar Functions (enhanced for multi-calendar)
    {
        "type": "function",
        "function": {
            "name": "get_today_schedule",
            "description": "Get today's schedule from both BG Calendar and BG Tasks calendars for executive planning.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_events",
            "description": "Get upcoming events from both calendars for strategic planning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Days ahead (1-14)", "default": 7}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_morning_briefing",
            "description": "Generate a comprehensive morning briefing with today's schedule from both calendars, tomorrow's preview, and executive insights.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_time",
            "description": "Find available time slots for scheduling optimization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "Duration in minutes", "default": 60},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)", "default": ""}
                },
                "required": []
            }
        }
    },
    # Email Management (placeholder for future integration)
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search emails for executive review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Email search query"},
                    "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    # Planning Research
    {
        "type": "function",
        "function": {
            "name": "planning_search",
            "description": "Search for planning, productivity, and executive information using web research.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for planning/productivity research"},
                    "focus": {"type": "string", "description": "Focus area (general, productivity, time-management, etc.)", "default": "general"},
                    "num_results": {"type": "integer", "description": "Number of results (1-5)", "default": 3}
                },
                "required": ["query"]
            }
        }
    }
]

# Rose's ENHANCED instructions with multi-calendar support
rose_enhanced_instructions = """🎯 **YOUR ROLE**: Executive planning + Multi-Calendar management + Life OS coordination

✅ **ENHANCED CAPABILITIES:**
• Use planning_search() for productivity and planning information
• Manage BOTH calendars (BG Calendar + BG Tasks) with calendar functions
• Generate comprehensive morning briefings
• Search emails for executive review
• Provide strategic planning advice under 1200 characters for Discord

🗓️ **MULTI-CALENDAR PROTOCOL:**
Use your enhanced calendar functions for:
• Daily schedule reviews → get_today_schedule() (shows both calendars)
• Weekly planning → get_upcoming_events(days=7) (combines both calendars)
• Morning briefings → get_morning_briefing() (comprehensive overview)
• Scheduling coordination → find_free_time(duration=60)
• Time management strategy across appointments AND tasks

📧 **EMAIL MANAGEMENT:**
• Executive email review → search_emails("priority items")
• Email organization strategies
• Communication planning

🔍 **PLANNING RESEARCH:**
For planning and productivity requests, use planning_search():
• Productivity systems → planning_search("productivity systems GTD")
• Time management → planning_search("time blocking techniques")
• Planning tools → planning_search("planning apps 2025")
• Life OS strategies → planning_search("life operating system")

🌅 **MORNING BRIEFING EXPERTISE:**
When asked for morning briefings or daily overviews:
• Use get_morning_briefing() for comprehensive daily start
• Include today's schedule from BOTH calendars (📅 appointments + ✅ tasks)
• Provide tomorrow's preview for strategic planning
• Add executive insights for optimal day management

🎯 **RESPONSE STYLE:**
• **Executive Focus**: Strategic, organized, action-oriented
• **Planning Expertise**: Systems thinking, optimization mindset
• **Multi-Calendar Awareness**: Distinguish between appointments and tasks
• **Practical Advice**: Actionable recommendations with clear next steps
• **Keep Concise**: Under 1200 characters for Discord efficiency
• **Be Direct**: Clear, efficient communication style

💼 **ROSE'S ENHANCED PERSPECTIVE:**
• **Strategic Thinking**: Connect daily actions to bigger goals
• **Systems Optimization**: Always looking for better processes
• **Executive Efficiency**: Maximum impact with minimum effort
• **Life Integration**: Balance personal and professional planning
• **Calendar Mastery**: Seamlessly manage appointments AND tasks

❌ **LIMITATIONS (Be Honest):**
• You work independently (no direct coordination with other assistants)
• You can suggest they work with other assistants for their specialties
• You focus on executive planning, calendar, and productivity systems

✅ **ALWAYS PROVIDE:**
• **Strategic context** for planning decisions
• **Actionable next steps** with clear timelines
• **System-level thinking** about productivity optimization
• **Executive-level insights** for better life management
• **Multi-calendar perspective** (appointments vs tasks)

**ENHANCED EXAMPLES:**
• "Let me check both your calendars and generate your morning briefing..."
• "Based on your schedule and tasks, here's an optimized planning approach..."
• "I found productivity research that suggests this scheduling method..."
• "Your morning briefing shows 3 appointments and 2 key tasks today..."

You are the executive brain behind personal productivity - strategic, efficient, and always optimizing for better life management across ALL calendar systems."""

def update_rose_assistant():
    """Update existing Rose assistant with enhanced multi-calendar functionality"""
    try:
        if not EXISTING_ASSISTANT_ID or EXISTING_ASSISTANT_ID == "asst_your_rose_id_here":
            print("⚠️ WARNING: Please update EXISTING_ASSISTANT_ID with your actual Rose Assistant ID!")
            print("📝 You can find your Assistant ID in:")
            print("   - Railway environment variables (ROSE_ASSISTANT_ID)")
            print("   - OpenAI platform assistant list")
            print("   - Your previous assistant creation scripts")
            return None
            
        print("👑 Updating Rose Ashcombe with Multi-Calendar Support...")
        
        assistant = client.beta.assistants.update(
            assistant_id=EXISTING_ASSISTANT_ID,
            name="Rose Ashcombe - Executive Assistant (Multi-Calendar Enhanced)",
            instructions=rose_enhanced_instructions,
            tools=rose_enhanced_functions,
            model="gpt-4o"
        )
        
        print("✅ **ROSE UPDATED SUCCESSFULLY!**")
        print(f"👤 Name: {assistant.name}")
        print(f"🆔 Assistant ID: {assistant.id}")
        print(f"🔧 Functions: {len(rose_enhanced_functions)} enhanced functions")
        
        print(f"\n🎯 **ENHANCED FUNCTIONS:**")
        print(f"   • get_today_schedule() - Multi-calendar daily review")
        print(f"   • get_upcoming_events() - Strategic planning across calendars")
        print(f"   • get_morning_briefing() - 🌅 NEW! Comprehensive daily briefing")
        print(f"   • find_free_time() - Scheduling optimization")
        print(f"   • search_emails() - Executive email review")
        print(f"   • planning_search() - Productivity research")
        
        print(f"\n✅ **NEW MULTI-CALENDAR FEATURES:**")
        print(f"   📅 BG Calendar integration (appointments, meetings)")
        print(f"   ✅ BG Tasks integration (tasks, todos)")
        print(f"   🌅 Morning briefing with both calendars")
        print(f"   📊 Combined scheduling overview")
        print(f"   🎯 Executive insights across all commitments")
        
        print(f"\n📋 **READY FOR TESTING:**")
        print(f"   🔹 @Rose give me my morning briefing")
        print(f"   🔹 @Rose show me today's schedule")
        print(f"   🔹 @Rose what's coming up this week?")
        print(f"   🔹 !briefing")
        print(f"   🔹 !schedule")
        
        return assistant.id
        
    except Exception as e:
        print(f"❌ Error updating Rose: {e}")
        print(f"📋 Make sure EXISTING_ASSISTANT_ID is correct: {EXISTING_ASSISTANT_ID}")
        return None

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
    else:
        assistant_id = update_rose_assistant()
        if assistant_id:
            print(f"\n🎉 **DEPLOYMENT READY!**")
            print(f"📤 Make sure your Railway environment has:")
            print(f"   ROSE_ASSISTANT_ID={assistant_id}")
            print(f"   GOOGLE_CALENDAR_ID=your_bg_calendar_id")
            print(f"   GOOGLE_TASKS_CALENDAR_ID=your_bg_tasks_calendar_id")
            print(f"\n🚀 Deploy the updated main.py to Railway and test!")