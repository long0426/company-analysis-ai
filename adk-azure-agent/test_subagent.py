from my_agent.agent import model, mcp_toolsets, get_current_time, get_mcp_log, format_search_results
from google.adk.agents.llm_agent import Agent

# 測試創建 sub-agent
print("Creating discovery agent...")
test_agent = Agent(
    model=model,
    name='test_discovery',
    instruction="Test agent",
    tools=[get_current_time, get_mcp_log, format_search_results] + mcp_toolsets
)

print(f"\nTotal tools: {len(test_agent.tools)}")
print("\nTool list:")
for i, tool in enumerate(test_agent.tools):
    if hasattr(tool, 'name'):
        print(f"  {i+1}. {tool.name}")
    elif hasattr(tool, '__name__'):
        print(f"  {i+1}. {tool.__name__} (function)")
    else:
        print(f"  {i+1}. {type(tool).__name__}")
