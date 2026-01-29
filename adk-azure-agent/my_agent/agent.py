from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters  # ADK 1.21.0 寫法
from dotenv import load_dotenv
from datetime import datetime

# 啟用 MCP 回覆記錄
from .mcp_toolset_wrapper import patch_mcp_tool
patch_mcp_tool()

load_dotenv()

def get_current_time() -> str:
    """取得當前時間"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================================
# Yahoo Finance MCP 設定
# ============================================================================

# 使用 uvx 啟動 yfmcp（首次執行會下載，需要較長時間）
server_params = StdioServerParameters(
    command="uvx",
    args=["yfmcp@latest"],
    env=None
)

connection_params = StdioConnectionParams(
    server_params=server_params,
    timeout=60.0  # 60 秒超時（ADK 1.21.0 支援此參數）
)

yfinance_toolset = McpToolset(
    connection_params=connection_params,
    tool_name_prefix="yf_",  # 工具前綴
)

# ============================================================================
# Agent 定義
# ============================================================================

model = LiteLlm(model="azure/gpt-4o")

root_agent = Agent(
    model=model,
    name='stock_agent',
    description='Financial Assistant',
    instruction="""
你是一個專業的財務分析助手。

請遵循以下規則：
1. 使用**繁體中文**回答。
2. 股票代碼：美股直接用代碼（如 AAPL），台股加後綴（如 2330.TW）。
3. 如果工具回傳英文，請翻譯成繁體中文。
    """.strip(),
    tools=[get_current_time, yfinance_toolset]
)

print("✓ Agent loaded with Yahoo Finance MCP (ADK 1.21.0)")
