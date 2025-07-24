#!/usr/bin/env python3
"""
Update Rose OpenAI Assistant - Make Her Proactive with Email Workflow Again
This script updates your OpenAI assistant to restore the proactive email workflow
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ROSE_ASSISTANT_ID") or os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    print("❌ Missing OPENAI_API_KEY or ROSE_ASSISTANT_ID environment variables")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

def update_rose_assistant():
    """Update Rose's assistant configuration to be more proactive with emails"""
    
    print("🌹 Updating Rose Ashcombe OpenAI Assistant Configuration...")
    print("=" * 60)
    
    # Enhanced instructions that make Rose proactive
    enhanced_instructions = """You are Rose Ashcombe, Executive Assistant extraordinaire. You are proactive, efficient, and take initiative to help users manage their digital life.

CORE PERSONALITY:
- Executive-level professional with strategic thinking
- Proactive problem-solver who anticipates needs
- Efficient communicator who provides actionable solutions
- Takes initiative to suggest improvements and cleanup

EMAIL WORKFLOW EXCELLENCE:
When users mention email problems (spam, newsletters, clutter), you should:

1. **IMMEDIATELY SEARCH** for relevant emails using smart_email_search
2. **ANALYZE PATTERNS** - identify common senders, subjects, or themes
3. **OFFER SPECIFIC ACTIONS** - "I found X emails from Y sender, shall I delete them?"
4. **EXECUTE WHEN CONFIRMED** - use batch functions to clean up efficiently
5. **PROVIDE SUMMARIES** - show highlights before bulk deletion

PROACTIVE EMAIL BEHAVIORS:
- When user says "delete emails from SKIMS" → search for SKIMS emails first, then batch delete
- When user mentions "hot weather deals" → search and offer to clean up promotional emails
- When user asks about "newsletters" → suggest batch cleanup by sender or subject
- Always OFFER to delete/clean up when you find bulk email patterns
- Provide email highlights/summaries before bulk actions

KEY FUNCTIONS TO USE PROACTIVELY:
- smart_email_search() - Find emails flexibly by content/sender/subject
- batch_delete_by_sender() - Clean up all emails from a specific sender
- batch_delete_by_subject() - Clean up emails with specific subject patterns
- get_recent_emails() - Check recent email activity
- search_emails() - Targeted email searches

EXAMPLE WORKFLOWS:
User: "delete emails from SKIMS"
You: *search for SKIMS emails* → "Found 15 emails from SKIMS with subjects like '25% off summer styles' and 'New arrivals'. Shall I delete all 15?"

User: "clean up hot weather deals"
You: *search for weather/deals emails* → "Found 10 promotional emails about summer deals. Here are the highlights: [list key offers]. Want me to delete these promotional emails?"

EXECUTIVE COMMUNICATION STYLE:
- Direct and actionable responses
- Use executive emoji (👑, 📧, 🎯, ⚡, 📊)
- Provide clear next steps
- Anticipate follow-up needs
- Professional but personable tone

CALENDAR & SCHEDULING:
- Proactively check for conflicts
- Suggest optimal timing
- Provide weather context for outdoor meetings
- Cross-reference multiple calendars

Always be solution-oriented and take initiative to improve the user's productivity and digital organization."""

    # Updated function definitions with batch operations
    function_definitions = [
        {
            "type": "function",
            "function": {
                "name": "get_recent_emails",
                "description": "Get recent emails from Gmail with optional query filtering",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Number of emails to retrieve (default: 10)"},
                        "query": {"type": "string", "description": "Gmail search query (default: 'in:inbox')"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_unread_emails",
                "description": "Get unread emails only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Number of unread emails to retrieve (default: 10)"}
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
                        "query": {"type": "string", "description": "Gmail search query (e.g., 'from:sender@email.com', 'subject:newsletter')"},
                        "count": {"type": "integer", "description": "Number of results to return (default: 10)"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "smart_email_search",
                "description": "Flexible email search that finds emails by content, subject, or sender patterns. Use this when user mentions email topics or cleanup needs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_terms": {"type": "string", "description": "Search terms (e.g., 'SKIMS', 'hot weather deals', 'newsletter')"},
                        "count": {"type": "integer", "description": "Number of results (default: 20)"}
                    },
                    "required": ["search_terms"]
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
                        "to_email": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body content"}
                    },
                    "required": ["to_email", "subject", "body"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_email_stats",
                "description": "Get email dashboard statistics and overview",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_email",
                "description": "Delete a specific email by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "Gmail message ID"}
                    },
                    "required": ["email_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "archive_email",
                "description": "Archive a specific email by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "Gmail message ID"}
                    },
                    "required": ["email_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_emails_from_sender",
                "description": "Delete multiple emails from a sender (legacy function - use batch_delete_by_sender instead)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sender_email": {"type": "string", "description": "Email address of sender"},
                        "count": {"type": "integer", "description": "Maximum emails to delete (default: 10)"}
                    },
                    "required": ["sender_email"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "batch_delete_by_sender",
                "description": "PROACTIVE BATCH DELETE: Delete multiple emails from a specific sender with enhanced feedback. Use this for bulk cleanup operations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sender_email": {"type": "string", "description": "Email address of sender to delete from"},
                        "count": {"type": "integer", "description": "Maximum emails to delete (default: 50, max: 200)"}
                    },
                    "required": ["sender_email"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "batch_delete_by_subject",
                "description": "PROACTIVE BATCH DELETE: Delete multiple emails containing specific text in the subject line. Perfect for newsletter/promotional cleanup.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject_text": {"type": "string", "description": "Text to search for in email subjects"},
                        "count": {"type": "integer", "description": "Maximum emails to delete (default: 25, max: 100)"}
                    },
                    "required": ["subject_text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mark_email_as_read",
                "description": "Mark email as read",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "Gmail message ID"}
                    },
                    "required": ["email_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mark_email_as_important",
                "description": "Mark email as important",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "Gmail message ID"}
                    },
                    "required": ["email_id"]
                }
            }
        }
    ]
    
    try:
        # Update the assistant
        updated_assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=enhanced_instructions,
            tools=function_definitions
        )
        
        print("✅ Rose Ashcombe assistant updated successfully!")
        print(f"📧 Assistant ID: {ASSISTANT_ID}")
        print(f"🔧 Functions updated: {len(function_definitions)}")
        
        print("\n🎯 Key improvements:")
        print("✅ Proactive email workflow restored")
        print("✅ Smart email search capabilities")
        print("✅ Batch delete operations")
        print("✅ Executive-level instructions")
        print("✅ Solution-oriented personality")
        
        print("\n🧪 Test these commands:")
        print("• @Rose delete emails from SKIMS")
        print("• @Rose clean up newsletter emails")  
        print("• @Rose find promotional emails")
        print("• @Rose check my unread emails")
        
        print(f"\n✨ Rose should now be proactive like she used to be!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

if __name__ == "__main__":
    success = update_rose_assistant()
    if success:
        print("\n🎉 SUCCESS: Rose has been restored to her proactive glory!")
    else:
        print("\n❌ FAILED: Could not update Rose's assistant configuration")
