#!/bin/bash

set -euo pipefail

# Debugging information
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "Contents of /usr/local/lib:"
ls -l /usr/local/lib | grep libdmtx

# Processing loop
while true
do
    HEADERS="$(mktemp)"
    
    # Get an event from the Lambda Runtime API
    EVENT_DATA=$(curl -sS -LD "$HEADERS" "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/next")

    # Extract the request ID for response
    REQUEST_ID=$(grep -Fi Lambda-Runtime-Aws-Request-Id "$HEADERS" | tr -d '[:space:]' | cut -d: -f2)

    # Pass the event to app.py and capture the response
    RESPONSE=$(python3 /var/task/app.py "$EVENT_DATA")

    # Send the response back to the Lambda Runtime API
    curl -X POST "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/$REQUEST_ID/response" -d "$RESPONSE"
done
