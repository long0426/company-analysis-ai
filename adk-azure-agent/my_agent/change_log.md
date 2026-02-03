# Change Log

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
