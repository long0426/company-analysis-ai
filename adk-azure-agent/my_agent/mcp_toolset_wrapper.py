"""
MCP 工具呼叫記錄器 - 攔截實際回覆結果
"""
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class McpCallLogger:
    """記錄 MCP 工具的呼叫參數和回覆結果"""
    
    def __init__(self, log_dir: str = None):
        # 預設存放在 my_agent/mcp_logs/
        if log_dir is None:
            current_dir = Path(__file__).parent
            log_dir = current_dir / "mcp_logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        print(f"✓ MCP responses will be logged to: {self.log_dir}/")
    
    def log_call(
        self,
        tool_name: str,
        arguments: dict,
        response: Any,
        success: bool = True,
        error: str = None,
        duration_ms: float = None
    ):
        """記錄一次 MCP 工具呼叫"""
        # 從 arguments 中提取 ticker（如果有）
        ticker = arguments.get('ticker', arguments.get('symbol', 'unknown'))
        
        # 動態建立檔案（包含 ticker）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"mcp_{ticker}_{timestamp}.jsonl"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "ticker": ticker,
            "arguments": arguments,
            "response": self._serialize(response),
            "success": success,
            "error": error,
            "duration_ms": duration_ms
        }
        
        # 寫入 JSONL 格式
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def _serialize(self, obj: Any) -> Any:
        """將物件序列化為 JSON 可處理的格式"""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        
        if isinstance(obj, (list, tuple)):
            return [self._serialize(item) for item in obj]
        
        if hasattr(obj, '__dict__'):
            return self._serialize(obj.__dict__)
        
        return str(obj)


# 全域 logger
_mcp_logger = McpCallLogger()


def patch_mcp_tool():
    """
    Monkey patch McpTool 的 run_async 方法以記錄呼叫
    """
    from google.adk.tools.mcp_tool.mcp_tool import McpTool
    
    # 保存原始 run_async 方法
    original_run_async = McpTool.run_async
    
    async def logged_run_async(self, *, args: dict, tool_context):
        """包裝後的 run_async 方法"""
        start_time = time.time()
        tool_name = getattr(self, 'name', 'unknown')
        
        try:
            # 呼叫原始方法
            result = await original_run_async(self, args=args, tool_context=tool_context)
            
            # 計算執行時間
            duration_ms = (time.time() - start_time) * 1000
            
            # 記錄成功呼叫
            _mcp_logger.log_call(
                tool_name=tool_name,
                arguments=args,
                response=result,
                success=True,
                duration_ms=duration_ms
            )
            
            return result
            
        except Exception as e:
            # 計算執行時間
            duration_ms = (time.time() - start_time) * 1000
            
            # 記錄失敗呼叫
            _mcp_logger.log_call(
                tool_name=tool_name,
                arguments=args,
                response=None,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
            
            raise
    
    # 應用 patch
    McpTool.run_async = logged_run_async
    print("✓ MCP Tool logging patch applied")
