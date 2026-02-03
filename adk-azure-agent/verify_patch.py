import asyncio
from typing import Any
from unittest.mock import MagicMock
import sys

# Mock google.adk module structure before importing mcp_toolset_wrapper
sys.modules['google'] = MagicMock()
sys.modules['google.adk'] = MagicMock()
sys.modules['google.adk.tools'] = MagicMock()
sys.modules['google.adk.tools.mcp_tool'] = MagicMock()
sys.modules['google.adk.tools.mcp_tool.mcp_tool'] = MagicMock()

# Define Mock McpTool
class MockMcpTool:
    name = "mock_tool"
    async def run_async(self, *, args: dict, tool_context: Any):
        print(f"Original run_async called with args: {args}")
        return {"status": "success"}

    def _get_declaration(self):
        return {
            "name": "mock_tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }

# Assign Mock to sys.modules
sys.modules['google.adk.tools.mcp_tool.mcp_tool'].McpTool = MockMcpTool

# Now import the wrapper which will patch the MockMcpTool
from my_agent.mcp_toolset_wrapper import patch_mcp_tool
patch_mcp_tool()

async def test_patch():
    print("\n--- Testing Schema Injection ---")
    tool = MockMcpTool()
    schema = tool._get_declaration()
    print("Schema properties keys:", schema['parameters']['properties'].keys())
    if 'ticker' in schema['parameters']['properties']:
        print("✅ Ticker injected into schema successfully")
    else:
        print("❌ Ticker NOT found in schema")

    print("\n--- Testing Execution Argument Stripping ---")
    # Simulate LLM calling with ticker
    args = {"query": "test query", "ticker": "AAPL"}
    print(f"Calling tool with args: {args}")
    
    try:
        # This calls the patched logged_run_async
        await tool.run_async(args=args, tool_context=None)
        print("✅ run_async execution completed")
    except Exception as e:
        print(f"❌ Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_patch())
