# Repository Guidelines

## Project Structure & Module Organization
專案根目錄包含 `main.py`（最小入口）、`pyproject.toml`、`uv.lock` 與本指南；AI 行為全部集中在 `my_agent/agent.py`，同資料夾的 `.env` 儲存 Azure OpenAI 憑證，務必從 `.gitignore` 以外的管道保護。新增工具或協作模組時，建議依功能拆分子模組（例如 `my_agent/tools/`）並透過 `my_agent/__init__.py` 暴露公開介面；測試實例則置於未來的 `tests/` 目錄，以 `test_<module>.py` 命名以利自動發現。

## Build, Test, and Development Commands
- `uv sync`：根據 `pyproject.toml` / `uv.lock` 同步依賴；新增套件後執行以確保一致性。
- `uv run python my_agent/agent.py`：於本機載入 `.env` 並輸出 Agent 設定，做為 smoke test。
- `uv run adk run my_agent`：啟動命令列互動以驗證多輪對話與工具呼叫。
- `uv run adk web --port 9000`：啟動 ADK Web UI；若埠號衝突，請調整 `--port`。
- `uv run pytest`（規劃中）：建立 `tests/` 後採此指令執行單元與整合測試，PR 需附結果摘要。

## Coding Style & Naming Conventions
程式碼採 Python 3.12 與 PEP 8 風格，縮排四個空白並保持 120 字元以內；所有 Tool 函式需加上型別註解與 docstring 描述輸入、輸出與安全性。環境變數讀取集中於 `agent.py`，若新增設定請使用 `os.getenv` 並在 README / 本文件同步說明。命名採動詞開頭的蛇形命名（如 `get_current_time`），類別以 PascalCase 命名；務必以 `Agent` 指令字串描述預期語氣與工具使用規則。

## Testing Guidelines
目前無自動化框架，因此每次提交前至少執行 `uv run python my_agent/agent.py`、CLI 與 Web smoke test，並在 PR 中貼上重點輸出。規劃導入 `pytest` 後，測試檔需以 Arrange-Act-Assert 結構撰寫並覆蓋工具的成功與失敗路徑，避免真實網路請改用 `unittest.mock` 或假資料。若功能依賴環境變數，測試需以 `monkeypatch` 注入臨時值，確保跨環境一致。

## Commit & Pull Request Guidelines
`main` 目前尚無正式歷史，請使用 Conventional Commits（例如 `feat: add exchange-rate tool`、`fix: guard azure env`），首行不超過 72 字元並避免合併多個主題。PR 需描述變更動機、核心差異、測試結果以及相關 issue（用 `Closes #id`），若修改對話流程或 UI，請附 CLI 輸出或 Web 截圖。提交前請確認無 `print` 除錯語句、`.env` 未被修改且 `uv.lock` 僅在依賴變更時更新。

## Security & Configuration Tips
敏感金鑰僅可保留於 `my_agent/.env` 或系統層秘密管理工具，不得寫入程式碼、日誌或 PR 描述；審查前請再次確認 diff 中沒有憑證字串。若新增工具會接觸外部 API，請在 docstring 與 PR 提醒授權、速率限制與錯誤處理策略，必要時加入節流或快取。部署到不同 Azure 訂閱時，務必更新 `.env` 並於 README 或雲端設定文件記錄對應的 `AZURE_OPENAI_DEPLOYMENT_NAME`。
落實以上守則可確保代理在本地與雲端均維持一致配置、可追蹤審查紀錄，並加速新成員上手。
未來若建置 CI，可在工作流程中依序執行 `uv sync`、`uv run pytest` 與 CLI/Web smoke 指令，以捕捉依賴與行為迴歸。
