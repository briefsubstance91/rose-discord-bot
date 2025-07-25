# add_calendar_functions_to_rose.py
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Rose's assistant ID
ROSE_ASSISTANT_ID = "asst_pvsyZQdHFQYUCkZe0HZHLA2z"

# Calendar function definitions - FULL MANAGEMENT SUITE
calendar_functions = [
    # READ FUNCTIONS
    {
        "type": "function",
        "function": {
            "name": "list_gcal_events",
            "description": "List or search events from Google Calendar. Use this to view upcoming events, search for specific meetings, or check calendar availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (use 'primary' for main calendar)",
                        "default": "primary"
                    },
                    "max_results": {
                        "type": "integer", 
                        "description": "Maximum number of events to return",
                        "default": 25
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query to filter events"
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Start time filter (RFC3339 format)"
                    },
                    "time_max": {
                        "type": "string", 
                        "description": "End time filter (RFC3339 format)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_gcal_event",
            "description": "Get detailed information about a specific calendar event by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID containing the event"
                    },
                    "event_id": {
                        "type": "string", 
                        "description": "The ID of the event to retrieve"
                    }
                },
                "required": ["calendar_id", "event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_time",
            "description": "Find available time slots across calendars for scheduling meetings",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of calendar IDs to check for availability"
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Start time for availability search (RFC3339 format)"
                    },
                    "time_max": {
                        "type": "string",
                        "description": "End time for availability search (RFC3339 format)"
                    }
                },
                "required": ["calendar_ids", "time_min", "time_max"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_gcal_calendars",
            "description": "List all available calendars in Google Calendar account",
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            }
        }
    },
    # WRITE FUNCTIONS - CREATE, EDIT, DELETE, MOVE
    {
        "type": "function",
        "function": {
            "name": "create_gcal_event",
            "description": "Create a new event in Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to create event in (use 'primary' for main calendar)",
                        "default": "primary"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title/summary"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description/details"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Event start time (RFC3339 format)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Event end time (RFC3339 format)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses"
                    }
                },
                "required": ["summary", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_gcal_event",
            "description": "Update/edit an existing calendar event. Use this to move events, change details, or modify attendees.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID containing the event"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "ID of the event to update"
                    },
                    "summary": {
                        "type": "string",
                        "description": "New event title/summary"
                    },
                    "description": {
                        "type": "string",
                        "description": "New event description/details"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "New start time (RFC3339 format) - use this to MOVE events"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "New end time (RFC3339 format) - use this to MOVE events"
                    },
                    "location": {
                        "type": "string",
                        "description": "New event location"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Updated list of attendee email addresses"
                    }
                },
                "required": ["calendar_id", "event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_gcal_event",
            "description": "Delete a calendar event permanently",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID containing the event"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "ID of the event to delete"
                    }
                },
                "required": ["calendar_id", "event_id"]
            }
        }
    }
]

try:
    # Get Rose's current configuration
    assistant = client.beta.assistants.retrieve(ROSE_ASSISTANT_ID)
    
    print(f"Current tools for {assistant.name}: {len(assistant.tools)}")
    
    # Combine existing tools with new calendar functions
    updated_tools = list(assistant.tools) + calendar_functions
    
    # Update Rose with calendar functions
    updated_assistant = client.beta.assistants.update(
        ROSE_ASSISTANT_ID,
        tools=updated_tools
    )
    
    print(f"✅ Successfully added {len(calendar_functions)} calendar functions to Rose!")
    print(f"Total tools now: {len(updated_assistant.tools)}")
    
    # List the new calendar functions
    print("\nNew calendar functions added:")
    for func in calendar_functions:
        print(f"- {func['function']['name']}: {func['function']['description']}")
        
    print(f"\n🎉 Rose now has FULL calendar management!")
    print("READ functions:")
    print("- View calendar events")
    print("- Search for specific meetings") 
    print("- Find free time slots")
    print("- Access calendar details")
    print("\nWRITE functions:")
    print("- CREATE new events")
    print("- UPDATE/MOVE existing events")
    print("- DELETE events")
    print("- Modify event details, times, attendees")
    print("\n✅ Rose can now handle the 'move meeting' request properly!")
    
except Exception as e:
    print(f"❌ Error updating Rose: {e}")
    print("Make sure your OPENAI_API_KEY is correct in .env file")
