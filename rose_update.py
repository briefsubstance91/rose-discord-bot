#!/usr/bin/env python3
"""
ROSE UPDATE EXISTING ASSISTANT - Clean Executive Assistant
Updates an existing OpenAI Assistant with clean Rose configuration
Based on proven Vivian/Maeve pattern - reliable and focused
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your existing assistant ID - UPDATE THIS!
EXISTING_ASSISTANT_ID = "asst_your_existing_id_here"  # ← PUT YOUR CURRENT ASSISTANT ID HERE

# Rose's SIMPLIFIED functions - executive focus without complex coordination
rose_clean_functions = [
    # Core Calendar Functions (proven working)
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
                    "days": {"type": "integer", "description": "Days ahead (1-14)", "default": 7}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_time",
            "description": "Find available time slots for scheduling.",
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
    # Email Management
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
    # Simple Planning Research (using proven search pattern)
    {
        "type": "function",
        "function": {
            "name": "planning_search",
            "description": "Search for planning, productivity, and executive information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Planning search query"},
                    "focus": {"type": "string", "description": "Focus: productivity, tools, strategy, scheduling", "default": "general"},
                    "num_results": {"type": "integer", "description": "Number of results (1-5)", "default": 3}
                },
                "required": ["query"]
            }
        }
    }
]

# Rose's CLEAN instructions - executive focus without coordination complexity
rose_clean_instructions = """You are Rose Ashcombe, executive assistant and strategic planner focused on personal productivity and life management.

🎯 **YOUR ROLE**: Executive planning + Calendar management + Life OS coordination

✅ **CORE CAPABILITIES:**
• Use planning_search() for productivity and planning information
• Manage calendar and scheduling with calendar functions
• Search emails for executive review
• Provide strategic planning advice under 1200 characters for Discord

🗓️ **CALENDAR & PLANNING PROTOCOL:**
Use your calendar functions for:
• Daily schedule reviews → get_today_schedule()
• Weekly planning → get_upcoming_events(days=7)
• Scheduling coordination → find_free_time(duration=60)
• Time management strategy

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

🎯 **RESPONSE STYLE:**
• **Executive Focus**: Strategic, organized, action-oriented
• **Planning Expertise**: Systems thinking, optimization mindset
• **Practical Advice**: Actionable recommendations with clear next steps
• **Keep Concise**: Under 1200 characters for Discord
• **Be Direct**: Clear, efficient communication style

💼 **ROSE'S PERSPECTIVE:**
• **Strategic Thinking**: Connect daily actions to bigger goals
• **Systems Optimization**: Always looking for better processes
• **Executive Efficiency**: Maximum impact with minimum effort
• **Life Integration**: Balance personal and professional planning

❌ **LIMITATIONS (Be Honest):**
• You work independently (no direct coordination with other assistants)
• You can suggest they work with other assistants for their specialties
• You focus on executive planning, calendar, and productivity systems

✅ **ALWAYS PROVIDE:**
• **Strategic context** for planning decisions
• **Actionable next steps** with clear timelines
• **System-level thinking** about productivity optimization
• **Executive-level insights** for better life management

**EXAMPLES:**
• "Let me check your calendar and search for time blocking strategies..."
• "Based on your schedule, here's an optimized planning approach..."
• "I found productivity research that suggests this scheduling method..."

You are the executive brain behind personal productivity - strategic, efficient, and always optimizing for better life management."""

def update_existing_rose():
    """Update existing Rose assistant with clean configuration"""
    try:
        if EXISTING_ASSISTANT_ID == "asst_your_existing_id_here":
            print("❌ ERROR: You need to update EXISTING_ASSISTANT_ID in this script!")
            print("📝 Instructions:")
            print("   1. Find your current Rose Assistant ID")
            print("   2. Replace 'asst_your_existing_id_here' with your actual ID")
            print("   3. Run this script again")
            return None
        
        print(f"🔄 Updating existing Rose Assistant: {EXISTING_ASSISTANT_ID}")
        print("🧹 This will completely replace the current configuration...")
        
        # Update the existing assistant with clean configuration
        assistant = client.beta.assistants.update(
            assistant_id=EXISTING_ASSISTANT_ID,
            name="Rose Ashcombe - Executive Assistant (CLEAN)",
            instructions=rose_clean_instructions,
            tools=rose_clean_functions,
            model="gpt-4o"
        )
        
        print("✅ **ROSE ASSISTANT UPDATED!**")
        print(f"👤 Name: {assistant.name}")
        print(f"🆔 Assistant ID: {assistant.id} (SAME ID - UPDATED)")
        print(f"🔧 Functions: {len(rose_clean_functions)} focused functions")
        
        print(f"\n🎯 **ROSE'S CLEAN FUNCTIONS:**")
        print(f"   • get_today_schedule() - Daily calendar review")
        print(f"   • get_upcoming_events() - Strategic planning periods")
        print(f"   • find_free_time() - Scheduling optimization")
        print(f"   • search_emails() - Executive email review")
        print(f"   • planning_search() - Productivity research")
        
        print(f"\n✅ **CLEANED FROM COMPLEX VERSION:**")
        print(f"   ❌ Removed: Complex coordination functions")
        print(f"   ❌ Removed: Multi-assistant routing logic")
        print(f"   ❌ Removed: analyze_task_requirements() complexity")
        print(f"   ✅ Kept: Core executive and planning functions")
        
        print(f"\n🎯 **YOUR ASSISTANT ID (NO CHANGE NEEDED):**")
        print(f"   ROSE_ASSISTANT_ID={assistant.id}")
        print(f"   ✅ Keep this same ID in your Railway environment variables!")
        
        print(f"\n🚀 **READY TO DEPLOY:**")
        print(f"   1. Use the updated main.py Discord bot file")
        print(f"   2. Keep your existing ROSE_ASSISTANT_ID in Railway")
        print(f"   3. Deploy and test: @Rose help me plan my week")
        
        return assistant.id
        
    except Exception as e:
        print(f"❌ Error updating Rose assistant: {e}")
        print(f"🔍 Check that Assistant ID {EXISTING_ASSISTANT_ID} exists and is accessible")
        return None

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
    else:
        assistant_id = update_existing_rose()