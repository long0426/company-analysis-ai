import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 定義 Log 目錄位置 (假設在 ../mcp_logs)
LOG_DIR = Path(__file__).parent.parent / "mcp_logs"

def get_recent_logs(ticker: str, minutes: int = 60) -> List[Path]:
    """
    取得最近 X 分鐘內的相關 Log 檔案
    支援舊格式 (mcp_logs/...) 與新格式 (mcp_logs/{ticker}/...)
    """
    if not LOG_DIR.exists():
        return []
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    relevant_files = []
    
    candidate_files = []
    
    # 1. 搜尋 Ticker 專屬目錄 (新結構)
    ticker_dir = LOG_DIR / ticker
    if ticker_dir.exists():
        candidate_files.extend(ticker_dir.glob("*.jsonl"))
        
    # 2. 搜尋 Root 目錄 (舊結構 & unknown)
    # 我們仍需包含 unknown，因為 Web Search 初始階段可能落在這裡
    candidate_files.extend(LOG_DIR.glob("*.jsonl"))
    
    # 遍歷所有候選檔案
    for log_file in candidate_files:
        try:
            # 解析時間
            # 新格式: {tool_name}_{YYYYMMDD_HHMMSS}.jsonl
            # 舊格式: mcp_{ticker}_{...}_{...}.jsonl
            
            parts = log_file.stem.split("_")
            if len(parts) < 2: 
                continue

            file_dt = None
            
            # 嘗試抓取時間字串 (通常在最後)
            # 格式可能是 YYYYMMDD_HHMMSS (2 parts) 或 YYYYMMDDHHMMSS (1 part)
            time_part = ""
            if len(parts[-1]) == 6 and len(parts[-2]) == 8 and parts[-1].isdigit() and parts[-2].isdigit():
                 time_part = parts[-2] + parts[-1]
            elif len(parts[-1]) == 14 and parts[-1].isdigit():
                 time_part = parts[-1]
            
            if time_part:
                file_dt = datetime.strptime(time_part, "%Y%m%d%H%M%S")
            
            if file_dt and file_dt > cutoff_time:
                # 篩選邏輯
                # 1. 如果檔案在 ticker_dir，直接收錄
                if log_file.parent.name == ticker:
                    relevant_files.append(log_file)
                # 2. 如果檔案在 root，檢查檔名是否包含 ticker
                elif log_file.parent == LOG_DIR:
                     if ticker in log_file.name:
                         relevant_files.append(log_file)
                         
        except Exception:
            continue
            
    return sorted(list(set(relevant_files))) # 去重並排序

def _matches_tool(tool_name: str, keywords: List[str]) -> bool:
    """簡易比對工具名稱"""
    if not tool_name:
        return False
    normalized = tool_name.lower()
    return any(keyword in normalized for keyword in keywords)

def analyze_step2_logs(ticker: str, minutes: int = 90) -> Dict[str, Any]:
    """
    檢查最近的 log 是否包含必需的 web_search 與 url_fetch
    用於強迫代理完成步驟 2
    """
    logs = get_recent_logs(ticker, minutes=minutes)
    web_keywords = ["web__search", "web_search", "search_web"]
    fetch_keywords = ["url__fetch", "url_fetch", "fetch_webpage", "fetch_url", "web_fetch_page", "web_fetch"]
    
    web_calls = 0
    fetch_calls = 0
    inspected = []
    
    for log_file in logs:
        inspected.append(log_file.name)
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    tool_name = entry.get("tool_name", "")
                    if _matches_tool(tool_name, web_keywords):
                        web_calls += 1
                    if _matches_tool(tool_name, fetch_keywords):
                        fetch_calls += 1
        except Exception:
            continue
    
    missing = []
    # if web_calls == 0:
    #     missing.append("web_search")
    # if fetch_calls == 0:
    #     missing.append("url_fetch")
    
    # 策略調整：與其強制報錯，不如僅回傳統計資訊，讓驗證主邏輯決定
    # 目前流程已允許不強制執行 Web Search，故此處均為 True
    
    return {
        "web_search_count": web_calls,
        "url_fetch_count": fetch_calls,
        "valid": True, # Always true for now as per new instructions
        "missing": missing,
        "logs_inspected": inspected or [p.name for p in logs]
    }

def flatten_json(y: Any, prefix: str = "") -> Dict[str, Any]:
    """將巢狀 JSON 展平，方便搜尋數值"""
    out = {}
    
    def flatten(x: Any, name: str = ""):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + ".")
        elif isinstance(x, list):
            for i, a in enumerate(x):
                # 限制陣列展開深度，避免過多無用資訊
                if i < 20: 
                    flatten(a, name + str(i) + ".")
        else:
            out[name[:-1]] = x
            
    flatten(y, prefix)
    return out

def extract_data_for_prompt(ticker: str) -> Dict[str, Any]:
    """
    從最近的 mcp_logs 提取所有可用數據
    回傳: {
        "extracted_data": {key: value},
        "source_map": {str(value): source_key},
        "logs_used": [filenames]
    }
    """
    logs = get_recent_logs(ticker)
    extracted = {}
    source_map = {} 
    
    for log_file in logs:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    response = entry.get("response", {})
                    
                    # 嘗試提取有用的內容
                    content_data = None
                    
                    # 1. 嘗試從 structuredContent (Yahoo Finance)
                    if 'structuredContent' in response:
                        res = response['structuredContent'].get('result', '')
                        if isinstance(res, str):
                            try:
                                content_data = json.loads(res)
                            except:
                                content_data = res
                        else:
                            content_data = res
                            
                    # 2. 嘗試從 content[0].text (Web Search / Generic)
                    elif 'content' in response and isinstance(response['content'], list):
                        if len(response['content']) > 0:
                            text = response['content'][0].get('text', '')
                            try:
                                content_data = json.loads(text)
                            except:
                                content_data = text
                    # 3. 嘗試直接解析 response (Local Tools like calculate_upside)
                    elif isinstance(response, (dict, list)):
                        content_data = response
                    
                    if content_data:
                        # 如果是字串(純文字搜尋結果)，不展平，直接作為全文檢索來源
                        if isinstance(content_data, str):
                            try:
                                # 嘗試二次解析 JSON string
                                content_data = json.loads(content_data)
                                flat = flatten_json(content_data)
                                for k, v in flat.items():
                                    if isinstance(v, (int, float, str)):
                                        extracted[k] = v
                                        source_map[str(v)] = f"{log_file.name}:{k}"
                            except:
                                key = f"{log_file.name}:raw_text"
                                extracted[key] = content_data
                        else:
                            flat = flatten_json(content_data)
                            for k, v in flat.items():
                                if isinstance(v, (int, float, str)):
                                    extracted[k] = v
                                    # 記錄來源：檔名 + 欄位
                                    # 注意：不同檔案可能有相同數值，這裡會覆蓋，但至少有一個來源
                                    source_map[str(v)] = f"{log_file.name}:{k}"
                                    
            
        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    # -------------------------------------------------------------------------
    # Cross-Exchange / Suspicious Data Detection
    # -------------------------------------------------------------------------
    suspicious_alerts = []
    
    # Simple heuristics
    # To avoid false positives (e.g. dual listings, benign mentions), we disable this check for now.
    # The agent should rely on the strict ticker log separation instead.
    # if ".TW" in ticker.upper():
    #     foreign_keywords = ["ASX:", "(ASX)", "Australian Securities Exchange", "NYSE:", "NASDAQ:"]
    #     for key, text_content in extracted.items():
    #         if isinstance(text_content, str):
    #             for kw in foreign_keywords:
    #                 if kw in text_content:
    #                     # suspicious_alerts.append(f"⚠️ Detected potential Foreign Exchange data ({kw}) in {key}. Target is {ticker}.")
    #                     pass
                        
    return {
        "ticker": ticker,
        "extracted_data": extracted,
        "source_map": source_map,
        "logs_used": [p.name for p in logs],
        "suspicious_alerts": suspicious_alerts
    }

def verify_prompt_data(ticker: str, prompt_content: str) -> str:
    """
    驗證工具：檢查 prompt 中的數字是否在 mcp_logs 中有來源
    
    Args:
        ticker: 股票代碼
        prompt_content: 擬生成的 Prompt 內容
        
    Returns:
        JSON 字串，包含驗證結果
    """
    
    # --- Helper to log history ---
    def log_verification_history(content: str, result: Dict[str, Any]):
        try:
            # 決定目錄
            target_dir = LOG_DIR / ticker
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            # 檔名格式: tool_name + 時間
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_file = target_dir / f"validate_key_message_{timestamp}.jsonl"
            
            record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "validate_key_message",
                "ticker": ticker,
                "content": content,
                "result": result
            }
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Error logging verification history: {e}")
    # -----------------------------

    data = extract_data_for_prompt(ticker)
    source_map = data["source_map"]
    logs_used = data["logs_used"]
    step2_requirement = analyze_step2_logs(ticker)
    
    # 1. 提取 Prompt 中的所有數字 (包含小數、百分比、金錢符號、千分位逗號)
    # 修改 Regex 以支援千分位 (e.g. 1,800)
    numbers = re.findall(r'-?\d+(?:,\d{3})*(?:\.\d+)?', prompt_content)
    
    matched = []
    unmatched = []
    
    # 為了比對方便，將 extracted values 轉為 float set (where possible)
    float_sources = {}
    for val_str, source in source_map.items():
        try:
            # 移除常見非數字字符
            clean_val = str(val_str).replace(',', '').replace('%', '').replace('$', '')
            f_val = float(clean_val)
            float_sources[f_val] = source
        except:
            continue
            
    # 檢查每個數字
    for num_str in numbers:
        # 移除逗號以便處理
        clean_num_str = num_str.replace(',', '')
        
        # 跳過過短的數字 (如 1, 2 用於列表)
        if len(clean_num_str) == 1: 
            continue
            
        try:
            val = float(clean_num_str)
            found = False
            source = ""
            
            # 策略 A: 直接浮點數匹配
            for src_val, src_path in float_sources.items():
                if abs(src_val - val) < 0.01: # 寬容度
                    found = True
                    source = src_path
                    break
                
            # 策略 B: 百分比匹配 (0.406 -> 40.6)
            if not found:
                for src_val, src_path in float_sources.items():
                    if abs(src_val * 100 - val) < 0.01:
                        found = True
                        source = f"{src_path} (x100%)"
                        break
            
            if found:
                matched.append(f"{num_str} -> {source}")
            else:
                # 可能是計算值 (如上漲空間)
                unmatched.append(num_str)
                
        except:
            continue
    

    suspicious_alerts = data.get("suspicious_alerts", [])
    
    base_valid = len(unmatched) == 0 and len(suspicious_alerts) == 0
    is_valid = base_valid and step2_requirement["valid"]
    
    msg_parts = []
    if len(unmatched) > 0:
        msg_parts.append(f"發現 {len(unmatched)} 個數值缺乏直接來源。")
    if len(suspicious_alerts) > 0:
        msg_parts.append(f"警告：檢測到 {len(suspicious_alerts)} 個可疑資料來源（如外國交易所數據匹配錯誤）。")
    if not step2_requirement["valid"]:
        missing = "、".join(step2_requirement["missing"]) or "web_search/url_fetch"
        msg_parts.append(f"尚未發現必要的步驟 2 工具呼叫（缺少：{missing}）。")
        
    final_message = "驗證通過" if is_valid else " ".join(msg_parts)

    result = {
        "verified": is_valid,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "unmatched_values": unmatched,
        "suspicious_alerts": suspicious_alerts,
        "logs_checked": logs_used,
        "step2_requirement": step2_requirement,
        "message": final_message
    }
    
    log_verification_history(prompt_content, result)
    
    return json.dumps(result, ensure_ascii=False, indent=2)
