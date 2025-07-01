#!/usr/bin/env bash

# MCP Taskmaster Wrapper Script
# This script ensures the proper environment for the MCP server

# Set the path to the task-master-ai binary
TASKMASTER_BIN="/nix/store/2sf7g4ch194d5r4sh1an8pfawszn21yj-task-master-ai-0.18.0/bin/task-master-ai"

# Check if the binary exists
if [ ! -f "$TASKMASTER_BIN" ]; then
    echo "Error: task-master-ai binary not found at $TASKMASTER_BIN" >&2
    exit 1
fi

# Execute the MCP server with all arguments passed through
exec "$TASKMASTER_BIN" "$@" 