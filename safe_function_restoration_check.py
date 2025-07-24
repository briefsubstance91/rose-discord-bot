#!/usr/bin/env python3
"""
SAFE FUNCTION RESTORATION CHECK FOR ROSE
Checks current main.py for existing functions and only adds missing ones
Prevents duplication and conflicts
"""

import os
import re

def analyze_current_main_py():
    """Analyze current main.py to see what's already there"""
    
    print("🔍 ======================================")
    print("🔍 CURRENT MAIN.PY ANALYSIS")
    print("🔍 ======================================")
    
    if not os.path.exists('main.py'):
        print("❌ main.py not found!")
        return False
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    # All functions that should exist (from main_old)
    target_functions = {
        # Basic email functions
        "get_recent_emails": "def get_recent_emails(",
        "get_unread_emails": "def get_unread_emails(",
        "search_emails": "def search_emails(",
        "get_email_dashboard": "def get_email_dashboard(",
        "archive_emails_by_query": "def archive_emails_by_query(",
        
        # Missing email functions
        "send_email": "def send_email(",
        "delete_email": "def delete_email(",
        "archive_email": "def archive_email(",
        "mark_email_as_read": "def mark_email_as_read(",
        "mark_email_as_important": "def mark_email_as_important(",
        "batch_delete_by_sender": "def batch_delete_by_sender(",
        "batch_delete_by_subject": "def batch_delete_by_subject(",
        "batch_archive_old_emails": "def batch_archive_old_emails(",
        "cleanup_promotional_emails": "def cleanup_promotional_emails(",
        "get_recent_emails_large": "def get_recent_emails_large(",
        "delete_emails_from_sender": "def delete_emails_from_sender(",
        
        # Planning & briefing functions
        "get_morning_briefing": "def get_morning_briefing(",
        "planning_search": "async def planning_search(",
        
        # Gmail initialization
        "initialize_gmail_service": "def initialize_gmail_service(",
    }
    
    # Function handlers that should exist
    target_handlers = {
        "send_email_handler": 'elif function_name == "send_email":',
        "delete_email_handler": 'elif function_name == "delete_email":',
        "archive_email_handler": 'elif function_name == "archive_email":',
        "mark_read_handler": 'elif function_name == "mark_email_as_read":',
        "mark_important_handler": 'elif function_name == "mark_email_as_important":',
        "batch_delete_sender_handler": 'elif function_name == "batch_delete_by_sender":',
        "batch_delete_subject_handler": 'elif function_name == "batch_delete_by_subject":',
        "batch_archive_handler": 'elif function_name == "batch_archive_old_emails":',
        "cleanup_promotional_handler": 'elif function_name == "cleanup_promotional_emails":',
        "large_emails_handler": 'elif function_name == "get_recent_emails_large":',
        "morning_briefing_handler": 'elif function_name == "get_morning_briefing":',
        "planning_search_handler": 'elif function_name == "planning_search":',
    }
    
    # Discord commands that should exist
    target_commands = {
        "briefing_command": "@bot.command(name='briefing'",
        "plan_command": "@bot.command(name='plan'",
        "quickemails_command": "@bot.command(name='quickemails'",
        "emailcount_command": "@bot.command(name='emailcount'",
        "emails_command": "@bot.command(name='emails'",
        "unread_command": "@bot.command(name='unread'",
        "emailstats_command": "@bot.command(name='emailstats'",
        "cleansender_command": "@bot.command(name='cleansender'",
    }
    
    print("\n📋 **FUNCTION ANALYSIS:**")
    
    existing_functions = []
    missing_functions = []
    
    for func_name, search_pattern in target_functions.items():
        if search_pattern in content:
            print(f"✅ {func_name}: EXISTS")
            existing_functions.append(func_name)
        else:
            print(f"❌ {func_name}: MISSING")
            missing_functions.append(func_name)
    
    print("\n📋 **FUNCTION HANDLER ANALYSIS:**")
    
    existing_handlers = []
    missing_handlers = []
    
    for handler_name, search_pattern in target_handlers.items():
        if search_pattern in content:
            print(f"✅ {handler_name}: EXISTS")
            existing_handlers.append(handler_name)
        else:
            print(f"❌ {handler_name}: MISSING")
            missing_handlers.append(handler_name)
    
    print("\n📋 **DISCORD COMMAND ANALYSIS:**")
    
    existing_commands = []
    missing_commands = []
    
    for cmd_name, search_pattern in target_commands.items():
        if search_pattern in content:
            print(f"✅ {cmd_name}: EXISTS")
            existing_commands.append(cmd_name)
        else:
            print(f"❌ {cmd_name}: MISSING")
            missing_commands.append(cmd_name)
    
    # Summary
    print(f"\n📊 **SUMMARY:**")
    print(f"Functions: {len(existing_functions)} existing, {len(missing_functions)} missing")
    print(f"Handlers: {len(existing_handlers)} existing, {len(missing_handlers)} missing")
    print(f"Commands: {len(existing_commands)} existing, {len(missing_commands)} missing")
    
    # Critical missing function check
    critical_missing = []
    if "batch_delete_by_sender" in missing_functions:
        critical_missing.append("batch_delete_by_sender (NEEDED FOR SKIMS DELETION)")
    if "send_email" in missing_functions:
        critical_missing.append("send_email")
    if "get_morning_briefing" in missing_functions:
        critical_missing.append("get_morning_briefing")
    if "planning_search" in missing_functions:
        critical_missing.append("planning_search")
    
    if critical_missing:
        print(f"\n🚨 **CRITICAL MISSING FUNCTIONS:**")
        for func in critical_missing:
            print(f"• {func}")
    
    return {
        'existing_functions': existing_functions,
        'missing_functions': missing_functions,
        'existing_handlers': existing_handlers,
        'missing_handlers': missing_handlers,
        'existing_commands': existing_commands,
        'missing_commands': missing_commands,
        'critical_missing': critical_missing
    }

def check_duplication_risk():
    """Check if there are any duplicate function definitions"""
    
    if not os.path.exists('main.py'):
        return False
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    print("\n🔍 **DUPLICATION RISK CHECK:**")
    
    # Look for potential duplicates
    function_patterns = [
        r'def get_recent_emails\(',
        r'def get_unread_emails\(',
        r'def search_emails\(',
        r'def batch_delete_by_sender\(',
        r'def send_email\(',
    ]
    
    duplicates_found = False
    for pattern in function_patterns:
        matches = re.findall(pattern, content)
        if len(matches) > 1:
            func_name = pattern.replace(r'def ', '').replace(r'\(', '')
            print(f"⚠️ DUPLICATE: {func_name} found {len(matches)} times")
            duplicates_found = True
    
    if not duplicates_found:
        print("✅ No duplicate functions detected")
    
    return duplicates_found

def recommend_safe_action(analysis_result):
    """Recommend the safest restoration approach"""
    
    print("\n🎯 **SAFE RESTORATION RECOMMENDATION:**")
    
    missing_count = len(analysis_result['missing_functions'])
    critical_count = len(analysis_result['critical_missing'])
    
    if missing_count == 0:
        print("✅ **NO ACTION NEEDED**")
        print("All functions are already present!")
        return "complete"
    
    elif critical_count > 0:
        print("🚨 **TARGETED RESTORATION NEEDED**")
        print(f"Only add the {critical_count} critical missing functions")
        print("This will fix SKIMS deletion without duplication risk")
        return "targeted"
    
    elif missing_count < 5:
        print("🔧 **SELECTIVE RESTORATION RECOMMENDED**") 
        print(f"Add only the {missing_count} missing functions")
        return "selective"
    
    else:
        print("⚠️ **CAREFUL FULL RESTORATION**")
        print("Many functions missing - proceed with duplication checks")
        return "careful_full"

def create_targeted_restoration_script(analysis_result):
    """Create a script that only adds the critical missing functions"""
    
    if "batch_delete_by_sender" not in analysis_result['missing_functions']:
        print("✅ batch_delete_by_sender already exists - SKIMS deletion should work!")
        return
    
    print("\n🔧 **CREATING TARGETED RESTORATION SCRIPT:**")
    
    script_content = '''#!/usr/bin/env python3
"""
TARGETED RESTORATION: Add only batch_delete_by_sender function
This fixes the SKIMS deletion issue without duplication
"""

import os

def add_batch_delete_by_sender():
    """Add only the missing batch_delete_by_sender function"""
    
    if not os.path.exists('main.py'):
        print("❌ main.py not found!")
        return False
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    # The critical missing function
    function_code = \'\'\'
def batch_delete_by_sender(sender_email, count=25):
    """Delete multiple emails from specific sender email address"""
    try:
        if not gmail_service:
            return "❌ Gmail service not available"
        
        # Search for emails from sender
        query = f"from:{sender_email}"
        search_result = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=min(count, 100)
        ).execute()
        
        messages = search_result.get('messages', [])
        
        if not messages:
            return f"📧 I have deleted 0 emails from {sender_email}. It appears there were no emails from this sender in your inbox. If there\\'s anything else you need, just let me know!"
        
        deleted_count = 0
        failed_count = 0
        
        for message in messages:
            try:
                gmail_service.users().messages().delete(
                    userId='me',
                    id=message['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting email {message['id']}: {e}")
                failed_count += 1
                continue
        
        result_msg = f"🗑️ **Batch Delete Complete**\\\\n"
        result_msg += f"✅ Deleted: {deleted_count} emails from {sender_email}\\\\n"
        if failed_count > 0:
            result_msg += f"❌ Failed: {failed_count} emails"
        
        return result_msg
        
    except Exception as e:
        print(f"❌ Gmail batch delete by sender error: {e}")
        return f"🗑️ **Batch Delete Error:** {str(e)[:100]}"

\'\'\'
    
    # Function handler
    handler_code = \'\'\'            elif function_name == "batch_delete_by_sender":
                sender = arguments.get('sender_email', '')
                count = arguments.get('count', 25)
                output = batch_delete_by_sender(sender, count)\'\'\'
    
    # Insert function after archive_emails_by_query
    if "def archive_emails_by_query(" in content:
        insertion_point = content.find("def archive_emails_by_query(")
        # Find end of function
        lines = content[insertion_point:].split('\\n')
        function_end = 0
        found_def = False
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and not found_def:
                found_def = True
                continue
            if found_def and line.strip() and not line.startswith(' ') and not line.startswith('\\t'):
                function_end = i
                break
        
        if function_end > 0:
            insert_pos = insertion_point + len('\\n'.join(lines[:function_end]))
            content = content[:insert_pos] + function_code + content[insert_pos:]
            print("✅ Added batch_delete_by_sender function")
    
    # Insert handler
    if 'elif function_name == "archive_emails_by_query":' in content:
        insertion_point = content.find('elif function_name == "archive_emails_by_query":')
        lines = content[insertion_point:].split('\\n')
        handler_end = 0
        
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith('elif function_name ==') or line.strip().startswith('else:'):
                handler_end = i
                break
        
        if handler_end > 0:
            insert_pos = insertion_point + len('\\n'.join(lines[:handler_end]))
            content = content[:insert_pos] + '\\n' + handler_code + content[insert_pos:]
            print("✅ Added batch_delete_by_sender handler")
    
    # Write updated content
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("\\n🎉 **TARGETED RESTORATION COMPLETE!**")
    print("✅ Added batch_delete_by_sender function")
    print("✅ Added function handler")
    print("🚀 SKIMS deletion should now work!")
    
    return True

if __name__ == "__main__":
    add_batch_delete_by_sender()
'''
    
    with open('targeted_restoration.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Created targeted_restoration.py")
    print("🚀 Run with: python3 targeted_restoration.py")

if __name__ == "__main__":
    print("🔍 Analyzing current Rose main.py for safe restoration...")
    
    # Check for duplicates first
    has_duplicates = check_duplication_risk()
    
    if has_duplicates:
        print("\n⚠️ **DUPLICATION RISK DETECTED!**")
        print("Recommend manual review before restoration")
        exit(1)
    
    # Analyze current state
    analysis = analyze_current_main_py()
    
    if not analysis:
        print("❌ Analysis failed!")
        exit(1)
    
    # Get recommendation
    action = recommend_safe_action(analysis)
    
    if action == "complete":
        print("\n✅ Rose is already complete!")
    elif action == "targeted":
        print("\n🎯 Creating targeted restoration for critical functions...")
        create_targeted_restoration_script(analysis)
    else:
        print(f"\n📋 Recommendation: {action}")
        print("Review the analysis above before proceeding with restoration")
