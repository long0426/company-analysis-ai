from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters  # ADK 1.21.0 寫法
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# 啟用 MCP 回覆記錄
from .mcp_toolset_wrapper import patch_mcp_tool
patch_mcp_tool()

# 匯入 MCP Log 讀取工具
from .mcp_log_reader import read_latest_mcp_response, format_mcp_response

load_dotenv()

# 新增驗證工具
from .tools.format_key_message import validate_key_message
from .tools.prompt_verifier import extract_data_for_prompt
from .tools.calculate_upside import calculate_upside_potential
from .tools.save_output import save_agent_response

def extract_data_tool(ticker: str) -> str:
    """
    從 mcp_logs 提取已記錄的關鍵數據，用於撰寫報告
    此工具會彙整多個 log 檔案中的數據 (包含 Yahoo Finance 和 Web Search)
    
    Args:
        ticker: 股票代碼
        
    Returns:
        JSON 格式的整合數據 (extracted_data)
    """
    import json
    try:
        data = extract_data_for_prompt(ticker)
        # 只回傳 extracted_data 和 source_map，避免过多雜訊
        result = {
            "extracted_data": data["extracted_data"],
            "source_map": data["source_map"]
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error extracting data: {str(e)}"

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

def format_search_results(search_results_json: str) -> str:
    """
    格式化股票搜尋結果，強制執行用戶選擇邏輯
    
    Args:
        search_results_json: yf_yfinance_search 回傳的 JSON 字串（陣列格式）
    
    Returns:
        格式化後的訊息，包含候選清單或後續指示
    """
    import json
    
    try:
        data = json.loads(search_results_json)
        
        # 處理 MCP response 的不同格式
        # 可能是直接的陣列，也可能包在 content[0].text 或 structuredContent.result 中
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            # 嘗試從 content.text 提取
            if 'content' in data and isinstance(data['content'], list) and len(data['content']) > 0:
                text_content = data['content'][0].get('text', '')
                results = json.loads(text_content) if text_content else []
            # 嘗試從 structuredContent.result 提取
            elif 'structuredContent' in data and 'result' in data['structuredContent']:
                result_text = data['structuredContent']['result']
                results = json.loads(result_text) if result_text else []
            else:
                return "❌ 搜尋結果格式錯誤，請重新搜尋"
        else:
            return "❌ 搜尋結果格式錯誤，請重新搜尋"
            
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return f"❌ 搜尋結果格式錯誤：{str(e)}"
    
    # 確保 results 是列表
    if not isinstance(results, list):
        return "❌ 搜尋結果格式錯誤（預期為陣列）"
    
    # 情況 1: 沒有找到結果（觸發 web-search 備援）
    if not results or len(results) == 0:
        return """⚠️ Yahoo Finance 找不到相關股票

---
__AGENT_ACTION__: USE_WEB_SEARCH
---

💡 將使用網路搜尋來尋找 ticker 資訊..."""
    
    # 情況 2: 只找到一個結果（自動繼續，不需用戶確認）
    if len(results) == 1:
        item = results[0]
        symbol = item.get('symbol', 'N/A')
        name = item.get('longname') or item.get('shortname', 'N/A')
        exchange = item.get('exchDisp') or item.get('exchange', 'N/A')
        
        return f"""✅ 找到唯一匹配結果：**{symbol}** - {name} ({exchange})

� **自動使用此 ticker 繼續查詢...**

---
__AGENT_ACTION__: USE_TICKER={symbol}
---"""
    
    # 情況 3: 找到多個結果（強制用戶選擇）
    lines = [f"找到 **{len(results)}** 個候選股票，請選擇：\n"]
    
    for idx, item in enumerate(results[:10], 1):  # 最多顯示 10 個
        symbol = item.get('symbol', 'N/A')
        name = item.get('longname') or item.get('shortname', 'N/A')
        exchange = item.get('exchDisp') or item.get('exchange', 'N/A')
        sector = item.get('sectorDisp') or item.get('sector', '')
        
        lines.append(f"**{idx}. {symbol}**")
        lines.append(f"   名稱：{name}")
        lines.append(f"   交易所：{exchange}")
        if sector:
            lines.append(f"   產業：{sector}")
        lines.append("")
    
    if len(results) > 10:
        lines.append(f"... 還有 {len(results) - 10} 個結果未顯示\n")
    
    lines.append("📌 **請回覆編號（1-10）或直接輸入 ticker 代碼**")
    
    return "\n".join(lines)

# ============================================================================
# MCP 動態載入設定 (Read from mcp_config.json)
# ============================================================================

def load_mcp_config():
    """讀取 mcp_config.json 並回傳 mcpServers 設定"""
    import json
    config_path = Path(__file__).parent.parent / "mcp_config.json"
    if not config_path.exists():
        print(f"⚠️ Config not found: {config_path}")
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("mcpServers", {})
    except Exception as e:
        print(f"❌ Error loading mcp_config.json: {e}")
        return {}

def load_system_prompt(filename: str) -> str:
    """
    從 system_prompt 目錄讀取指定的 prompt 檔案
    
    Args:
        filename: 檔案名稱（例如："get_ticker_info.md"）
    
    Returns:
        prompt 內容字串
    """
    prompt_path = Path(__file__).parent / "system_prompt" / filename
    if not prompt_path.exists():
        print(f"⚠️ System prompt not found: {prompt_path}")
        return ""
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error loading system prompt: {e}")
        return ""

mcp_servers = load_mcp_config()
mcp_toolsets = []

# 定義工具前綴映射 (因為 mcp_config.json 不支援非標準欄位)
prefix_mapping = {
    "yfinance": "yf_",      # Keep yf_ prefix for clarity
    "web-search": "web_",   # search_search -> web_search
    "fetch-webpage": "url_" # fetch_fetch -> url_fetch
}

for name, config in mcp_servers.items():
    try:
        # 建構參數
        server_params = StdioServerParameters(
            command=config.get("command"),
            args=config.get("args", []),
            env=config.get("env")  # 若無則為 None
        )
        
        # 決定 prefix
        prefix = prefix_mapping.get(name, f"{name.replace('-', '_')}_")
        
        # 建立 Toolset
        toolset = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=server_params,
                timeout=60.0
            ),
            tool_name_prefix=prefix
        )
        mcp_toolsets.append(toolset)
        print(f"✓ Loaded MCP server: {name} (prefix: {prefix})")
        
    except Exception as e:
        print(f"❌ Failed to load MCP server {name}: {e}")

# ============================================================================
# Model Initialization
# ============================================================================

model = LiteLlm(model="azure/gpt-4o")

# ============================================================================
# Sub-Agents
# ============================================================================

discovery_agent = Agent(
    model=model,
    name='discovery_agent',
    description='負責 Ticker 探索與資料獲取。擁有 Yahoo Finance 與 Web Search 工具。',
    instruction=load_system_prompt("get_ticker_info.md"),
    tools=[get_current_time, get_mcp_log, format_search_results, save_agent_response] + mcp_toolsets
)

analysis_agent = Agent(
    model=model,
    name='analysis_agent',
    description='負責分析資料並生成關鍵訊息。擁有資料讀取與分析工具。',
    instruction=load_system_prompt("generate_key_message.md"),
    tools=[
        get_current_time, get_mcp_log, extract_data_tool, 
        validate_key_message, calculate_upside_potential, 
        save_agent_response, format_search_results
    ] + mcp_toolsets
)

# ============================================================================
# Core Agent (Orchestrator)
# ============================================================================

try:
    from google.adk.tools import ToolContext
except ImportError:
    ToolContext = Any

def read_agent_response_file(ticker: str, tool_context: ToolContext = None) -> str:
    """
    Step 3: 讀取最終報告檔案內容。
    
    Args:
        ticker: 股票代碼 (必須與寫入時一致)
        tool_context: ADK 自動注入 (用於獲取 SessionID)
    """
    try:
        # 獲取 Session ID
        session_id = "unknown_session"
        if tool_context and hasattr(tool_context, 'session') and tool_context.session:
            session_id = tool_context.session.id
                
        # 建構檔名
        filename = f"agent_response_{session_id}_{ticker}.md"
        file_path = Path(__file__).parent / filename
        
        if not file_path.exists(): 
            return f"尚未生成任何報告 (檔案不存在: {filename})。請確認 Ticker 是否正確或 Discovery Agent 是否執行成功。"
            
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"

# 注意：Orchestrator 不直接執行任務，而是調度給子 Agent
root_agent = Agent(
    model=model,
    name='stock_agent',
    description='Financial Analysis Orchestrator',
    instruction=load_system_prompt("orchestrator.md"),
    # 在這裡註冊 sub_agents，ADK 會自動提供 Transfer 工具
    sub_agents=[discovery_agent, analysis_agent],
    tools=[read_agent_response_file]
)

print(f"✓ Orchestrator initializes with {len(root_agent.sub_agents)} sub-agents")
