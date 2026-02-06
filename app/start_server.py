#!/usr/bin/env python3
"""
Simple startup script for the MCP Server
"""
import os
import sys

# Add the src directory to Python path
# When running from /app, src is at /app/src
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.server import main

if __name__ == "__main__":
    # Starting SAP MCP Server...
    main()