#!/usr/bin/env python3
"""
獨立的 Discovery Agent - 執行 get_ticker_info.md 流程
"""
import sys
import os

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from my_agent.agent import model, mcp_toolsets, get_current_time, get_mcp_log, format_search_results, load_system_prompt, save_agent_response
from google.adk.agents.llm_agent import Agent

def main():
    if len(sys.argv) < 2:
        print("Usage: discovery_agent.py <query>")
        sys.exit(1)
    
    user_query = " ".join(sys.argv[1:])
    
    print(f"\n{'='*60}")
    print(f"[Discovery Agent] Processing: {user_query}")
    print(f"{'='*60}\n")
    
    # 創建獨立的 Agent
    discovery_agent = Agent(
        model=model,
        name='discovery_agent',
        instruction=load_system_prompt("get_ticker_info.md"),
        tools=[get_current_time, get_mcp_log, format_search_results] + mcp_toolsets
    )
    
    print(f"✓ Agent created with {len(discovery_agent.tools)} tools")
    print("✓ Starting execution...\n")
    
    # 注意：這裡需要正確的執行方式
    # TODO: 實現正確的 ADK Agent 執行
    
if __name__ == "__main__":
    main()
