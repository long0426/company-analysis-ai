#!/usr/bin/env python3
"""
Agent 回覆比對工具

用途：比對 Agent 的回覆內容與原始 MCP JSON 是否一致
"""
import json
import sys
from pathlib import Path


def load_latest_mcp_json(ticker: str) -> dict:
    """讀取最新的 MCP JSON 記錄"""
    log_dir = Path(__file__).parent / "my_agent" / "mcp_logs"
    pattern = f"mcp_{ticker}_*.jsonl"
    matching_files = list(log_dir.glob(pattern))
    
    if not matching_files:
        print(f"❌ 找不到 {ticker} 的 MCP log 檔案")
        sys.exit(1)
    
    latest_file = sorted(matching_files)[-1]
    print(f"📁 讀取 MCP log: {latest_file.name}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        entry = json.loads(lines[-1])
        
    # 提取實際的股票資料
    raw_response = entry['response']
    content_text = raw_response['content'][0]['text']
    stock_data = json.loads(content_text)
    
    return stock_data


def load_agent_response(response_file: str) -> dict:
    """讀取 Agent 回覆的 JSON（從檔案）"""
    with open(response_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除 code block 標記（如果有）
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]  # 移除 ```json
    if content.startswith('```'):
        content = content[3:]  # 移除 ```
    if content.endswith('```'):
        content = content[:-3]  # 移除結尾的 ```
    
    content = content.strip()
    
    return json.loads(content)


def compare_json(original: dict, agent_response: dict) -> dict:
    """比對兩個 JSON 物件"""
    result = {
        'identical': False,
        'missing_keys': [],
        'extra_keys': [],
        'different_values': [],
        'stats': {
            'original_keys': len(original.keys()),
            'response_keys': len(agent_response.keys()),
            'identical_keys': 0
        }
    }
    
    # 檢查缺失的 key
    for key in original.keys():
        if key not in agent_response:
            result['missing_keys'].append(key)
    
    # 檢查多出來的 key
    for key in agent_response.keys():
        if key not in original:
            result['extra_keys'].append(key)
    
    # 檢查值是否相同
    for key in original.keys():
        if key in agent_response:
            if original[key] != agent_response[key]:
                result['different_values'].append({
                    'key': key,
                    'original': original[key],
                    'response': agent_response[key]
                })
            else:
                result['stats']['identical_keys'] += 1
    
    # 判斷是否完全一致
    result['identical'] = (
        len(result['missing_keys']) == 0 and
        len(result['extra_keys']) == 0 and
        len(result['different_values']) == 0
    )
    
    return result


def print_comparison_report(result: dict):
    """輸出比對報告"""
    print("\n" + "=" * 60)
    print("📊 比對報告")
    print("=" * 60)
    
    # 統計資訊
    stats = result['stats']
    print(f"\n📈 統計：")
    print(f"  - 原始 JSON 欄位數：{stats['original_keys']}")
    print(f"  - Agent 回覆欄位數：{stats['response_keys']}")
    print(f"  - 相同欄位數：{stats['identical_keys']}")
    
    # 結果
    if result['identical']:
        print(f"\n✅ 完全一致！Agent 回覆的內容與原始 JSON 完全相同。")
    else:
        print(f"\n❌ 發現差異！")
        
        if result['missing_keys']:
            print(f"\n⚠️ 遺漏的欄位 ({len(result['missing_keys'])} 個)：")
            for key in result['missing_keys'][:10]:  # 只顯示前 10 個
                print(f"  - {key}")
            if len(result['missing_keys']) > 10:
                print(f"  ... 還有 {len(result['missing_keys']) - 10} 個")
        
        if result['extra_keys']:
            print(f"\n⚠️ 多出來的欄位 ({len(result['extra_keys'])} 個)：")
            for key in result['extra_keys'][:10]:
                print(f"  - {key}")
            if len(result['extra_keys']) > 10:
                print(f"  ... 還有 {len(result['extra_keys']) - 10} 個")
        
        if result['different_values']:
            print(f"\n⚠️ 值不同的欄位 ({len(result['different_values'])} 個)：")
            for item in result['different_values'][:5]:
                print(f"  - {item['key']}:")
                print(f"    原始: {item['original']}")
                print(f"    回覆: {item['response']}")
            if len(result['different_values']) > 5:
                print(f"  ... 還有 {len(result['different_values']) - 5} 個")
    
    print("\n" + "=" * 60)


def main():
    """主程式"""
    if len(sys.argv) < 3:
        print("使用方式：")
        print("  python compare_agent_response.py <TICKER> <RESPONSE_FILE>")
        print("\n範例：")
        print("  1. 先從 Web UI 複製 Agent 的回覆，存到 agent_response.json")
        print("  2. python compare_agent_response.py AAPL agent_response.json")
        sys.exit(1)
    
    ticker = sys.argv[1]
    response_file = sys.argv[2]
    
    print(f"🔍 開始比對 {ticker} 的資料...")
    
    # 讀取原始 JSON
    original_json = load_latest_mcp_json(ticker)
    print(f"✓ 原始 JSON 已讀取 ({len(original_json.keys())} 個欄位)")
    
    # 讀取 Agent 回覆
    try:
        agent_json = load_agent_response(response_file)
        print(f"✓ Agent 回覆已讀取 ({len(agent_json.keys())} 個欄位)")
    except Exception as e:
        print(f"❌ 讀取 Agent 回覆失敗：{e}")
        sys.exit(1)
    
    # 比對
    result = compare_json(original_json, agent_json)
    
    # 輸出報告
    print_comparison_report(result)
    
    # 回傳狀態碼
    sys.exit(0 if result['identical'] else 1)


if __name__ == "__main__":
    main()
