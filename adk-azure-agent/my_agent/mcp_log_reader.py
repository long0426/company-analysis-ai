"""
MCP Log 讀取工具 - 讀取指定 ticker 的最新 MCP 回覆記錄
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


def read_latest_mcp_response(ticker: str) -> Optional[Dict[str, Any]]:
    """
    讀取指定 ticker 的近期所有 MCP 回覆記錄並彙整
    (Fix: 不再只回傳這新的一個，而是回傳所有近期工具的執行結果彙整)
    
    Args:
        ticker: 股票代碼（例如：2330.TW, AAPL）
    
    Returns:
        彙整後的 Dict，key 為 tool_name，value 為該工具最新的 response
    """
    # MCP logs 目錄
    log_dir = Path(__file__).parent / "mcp_logs"
    
    if not log_dir.exists():
        return None
    
    # 尋找符合 ticker 的所有檔案
    candidate_files = []
    
    # 1. 搜尋 Ticker 專屬目錄 (新結構)
    ticker_dir = log_dir / ticker
    if ticker_dir.exists():
        candidate_files.extend(list(ticker_dir.glob("*.jsonl")))
        
    # 2. 搜尋 Root 目錄 (舊結構 & unknown)
    candidate_files.extend(list(log_dir.glob(f"mcp_{ticker}_*.jsonl")))
    candidate_files.extend(list(log_dir.glob(f"mcp_*_{ticker}_*.jsonl")))
    candidate_files = list(set(candidate_files))
    
    if not candidate_files:
        return None
    
    # 彙整結果的容器
    aggregated_response = {}
    
    # 依時間排序 (舊->新)，確保新的覆蓋舊的
    sorted_files = sorted(candidate_files)
    
    for file_path in sorted_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    continue
                
                # 解析最後一行的 JSON
                last_entry = json.loads(lines[-1])
                tool_name = last_entry.get('tool_name')
                raw_response = last_entry.get('response')
                
                if not tool_name or not raw_response:
                    continue
                
                # 解析 Content
                parsed_content = None
                
                if isinstance(raw_response, dict):
                    if 'content' in raw_response and raw_response['content']:
                        # 從 content[0].text 提取
                        content_text = raw_response['content'][0].get('text', '')
                        if content_text:
                            try:
                                parsed_content = json.loads(content_text)
                            except:
                                parsed_content = content_text
                    elif 'structuredContent' in raw_response:
                        # 從 structuredContent.result 提取
                        result_text = raw_response['structuredContent'].get('result', '')
                        if result_text:
                            try:
                                parsed_content = json.loads(result_text)
                            except:
                                parsed_content = result_text
                
                # 如果無法解析，就用原始的
                if parsed_content is None:
                    parsed_content = raw_response

                # 存入彙整字典 (Key 為工具名稱，確保每個工具只留最新一份)
                aggregated_response[tool_name] = parsed_content
                
        except Exception as e:
            print(f"⚠️ Error reading MCP log {file_path}: {e}")
            continue

    return aggregated_response


def format_mcp_response(response: Dict[str, Any], ticker: str) -> str:
    """
    將 MCP response 格式化為友善的 Markdown 文字（不分類，原始順序）
    
    Args:
        response: MCP response 資料
        ticker: 股票代碼
    
    Returns:
        格式化後的 Markdown 文字
    """
    if not response:
        return f"❌ 找不到 {ticker} 的記錄"
    
    lines = []
    lines.append(f"# 📊 {ticker} 完整股票資訊\n")
    
    # 直接按原始順序顯示所有欄位
    for key, value in response.items():
        if value is None:
            continue
            
        # 格式化不同類型的值
        if isinstance(value, float):
            if key in ['marketCap', 'enterpriseValue', 'totalRevenue', 'totalCash', 'totalDebt', 'grossProfits', 'ebitda', 'freeCashflow', 'operatingCashflow']:
                # 大數字格式化
                if value > 1e12:
                    formatted_value = f"{value/1e12:.2f}T"
                elif value > 1e9:
                    formatted_value = f"{value/1e9:.2f}B"
                elif value > 1e6:
                    formatted_value = f"{value/1e6:.2f}M"
                else:
                    formatted_value = f"{value:,.2f}"
            elif 'Percent' in key or 'percent' in key or 'Yield' in key or 'yield' in key or 'Margins' in key or 'margins' in key:
                # 百分比
                formatted_value = f"{value * 100:.2f}%" if value < 1 else f"{value:.2f}%"
            else:
                formatted_value = f"{value:.4f}" if abs(value) < 1 else f"{value:,.2f}"
        elif isinstance(value, int):
            formatted_value = f"{value:,}"
        elif isinstance(value, list):
            # 展開陣列
            if not value:
                lines.append(f"- **{key}**: []")
                continue
            else:
                lines.append(f"- **{key}**: [{len(value)} 項目]")
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        # 展開物件陣列
                        lines.append(f"  - 項目 {i}:")
                        for sub_key, sub_value in item.items():
                            if isinstance(sub_value, (int, float)):
                                if isinstance(sub_value, int):
                                    lines.append(f"    - {sub_key}: {sub_value:,}")
                                else:
                                    lines.append(f"    - {sub_key}: {sub_value:.2f}")
                            else:
                                lines.append(f"    - {sub_key}: {sub_value}")
                    else:
                        lines.append(f"  - {item}")
                continue
        elif isinstance(value, dict):
            # 展開字典
            lines.append(f"- **{key}**:")
            for sub_key, sub_value in value.items():
                lines.append(f"  - {sub_key}: {sub_value}")
            continue
        else:
            formatted_value = str(value)
        
        lines.append(f"- **{key}**: {formatted_value}")
    
    return "\n".join(lines)


# 測試函數（可選）
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        response = read_latest_mcp_response(ticker)
        print(format_mcp_response(response, ticker))
    else:
        print("Usage: python mcp_log_reader.py <TICKER>")
        print("Example: python mcp_log_reader.py AAPL")
