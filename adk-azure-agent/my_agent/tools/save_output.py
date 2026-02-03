from pathlib import Path
import json

def save_agent_response(content: str) -> str:
    """
    將 Agent 生成的最終內容寫入 agent_response.md 檔案。
    
    Args:
        content: 要儲存的文字內容
        
    Returns:
        執行結果訊息
    """
    try:
        # 定義檔案路徑 (相對於 my_agent 目錄)
        target_file = Path(__file__).parent.parent / "agent_response.md"
        
        # 決定寫入模式：Append (a)
        # 並在內容前後加入分隔線與時間戳記，方便閱讀
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        entry = f"\n\n---\n**Timestamp**: {timestamp}\n\n{content}\n"
        
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(entry)
            
        return json.dumps({"status": "success", "message": f"Content saved to {target_file}"}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
