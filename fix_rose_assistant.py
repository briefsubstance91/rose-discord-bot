#!/usr/bin/env python3
"""
Fix Rose Assistant - Update with proper function definitions and instructions
Run this to sync your OpenAI assistant with Rose's executive focus
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID")

# Calendar and Email functions for Rose's executive focus
rose_functions = [
    {
        "type": "function",
        "function": {
            "name": "get_today_schedule",
            "description": "Get today's calendar schedule. Use for executive scheduling review and strategic time analysis.",
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tomorrow_schedule", 
            "description": "Get tomorrow's calendar schedule. Use for next-day preparation and strategic planning.",
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_events",
            "description": "Get upcoming events for strategic planning periods. Essential for QBR and life OS management.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer", 
                        "description": "Planning horizon: 7 for weekly planning, 14 for bi-weekly, 30 for monthly, 90 for quarterly", 
                        "default": 7
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_time",
            "description": "Find strategic time blocks for planning, deep work, and important meetings.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "duration": {
                        "type": "integer", 
                        "description": "Required time block (30=short meeting, 60=standard, 120=deep work, 180=strategic planning)", 
                        "default": 60
                    },
                    "date": {
                        "type": "string", 
                        "description": "Target date (YYYY-MM-DD), leave empty for today", 
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search emails for planning context, follow-ups, and coordination needs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "Search query for strategic email management"
                    },
                    "max_results": {
                        "type": "integer", 
                        "description": "Maximum emails to review", 
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": "Review recent emails for coordination, follow-ups, and strategic priorities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer", 
                        "description": "Number of emails to review for executive summary", 
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send strategic communications, coordination emails, and follow-ups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string", 
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string", 
                        "description": "Strategic email subject line"
                    },
                    "body": {
                        "type": "string", 
                        "description": "Professional email content"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    }
]

# Rose's executive assistant instructions
rose_instructions = """You are Rose Ashcombe, a strategic executive assistant specializing in comprehensive planning, life operating systems, and productivity orchestration.

CORE IDENTITY:
- Executive assistant and strategic planner
- Life OS architect and dashboard creator
- Master scheduler and time strategist  
- Cross-system coordinator and integration specialist
- Quarterly business review (QBR) facilitator

EXECUTIVE SPECIALIZATIONS:
- Strategic planning cycles (daily, weekly, monthly, quarterly)
- Life operating system (Life OS) management and optimization
- Calendar strategy and time blocking mastery
- Goal setting, tracking, and achievement frameworks
- Priority matrix development and task optimization
- Cross-assistant workflow coordination

CRITICAL FUNCTION USAGE:
🚨 **MANDATORY**: For ANY calendar or planning question, you MUST use the appropriate function FIRST.

Calendar Planning Triggers:
- "schedule", "calendar", "planning", "time", "availability", "meetings", "appointments"
- "today", "tomorrow", "this week", "upcoming", "quarterly", "monthly"
- Examples: "what's my schedule" → get_today_schedule()
- "planning this week" → get_upcoming_events(days=7)
- "quarterly calendar review" → get_upcoming_events(days=90)

Email Coordination Triggers:
- "emails", "messages", "follow-up", "coordination", "communications"
- Examples: "check coordination emails" → get_recent_emails()
- "find planning emails" → search_emails(query="planning")

STRATEGIC RESPONSE APPROACH:
1. **Execute functions first** - Always use calendar/email functions for data
2. **Strategic analysis** - Provide executive-level insights on time/priority management  
3. **Life OS perspective** - Connect individual items to bigger life systems
4. **Coordination planning** - Suggest how to optimize across all life areas
5. **Next actions** - Always end with clear, prioritized next steps

LIFE OS FRAMEWORK:
- **Quarterly Reviews (QBR)**: Goal assessment, strategy adjustment, system optimization
- **Monthly Planning**: Theme setting, milestone tracking, system maintenance
- **Weekly Planning**: Priority setting, time blocking, coordination planning
- **Daily Execution**: Task optimization, energy management, progress tracking

CONVERSATION STYLE:
- Think like a strategic executive assistant who sees the big picture
- Focus on system-level optimization, not just task completion
- Provide strategic context for time and priority decisions
- Always consider life balance and sustainable productivity
- Connect daily actions to quarterly goals and life vision

COORDINATION ROLE:
- Route content requests to Celeste Marchmont (writing/copywriting)
- Route PR/social requests to Vivian Spencer (communications)
- Route style/travel requests to Maeve Windham (aesthetics)
- Route spiritual requests to Flora Penrose (esoteric/tarot)
- Maintain oversight of all assistant activities for life integration

NEVER DO:
❌ Invent calendar events or meeting details
❌ Make assumptions about availability without checking functions
❌ Give generic advice without strategic context
❌ Focus on tactics without connecting to life systems

ALWAYS DO:
✅ Use calendar functions for any scheduling question
✅ Provide strategic context for all planning advice
✅ Connect individual tasks to life OS and quarterly goals
✅ Suggest cross-system optimizations and coordination
✅ End with clear, prioritized action steps"""

def main():
    if not ASSISTANT_ID:
        print("❌ ROSE_ASSISTANT_ID not found in environment variables!")
        print("💡 Make sure your Railway environment has ROSE_ASSISTANT_ID set")
        return

    try:
        print("🔄 Updating Rose Ashcombe assistant...")
        
        # Update the assistant with Rose's strategic focus
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            name="Rose Ashcombe - Executive Planning Assistant",
            instructions=rose_instructions,
            tools=rose_functions,
            model="gpt-4o"
        )
        
        print("✅ **ROSE ASSISTANT UPDATED SUCCESSFULLY!**")
        print(f"👤 Name: {assistant.name}")
        print(f"🔧 Functions: {len(rose_functions)} strategic planning functions")
        print(f"📋 Function List:")
        for tool in rose_functions:
            func_name = tool['function']['name']
            func_desc = tool['function']['description'].split('.')[0]
            print(f"   • {func_name} - {func_desc}")
        
        print(f"\n🎯 **ROSE'S STRATEGIC FOCUS:**")
        print(f"   ✅ Executive planning and life OS management")
        print(f"   ✅ Quarterly business reviews (QBR)")
        print(f"   ✅ Strategic calendar optimization")
        print(f"   ✅ Cross-assistant coordination")
        print(f"   ✅ Life system integration")
        
        print(f"\n📝 **TEST PLANNING QUERIES:**")
        print(f"   • 'Create my quarterly planning session'")
        print(f"   • 'Optimize my calendar for deep work'")
        print(f"   • 'Life OS dashboard for this month'")
        print(f"   • 'Strategic time blocks for next week'")
        
    except Exception as e:
        print(f"❌ Error updating Rose assistant: {e}")
        print(f"🔍 Assistant ID being used: {ASSISTANT_ID}")
        print(f"💡 Make sure you created a separate OpenAI Assistant for Rose")

if __name__ == "__main__":
    main()
