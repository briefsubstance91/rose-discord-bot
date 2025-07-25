# check_rose_functions.py
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Rose's assistant ID
ROSE_ASSISTANT_ID = "asst_pvsyZQdHFQYUCkZe0HZHLA2z"

try:
    # Get Rose's details
    assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
    
    print(f"Assistant: {assistant.name}")
    print(f"Model: {assistant.model}")
    print("\nTools enabled:")
    
    for tool in assistant.tools:
        print(f"- {tool.type}")
        if hasattr(tool, 'function') and tool.function:
            print(f"  Function: {tool.function.name}")
            print(f"  Description: {tool.function.description}")
            
    print(f"\nTotal tools: {len(assistant.tools)}")
    
    # Check specifically for calendar-related functions
    calendar_functions = []
    for tool in assistant.tools:
        if hasattr(tool, 'function') and tool.function:
            if 'calendar' in tool.function.name.lower() or 'event' in tool.function.name.lower():
                calendar_functions.append(tool.function.name)
    
    if calendar_functions:
        print(f"\nCalendar-related functions found:")
        for func in calendar_functions:
            print(f"- {func}")
    else:
        print("\nNo calendar-related functions found!")
        
except Exception as e:
    print(f"Error: {e}")
    print("Make sure OPENAI_API_KEY is set as environment variable")
    print("Example: export OPENAI_API_KEY='your-api-key-here'")
