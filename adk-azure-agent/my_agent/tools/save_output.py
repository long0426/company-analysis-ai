from pathlib import Path
import json
from datetime import datetime
try:
    from google.adk.tools import ToolContext
except ImportError:
    # For local testing without full ADK env
    ToolContext = Any

def save_agent_response(content: str, ticker: str, mode: str = "append", tool_context: ToolContext = None) -> str:
    """
    將 Agent 生成的內容寫入 agent_response 檔案。
    
    Args:
        content: 要儲存的文字內容
        ticker: 股票代碼 (用於區分檔案)
        mode: 寫入模式 ("overwrite" 為覆蓋/清除舊檔, "append" 為附加)
        tool_context: ADK 自動注入的工具上下文 (用於獲取 SessionID)
        
    Returns:
        執行結果訊息
    """
    try:
        # 獲取 Session ID
        session_id = "unknown_session"
        
        # DEBUG: Check session property
        if tool_context:
            try:
                if hasattr(tool_context, 'session') and tool_context.session:
                    session_id = tool_context.session.id
                    print(f"[DEBUG] Retrieved session_id: {session_id}")
                else:
                    print("[DEBUG] tool_context has no session property or it is None")
                    # Fallback to internal if needed (should not be needed based on docs)
                    if hasattr(tool_context, '_invocation_context'):
                        session_id = tool_context._invocation_context.session.id
                        print(f"[DEBUG] Retrieved from _invocation_context: {session_id}")
            except Exception as e:
                print(f"[DEBUG] Error retrieving session_id: {e}")

        # 定義檔案路徑 (相對於 my_agent 目錄)
        
        # 定義檔案路徑 (相對於 my_agent 目錄)
        # 格式: agent_response_{session_id}_{ticker}.md
        filename = f"agent_response_{session_id}_{ticker}.md"
        target_file = Path(__file__).parent.parent / filename
        
        # 決定寫入模式
        file_mode = "w" if mode == "overwrite" else "a"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n---\n**Timestamp**: {timestamp}\n\n{content}\n"
        
        # 如果是 overwrite 模式，直接寫入 header + content
        if mode == "overwrite":
            entry = f"# Agent Response for {ticker} (Session: {session_id})\n{entry}"

        with open(target_file, file_mode, encoding="utf-8") as f:
            f.write(entry)
            
        return json.dumps({
            "status": "success", 
            "message": f"Content saved to {filename}",
            "file_path": str(target_file)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
