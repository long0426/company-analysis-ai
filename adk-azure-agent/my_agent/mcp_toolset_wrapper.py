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
        ticker = arguments.get('ticker', arguments.get('symbol'))

        # 若無 ticker，嘗試從 query 提取 (針對 web_search 工具)
        if not ticker and 'query' in arguments:
            query = arguments['query']
            if isinstance(query, str) and query.strip():
                # 取第一個詞作為識別 (例如 "Apple partnerships" -> "Apple")
                # 雖不完美，但比 "unknown" 更能識別
                ticker = query.strip().split()[0]
        
        if not ticker:
            ticker = 'unknown'
        
        # 動態建立檔案（包含 tool_name 和 ticker）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 簡化 tool_name (移除 prefix 如 search_, yf_ 等，如果有的話)
        safe_tool_name = tool_name.replace('/', '_').replace('\\', '_')
        
        # 新結構: mcp_logs/{ticker}/{tool_name}_{timestamp}.jsonl
        # 1. 決定目錄
        if ticker == 'unknown':
             target_dir = self.log_dir
             file_name = f"mcp_unknown_{safe_tool_name}_{timestamp}.jsonl"
        else:
             target_dir = self.log_dir / ticker
             target_dir.mkdir(exist_ok=True)
             file_name = f"{safe_tool_name}_{timestamp}.jsonl"
             
        log_file = target_dir / file_name
        
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


# 全域變數用於追蹤最近一次出現的有效 ticker
_LAST_SEEN_TICKER = "unknown"

def patch_mcp_tool():
    """
    Monkey patch McpTool:
    1. run_async: 攔截執行以記錄 Log，並移除注入的 ticker 參數
    2. _get_declaration: 注入 ticker 參數到工具 Schema，讓 LLM 知道可以傳入
    """
    from google.adk.tools.mcp_tool.mcp_tool import McpTool
    
    # ------------------------------------------------------------------------
    # 1. Patch run_async (執行攔截)
    # ------------------------------------------------------------------------
    original_run_async = McpTool.run_async
    
    async def logged_run_async(self, *, args: dict, tool_context):
        """包裝後的 run_async 方法"""
        global _LAST_SEEN_TICKER
        
        start_time = time.time()
        tool_name = getattr(self, 'name', 'unknown')
        
        # 複製 args 以免修改原始字典影響其他部分
        # 並在此處提取 ticker 用於 Log
        log_args = args.copy()
        
        # 優先嘗試從當前 args 取得 ticker
        current_ticker = log_args.get('ticker', log_args.get('symbol'))
        
        if current_ticker and isinstance(current_ticker, str) and current_ticker.strip():
            # 如果這次有 ticker，更新全域上下文
            _LAST_SEEN_TICKER = current_ticker.strip()
            ticker = _LAST_SEEN_TICKER
        else:
            # 如果這次沒有 ticker (例如 url_fetch)，使用最近一次的上下文
            ticker = _LAST_SEEN_TICKER
        
        # 將最終決定的 ticker 放回 log_args 以便記錄
        log_args['ticker'] = ticker
        
        # 準備傳給實際工具的 args (必須移除注入的 ticker，否則 MCP Server 會報錯)
        execution_args = args.copy()
        if 'ticker' in execution_args:
            del execution_args['ticker']

        try:
            # 呼叫原始方法 (使用淨化過的 args)
            result = await original_run_async(self, args=execution_args, tool_context=tool_context)
            
            # 計算執行時間
            duration_ms = (time.time() - start_time) * 1000
            
            # 記錄成功呼叫 (使用包含 ticker 的 log_args)
            _mcp_logger.log_call(
                tool_name=tool_name,
                arguments=log_args,
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
                arguments=log_args,
                response=None,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
            
            raise

    # ------------------------------------------------------------------------
    # 2. Patch _get_declaration (Schema 注入)
    # ------------------------------------------------------------------------
    original_get_declaration = McpTool._get_declaration
    
    def patched_get_declaration(self):
        """
        攔截工具定義生成，注入 ticker 參數
        """
        schema = original_get_declaration(self)
        
        try:
            # 確認 schema 結構並注入 ticker
            if 'parameters' in schema and 'properties' in schema['parameters']:
                schema['parameters']['properties']['ticker'] = {
                    "type": "string",
                    "description": "The stock ticker symbol associated with this operation (e.g., AAPL). ALWAYS provide this if known, for context tracking."
                }
                # 注意：我們不把 ticker 加到 required，讓它是可選的
        except Exception as e:
            print(f"⚠️ Failed to inject ticker schema for {getattr(self, 'name', 'unknown')}: {e}")
            
        return schema

    # 應用 patches
    McpTool.run_async = logged_run_async
    McpTool._get_declaration = patched_get_declaration
    
    print("✓ MCP Tool logging & schema injection patch applied")
