#!/usr/bin/env python3
"""
啟動腳本：預載 Yahoo Finance MCP Server

此腳本會在 ADK Web UI 啟動前先下載並啟動 MCP Server，
避免第一次查詢時需要等待 15-20 秒下載套件的問題。

使用方法：
    python3 preload_and_start.py

然後在另一個終端機執行：
    uv run adk web --port 9000
"""

import asyncio
import sys
import os

# 確保可以 import my_agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from my_agent.agent import yfinance_toolset


async def preload_mcp_server():
    """預載 MCP Server"""
    print("\n" + "=" * 70)
    print("🚀 Yahoo Finance MCP Server 預載工具")
    print("=" * 70)
    print("\n📦 正在下載和啟動 MCP Server...")
    print("   （首次執行需要下載 65 個套件，可能需要 15-20 秒）\n")
    
    try:
        # 直接透過 MCP Session Manager 建立連線
        session = await yfinance_toolset._mcp_session_manager.create_session()
        
        # 取得工具列表以驗證連線
        result = await session.list_tools()
        tools_count = len(result.tools) if hasattr(result, 'tools') else 0
        
        print("✅ MCP Server 預載成功！\n")
        print(f"   📊 可用工具數量: {tools_count}")
        
        if hasattr(result, 'tools') and result.tools:
            print("\n   🔧 工具列表:")
            for i, tool in enumerate(result.tools[:5], 1):
                print(f"      {i}. {tool.name}")
            if tools_count > 5:
                print(f"      ... 及其他 {tools_count - 5} 個工具")
        
        print("\n" + "=" * 70)
        print("✨ MCP Server 已就緒並快取！")
        print("=" * 70)
        print("\n💡 下一步:")
        print("   現在可以啟動 ADK Web UI（在另一個終端機）：")
        print("   \u001b[1m\u001b[32muv run adk web --port 9000\u001b[0m")
        print("\n   第一次查詢將會非常快速（< 5 秒）\n")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ MCP Server 預載失敗\n")
        print(f"   錯誤訊息: {e}\n")
        print("   💡 提示：")
        print("      仍然可以啟動 Web UI，第一次查詢時會自動啟動 MCP Server")
        print("      只是會需要等待 15-20 秒\n")
        print("=" * 70)
        return False


def main():
    """主程式"""
    try:
        asyncio.run(preload_mcp_server())
    except KeyboardInterrupt:
        print("\n\n⚠️  已取消預載")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 執行錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
