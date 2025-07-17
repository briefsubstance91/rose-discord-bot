#!/usr/bin/env python3
"""
Automated Rose Date Fix Script
This script will update your main.py file to fix Rose's date awareness
"""

import os
import re
from datetime import datetime

def backup_main_py():
    """Create a backup of main.py before making changes"""
    if os.path.exists('main.py'):
        backup_name = f"main_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        os.system(f"cp main.py {backup_name}")
        print(f"✅ Backup created: {backup_name}")
        return True
    else:
        print("❌ main.py not found in current directory")
        return False

def update_main_py():
    """Update main.py with date awareness fix"""
    
    if not os.path.exists('main.py'):
        print("❌ main.py not found. Make sure you're in the right directory.")
        return False
    
    # Read the current file
    with open('main.py', 'r') as file:
        content = file.read()
    
    # Pattern to find the enhanced_message section
    pattern = r'enhanced_message = f"""USER EXECUTIVE REQUEST: \{clean_message\}.*?"""'
    
    # New enhanced_message with date awareness
    replacement = '''# Get current date context for Rose
        toronto_tz = pytz.timezone('America/Toronto')
        now = datetime.now(toronto_tz)
        today_formatted = now.strftime('%A, %B %d, %Y')
        today_date = now.strftime('%Y-%m-%d')
        tomorrow = now + timedelta(days=1)
        tomorrow_formatted = tomorrow.strftime('%A, %B %d, %Y') 
        tomorrow_date = tomorrow.strftime('%Y-%m-%d')

        enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}

CURRENT DATE & TIME CONTEXT:
- TODAY: {today_formatted} ({today_date})
- TOMORROW: {tomorrow_formatted} ({tomorrow_date})
- TIMEZONE: America/Toronto

RESPONSE GUIDELINES:
- Use professional executive formatting with strategic headers
- AVAILABLE CALENDARS: {[name for name, _, _ in accessible_calendars]}
- Apply executive assistant tone: strategic, organized, action-oriented
- Keep main content under 1200 characters for Discord efficiency
- Use headers like: 👑 **Executive Summary:** or 📊 **Strategic Analysis:**
- When user says "tomorrow" use {tomorrow_date} ({tomorrow_formatted})
- When user says "today" use {today_date} ({today_formatted})
- All times are in Toronto timezone (America/Toronto)"""'''
    
    # Replace the section
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if updated_content == content:
        print("⚠️ Pattern not found. Manual update required.")
        print("\nSearch for this line in main.py:")
        print('enhanced_message = f"""USER EXECUTIVE REQUEST: {clean_message}')
        return False
    
    # Write the updated file
    with open('main.py', 'w') as file:
        file.write(updated_content)
    
    print("✅ main.py updated with date awareness fix!")
    return True

def main():
    print("🔧 Rose Date Awareness Fix")
    print("==========================")
    
    # Check if we're in the right directory
    current_dir = os.getcwd()
    print(f"📁 Current directory: {current_dir}")
    
    if not os.path.exists('main.py'):
        print("\n❌ main.py not found!")
        print("💡 Make sure you're in the rose-discord-bot directory:")
        print("   cd /Users/bgelineau/Downloads/rose-discord-bot/")
        return
    
    # Create backup
    if backup_main_py():
        # Apply the fix
        if update_main_py():
            print("\n🎉 Success! Rose now has proper date awareness.")
            print("\n🚀 Next steps:")
            print("1. Restart Rose: python3 main.py")
            print("2. Test with: @Rose Ashcombe move [task] to tomorrow")
            print("\n📅 Rose will now use the correct date for 'tomorrow'!")
        else:
            print("\n📝 Manual update required. See instructions above.")
    else:
        print("\n❌ Could not create backup. Stopping for safety.")

if __name__ == "__main__":
    main()
