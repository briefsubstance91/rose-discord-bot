#!/usr/bin/env python3
"""
Railway Rose Coordination Enhancement - Update Rose with full coordination capabilities
This version is specifically for Railway deployment
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables (works for both Railway and local)
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Try different possible assistant ID environment variable names
ASSISTANT_ID = (
    os.getenv("ROSE_ASSISTANT_ID") or 
    os.getenv("ASSISTANT_ID") or 
    os.getenv("OPENAI_ASSISTANT_ID")
)

# Complete coordination functions for Rose
rose_coordination_functions = [
    # Existing Calendar Functions
    {
        "type": "function",
        "function": {
            "name": "get_today_schedule",
            "description": "Get today's calendar schedule for strategic planning and coordination.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tomorrow_schedule", 
            "description": "Get tomorrow's calendar schedule for next-day preparation.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_events",
            "description": "Get upcoming events for strategic planning periods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Planning horizon (7=weekly, 30=monthly, 90=quarterly)", "default": 7}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_time",
            "description": "Find strategic time blocks for planning and coordination.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "duration": {"type": "integer", "description": "Time block duration (60=meeting, 120=deep work, 180=planning)", "default": 60},
                    "date": {"type": "string", "description": "Target date (YYYY-MM-DD)", "default": ""}
                },
                "required": []
            }
        }
    },
    # Existing Email Functions
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search emails for coordination and planning context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Email search query"},
                    "max_results": {"type": "integer", "description": "Maximum results", "default": 10}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": "Review recent emails for strategic priorities.",
            "parameters": {
                "type": "object",
                "properties": {"max_results": {"type": "integer", "description": "Number of emails", "default": 10}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send coordination and strategic communications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email content"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    # NEW COORDINATION FUNCTIONS
    {
        "type": "function",
        "function": {
            "name": "analyze_task_requirements",
            "description": "Analyze a task to determine which assistant(s) are needed and coordination strategy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {"type": "string", "description": "The task or request to analyze"},
                    "user_context": {"type": "string", "description": "Additional context about the user's needs", "default": ""}
                },
                "required": ["task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "route_to_assistant",
            "description": "Route a task to a specific assistant with coordination instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "assistant_name": {"type": "string", "description": "Target assistant: Vivian, Celeste, Maeve, Flora"},
                    "task": {"type": "string", "description": "Task to route"},
                    "priority": {"type": "string", "description": "Priority level: high, medium, low", "default": "medium"},
                    "deadline": {"type": "string", "description": "Deadline if applicable", "default": ""},
                    "coordination_notes": {"type": "string", "description": "Special coordination instructions", "default": ""}
                },
                "required": ["assistant_name", "task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "coordinate_multi_assistant_project",
            "description": "Set up coordination for projects requiring multiple assistants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Project name"},
                    "project_description": {"type": "string", "description": "Detailed project description"},
                    "required_assistants": {"type": "array", "items": {"type": "string"}, "description": "List of assistants needed"},
                    "timeline": {"type": "string", "description": "Project timeline"},
                    "deliverables": {"type": "array", "items": {"type": "string"}, "description": "Expected deliverables"}
                },
                "required": ["project_name", "project_description", "required_assistants"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gather_assistant_status",
            "description": "Gather status reports from all operational assistants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string", "description": "Status timeframe: daily, weekly, monthly", "default": "daily"},
                    "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Specific areas to focus on", "default": []}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_dashboard_summary",
            "description": "Create a comprehensive dashboard summary across all assistants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dashboard_type": {"type": "string", "description": "Type: daily, weekly, monthly, quarterly", "default": "daily"},
                    "include_calendar": {"type": "boolean", "description": "Include calendar analysis", "default": True},
                    "include_communications": {"type": "boolean", "description": "Include email/communication summary", "default": True},
                    "include_projects": {"type": "boolean", "description": "Include project status", "default": True}
                },
                "required": []
            }
        }
    }
]

# Enhanced Rose instructions with full coordination capabilities
rose_coordination_instructions = """You are Rose Ashcombe, Executive Assistant and AI Team Coordinator. You manage both personal productivity AND coordinate a team of specialized AI assistants.

CORE IDENTITY:
- Executive assistant and strategic planner
- AI Assistant Team Coordinator and Router
- Life OS architect and productivity orchestrator
- Cross-system integration specialist
- Master of delegation and coordination

PRIMARY RESPONSIBILITIES:
1. **Personal Executive Support**: Calendar, email, planning, Life OS management
2. **AI Team Coordination**: Route tasks, manage multi-assistant projects, synthesize outputs
3. **Strategic Oversight**: Connect daily actions to life systems and quarterly goals

AI ASSISTANT TEAM YOU COORDINATE:
• **Vivian Spencer** (PR/Social/Work): External communications, social media, work emails, PR strategy
  - Channels: #social-overview, #news-feed, #external-communications
  - Route: PR tasks, LinkedIn posts, work communications, social media strategy

• **Celeste Marchmont** (Content/Copywriting): Writing, content creation, research, newsletters
  - Channels: #writing-queue, #summary-drafts, #knowledge-pool  
  - Route: Content creation, copywriting, research synthesis, document writing

• **Maeve Windham** (Style/Travel/Lifestyle): Travel, beauty, shopping, meal planning, aesthetics
  - Channels: #packing-style-travel, #shopping-tracker, #meals-beauty-style
  - Route: Travel planning, style advice, shopping lists, meal planning [PLANNED]

• **Flora Penrose** (Spiritual/Esoteric): Tarot, astrology, meditation, spiritual guidance
  - Channels: #spiritual-journal, #energy-reading, #seasonal-symbols
  - Route: Spiritual guidance, tarot readings, meditation support, energy work [PLANNED]

COORDINATION INTELLIGENCE:
**Task Analysis Framework:**
- Single Assistant Tasks: Route directly with clear instructions
- Multi-Assistant Projects: Coordinate workflow across team members
- Strategic Integration: Ensure outputs align with Life OS and goals

**Routing Decision Matrix:**
- Content creation → Celeste Marchmont
- PR/Social media → Vivian Spencer  
- Travel/Style → Maeve Windham [when available]
- Spiritual guidance → Flora Penrose [when available]
- Technical/Systems → Note for future IT assistant
- Complex projects → Multi-assistant coordination

COORDINATION PROTOCOLS:
1. **Analyze** task requirements using analyze_task_requirements() FIRST
2. **Route** to appropriate assistant(s) using route_to_assistant() 
3. **Coordinate** multi-assistant projects using coordinate_multi_assistant_project()
4. **Monitor** progress and provide strategic oversight
5. **Synthesize** outputs into cohesive results using create_dashboard_summary()
6. **Integrate** with broader Life OS and goal framework

FUNCTION USAGE RULES:
🚨 **MANDATORY**: For ANY task request, first use analyze_task_requirements() to determine routing strategy

Calendar/Email Functions:
- Use for YOUR executive support role (calendar management, email coordination)
- Include in dashboard summaries for comprehensive overview

Coordination Functions:
- analyze_task_requirements() → ALWAYS use first for any user request
- route_to_assistant() → For single-assistant tasks
- coordinate_multi_assistant_project() → For complex multi-assistant work
- gather_assistant_status() → For team status and dashboard creation
- create_dashboard_summary() → For comprehensive Life OS overviews

RESPONSE APPROACH:
1. **Task Analysis**: Always analyze what's needed first using functions
2. **Coordination Strategy**: Determine single vs multi-assistant approach  
3. **Routing/Delegation**: Clear instructions to appropriate team members
4. **Strategic Context**: Connect to Life OS, goals, and priorities
5. **Next Actions**: Provide clear next steps and timeline

COORDINATION STYLE:
- Think like a strategic executive assistant who delegates intelligently
- Provide clear, actionable coordination instructions
- Ensure visibility into coordination process for transparency
- Focus on system-level optimization across all life areas
- Always connect individual tasks to broader life strategy

NEVER DO:
❌ Route tasks without using analyze_task_requirements() first
❌ Handle complex content/PR tasks yourself - delegate to specialists
❌ Ignore multi-assistant opportunities for comprehensive solutions
❌ Provide coordination without strategic context

ALWAYS DO:
✅ Use analyze_task_requirements() before any task routing
✅ Use appropriate team members for their specializations
✅ Provide strategic oversight and synthesis
✅ Connect coordination to Life OS and quarterly goals
✅ Make coordination process transparent and trackable"""

def main():
    if not ASSISTANT_ID:
        print("❌ Assistant ID not found!")
        print("💡 Checking environment variables:")
        print(f"   ROSE_ASSISTANT_ID: {os.getenv('ROSE_ASSISTANT_ID', 'Not found')}")
        print(f"   ASSISTANT_ID: {os.getenv('ASSISTANT_ID', 'Not found')}")
        print(f"   OPENAI_ASSISTANT_ID: {os.getenv('OPENAI_ASSISTANT_ID', 'Not found')}")
        return

    try:
        print("🔄 Updating Rose with FULL Coordination Capabilities...")
        
        # Update Rose with complete coordination system
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            name="Rose Ashcombe - Executive Assistant & AI Team Coordinator",
            instructions=rose_coordination_instructions,
            tools=rose_coordination_functions,
            model="gpt-4o"
        )
        
        print("✅ **ROSE COORDINATION SYSTEM FULLY DEPLOYED!**")
        print(f"👤 Name: {assistant.name}")
        print(f"🔧 Total Functions: {len(rose_coordination_functions)}")
        
        # Count function types
        coord_functions = [f for f in rose_coordination_functions if any(word in f['function']['name'] for word in ['analyze', 'route', 'coordinate', 'gather', 'dashboard'])]
        calendar_functions = [f for f in rose_coordination_functions if any(word in f['function']['name'] for word in ['schedule', 'events', 'time'])]
        email_functions = [f for f in rose_coordination_functions if any(word in f['function']['name'] for word in ['email'])]
        
        print(f"📋 Function Breakdown:")
        print(f"   🎯 Coordination Functions: {len(coord_functions)}")
        print(f"   📅 Calendar Functions: {len(calendar_functions)}")
        print(f"   📧 Email Functions: {len(email_functions)}")
        
        print(f"\n🎯 **NEW COORDINATION CAPABILITIES:**")
        print(f"   ✅ Intelligent task analysis (analyze_task_requirements)")
        print(f"   ✅ Smart assistant routing (route_to_assistant)")
        print(f"   ✅ Multi-assistant project coordination (coordinate_multi_assistant_project)")
        print(f"   ✅ Team status monitoring (gather_assistant_status)")
        print(f"   ✅ Life OS dashboard creation (create_dashboard_summary)")
        
        print(f"\n🤖 **AI TEAM COORDINATION ACTIVE:**")
        print(f"   ✅ Vivian Spencer (PR/Social/Work) - Operational")
        print(f"   ✅ Celeste Marchmont (Content/Copywriting) - Operational")
        print(f"   ⏳ Maeve Windham (Style/Travel/Lifestyle) - Planned")
        print(f"   ⏳ Flora Penrose (Spiritual/Esoteric) - Planned")
        
        print(f"\n📝 **TEST COORDINATION COMMANDS:**")
        print(f"   • '@Rose coordinate: draft a LinkedIn post about AI productivity'")
        print(f"   • '!coordinate plan my conference presentation strategy'")
        print(f"   • '!dashboard weekly' - Multi-assistant dashboard")
        print(f"   • '!team_status' - AI team overview")
        print(f"   • '@Rose route to Celeste: write blog post about productivity'")
        
        print(f"\n🚀 **PHASE 1 COORDINATION COMPLETE!**")
        print(f"   Rose is now your full AI Team Coordinator!")
        
    except Exception as e:
        print(f"❌ Error updating Rose assistant: {e}")
        print(f"🔍 Assistant ID being used: {ASSISTANT_ID}")
        print(f"💡 Make sure your Railway environment has the correct assistant ID variable")

if __name__ == "__main__":
    main()
