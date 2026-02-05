import json
from pathlib import Path
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters
import asyncio

async def inspect():
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
    
    print(f"Prefix Mapping: {prefix_mapping}\n")

    for name, config in mcp_servers.items():
        print(f"Server Key: '{name}'")
        calculated_prefix = prefix_mapping.get(name, f"{name.replace('-', '_')}_")
        print(f"Calculated Prefix: '{calculated_prefix}'")
        
        try:
            server_params = StdioServerParameters(
                command=config.get("command"),
                args=config.get("args", []),
                env=config.get("env")
            )
            
            toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=server_params,
                    timeout=10.0
                ),
                tool_name_prefix=calculated_prefix
            )
            
            tools = await toolset.get_tools()
            print(f"Tools for {name}:")
            for t in tools:
                tname = getattr(t, 'name', str(t))
                print(f"  - {tname}")
                
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(inspect())
