#!/usr/bin/env python3
"""Debug script to check what's in the logs."""

import requests
import json

# Fetch the logs
response = requests.get('http://localhost:3000/api/logs/api-calls')
logs = response.json()

print(f"Total logs: {len(logs)}")
print()

if logs:
    latest = logs[-1]
    print("Latest log entry:")
    print(json.dumps(latest, indent=2))
    print()
    print(f"Has 'request' field: {'request' in latest}")
    print(f"Has 'response' field: {'response' in latest}")
    print(f"Response value: {latest.get('response')}")
else:
    print("No logs found")
