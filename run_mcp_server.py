#!/usr/bin/env python3
"""
run_mcp_server.py — entry point for the Summarize MCP server.

Standalone launcher so MCP hosts (Claude Desktop / Code) can start the server
WITHOUT relying on the working directory being the project root. It inserts the
project root into sys.path itself, then runs the FastMCP server over stdio.

Usage (from any directory):
    <python.exe> D:\\VS_CODE_PROJECT\\SP_Summarize_Project\\run_mcp_server.py
"""

import os
import sys

# Project root = the folder this file lives in. Put it on sys.path so the
# `backend` package resolves regardless of the host's working directory.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.mcp_server import mcp  # noqa: E402  (after sys.path tweak)

if __name__ == "__main__":
    mcp.run()
