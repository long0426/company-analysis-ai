from google.adk.tools import ToolContext

def set_discovery_context(query: str, tool_context: ToolContext = None) -> str:
    """
    設定 Discovery Agent 的搜尋目標 (Query)。
    Orchestrator 必須在轉移給 Discovery Agent 之前呼叫此工具。
    
    Args:
        query: 用戶的原始查詢 (例如 "分析台積電" 或 "2330")
        tool_context: 自動注入的 Context
    """
    if tool_context and tool_context.session:
        tool_context.session.state["discovery_query"] = query
        return f"✅ Discovery Context Set: {query}"
    return "❌ Failed to set context (No Session)"

def set_analysis_context(ticker: str, tool_context: ToolContext = None) -> str:
    """
    設定 Analysis Agent 的目標 Ticker。
    Orchestrator 必須在轉移給 Analysis Agent 之前呼叫此工具。
    
    Args:
        ticker: 目標股票代碼 (例如 "2330.TW")
        tool_context: 自動注入的 Context
    """
    if tool_context and tool_context.session:
        tool_context.session.state["analysis_ticker"] = ticker
        return f"✅ Analysis Context Set: {ticker}"
    return "❌ Failed to set context (No Session)"
