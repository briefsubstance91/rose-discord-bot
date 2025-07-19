#!/usr/bin/env python3
"""
ROSE ASSISTANT EMAIL FUNCTIONS UPDATE
Script to add email capabilities to Rose's OpenAI Assistant
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

# Updated instructions with email capabilities
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

EMAIL RESPONSE FORMATTING:
For email management tasks:
👑 **Executive Summary:** [Brief overview of email action]
📧 **Email Management:** [Email details, actions taken]
🎯 **Next Steps:** [Recommended follow-up actions]

CALENDAR RESPONSE FORMATTING:
For calendar events (creation, updates, scheduling):
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

EXECUTIVE INTEGRATION:
- For briefings, include both calendar and email statistics
- Coordinate email responses with calendar availability
- Suggest email scheduling based on calendar gaps
- Provide strategic insights for email and time management

CHANNEL OWNERSHIP:
- #life-os: Life operating system and quarterly reviews
- #calendar: Calendar management and scheduling strategy  
- #planning-hub: Strategic planning and productivity optimization

EMAIL MANAGEMENT EXAMPLES:
- "Check my unread emails" → use get_unread_emails()
- "Find emails from Sarah about the project" → use search_emails("from:sarah project")
- "Send email to team@company.com about meeting" → use send_email()
- "Archive old newsletters" → use search_emails() then archive_email()
- "Show me today's important emails" → use search_emails("is:important newer_than:1d")

Always provide executive-level insights with practical coordination between email and calendar management."""

# New email functions to add to the assistant
EMAIL_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails",
            "description": "Get recent emails from inbox with optional filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of emails to retrieve (default: 10)",
                        "default": 10
                    },
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (default: 'in:inbox'). Examples: 'is:unread', 'from:john@company.com', 'subject:meeting'",
                        "default": "in:inbox"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_unread_emails",
            "description": "Get unread emails from inbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of unread emails to retrieve (default: 10)",
                        "default": 10
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search emails using Gmail search syntax",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query. Examples: 'from:john@company.com', 'subject:meeting', 'has:attachment', 'is:important', 'newer_than:1d'"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of emails to retrieve (default: 10)",
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
            "name": "send_email",
            "description": "Send an email through Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content"
                    }
                },
                "required": ["to_email", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_email_stats",
            "description": "Get email statistics for executive dashboard",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_email",
            "description": "Delete an email (move to trash)",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail email ID to delete"
                    }
                },
                "required": ["email_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "archive_email",
            "description": "Archive an email (remove from inbox)",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail email ID to archive"
                    }
                },
                "required": ["email_id"]
            }
        }
    }
]

def update_rose_assistant():
    """Update Rose's assistant with email capabilities"""
    try:
        print("🔄 Updating Rose's assistant with email capabilities...")
        
        # Get current assistant details
        assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"✅ Retrieved assistant: {assistant.name}")
        
        # Get current tools
        current_tools = list(assistant.tools) if assistant.tools else []
        print(f"📋 Current tools: {len(current_tools)}")
        
        # Check for existing email functions
        existing_function_names = set()
        for tool in current_tools:
            if hasattr(tool, 'function') and hasattr(tool.function, 'name'):
                existing_function_names.add(tool.function.name)
        
        print(f"🔍 Existing functions: {existing_function_names}")
        
        # Filter out email functions that already exist
        new_email_functions = []
        skipped_functions = []
        
        for func in EMAIL_FUNCTIONS:
            func_name = func['function']['name']
            if func_name not in existing_function_names:
                new_email_functions.append(func)
                print(f"  ➕ Will add: {func_name}")
            else:
                skipped_functions.append(func_name)
                print(f"  ⏭️ Already exists: {func_name}")
        
        if not new_email_functions:
            print("✅ All email functions already exist! Updating instructions only...")
            # Update the assistant with new instructions
            updated_assistant = client.beta.assistants.update(
                assistant_id=ROSE_ASSISTANT_ID,
                instructions=UPDATED_INSTRUCTIONS
            )
            print(f"📝 Instructions updated with email management guidelines")
            return True
        
        # Add new email functions to existing tools
        updated_tools = current_tools + new_email_functions
        
        # Update the assistant
        updated_assistant = client.beta.assistants.update(
            assistant_id=ROSE_ASSISTANT_ID,
            instructions=UPDATED_INSTRUCTIONS,
            tools=updated_tools
        )
        
        print(f"✅ Assistant updated successfully!")
        print(f"📧 Added {len(new_email_functions)} new email functions")
        print(f"⏭️ Skipped {len(skipped_functions)} existing functions")
        print(f"🔧 Total tools: {len(updated_tools)}")
        print(f"📝 Instructions updated with email management guidelines")
        
        # Show function summary
        if new_email_functions:
            print("\n📧 New Email Functions Added:")
            for func in new_email_functions:
                name = func['function']['name']
                desc = func['function']['description']
                print(f"  • {name}: {desc}")
        
        if skipped_functions:
            print(f"\n⏭️ Skipped Existing Functions: {', '.join(skipped_functions)}")
        
        print(f"\n👑 Rose is now ready for complete executive email management!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        print(f"📋 Full error details: {str(e)}")
        return False

def verify_update():
    """Verify the assistant was updated correctly"""
    try:
        print("\n🔍 Verifying assistant update...")
        
        assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        
        email_functions = [tool for tool in assistant.tools if 'email' in tool.function.name.lower()]
        
        print(f"✅ Assistant verification complete")
        print(f"📧 Email functions found: {len(email_functions)}")
        
        if len(email_functions) >= 7:
            print("🎉 All email functions successfully added!")
            return True
        else:
            print("⚠️ Some email functions may be missing")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying update: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Rose Assistant Email Integration Update")
    print("=" * 50)
    
    # Update assistant
    success = update_rose_assistant()
    
    if success:
        # Verify update
        verify_update()
        
        print("\n" + "=" * 50)
        print("✅ EMAIL INTEGRATION COMPLETE!")
        print("🎯 Next Steps:")
        print("   1. Enable Gmail API in Google Cloud Console")
        print("   2. Replace your main.py with the updated version")
        print("   3. Test with: !emails, !unread, !emailstats")
        print("   4. Try: @Rose check my unread emails")
        print("   5. Try: @Rose send email to team about meeting")
        print("\n👑 Rose is ready for executive email management!")
    else:
        print("\n❌ Update failed. Please check your environment variables and try again.")