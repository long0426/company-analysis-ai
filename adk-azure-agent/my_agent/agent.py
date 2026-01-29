from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters  # ADK 1.21.0 寫法
from dotenv import load_dotenv
from datetime import datetime

# 啟用 MCP 回覆記錄
from .mcp_toolset_wrapper import patch_mcp_tool
patch_mcp_tool()

# 匯入 MCP Log 讀取工具
from .mcp_log_reader import read_latest_mcp_response, format_mcp_response

load_dotenv()

def get_current_time() -> str:
    """取得當前時間"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_mcp_log(ticker: str) -> str:
    """
    讀取指定 ticker 的最新 MCP 回覆記錄
    
    Args:
        ticker: 股票代碼（例如：2330.TW, AAPL）
    
    Returns:
        MCP 回覆的原始資料（JSON 格式字串）
    """
    import json
    response = read_latest_mcp_response(ticker)
    if not response:
        return f"❌ 找不到 {ticker} 的記錄"
    
    # 用 code block 包裝 JSON，確保格式正確
    json_str = json.dumps(response, ensure_ascii=False, indent=2)
    return f"```json\n{json_str}\n```"

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
你是財務資訊助手。

當用戶查詢股票時，請**嚴格遵守**以下步驟：

1. 使用 Yahoo Finance 工具查詢（例如：yf_get_ticker_info）
2. 使用 get_mcp_log 讀取剛才的記錄
3. **原封不動**地回傳 get_mcp_log 的完整結果

**絕對禁止**：
- ❌ 修改、刪除或添加任何內容
- ❌ 總結、摘要或重新格式化
- ❌ 添加任何解釋、說明或連結
- ❌ 翻譯或改寫任何文字
- ❌ 在結果前後添加任何文字

**唯一允許**：
- ✅ 直接複製貼上 get_mcp_log 的完整輸出

**基本規則**：
- 使用繁體中文
- 美股：AAPL，台股：2330.TW
    """.strip(),
    tools=[get_current_time, get_mcp_log, yfinance_toolset]
)

print("✓ Agent loaded with Yahoo Finance MCP (ADK 1.21.0)")
