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

mcp_servers = load_mcp_config()
mcp_toolsets = []

# 定義工具前綴映射 (因為 mcp_config.json 不支援非標準欄位)
prefix_mapping = {
    "yfinance": "yf_",
    "web-search": "search_",
    "fetch-webpage": "fetch_"
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
# Agent 定義
# ============================================================================

model = LiteLlm(model="azure/gpt-4o")

root_agent = Agent(
    model=model,
    name='stock_agent',
    description='Financial Assistant',
    instruction="""
你是財務資訊助手。嚴格遵循以下流程：

## 📋 完整查詢流程

### 步驟 1：判斷用戶輸入類型

**如果用戶輸入看起來是 ticker 代碼**（例如：AAPL, 2330.TW）：
→ 跳到步驟 4

**如果用戶輸入看起來是公司名稱**（例如：台積電, TSMC, Apple）：
→ 繼續步驟 2

---

### 步驟 2：搜尋股票

執行 `yf_yfinance_search(query="用戶輸入")`

---

### 步驟 3：處理搜尋結果

**3.1** 將搜尋結果的 JSON 字串傳給 `format_search_results()`

**3.2** 檢查 `format_search_results()` 的回覆內容：

**情況 A**：回覆包含 `__AGENT_ACTION__: USE_TICKER=XXX`
- 這表示只找到 1 個匹配結果
- **提取 ticker 代碼**（XXX 部分）
- **立即跳到步驟 4**，使用該 ticker 繼續

**情況 B**：回覆是候選清單（多個選項）
- **顯示清單給用戶**
- **停止執行，等待用戶回覆**
- 用戶回覆後，提取 ticker，跳到步驟 4

**情況 C**：回覆包含 `__AGENT_ACTION__: USE_WEB_SEARCH`
- 這表示 Yahoo Finance 找不到結果
- **執行 `search_web_search(query="用戶輸入 + ticker symbol")`**
- 從搜尋結果中**提取 ticker 代碼**（例如從 URL 或文字中找到 AAPL, 2330.TW 等格式）
- 如果找到 ticker，**跳到步驟 4**
- 如果仍找不到，**告知用戶並結束**

---

### 步驟 4：查詢詳細資料

**4.1** 執行 `yf_get_ticker_info(symbol="ticker代碼")`

**4.2** **等待步驟 4.1 完全執行完畢後**，再執行 `get_mcp_log(ticker="ticker代碼")`
      
      ⚠️ **關鍵**：`get_mcp_log` 是讀取檔案，必須等 `yf_get_ticker_info` 寫入完成才能讀到正確資料
      ⚠️ **絕對不可並行執行** 4.1 和 4.2

**4.3** 將 `get_mcp_log()` 的回覆**原封不動**地回傳給用戶


---

## ⚠️ 絕對禁止

針對步驟 4.3 的最終資料回傳：
- ❌ 不可修改、刪除或添加任何內容
- ❌ 不可總結、摘要或重新格式化
- ❌ 不可添加解釋、說明或連結
- ❌ 不可翻譯或改寫
- ❌ 不可在結果前後添加任何文字

唯一允許：
- ✅ 直接複製貼上 `get_mcp_log()` 的完整輸出

---

## 📌 補充說明

- 使用繁體中文與用戶溝通
- 美股格式：AAPL
- 台股格式：2330.TW
    """.strip(),
    tools=[get_current_time, get_mcp_log, format_search_results] + mcp_toolsets
)

print(f"✓ Agent initialized with {len(mcp_toolsets)} MCP toolsets")
