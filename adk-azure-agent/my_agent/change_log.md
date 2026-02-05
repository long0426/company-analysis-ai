# Change Log

## 2026-02-05
- **File**: `system_prompt/generate_key_message.md`
- **Action**: Modified
- **Description**: 移除 Prompt 中關於 `web_search` 的過時指令。
- **Reason**: 流程調整，後續步驟不再使用 Web Search。

- **File**: `system_prompt/generate_key_message.md`
- **Action**: Refactor
- **Description**: 合併重複的「步驟 1」標題。
- **Reason**: 消除結構冗餘，避免 LLM 對執行步驟產生混淆。

- **File**: `system_prompt/generate_key_message.md`
- **Action**: Modified
- **Description**: 修正 Web Search 使用規則。恢復「步驟 0」可使用 Web Search 查找 Ticker，但明確禁止在「步驟 1」及之後使用 Web Search 獲取資料。
- **Reason**: 區分「工具查找」與「資料獲取」的邊界，確保資料來源單一化 (Yahoo Finance) 同時保有查找代碼的彈性。

- **File**: `system_prompt/orchestrator.md`
- **Action**: Modified (Temporary)
- **Description**: 暫時修改 Orchestrator 流程。跳過 `discovery_agent`，直接將用戶請求轉發給 `analysis_agent`。
- **Reason**: 為了驗證 `analysis_agent` (對應 `generate_key_message.md`) 的獨立運作能力與 Ticker 辨識邏輯。測試完成後需還原。

- **File**: `system_prompt/generate_key_message.md`
- **Action**: Modified
- **Description**: 強化 Step 1 指令。明確要求 `yf_get_ticker_news` 為強制執行項目，並增加 Self-Correction 檢查點，防止 Agent 跳過新聞獲取步驟。
- **Reason**: 修正 Agent 在獲取 Info 後誤判資料足夠而跳過 News 的行為。

- **File**: `system_prompt/generate_key_message.md`
- **Action**: Modified
- **Description**: 明確定義任務目標為「撰寫分析短文」，並在 Step 4 與禁止清單中，嚴格禁止將 Raw JSON 或 API 回傳值直接存檔。
- **Reason**: 修正 Agent 誤將資料獲取階段當作最終目標，導致產出 Log Dump 而非分析報告的問題。

- **File**: `system_prompt/orchestrator.md`
- **Action**: Restore & Refine
- **Description**: 還原 Orchestrator 流程為 `Discovery` -> `Analysis` -> `Report`。調整邏輯：Discovery 負責找 Ticker，若成功則傳 Ticker 給 Analysis，若失敗則傳原始 Input 給 Analysis 嘗試自行搜尋。
- **Reason**: 結束 `analysis_agent` 的獨立驗證階段，恢復完整的 Agent 協作鏈路，並增加 Ticker 識別的容錯機制。

- **File**: `system_prompt/generate_key_message.md`
- **Action**: Modified
- **Description**: 強化 Step 4 指令，將「存檔」與「移交」定義為原子操作，並增加強烈的負面提示 (Negative Prompt)，禁止 Agent 在存檔後輸出任何閒聊文字，確保控制權能正確移交回 Orchestrator。
- **Reason**: 修正 Agent 在存檔後直接對用戶說話，導致 Orchestrator 無法執行「讀檔」步驟的問題。
- **File**: `system_prompt/generate_key_message.md`
- **Action**: Refined Goal
- **Description**: 將「產出目標」從「分析短文」修改為「生成並寫入檔案」，並增加負面提示「請勿直接輸出給用戶」。
- **Reason**: 解決 Agent 因誤解目標而直接將內容輸出到對話視窗，導致流程中斷的問題。
## 2026-02-03
- **File**: `system_prompt/generate_key_message.md`, `agent.py`, `tools/calculate_upside.py`
- **Action**: Modified & Added
- **Description**: 
    1. 移除 `generate_key_message.md` 中強制執行的「步驟 2：Web Search」。
    2. 新增 `calculate_upside_potential` 工具，解決上漲空間驗證失敗問題。
- **Reason**: 
    1. 避免資訊過載並加速流程。
    2. 解決上漲空間為計算值導致的驗證失敗問題，確保所有數值皆有 Log 可循。
    
- **File**: `tools/prompt_verifier.py`
- **Action**: Modified
- **Description**: 
    1. 移除強制 Web Search 檢查 (改為總是回傳 Valid)。
    2. 增強 `extract_data_for_prompt`，支援解析非標準 MCP 格式的 Log (如 Local Tools 產生的 JSON)。
- **Reason**: 配合 `generate_key_message.md` 流程調整，並修復 `calculate_upside_potential` 輸出無法被驗證器讀取的 Bug。

- **File**: `agent.py`, `tools/save_output.py`, `system_prompt/generate_key_message.md`
- **Action**: Added & Modified
- **Description**: 
    1. 新增 `save_agent_response` 工具，將 Agent 回覆存入 `agent_response.md` (Append mode)。
    2. 修改 Prompt 強制 Agent 在最終輸出前呼叫此工具。
- **Reason**: 應使用者要求，保留 Agent 的最終生成結果以供後續查閱。

- **File**: `agent.py`, `system_prompt/orchestrator.md`
- **Action**: Modified & Added
- **Description**: 
    1. 新增 `orchestrator.md` 作為 Agent 的核心指揮 prompt。
    2. 重構 `agent.py` 中的 `root_agent`，將其轉變為 Orchestrator 模式。
    3. 實作 `run_ticker_discovery_task` 與 `run_key_message_task` 工具，分別動態調用 `get_ticker_info.md` 與 `generate_key_message.md` 的獨立 Agent。
    4. 實作 Pipeline 流程：Step 1 (Discovery) -> Step 2 (Analysis) -> Step 3 (Report)。
- **Reason**: 
    1. 整合 System Prompt，確保每個階段使用獨立的 Context Window 以避免 Token 過載與幻覺。
    2. 強制執行嚴格的 SOP 順序。
