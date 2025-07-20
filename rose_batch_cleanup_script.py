#!/usr/bin/env python3
"""
ROSE BATCH EMAIL CLEANUP ENHANCEMENT
Add batch cleanup functions for efficient email management
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

# Batch cleanup functions
BATCH_CLEANUP_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "batch_delete_by_subject",
            "description": "Delete multiple emails containing specific text in subject line",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_text": {
                        "type": "string",
                        "description": "Text to search for in email subjects (e.g., 'deployment crashed', 'newsletter')"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of emails to delete (default: 25, max: 100)",
                        "default": 25
                    }
                },
                "required": ["subject_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "batch_archive_old_emails",
            "description": "Archive emails older than specified days",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_old": {
                        "type": "integer",
                        "description": "Archive emails older than this many days (e.g., 30, 60, 90)"
                    },
                    "query_filter": {
                        "type": "string",
                        "description": "Additional filter (e.g., 'from:newsletter', 'label:promotions')",
                        "default": ""
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of emails to archive (default: 50, max: 200)",
                        "default": 50
                    }
                },
                "required": ["days_old"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cleanup_promotional_emails",
            "description": "Clean up promotional/marketing emails in bulk",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to take: 'delete' or 'archive'",
                        "enum": ["delete", "archive"],
                        "default": "archive"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of promotional emails to process (default: 50, max: 200)",
                        "default": 50
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_emails_large",
            "description": "Get large number of recent emails for review (up to 100)",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of emails to retrieve (default: 50, max: 100)",
                        "default": 50
                    },
                    "query": {
                        "type": "string",
                        "description": "Gmail search query",
                        "default": "in:inbox"
                    }
                }
            }
        }
    }
]

# Update instructions to include batch operations
BATCH_CLEANUP_INSTRUCTIONS = """
BATCH EMAIL CLEANUP CAPABILITIES:
- batch_delete_by_subject(subject_text, count): Delete emails with specific subject text
- batch_archive_old_emails(days_old, query_filter, count): Archive old emails
- cleanup_promotional_emails(action, count): Clean up marketing emails
- get_recent_emails_large(count, query): Get up to 100 emails for review

BATCH CLEANUP EXAMPLES:
- "Delete all emails with 'deployment crashed'" → use batch_delete_by_subject()
- "Archive emails older than 60 days" → use batch_archive_old_emails()
- "Clean up promotional emails" → use cleanup_promotional_emails()
- "Show me 75 recent emails" → use get_recent_emails_large()

BATCH CLEANUP FORMATTING:
📧 **Batch Cleanup:** [Action taken]
📊 **Processed:** [Number] emails
🎯 **Status:** [Success/partial/failed details]

For batch operations, always confirm significant actions and provide clear counts.
"""

def update_rose_batch_cleanup():
    """Add batch cleanup functions to Rose's assistant"""
    try:
        print("🔄 Adding batch email cleanup functions to Rose...")
        
        # Get current assistant details
        assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        print(f"✅ Retrieved assistant: {assistant.name}")
        
        # Get current instructions and add batch cleanup info
        current_instructions = assistant.instructions or ""
        updated_instructions = current_instructions + "\n\n" + BATCH_CLEANUP_INSTRUCTIONS
        
        # Get current tools
        current_tools = list(assistant.tools) if assistant.tools else []
        existing_function_names = set()
        for tool in current_tools:
            if hasattr(tool, 'function') and hasattr(tool.function, 'name'):
                existing_function_names.add(tool.function.name)
        
        print(f"🔍 Existing functions: {len(existing_function_names)}")
        
        # Add missing batch functions
        new_functions = []
        for func in BATCH_CLEANUP_FUNCTIONS:
            func_name = func['function']['name']
            if func_name not in existing_function_names:
                new_functions.append(func)
                print(f"  ➕ Will add batch function: {func_name}")
            else:
                print(f"  ⏭️ Already exists: {func_name}")
        
        if new_functions:
            # Combine existing tools with new functions
            all_tools = current_tools + new_functions
            
            # Update assistant with new instructions and tools
            updated_assistant = client.beta.assistants.update(
                assistant_id=ROSE_ASSISTANT_ID,
                instructions=updated_instructions,
                tools=all_tools
            )
            
            print(f"✅ Added {len(new_functions)} batch cleanup functions")
        else:
            # Just update instructions
            updated_assistant = client.beta.assistants.update(
                assistant_id=ROSE_ASSISTANT_ID,
                instructions=updated_instructions
            )
            print("✅ All batch functions already exist, updated instructions only")
        
        # Verify final configuration
        final_assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
        total_tools = len(final_assistant.tools) if final_assistant.tools else 0
        
        print(f"\n🎯 ROSE BATCH CLEANUP ENHANCEMENT COMPLETE:")
        print(f"   📧 Batch operations: Available")
        print(f"   📊 Max emails per operation: Up to 100-200")
        print(f"   🛠️ Total tools: {total_tools}")
        print(f"   ⚡ Ready for efficient email cleanup")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Rose's assistant: {e}")
        return False

if __name__ == "__main__":
    success = update_rose_batch_cleanup()
    if success:
        print("\n✨ Rose now has enhanced batch email cleanup capabilities!")
        print("📧 Can process 25-200 emails per operation")
        print("🗑️ Batch delete by subject, sender, or age")
        print("📦 Bulk archive promotional and old emails")
        print("📋 Review up to 100 emails at once")
    else:
        print("\n❌ Update failed - check error messages above")