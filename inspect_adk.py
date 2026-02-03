from google.adk.tools.mcp_tool.mcp_tool import McpTool, McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters
import inspect
import json

print("\n--- McpTool Attributes ---")
for name, member in inspect.getmembers(McpTool):
    if not name.startswith("__"):
        print(f"- {name}")

print("\n--- McpToolset Attributes ---")
for name, member in inspect.getmembers(McpToolset):
    if not name.startswith("__"):
        print(f"- {name}")

print("\n--- _get_declaration source code check ---")
try:
    src = inspect.getsource(McpTool._get_declaration)
    print(src)
except Exception as e:
    print(f"Could not get source: {e}")

