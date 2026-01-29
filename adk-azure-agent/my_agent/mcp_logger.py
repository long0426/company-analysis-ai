"""
MCP Tool 呼叫記錄工具 - JSON 格式
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class McpCallLogger:
    """記錄 MCP 工具呼叫到 JSON 檔案"""
    
    def __init__(self, log_dir: str = None):
        # 預設存放在 my_agent/mcp_logs/
        if log_dir is None:
            current_dir = Path(__file__).parent
            log_dir = current_dir / "mcp_logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 建立當次執行的 log 檔案
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"mcp_calls_{timestamp}.jsonl"
        
        print(f"✓ MCP calls will be logged to: {self.log_file}")
    
    def log_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        response: Any,
        success: bool = True,
        error: str = None,
        duration_ms: float = None
    ):
        """
        記錄一次 MCP 工具呼叫
        
        Args:
            tool_name: 工具名稱
            arguments: 呼叫參數
            response: 回應內容
            success: 是否成功
            error: 錯誤訊息（如果失敗）
            duration_ms: 執行時間（毫秒）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "response": self._serialize_response(response),
            "success": success,
            "error": error,
            "duration_ms": duration_ms
        }
        
        # 追加寫入 JSONL 格式（每行一個 JSON）
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def _serialize_response(self, response: Any) -> Any:
        """將回應轉換為可序列化的格式"""
        if response is None:
            return None
        
        # 如果是字串，直接返回
        if isinstance(response, (str, int, float, bool)):
            return response
        
        # 如果是 dict 或 list，遞迴處理
        if isinstance(response, dict):
            return {k: self._serialize_response(v) for k, v in response.items()}
        
        if isinstance(response, list):
            return [self._serialize_response(item) for item in response]
        
        # 如果有 __dict__ 屬性，轉換為 dict
        if hasattr(response, '__dict__'):
            return self._serialize_response(response.__dict__)
        
        # 其他情況轉為字串
        return str(response)


# 全域 logger 實例
_mcp_logger = None


def get_mcp_logger() -> McpCallLogger:
    """取得全域 MCP Logger"""
    global _mcp_logger
    if _mcp_logger is None:
        _mcp_logger = McpCallLogger()
    return _mcp_logger
