#!/usr/bin/env python3
"""
ROSE DIRECT WORK CALENDAR INTEGRATION
Rose accesses work calendar directly from Gmail account
Eliminates need for Vivian intermediary - cleaner architecture
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get Rose's assistant ID
ROSE_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")

# Rose's enhanced functions with direct work calendar access
rose_direct_work_functions = [
    # Enhanced morning briefing with direct work calendar
    {
        "type": "function",
        "function": {
            "name": "get_comprehensive_morning_briefing",
            "description": "Get complete executive morning briefing with weather, direct work calendar access, and personal calendar integration",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_work_calendar": {"type": "boolean", "description": "Include work calendar from Gmail", "default": True},
                    "include_personal_calendar": {"type": "boolean", "description": "Include personal calendars", "default": True},
                    "include_weather": {"type": "boolean", "description": "Include weather briefing", "default": True}
                },
                "required": []
            }
        }
    },
    # Direct work calendar access
    {
        "type": "function",
        "function": {
            "name": "get_work_calendar_direct",
            "description": "Get work calendar events directly from Gmail calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days to look ahead (1-30)", "default": 1},
                    "calendar_type": {"type": "string", "description": "Type: today, upcoming, week, month", "default": "today"}
                },
                "required": []
            }
        }
    },
    # Work calendar analysis
    {
        "type": "function",
        "function": {
            "name": "analyze_work_schedule",
            "description": "Analyze work calendar for priorities, conflicts, and strategic insights",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {"type": "string", "description": "Analysis focus: priorities, conflicts, prep, travel", "default": "priorities"},
                    "timeframe": {"type": "string", "description": "Timeframe: today, tomorrow, week", "default": "today"}
                },
                "required": []
            }
        }
    },
    # Cross-calendar coordination
    {
        "type": "function",
        "function": {
            "name": "coordinate_work_personal_calendars",
            "description": "Coordinate between work and personal calendars for optimal scheduling",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Days to analyze (1-14)", "default": 7},
                    "focus": {"type": "string", "description": "Focus: conflicts, gaps, optimization", "default": "optimization"}
                },
                "required": []
            }
        }
    },
    # Work meeting preparation
    {
        "type": "function",
        "function": {
            "name": "get_meeting_prep_summary",
            "description": "Get summary of meetings requiring preparation and follow-up",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string", "description": "Timeframe: today, tomorrow, week", "default": "today"},
                    "preparation_level": {"type": "string", "description": "Level: all, high-priority, critical", "default": "all"}
                },
                "required": []
            }
        }
    },
    # Calendar integration status check
    {
        "type": "function",
        "function": {
            "name": "get_calendar_integration_status",
            "description": "Check status of all calendar integrations and connections",
            "parameters": {
                "type": "object",
                "properties": {
                    "detailed_check": {"type": "boolean", "description": "Include detailed diagnostic information", "default": True}
                },
                "required": []
            }
        }
    }
]

# Rose's enhanced instructions with direct work calendar access
rose_direct_work_instructions = """You are Rose Ashcombe, Executive Assistant with DIRECT work calendar access. You are the strategic coordinator who puts it all together for comprehensive life management.

**CORE ROLE:**
- Executive Assistant and Life OS Manager
- Planning, scheduling, calendar management & strategy  
- Time management and strategic coordination
- Direct work calendar access (no dependency on other assistants)
- Cross-calendar optimization and conflict resolution

**DIRECT WORK CALENDAR CAPABILITIES:**
- You have DIRECT access to the work Gmail calendar
- You can retrieve work meetings, analyze priorities, and coordinate scheduling
- You provide comprehensive briefings combining weather, work calendar, and personal schedules
- You identify meeting preparation needs and scheduling optimization opportunities
- You coordinate between work and personal calendars for optimal life management

**PRIMARY FUNCTIONS:**
1. **Comprehensive Morning Briefings**: Weather + Direct Work Calendar + Personal Calendar + Strategic Insights
2. **Direct Work Calendar Access**: Real-time work meeting data without intermediary
3. **Cross-Calendar Coordination**: Optimize work and personal scheduling
4. **Meeting Preparation Intelligence**: Identify prep needs and timeline management
5. **Strategic Calendar Analysis**: Priorities, conflicts, optimization opportunities
6. **Calendar Health Monitoring**: Check all integration status and connectivity

**COMMUNICATION STYLE:**
- Professional yet warm, like a trusted executive assistant
- Proactive with strategic recommendations
- Clear, actionable insights with context
- Strategic thinking with practical execution
- Always focused on optimization and efficiency

**ENHANCED BRIEFING FORMAT:**
👑 **Comprehensive Executive Briefing for [Date]**

🌤️ **Weather Update (Toronto)**: [Temperature] [Condition]
🌡️ Feels like: [Temp] | Humidity: [%]
🔆 UV Index: [Level] - [Protection recommendations]

💼 **Work Calendar (Direct Access)**: [X] work meetings
[List work meetings with times and types]

📊 **Work Priorities Analysis**:
- Meeting breakdown by type (client, internal, presentations, etc.)
- Preparation requirements identified
- Travel/logistics considerations
- Strategic recommendations

📅 **Personal Schedule**: [X] personal events
[Personal calendar summary]

🤝 **Cross-Calendar Coordination**:
- Conflict analysis
- Optimization opportunities
- Strategic scheduling recommendations

📋 **Meeting Prep Summary**:
- High priority preparation needed
- Timeline recommendations
- Resource requirements

You understand the executive need for strategic time management, meeting preparation, and work-life balance optimization. Always provide actionable insights that help optimize productivity and reduce scheduling stress.

**WORK CALENDAR INTELLIGENCE:**
- Detect meeting patterns and scheduling optimization opportunities
- Identify preparation requirements and timeline management
- Flag travel logistics and scheduling considerations
- Coordinate work priorities with personal commitments
- Provide strategic recommendations for calendar optimization

Remember: You have DIRECT access to the work calendar, eliminating dependencies on other assistants while maintaining strategic coordination capabilities across all scheduling needs."""

def update_rose_with_direct_work_calendar():
    """Update Rose's assistant with direct work calendar access"""
    if not ROSE_ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found!")
        print("💡 Check these environment variables:")
        for key in ['ROSE_ASSISTANT_ID', 'ASSISTANT_ID']:
            print(f"   {key}: {os.getenv(key, 'Not found')}")
        return

    try:
        print("👑 UPDATING ROSE WITH DIRECT WORK CALENDAR ACCESS...")
        
        # Update Rose with direct work calendar functions
        assistant = client.beta.assistants.update(
            assistant_id=ROSE_ASSISTANT_ID,
            name="Rose Ashcombe - Executive Assistant (Direct Work Calendar)",
            instructions=rose_direct_work_instructions,
            tools=[
                {"type": "file_search"},        # Preserve file search
                {"type": "code_interpreter"}    # Preserve code interpreter
            ] + [{"type": "function", "function": func["function"]} for func in rose_direct_work_functions],
            model="gpt-4o"
        )
        
        print("✅ **ROSE DIRECT WORK CALENDAR INTEGRATION COMPLETE!**")
        print(f"👤 Assistant: {assistant.name}")
        print(f"🔧 Total Tools: {len(assistant.tools)}")
        
        print(f"\n💼 **NEW DIRECT WORK CALENDAR CAPABILITIES:**")
        print(f"   ✅ Direct Gmail work calendar access (no Vivian dependency)")
        print(f"   ✅ Real-time work meeting analysis and categorization")
        print(f"   ✅ Cross-calendar coordination (work + personal)")
        print(f"   ✅ Meeting preparation intelligence and timeline management")
        print(f"   ✅ Strategic scheduling optimization and conflict resolution")
        
        print(f"\n🔧 **ENHANCED FUNCTIONS:**")
        print(f"   🆕 get_comprehensive_morning_briefing() - Complete briefing with direct work access")
        print(f"   🆕 get_work_calendar_direct() - Direct Gmail work calendar access")
        print(f"   🆕 analyze_work_schedule() - Strategic work calendar analysis")
        print(f"   🆕 coordinate_work_personal_calendars() - Cross-calendar optimization")
        print(f"   🆕 get_meeting_prep_summary() - Meeting preparation planning")
        print(f"   🆕 get_calendar_integration_status() - All calendar health check")
        
        print(f"\n🧪 **TEST THE DIRECT INTEGRATION:**")
        print(f"   • '@Rose give me my comprehensive morning briefing'")
        print(f"   • '@Rose analyze my work schedule for today'")
        print(f"   • '@Rose coordinate my work and personal calendars'")
        print(f"   • '@Rose what meetings need prep today?'")
        print(f"   • '!briefing' - Command will now include direct work calendar")
        
        print(f"\n📝 **NEXT STEPS:**")
        print(f"   1. Update Rose's main.py with direct work calendar functions")
        print(f"   2. Ensure Gmail calendar access is configured in Google Cloud")
        print(f"   3. Deploy updated Rose to Railway")
        print(f"   4. Test direct work calendar integration")
        
        print(f"\n💡 **ARCHITECTURE IMPROVEMENT:**")
        print(f"   ✅ Eliminated Vivian dependency for work calendar")
        print(f"   ✅ Rose now has complete calendar autonomy")
        print(f"   ✅ Real-time work calendar access without intermediary")
        print(f"   ✅ Simplified integration with better performance")
        
        print(f"\n👑 **ROSE IS NOW WORK CALENDAR AUTONOMOUS!**")
        
        return assistant.id
        
    except Exception as e:
        print(f"❌ Error updating Rose with direct work calendar: {e}")
        print(f"🔍 Assistant ID: {ROSE_ASSISTANT_ID}")
        return None

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
    else:
        update_rose_with_direct_work_calendar()