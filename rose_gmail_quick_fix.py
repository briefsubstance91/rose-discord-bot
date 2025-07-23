#!/usr/bin/env python3
"""
ROSE GMAIL QUICK FIX
Fixes the NameError and adds missing Gmail functions
Simpler approach - just fix what's broken
"""

import os
import shutil
from datetime import datetime

def quick_fix_main_py():
    """Quick fix for the Gmail integration issues"""
    print("🔧 Quick fixing Rose Gmail integration...")
    
    # Read current main.py
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        print("✅ Read main.py successfully")
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return False
    
    # Create backup first
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"main_backup_quickfix_{timestamp}.py"
        shutil.copy("main.py", backup_name)
        print(f"✅ Backup created: {backup_name}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False
    
    # Fix 1: Remove the problematic line that's causing the NameError
    if "gmail_services_initialized = initialize_gmail_service()" in content:
        content = content.replace(
            "gmail_services_initialized = initialize_gmail_service()",
            "# Gmail integration - will be added later"
        )
        print("✅ Removed problematic Gmail initialization line")
    
    # Fix 2: Add gmail_service variable if missing
    if "gmail_service = None" not in content:
        if "calendar_service = None" in content:
            content = content.replace(
                "calendar_service = None",
                "calendar_service = None\ngmail_service = None"
            )
            print("✅ Added gmail_service variable")
    
    # Fix 3: Add basic Gmail function stubs to prevent errors
    gmail_stubs = '''
# ============================================================================
# GMAIL FUNCTION STUBS (BASIC IMPLEMENTATION)
# ============================================================================

def get_recent_emails(count=10, unread_only=False, include_body=False):
    """Get recent emails (stub implementation)"""
    return f"📧 **Gmail Integration:** Coming soon! Requested {count} emails (unread_only: {unread_only})"

def search_emails(query, max_results=10, include_body=False):
    """Search emails (stub implementation)"""
    return f"📧 **Gmail Search:** Coming soon! Query: '{query}' (max: {max_results})"

def get_email_stats(days=7):
    """Get email stats (stub implementation)"""
    return f"📊 **Gmail Stats:** Coming soon! Analysis for {days} days"

def delete_emails_from_sender(sender_email, max_delete=50, confirm=False):
    """Delete emails from sender (stub implementation)"""
    return f"🗑️ **Gmail Delete:** Coming soon! Would delete from {sender_email} (confirm: {confirm})"

def mark_emails_read(query, max_emails=50):
    """Mark emails as read (stub implementation)"""
    return f"✅ **Gmail Mark Read:** Coming soon! Query: '{query}' (max: {max_emails})"

def archive_emails(query, max_emails=50):
    """Archive emails (stub implementation)"""
    return f"📦 **Gmail Archive:** Coming soon! Query: '{query}' (max: {max_emails})"

'''
    
    # Add Gmail stubs before the handle_rose_functions_enhanced function
    if "async def handle_rose_functions_enhanced" in content and "def get_recent_emails" not in content:
        content = content.replace(
            "async def handle_rose_functions_enhanced",
            gmail_stubs + "\nasync def handle_rose_functions_enhanced"
        )
        print("✅ Added Gmail function stubs")
    
    # Fix 4: Update function handlers to include Gmail functions
    gmail_handlers = '''
            # GMAIL FUNCTIONS (BASIC)
            elif function_name == "search_emails":
                query = arguments.get('query', '')
                max_results = arguments.get('max_results', 10)
                include_body = arguments.get('include_body', False)
                output = search_emails(query, max_results, include_body)
                    
            elif function_name == "get_recent_emails":
                count = arguments.get('count', 10)
                unread_only = arguments.get('unread_only', False)
                include_body = arguments.get('include_body', False)
                output = get_recent_emails(count, unread_only, include_body)
                
            elif function_name == "get_email_stats":
                days = arguments.get('days', 7)
                output = get_email_stats(days)
                
            elif function_name == "delete_emails_from_sender":
                sender_email = arguments.get('sender_email', '')
                max_delete = arguments.get('max_delete', 50)
                confirm = arguments.get('confirm', False)
                output = delete_emails_from_sender(sender_email, max_delete, confirm)
                    
            elif function_name == "mark_emails_read":
                query = arguments.get('query', '')
                max_emails = arguments.get('max_emails', 50)
                output = mark_emails_read(query, max_emails)
                    
            elif function_name == "archive_emails":
                query = arguments.get('query', '')
                max_emails = arguments.get('max_emails', 50)
                output = archive_emails(query, max_emails)
                
'''
    
    # Find the right place to add Gmail handlers
    if 'else:\n                output = f"❓ Function {function_name} not fully implemented yet"' in content:
        if "elif function_name == \"search_emails\":" not in content:
            content = content.replace(
                'else:\n                output = f"❓ Function {function_name} not fully implemented yet"',
                gmail_handlers + '\n            else:\n                output = f"❓ Function {function_name} not fully implemented yet"'
            )
            print("✅ Added Gmail function handlers")
    
    # Fix 5: Add basic Gmail commands
    gmail_commands = '''
@bot.command(name='emails')
async def emails_command(ctx, count: int = 10):
    """Get recent emails (basic implementation)"""
    try:
        result = get_recent_emails(count)
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"📧 Error: {e}")

@bot.command(name='unread')
async def unread_command(ctx, count: int = 10):
    """Get unread emails (basic implementation)"""
    try:
        result = get_recent_emails(count, unread_only=True)
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"📧 Error: {e}")

@bot.command(name='emailstats')
async def emailstats_command(ctx):
    """Get email stats (basic implementation)"""
    try:
        result = get_email_stats()
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"📊 Error: {e}")

'''
    
    # Add Gmail commands before error handling
    if "@bot.command(name='help')" in content and "@bot.command(name='emails')" not in content:
        content = content.replace(
            "@bot.command(name='help')",
            gmail_commands + "\n@bot.command(name='help')"
        )
        print("✅ Added basic Gmail commands")
    
    # Write the fixed content
    try:
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Fixed main.py written successfully")
        
        print("\n🎯 **QUICK FIX COMPLETE!**")
        print("📁 Backup saved")
        print("🔧 Fixed NameError")
        print("📧 Added Gmail function stubs")
        print("💬 Added basic Gmail commands")
        print("\n✅ **Rose should now start without errors**")
        print("📧 Gmail functions return 'Coming soon' messages")
        print("\n🧪 **Test with:**")
        print("   python3 main.py")
        print("   !emailstats")
        
        return True
        
    except Exception as e:
        print(f"❌ Error writing fixed main.py: {e}")
        return False

if __name__ == "__main__":
    quick_fix_main_py()