
import json

# Method 1: If you have a JSON file
def convert_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Convert to single line
    single_line = json.dumps(data, separators=(',', ':'))
    
    print("Copy this value to Railway GOOGLE_SERVICE_ACCOUNT_JSON:")
    print(single_line)
    return single_line

# Method 2: If you have JSON as a string
def convert_json_string(json_string):
    try:
        data = json.loads(json_string)
        single_line = json.dumps(data, separators=(',', ':'))
        print("Converted JSON:")
        print(single_line)
        return single_line
    except json.JSONDecodeError as e:
        print(f"Error: {e}")
        return None

# Usage:
# convert_json_file('path/to/your/service-account.json')
# convert_json_string('your json string here')
