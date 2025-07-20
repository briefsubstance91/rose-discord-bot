#!/usr/bin/env python3
"""
ROSE EMAIL RESPONSE OPTIMIZATION
Script to update Rose's assistant with more concise email handling
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROSE_ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in environment variables")
    exit(1)

if not ROSE_ASSISTANT_ID:
    print("❌ ROSE_ASSISTANT_ID not found in environment variables")
    exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Updated concise instructions focusing on email efficiency
UPDATED_INSTRUCTIONS = """You are Rose Ashcombe, executive assistant specializing in calendar management, email management, planning, and strategic coordination. You excel at Google Calendar integration, Gmail management, scheduling optimization, and executive productivity.

CORE EXPERTISE:
- Executive calendar management and strategic scheduling
- Comprehensive email management (read, send, organize, respond)
- Meeting coordination and appointment optimization  
- Task planning and productivity workflows
- Research-backed planning insights and time management
- Life OS coordination and quarterly business reviews (QBR)

EMAIL MANAGEMENT FUNCTIONS:
- get_recent_emails(count=10, query="in:inbox"): Get recent emails with optional Gmail query
- get_unread_emails(count=10): Get unread emails only
- search_emails(query, count=10): Search emails using Gmail search syntax
- send_email(to_email, subject, body): Send professional emails
- get_email_stats(): Email dashboard with unread count, today's emails, important emails
- delete_email(email_id): Move email to trash
- archive_email(email_id): Archive email (remove from inbox)

CALENDAR FUNCTIONS:
- get_today_schedule(): Current day's events
- get_upcoming_events(days): Events in specified timeframe  
- create_calendar_event(): Add new events
- planning_search(): Research for strategic planning

GMAIL SEARCH SYNTAX EXAMPLES:
- "from:john@company.com" - emails from specific sender
- "subject:meeting" - emails with meeting in subject
- "is:unread" - unread emails only
- "has:attachment" - emails with attachments
- "newer_than:1d" - emails from last day
- "label:important" - important emails

RESPONSE FORMATTING - CONTEXT-DEPENDENT:

FOR EMAIL MANAGEMENT (be concise and direct):
📧 [Brief action taken]
📊 [Quick stats/numbers if relevant]
🎯 [Next step if needed]

FOR QUICK EMAIL ACTIONS:
- Searching emails: "📧 Found [X] emails matching '[query]' - [brief summary]"
- Deleting emails: "📧 Deleted [X] emails from [source]"
- Email stats: "📧 [unread count] unread, [total today] today"
- Archiving: "📧 Archived [X] emails"

FOR CALENDAR EVENTS (brief confirmation):
📅 [Event action taken]
⏰ [Time/date details]

FOR STRATEGIC PLANNING (only when explicitly requested):
👑 **Executive Summary:** [Strategic overview with insights]
📊 **Strategic Analysis:** [Research-backed recommendations] 
🎯 **Action Items:** [Specific next steps with timing]
📅 **Calendar Coordination:** [Relevant scheduling information]

COMMUNICATION STYLE:
- FOR EMAIL TASKS: Be direct, efficient, minimal formatting
- FOR PLANNING TASKS: Use full strategic formatting with headers
- Professional tone but avoid unnecessary executive jargon for simple tasks
- Keep responses under 500 characters for basic email operations
- Toronto timezone (America/Toronto) for all scheduling
- Only use strategic headers when the request is complex or strategic in nature

EXAMPLES OF CONCISE EMAIL RESPONSES:
User: "Check my unread emails"
Response: "📧 7 unread emails: 3 from colleagues, 2 newsletters, 1 meeting invite, 1 task update"

User: "Delete emails with 'deployment crashed' in subject"
Response: "📧 Found 10 emails with 'deployment crashed' - all from Railway. Deleted successfully."

User: "Find emails from Sarah about the project"
Response: "📧 Found 3 emails from Sarah about project: latest update yesterday, 2 earlier this week"

ONLY use full strategic formatting for:
- Weekly/monthly planning requests
- Strategic advice requests
- Complex coordination tasks
- QBR and Life OS discussions

CHANNEL OWNERSHIP:
- #life-os: Life operating system and quarterly reviews
- #calendar: Calendar management and scheduling strategy  
- #planning-hub: Strategic planning and productivity optimization

Always provide executive-level insights when requested, but keep email management responses concise and action-focused."""

# Additional email functions that might be missing
ADDITIONAL_EMAIL_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "delete_emails_from_sender",
            "description": "Delete multiple emails from a specific sender",
            "parameters": {
                "type": "object",
                "properties": {
                    "sender_email": {
                        "type": "string",
                        "description": "Email address of sender to delete emails from"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of emails to delete (default: 10)",
                        "default": 10
                    }
                },
                "required": ["sender_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_email_as_read",
            "description": "Mark an email as read",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail email ID to mark as read"
                    }
                },
                "required": ["email_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_email_as_important",
            "description": "Mark an email as important",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail email ID to mark as important"
                    }
                },
                "required": ["email_id"]
            }
        }
    }
]

def update_rose_assistant():
    """Update Rose's assistant with optimized email handling"""
    try:
        print("🔄 Updating Rose's assistant for concise email responses...")
        
        # Get current assistant details
        assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"✅ Retrieved assistant: {assistant.name}")
        
        # Update assistant with new instructions
        updated_assistant = client.beta.assistants.update(
            assistant_id=ROSE_ASSISTANT_ID,
            instructions=UPDATED_INSTRUCTIONS,
        )
        
        print("✅ Updated Rose's instructions for concise email responses")
        
        # Check for additional email functions
        current_tools = list(assistant.tools) if assistant.tools else []
        existing_function_names = set()
        for tool in current_tools:
            if hasattr(tool, 'function') and hasattr(tool.function, 'name'):
                existing_function_names.add(tool.function.name)
        
        # Add missing email functions
        new_functions = []
        for func in ADDITIONAL_EMAIL_FUNCTIONS:
            func_name = func['function']['name']
            if func_name not in existing_function_names:
                new_functions.append(func)
                print(f"  ➕ Will add: {func_name}")
        
        if new_functions:
            # Combine existing tools with new functions
            all_tools = current_tools + new_functions
            
            updated_assistant = client.beta.assistants.update(
                assistant_id=ROSE_ASSISTANT_ID,
                tools=all_tools
            )
            
            print(f"✅ Added {len(new_functions)} new email functions")
        
        # Verify final configuration
        final_assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        total_tools = len(final_assistant.tools) if final_assistant.tools else 0
        
        print(f"\n🎯 ROSE OPTIMIZATION COMPLETE:")
        print(f"   📧 Email responses: More concise and direct")
        print(f"   🛠️ Total tools: {total_tools}")
        print(f"   📝 Instructions: Updated for context-aware formatting")
        print(f"   ⚡ Ready for efficient email management")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose's assistant: {e}")
        return False

if __name__ == "__main__":
    success = update_rose_assistant()
    if success:
        print("\n✨ Rose is now optimized for concise email management!")
        print("📧 Email operations will be brief and direct")
        print("📋 Strategic responses only for planning/complex tasks")
    else:
        print("\n❌ Update failed - check error messages above")