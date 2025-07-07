#!/usr/bin/env python3
"""
ROSE ASHCOMBE - COMPLETE FIXED SETUP
Executive Assistant with File Search + Code Interpreter + Functions
Preserves all tools properly for planning and productivity
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Rose's COMPLETE functions with all tools preserved
rose_complete_functions = [
    # Core planning search
    {
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
    },
    # Calendar functions
    {
        "name": "get_today_schedule",
        "description": "Get today's calendar schedule for executive planning.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_upcoming_events",
        "description": "Get upcoming calendar events for strategic planning.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days ahead (1-14)", "default": 7}
            },
            "required": []
        }
    },
    {
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
    },
    # Email management
    {
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
]

# Rose's complete instructions
rose_complete_instructions = """You are Rose Ashcombe, executive assistant and strategic planner with comprehensive digital tools for productivity optimization.

👑 **YOUR ROLE**: Executive Planning + Life OS Coordination + Strategic Productivity + System Optimization

✨ **ENHANCED CAPABILITIES:**
• File Search: Access planning templates, productivity documents, life OS frameworks
• Code Interpreter: Analyze productivity metrics, time tracking data, goal progression
• Custom Functions: Calendar management, email coordination, productivity research

🗓️ **FUNCTION USAGE PROTOCOL:**

**FOR PLANNING & PRODUCTIVITY:**
• Use planning_search() for productivity systems, time management strategies
• Research latest tools and methodologies for life optimization
• Find executive-level planning and strategy frameworks

**FOR CALENDAR MANAGEMENT:**
• Use get_today_schedule() for daily executive briefings
• Use get_upcoming_events() for strategic planning periods
• Use find_free_time() for optimal scheduling and time blocking

**FOR EMAIL COORDINATION:**
• Use search_emails() for executive communications review
• Manage stakeholder correspondence and follow-ups
• Coordinate scheduling and planning communications

📊 **DATA ANALYSIS WITH CODE INTERPRETER:**
• Productivity metrics tracking and analysis
• Time allocation optimization studies
• Goal progression and milestone tracking
• Life OS dashboard creation and maintenance

📋 **DOCUMENT MANAGEMENT WITH FILE SEARCH:**
• Access planning templates and frameworks
• Reference productivity methodologies and systems
• Analyze previous planning cycles and reviews
• Life OS documentation and process guides

💼 **EXECUTIVE STYLE:**
• Strategic thinking with systems-level optimization
• Executive-level insights for decision making
• Process improvement and efficiency focus
• Life integration and holistic planning approach

🎯 **RESPONSE FRAMEWORK:**
1. **Strategic Context**: Connect tasks to bigger picture goals
2. **System Optimization**: Look for process improvements
3. **Data-Driven Decisions**: Use metrics and analysis when relevant
4. **Executive Efficiency**: Maximum impact with minimum effort
5. **Life Integration**: Balance all life areas in planning

✅ **ALWAYS PROVIDE:**
• Strategic context for planning decisions
• Actionable next steps with clear timelines
• System-level thinking about productivity optimization
• Executive-level insights for better life management
• Integration across personal and professional planning

Keep responses under 1200 characters for Discord. Focus on strategic planning with executive efficiency."""

def create_complete_rose():
    """Create Rose with all tools preserved - File Search + Code Interpreter + Functions"""
    try:
        print("👑 Creating Complete Rose Ashcombe - Executive Assistant with All Tools...")
        
        # BUILD COMPLETE TOOLS ARRAY - Preserves all toggles
        complete_tools = [
            {"type": "file_search"},        # Keeps File Search toggle ON
            {"type": "code_interpreter"}    # Keeps Code Interpreter toggle ON
        ]
        
        # Add all custom functions
        for func in rose_complete_functions:
            complete_tools.append({"type": "function", "function": func})
        
        # Create assistant with ALL tools
        assistant = client.beta.assistants.create(
            name="Rose Ashcombe - Executive Assistant (Complete)",
            instructions=rose_complete_instructions,
            tools=complete_tools,
            model="gpt-4o"
        )
        
        print("✅ **COMPLETE ROSE CREATED WITH ALL TOOLS!**")
        print(f"👤 Name: {assistant.name}")
        print(f"🆔 Assistant ID: {assistant.id}")
        print(f"🔧 Total Tools: {len(complete_tools)}")
        
        print(f"\n👑 **ROSE'S COMPLETE TOOLS:**")
        print(f"   ✅ File Search - Planning documents & templates access")
        print(f"   ✅ Code Interpreter - Productivity metrics & data analysis")
        print(f"   ✅ planning_search() - Productivity research")
        print(f"   ✅ get_today_schedule() - Daily executive planning")
        print(f"   ✅ get_upcoming_events() - Strategic timeline planning")
        print(f"   ✅ find_free_time() - Optimal scheduling")
        print(f"   ✅ search_emails() - Executive communications")
        
        print(f"\n📊 **ENHANCED CAPABILITIES:**")
        print(f"   ✅ Productivity metrics analysis (Code Interpreter)")
        print(f"   ✅ Life OS document management (File Search)")
        print(f"   ✅ Executive planning research (Web Search)")
        print(f"   ✅ Calendar integration and optimization")
        
        print(f"\n📝 **SAVE THIS ASSISTANT ID:**")
        print(f"   ROSE_ASSISTANT_ID={assistant.id}")
        print(f"   Add this to your Railway environment variables!")
        
        return assistant.id
        
    except Exception as e:
        print(f"❌ Error creating complete Rose: {e}")
        return None

def update_existing_rose(existing_id):
    """Update existing Rose with all tools preserved"""
    try:
        print(f"🔄 Updating existing Rose: {existing_id}")
        
        # BUILD COMPLETE TOOLS ARRAY
        complete_tools = [
            {"type": "file_search"},        # Preserves File Search
            {"type": "code_interpreter"}    # Preserves Code Interpreter
        ]
        
        # Add all custom functions
        for func in rose_complete_functions:
            complete_tools.append({"type": "function", "function": func})
        
        # Update with ALL tools preserved
        assistant = client.beta.assistants.update(
            assistant_id=existing_id,
            name="Rose Ashcombe - Executive Assistant (Fixed)",
            instructions=rose_complete_instructions,
            tools=complete_tools,
            model="gpt-4o"
        )
        
        print("✅ **ROSE UPDATED WITH ALL TOOLS PRESERVED!**")
        print(f"🔧 Tools count: {len(complete_tools)}")
        print(f"✅ File Search & Code Interpreter will stay ON")
        
        return assistant.id
        
    except Exception as e:
        print(f"❌ Error updating Rose: {e}")
        return None

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        exit(1)
    
    print("👑 ROSE COMPLETE SETUP")
    print("=" * 50)
    
    choice = input("Create new Rose (n) or update existing (u)? [n/u]: ").lower()
    
    if choice == 'u':
        existing_id = input("Enter existing Rose Assistant ID: ").strip()
        if existing_id:
            update_existing_rose(existing_id)
        else:
            print("❌ No Assistant ID provided")
    else:
        create_complete_rose()
