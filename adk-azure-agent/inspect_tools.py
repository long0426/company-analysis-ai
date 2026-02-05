
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters
import json
from pathlib import Path

def inspect_tools():
    # Load config similar to agent.py
    config_path = Path("mcp_config.json")
    if not config_path.exists():
        print("Config not found")
        return

    with open(config_path) as f:
        mcp_servers = json.load(f).get("mcpServers", {})

    prefix_mapping = {
        "yfinance": "yf_",
        "web-search": "web_",
        "fetch-webpage": "url_"
    }

    for name, config in mcp_servers.items():
        print(f"\n--- Checking Server: {name} ---")
        try:
            server_params = StdioServerParameters(
                command=config.get("command"),
                args=config.get("args", []),
                env=config.get("env")
            )
            
            prefix = prefix_mapping.get(name, f"{name.replace('-', '_')}_")
            
            toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=server_params,
                    timeout=30.0
                ),
                tool_name_prefix=prefix
            )
            
            print("Calling get_tools()...")
            import asyncio
            
            # Helper to run async if needed
            tools = toolset.get_tools()
            
            # Check if tools is a list or coroutine
            if asyncio.iscoroutine(tools):
                tools = asyncio.run(tools)
                
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                 # Check if tool has .name or if it is a dict
                 name = getattr(tool, 'name', str(tool))
                 print(f"  - {name}")
        except Exception as e:
            print(f"Failed to load {name}: {e}")

if __name__ == "__main__":
    inspect_tools()
