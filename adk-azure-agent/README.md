# Google ADK + Azure OpenAI 專案

這是一個使用 **Google ADK (Agent Development Kit)** 框架，並透過 **LiteLLM** 整合 **Azure OpenAI** 的 AI Agent 專案。

## 🚀 快速開始

### 環境需求

- Python 3.10+
- uv (套件管理工具)
- Azure OpenAI 帳號與 API 金鑰

### 安裝步驟

1. **確認環境變數配置**

   編輯 `my_agent/.env` 檔案，確認 Azure OpenAI 配置：
   ```bash
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name  # 請填入實際的部署名稱
   ```

2. **測試 Agent 載入**

   ```bash
   uv run python my_agent/agent.py
   ```

## 📝 使用方式

### CLI 命令列模式

```bash
uv run adk run my_agent
```

進入互動式命令列，直接與 Agent 對話。

### Web UI 模式（推薦）

```bash
uv run adk web --port 9000
```

然後在瀏覽器開啟：`http://localhost:9000`

在 Web UI 中：
1. 左上角選擇 `azure_agent`
2. 在聊天介面輸入訊息
3. Agent 會使用 Azure OpenAI 回應

> **⚠️ 注意**：ADK Web UI 僅供開發和除錯使用，不適合正式環境部署。

## 🛠️ Agent 功能

當前 Agent 包含以下示範功能：

1. **對話能力**：使用 Azure OpenAI 進行自然語言對話
2. **時間查詢**：`get_current_time(city)` - 查詢指定城市時間

### 測試範例

在 Web UI 或 CLI 中嘗試：
- "你是誰？"
- "現在台北幾點？"

## 🔍 驗證 Agent 回覆準確性

### 使用 `compare_agent_response.py` 比對工具

此工具用於驗證 Agent 的最終回覆是否與原始 MCP JSON 資料完全一致，確保 Agent 沒有修改、刪除或添加任何內容。

#### 使用步驟

1. **從 Web UI 複製 Agent 的回覆**
   - 在 Agent 查詢完股票後，複製其回覆的 JSON 資料
   - 存成檔案，例如 `agent_response.json`

2. **執行比對**
   ```bash
   python compare_agent_response.py <TICKER> <RESPONSE_FILE>
   ```

   範例：
   ```bash
   # 比對台積電 (2330.TW) 的資料
   python compare_agent_response.py 2330.TW agent_response.json
   
   # 比對蘋果 (AAPL) 的資料
   python compare_agent_response.py AAPL agent_response.json
   ```

3. **查看比對結果**
   
   工具會顯示：
   - ✅ **完全一致**：Agent 回覆與原始 JSON 完全相同
   - ❌ **發現差異**：
     - 遺漏的欄位 (missing_keys)
     - 多出來的欄位 (extra_keys)
     - 值不同的欄位 (different_values)
   - 📈 **統計資訊**：原始欄位數、回覆欄位數、相同欄位數

#### 工作原理

1. 讀取 `my_agent/mcp_logs/mcp_{TICKER}_*.jsonl` 中的最新記錄
2. 從記錄中提取原始 Yahoo Finance API 回傳的 JSON
3. 將其與 Agent 的回覆進行欄位級別的比對
4. 輸出詳細的差異報告

#### 注意事項

- 此工具需要 `my_agent/mcp_logs/` 目錄中存在對應 ticker 的 log 檔案
- 如果 Agent 使用了 `search` 工具，log 檔名可能是 `mcp_unknown_*.jsonl`
- 比對結果可用於驗證 Agent 是否嚴格遵守「原封不動回傳」的指令

## 📁 專案結構

```
adk-azure-agent/
├── my_agent/
│   ├── agent.py          # 主要 Agent 程式碼
│   ├── .env              # Azure OpenAI 配置（敏感資料）
│   └── __init__.py
├── pyproject.toml        # uv 專案配置
├── uv.lock               # 依賴鎖定檔案
└── README.md             # 本檔案
```

## 🔧 擴充開發

### 新增自訂 Tool

在 `agent.py` 中定義新的 Python 函數：

```python
def your_custom_tool(param: str) -> dict:
    """
    工具描述（Agent 會讀取這個 docstring）
    
    Args:
        param: 參數說明
        
    Returns:
        結果字典
    """
    # 你的實作
    return {"result": "..."}
```

然後將它加到 Agent 的 `tools` 列表：

```python
root_agent = Agent(
    # ... 其他配置
    tools=[get_current_time, your_custom_tool]
)
```

### 修改 Agent 指令

編輯 `agent.py` 中 `root_agent` 的 `instruction` 參數來調整 Agent 的行為。

## 🔑 關於 Azure OpenAI

本專案使用 LiteLLM 作為通用 LLM 介面層，支援：
- Azure OpenAI 的所有模型（GPT-3.5、GPT-4、GPT-4o 等）
- 輕鬆切換到其他 LLM 提供者（只需修改模型配置）

## 📚 相關資源

- [Google ADK 官方文檔](https://google.github.io/adk-docs/)
- [LiteLLM 文檔](https://docs.litellm.ai/)
- [Azure OpenAI 服務](https://azure.microsoft.com/zh-tw/products/ai-services/openai-service)

## ⚠️ 安全提醒

- **不要將 `.env` 檔案提交到版本控制**（已在 `.gitignore` 中）
- API 金鑰是敏感資料，請妥善保管
- 在生產環境中應使用更安全的密鑰管理方案

## 📄 授權

本專案僅供學習與開發使用。
