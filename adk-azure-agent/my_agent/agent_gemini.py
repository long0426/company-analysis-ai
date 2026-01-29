from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

# ============================================================================
# 方案 2：切換到 Gemini（如果方案 1 失敗）
# ============================================================================

def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 使用 Gemini（無嚴格內容過濾）
model = LiteLlm(model="gemini/gemini-2.0-flash-exp")

root_agent = Agent(
    model=model,
    name='gemini_agent',
    description='財務資訊查詢助手',  # Gemini 支援繁體中文
    tools=[get_current_time]
)

print("✓ Gemini agent loaded")
