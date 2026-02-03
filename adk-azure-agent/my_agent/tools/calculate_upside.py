from typing import Dict, Union
import json
from ..mcp_toolset_wrapper import _mcp_logger

def calculate_upside_potential(current_price: float, target_price: float, ticker: str) -> str:
    """
    計算股價上漲空間並記錄至 MCP Log 以供驗證器使用
    
    Args:
        current_price: 當前股價
        target_price: 目標價
        ticker: 股票代碼 (e.g. 2330.TW)
        
    Returns:
        JSON 字串，包含計算結果 (upside_percentage)
    """
    try:
        if current_price <= 0:
            return json.dumps({"error": "Current price must be positive"}, ensure_ascii=False)
            
        upside = ((target_price - current_price) / current_price) * 100
        upside_rounded = round(upside, 2)
        
        result = {
            "ticker": ticker,
            "current_price": current_price,
            "target_price": target_price,
            "upside_percentage": upside_rounded,
            "message": f"{upside_rounded}%"
        }
        
        # 手動觸發 Log 記錄，因為這是本地 python 函數而非 MCP 工具
        # 這樣 validate_key_message 才能抓到這個數字的來源
        _mcp_logger.log_call(
            tool_name="calculate_upside_potential",
            arguments={
                "current_price": current_price,
                "target_price": target_price,
                "ticker": ticker
            },
            response=result,
            success=True,
            duration_ms=0  # Local call, negligible
        )
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error calculating upside: {str(e)}"
        _mcp_logger.log_call(
            tool_name="calculate_upside_potential",
            arguments={
                "current_price": current_price,
                "target_price": target_price,
                "ticker": ticker
            },
            response=None,
            success=False,
            error=error_msg,
            duration_ms=0
        )
        return json.dumps({"error": error_msg}, ensure_ascii=False)
