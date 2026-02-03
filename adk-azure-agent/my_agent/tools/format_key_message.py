from typing import Dict, Any
import json
from .prompt_verifier import verify_prompt_data

def validate_key_message(content: str, ticker: str) -> str:
    """
    驗證重要訊息內容是否符合規範
    1. 檢查字數 (80-120字)
    2. 檢查數值來源 (比對 mcp_logs)
    3. 確認步驟 2（web_search + url_fetch）已有紀錄
    
    Args:
        content: 擬生成的段落內容或 Prompt 內容
        ticker: 股票代碼
        
    Returns:
        JSON 格式的驗證報告
    """
    # 1. 字數檢查
    # 移除空白後的字數
    clean_content = content.strip()
    char_count = len(clean_content)
    
    length_valid = 80 <= char_count <= 120
    
    # 2. 數值驗證
    # 呼叫 prompt_verifier
    verify_result_json = verify_prompt_data(ticker, content)
    verify_result = json.loads(verify_result_json)
    
    final_result = {
        "is_valid": length_valid and verify_result["verified"],
        "checks": {
            "length": {
                "valid": length_valid,
                "current": char_count,
                "required": "80-120"
            },
            "data_source": verify_result,
            "hygiene": {
                "valid": len(verify_result.get("suspicious_alerts", [])) == 0,
                "alerts": verify_result.get("suspicious_alerts", [])
            }
        }
    }
    
    return json.dumps(final_result, ensure_ascii=False, indent=2)
