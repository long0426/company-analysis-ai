import json
import os
import datetime
import logging

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams

from google.adk.tools import FunctionTool
from mcp.client.stdio import StdioServerParameters
from google.adk.models import LlmRequest
from google.genai import types

from .tools.instruction_reader import instruction_reader_tool
from .tools.yahoo_finance_tool import yahoo_finance_tool

# 設定 Logger
logger = logging.getLogger("stock_agent")
logger.setLevel(logging.INFO)

# ... (omitting intermediate code, focus on load_instructions modification)

def load_instructions(
    instruction_dir=os.path.join(os.path.dirname(__file__), "instructions")
):
    """
    動態載入核心 instruction 文件 (Slim Mode)
    僅載入 agent_execution.md (憲法) 和 00_master_orchestrator (地圖)。
    其餘詳細指南需透過 read_instruction_manual 工具按需讀取。
    """
    instructions = []
    
    if not os.path.exists(instruction_dir):
        logger.warning(f"Warning: {instruction_dir} not found.")
        return "You are a professional Stock Analyst Agent."
    
    # 1. 載入 agent_execution.md (執行配置/憲法)
    exec_config = os.path.join(instruction_dir, "agent_execution.md")
    if os.path.exists(exec_config):
        try:
            with open(exec_config, "r", encoding="utf-8") as f:
                content = f.read()
                _, content = parse_frontmatter(content)
                instructions.append(content)
            logger.info("✅ Loaded Core: agent_execution.md")
        except Exception as e:
            logger.error(f"⚠️ Failed to load agent_execution.md: {e}")
            
    # 2. 載入 00_master_orchestrator_*.md (主控編排器/地圖)
    # 尋找 00_ 開頭的文件
    master_file = None
    for f in os.listdir(instruction_dir):
        if f.startswith("00_") and f.endswith(".md"):
            master_file = f
            break
            
    if master_file:
        try:
            filepath = os.path.join(instruction_dir, master_file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                _, content = parse_frontmatter(content)
                instructions.append(content)
            logger.info(f"✅ Loaded Core: {master_file}")
        except Exception as e:
            logger.error(f"⚠️ Failed to load {master_file}: {e}")
            
    # 3. 添加動態載入說明與可用模組清單
    instructions.append("""
---
# 📚 知識庫使用說明 (Dynamic Context Loading)

為了保持思維清晰，系統**未載入**所有的詳細寫作指南 (Writing Guides)。
您必須在執行特定任務前，使用工具 `read_instruction_manual` 查閱對應的操作手冊。

**可用模組/手冊清單 (Available Manuals):**
""")
    
    # 動態生成模組清單 (現在包含從 Markdown 解析出的 description)
    modules = extract_modules_from_instructions(instruction_dir)
    for module_id, info in sorted(modules.items(), key=lambda x: x[1]['order']):
        instructions.append(f"### {info['name']} (ID: `{module_id}`)")
        # 顯示關鍵字/別名
        if info['aliases']:
            instructions.append(f"- **關鍵字**: {', '.join(info['aliases'][:3])}")
        # 顯示解析出的用途說明 (這是關鍵，替代了原本硬編碼的建議)
        if info['description']:
            instructions.append(f"- **用途/時機**: {info['description']}")
        instructions.append("") # 空行分隔

    instructions.append("**請養成「先查書，再做事」的習慣，確實查閱對應手冊以符合規範！**")

    result = "\n\n".join(instructions)
    
    # [DEBUG] Log System Prompt to file
    try:
        log_dir = os.path.join(instruction_dir, "../logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"debug_system_prompt_{timestamp}.md")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(result)

        logger.info(f"📝 System Prompt logged to: {log_file}")
    except Exception as e:
        logger.error(f"⚠️ Failed to log system prompt: {e}")

    return result


# ... (omitting intermediate code) ...


def reload_agent():
    """
    重新載入 Agent（開發環境使用）
    
    Returns:
        Agent: 新的 Agent 實例
    """
    global root_agent
    
    print("\n" + "="*60)
    print("🔄 Reloading Agent with fresh instructions...")
    print("="*60 + "\n")
    
    # 載入 MCP 工具
    mcp_tools = load_mcp_tools()
    
    # 重新創建 Agent
    root_agent = Agent(
        model=LiteLlm(model="azure/gpt-4o"),
        name="stock_analyst",
        description="""
        您是一位專業的投資分析師。
    
        **工作模式變更通知**：
        為了提升準確度，詳細的寫作指南不再預先載入。
        您必須利用 `read_instruction_manual` 工具，採取「按需查閱 (Just-in-Time Learning)」的策略。
        
        **默認行為**：
        1. 收到股票代號 (如 TSMC)。
        2. 閱讀 `00_master_orchestrator.md` (已載入) 了解整體流程。
        3. **Action Phase**: 調用 `get_stock_info` 獲取數據。
        4. **Learning Phase**: 調用 `read_instruction_manual('part_a_writing_guide')` 等工具，複習寫作規範。
        5. **Execution Phase**: 嚴格按照剛讀到的規範與 `agent_execution.md` 的要求撰寫報告。
        
        請嚴格遵循 agent_execution.md 與 master_orchestrator.md 中定義的完整執行流程。
        遇到股票代號輸入時，**嚴禁**僅給出簡單摘要，必須生成完整報告。
        所有輸出必須使用繁體中文。
        """,
        tools=mcp_tools + [yahoo_finance_tool, instruction_reader_tool],
        static_instruction=get_instructions(force_reload=True),
    )
    
    logger.info("\n" + "="*60)
    logger.info("🔄 Reloading Agent with fresh instructions...")
    logger.info("="*60 + "\n")
    return root_agent


def load_mcp_tools(config_path="mcp_servers.json"):
    """
    從配置檔案載入 MCP 工具。

    Args:
        config_path (str): MCP 配置檔案路徑

    Returns:
        list: MCP 工具清單
    """
    tools = []

    # 確保使用絕對路徑
    if not os.path.isabs(config_path):
        # 從專案根目錄尋找配置檔案
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        config_path = os.path.join(project_root, config_path)

    logger.info(f"🔍 Looking for MCP config at: {config_path}")

    if not os.path.exists(config_path):
        logger.warning(f"Warning: {config_path} not found. Skipping MCP tools.")
        return tools

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        logger.info(f"📄 Found {len(config.get('mcpServers', {}))} MCP server(s) in config")

        for name, params in config.get("mcpServers", {}).items():
            logger.info(f"Loading MCP tool: {name}")
            logger.info(f"  Command: {params.get('command')} {' '.join(params.get('args', []))}")

            try:
                stdio_params = StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=params.get("command"),
                        args=params.get("args", []),
                        env=params.get("env"),
                    )
                )
                tools.append(
                    McpToolset(
                        connection_params=stdio_params,
                        tool_name_prefix=params.get("tool_name_prefix", f"{name}_"),
                    )
                )
                logger.info(f"✅ Loaded: {name}")

            except Exception as tool_error:
                logger.error(f"❌ Failed to load {name}: {tool_error}")
                import traceback
                traceback.print_exc()
                # 繼續載入其他工具，不要因為一個失敗就全部中斷

    except Exception as e:
        logger.error(f"⚠️ Error loading MCP config: {e}")
        import traceback
        traceback.print_exc()

    logger.info(f"📊 Total MCP tools loaded: {len(tools)}")
    return tools


# ============================================================================
# Instruction Loader with Dynamic Module Detection
# ============================================================================

import re
from typing import Dict, Any, Tuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("⚠️ Warning: pyyaml not installed. Frontmatter parsing disabled.")
    logger.warning("   Install with: uv add pyyaml")


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    解析 YAML frontmatter
    
    Args:
        content: 文件內容
    
    Returns:
        (frontmatter_dict, content_without_frontmatter)
    """
    if not YAML_AVAILABLE:
        return {}, content
    
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if match:
        yaml_content, markdown_content = match.groups()
        try:
            frontmatter = yaml.safe_load(yaml_content)
            return frontmatter or {}, markdown_content
        except yaml.YAMLError as e:
            logger.warning(f"⚠️ Warning: Failed to parse YAML frontmatter: {e}")
            return {}, content
    
    return {}, content


def parse_markdown_metadata(content: str) -> Dict[str, Any]:
    """
    從 Markdown 內容中解析列表式元數據 (Fallback for missing YAML)
    
    尋找類似以下的模式:
    - **key**: value
    """
    metadata = {}
    # 查找所有 - **Key**: Value 格式的行 (只在文件前 50 行查找)
    lines = content.split('\n')[:50]
    
    for line in lines:
        match = re.match(r'^[-*]\s+\*\*([^*\n]+)\*\*:\s*(.+)$', line.strip())
        if match:
            key = match.group(1).lower()
            value = match.group(2).strip()
            
            # 映射常見鍵名到標準字段
            if key in ['用途', 'purpose', 'description', '說明']:
                metadata['description'] = value
            elif key in ['name', '名稱', 'title']:
                metadata['name'] = value
            elif key in ['alias', 'aliases', '別名']:
                metadata['aliases'] = [a.strip() for a in value.split(',')]
                
    return metadata


def extract_modules_from_instructions(instruction_dir: str) -> Dict[str, Dict]:
    """
    從 instructions 目錄自動識別可用模組
    優先解析 YAML frontmatter，失敗則嘗試解析 Markdown metadata
    """
    modules = {}
    # 匹配: 數字_模組ID_其他.md
    pattern = re.compile(r'(\d+)_([a-z_]+)(?:_(.+))?\.md')
    
    # 預設別名庫 (僅作後備)
    DEFAULT_ALIASES = {
        'master_orchestrator': ['主控編排器', 'orchestrator'],
        'include_all': ['全部', 'all'],
    }
    
    if not os.path.exists(instruction_dir):
        return modules
    
    for filename in os.listdir(instruction_dir):
        if filename == 'agent_execution.md':
            continue
            
        match = pattern.match(filename)
        if match:
            order = match.group(1)
            module_id = match.group(2)
            filepath = os.path.join(instruction_dir, filename)
            
            module_info = {}
            description = ""
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 1. 嘗試 YAML 解析
                frontmatter, _ = parse_frontmatter(content)
                if frontmatter and 'module' in frontmatter:
                    module_info = frontmatter.get('module', {})
                    description = module_info.get('description', '')
                else:
                    # 2. 嘗試 Markdown 解析
                    md_metadata = parse_markdown_metadata(content)
                    module_info = md_metadata
                    description = md_metadata.get('description', '')
                    
            except Exception as e:
                logger.warning(f"⚠️ Warning: Failed to read {filename}: {e}")
            
            # 生成預設名稱
            default_name = module_id.replace('_', ' ').title()
            
            # 合併別名 (預設別名 + 文件中定義的別名)
            aliases = DEFAULT_ALIASES.get(module_id, [])
            if 'aliases' in module_info:
                if isinstance(module_info['aliases'], list):
                    aliases.extend(module_info['aliases'])
                else:
                    aliases.append(module_info['aliases'])
            
            modules[module_id] = {
                'file': filename,
                'order': int(order),
                'path': filepath,
                'name': module_info.get('name', default_name),
                'aliases': list(set(aliases)), # 去重
                'word_count': module_info.get('word_count', {}),
                'description': description, # 這是關鍵，來自 "用途"
                'optional': module_info.get('optional', True),
            }
    
    return modules


def load_instructions(
    instruction_dir=os.path.join(os.path.dirname(__file__), "instructions")
):
    """
    動態載入所有 instruction 文件
    
    Args:
        instruction_dir: instruction 文件目錄路徑
    
    Returns:
        str: 組合後的完整指令內容
    """
    instructions = []
    
    # 檢查指令目錄是否存在
    if not os.path.exists(instruction_dir):
        logger.warning(f"Warning: {instruction_dir} not found.")
        return """
        You are a professional Stock Analyst Agent.
        Your goal is to provide insightful analysis of stock information provided by the user.
        
        **Constraints:** 
        1. You MUST output your final response in **Traditional Chinese (繁體中文)**.
        """
    
    # 1. 優先載入 agent_execution.md (執行配置)
    exec_config = os.path.join(instruction_dir, "agent_execution.md")
    if os.path.exists(exec_config):
        try:
            with open(exec_config, "r", encoding="utf-8") as f:
                content = f.read()
                # 移除 frontmatter (如果有)
                _, content = parse_frontmatter(content)
                instructions.append(content)
            logger.info("✅ Loaded: agent_execution.md")
        except Exception as e:
            logger.error(f"⚠️ Failed to load agent_execution.md: {e}")
    
    # 2. 載入所有其他 .md 文件 (按檔名排序)
    files = sorted([
        f for f in os.listdir(instruction_dir) 
        if f.endswith(".md") and f != "agent_execution.md"
    ])
    
    for filename in files:
        filepath = os.path.join(instruction_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # 移除 frontmatter，僅保留 markdown 內容
                _, content = parse_frontmatter(content)
                instructions.append(content)
            logger.info(f"✅ Loaded: {filename}")
        except Exception as e:
            logger.error(f"⚠️ Failed to load {filename}: {e}")
    
    # 3. 自動生成模組清單說明（包含別名資訊）
    modules = extract_modules_from_instructions(instruction_dir)
    module_info = "\n\n---\n\n# 🔍 系統已識別的模組\n\n"
    module_info += "本系統自動掃描 instructions 目錄並解析 frontmatter，識別以下可用模組:\n\n"
    
    for module_id, info in sorted(modules.items(), key=lambda x: x[1]['order']):
        module_info += f"## {info['name']} ({module_id})\n\n"
        module_info += f"- **文件**: {info['file']}\n"
        if info['description']:
            module_info += f"- **說明**: {info['description']}\n"
        if info['aliases']:
            aliases_str = '、'.join(f'"{a}"' for a in info['aliases'])
            module_info += f"- **別名**: {aliases_str}\n"
        if info['word_count']:
            wc = info['word_count']
            if 'min' in wc and 'max' in wc:
                module_info += f"- **字數**: {wc['min']}-{wc['max']} 字\n"
        module_info += "\n"
    
    module_info += "用戶可以使用模組名稱或任何別名來選擇性生成任意模組組合。\n"
    
    logger.info(f"\n📊 Total modules detected: {len(modules)}")
    for module_id, info in sorted(modules.items(), key=lambda x: x[1]['order']):
        aliases = ', '.join(info['aliases'][:3])  # 顯示前3個別名
        logger.info(f"   - {info['name']}: {aliases}...")
    
    # 組合所有內容
    result = "\n\n---\n\n".join(instructions) + module_info
    logger.info(f"\n📝 Total instruction length: {len(result)} characters")
    
    return result




# ============================================================================
# Agent Configuration with Caching and Reload Support
# ============================================================================

# 全局緩存
_instruction_cache = None
_instruction_mtime = {}  # 儲存文件的修改時間


def get_instruction_files_mtime(instruction_dir):
    """獲取所有 instruction 文件的修改時間"""
    mtimes = {}
    if not os.path.exists(instruction_dir):
        return mtimes
    
    for filename in os.listdir(instruction_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(instruction_dir, filename)
            try:
                mtimes[filename] = os.path.getmtime(filepath)
            except OSError:
                pass
    
    return mtimes


def has_instructions_changed(instruction_dir):
    """檢查 instruction 文件是否有變化"""
    global _instruction_mtime
    
    current_mtimes = get_instruction_files_mtime(instruction_dir)
    
    # 第一次檢查或文件數量變化
    if not _instruction_mtime or len(_instruction_mtime) != len(current_mtimes):
        return True
    
    # 檢查每個文件的修改時間
    for filename, mtime in current_mtimes.items():
        if filename not in _instruction_mtime or _instruction_mtime[filename] != mtime:
            return True
    
    return False


def get_instructions(
    force_reload: bool = False,
    auto_detect_changes: bool = False,
    instruction_dir=None
):
    """
    獲取 instructions（帶緩存支持）
    
    Args:
        force_reload: 強制重新載入，忽略緩存
        auto_detect_changes: 自動偵測文件變化，若有變化則重新載入
        instruction_dir: instruction 文件目錄路徑
    
    Returns:
        str: 組合後的完整指令內容
    """
    global _instruction_cache, _instruction_mtime
    
    if instruction_dir is None:
        instruction_dir = os.path.join(os.path.dirname(__file__), "instructions")
    
    # 檢查是否需要重新載入
    need_reload = (
        force_reload or 
        _instruction_cache is None or
        (auto_detect_changes and has_instructions_changed(instruction_dir))
    )
    
    if need_reload:
        logger.info("🔄 Reloading instructions...")
        _instruction_cache = load_instructions(instruction_dir)
        _instruction_mtime = get_instruction_files_mtime(instruction_dir)
    else:
        logger.info("✅ Using cached instructions")
    
    return _instruction_cache


def reload_agent():
    """
    重新載入 Agent（開發環境使用）
    
    Returns:
        Agent: 新的 Agent 實例
    """
    global root_agent
    
    logger.info("\n" + "="*60)
    logger.info("🔄 Reloading Agent with fresh instructions...")
    logger.info("="*60 + "\n")
    
    # 載入 MCP 工具
    mcp_tools = load_mcp_tools()
    
    # 重新創建 Agent
    root_agent = Agent(
        model=LiteLlm(model="azure/gpt-4o"),
        name="stock_analyst",
        description="""
        您是一位專業的投資分析師。
        
        系統會自動識別可用的分析模組（通過解析 instruction 文件的 frontmatter），
        用戶可以使用模組名稱或別名選擇需要的模組組合。
        
        默認行為：生成所有已識別的模組
        靈活選擇：用戶可指定特定模組（例如:"只要券商報告"、"忽略附錄"等）
        
        請嚴格遵循 system instructions 中定義的完整執行流程與格式要求。
        所有輸出必須使用繁體中文。
        
        您可以使用以下工具：
        - get_stock_info: 獲取股票基本資訊、財務數據和新聞
        - search_*: 搜尋網路上的財經新聞、產業分析文章
        - fetch_*: 抓取特定網頁的詳細內容
        """,
        tools=mcp_tools + [yahoo_finance_tool],
        static_instruction=get_instructions(force_reload=True),
    )
    
    logger.info("\n✅ Agent reloaded successfully!\n")
    return root_agent


# ============================================================================
# Agent Factory & Pipeline Execution (New Architecture)
# ============================================================================

from typing import TypedDict, List, Optional

class AnalysisContext(TypedDict):
    """分析上下文：在流水線各階段間傳遞的狀態"""
    ticker: str
    company_name: str
    report_date: str
    analysis_start_date: str
    analysis_end_date: str
    data_source: str
    analysis_angles: List[str]
    report_type: str
    # 儲存中間產物
    part_a_content: Optional[str]
    part_b_content: Optional[str]
    appendix_content: Optional[str]

def resolve_instruction_file(instruction_dir: str, filename: str) -> str:
    """
    動態解析 Instruction 檔案路徑 (支援版本號自動匹配)
    
    規則：
    1. 若精確匹配到檔案，直接回傳。
    2. 若無，則嘗試匹配 "base_name" + "_v*.md"。
    3. 取字母排序最大的版本 (latest version)。
    """
    # 1. 直接匹配
    exact_path = os.path.join(instruction_dir, filename)
    if os.path.exists(exact_path):
        return exact_path
        
    # 2. 模糊匹配版本
    base_name = filename.replace('.md', '')
    candidates = []
    
    if os.path.exists(instruction_dir):
        for f in os.listdir(instruction_dir):
            if f.startswith(base_name) and f.endswith(".md"):
                candidates.append(f)
                
    if candidates:
        # 排序取最新版 (v3.4.0 > v3.3.0)
        best_match = sorted(candidates)[-1]
        logger.info(f"🔗 Resolved '{filename}' to '{best_match}'")
        return os.path.join(instruction_dir, best_match)
        
    logger.warning(f"⚠️ Instruction file not found: {filename}")
    return exact_path # Return original path to let it fail gracefully later

def create_stage_agent(
    stage_name: str,
    instruction_files: List[str],
    description_override: str = "",
    tools: List[any] = None,
    include_base_instructions: bool = True
) -> Agent:
    """
    Agent Factory: 創建特定階段專用的輕量級 Agent
    
    Args:
        stage_name: 階段名稱 (用於 Log)
        instruction_files: 需要載入的指令檔案列表 (e.g., ['04_part_a_writing_guide.md'])
        description_override: 該 Agent 的專屬角色說明
        tools: 該 Agent 可使用的工具列表
        include_base_instructions: 是否包含 agent_execution.md (預設 True)
    """
    logger.info("🏭 Creating Agent for " + stage_name + "...")
    
    # 1. 基礎指令 (可選包含 agent_execution.md)
    base_instructions = []
    instruction_dir = os.path.join(os.path.dirname(__file__), "instructions")
    
    if include_base_instructions:
        # 讀取 agent_execution.md
        exec_config = os.path.join(instruction_dir, "agent_execution.md")
        if os.path.exists(exec_config):
            with open(exec_config, "r", encoding="utf-8") as f:
                content = f.read()
                _, content = parse_frontmatter(content)
                base_instructions.append(content)
            
    # 2. 階段特定指令
    for fname in instruction_files:
        if not fname.endswith(".md"): 
            fname += ".md"
            
        # [Fix] 使用動態解析，不再寫死版本號
        fpath = resolve_instruction_file(instruction_dir, fname)
        
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                _, content = parse_frontmatter(content)
                base_instructions.append(content)
        else:
            logger.warning(f"⚠️ Instruction file not found: {fname}")

    combined_instructions = "\n\n---\n\n".join(base_instructions)
    
    # 3. 創建 Agent
    return Agent(
        model=LiteLlm(model="azure/gpt-4o"),
        name=f"stock_analyst_{stage_name.replace(' ', '_')}",
        description=description_override or "您是專業的股票分析師，請專注於當前的分析階段。",
        tools=tools or [],
        static_instruction=combined_instructions,
        include_contents='none'
    )


async def _execute_agent_and_get_text(agent: Agent, prompt: str, parent_context=None) -> str:
    """
    Helper function to execute an Agent's logic using its underlying model.
    We bypass `agent.run_async` because it is strictly tied to the framework's Event/Session loop
    and doesn't allow easy injection of new prompts for sub-tasks (Stage 1/2/3).
    """
    response_text = ""
    try:
        # Construct messages manually
        # ADK LiteLlm uses LlmRequest logic
        # structure: contents=[{'role': '...', 'parts': [{'text': '...'}]}]
        
        contents = []
        
        # Combine Description (Agent Persona + Date) and Static Instructions
        full_system_prompt = ""
        if agent.description:
            full_system_prompt += f"{agent.description}\n\n"
        
        if agent.static_instruction:
            full_system_prompt += agent.static_instruction

        if full_system_prompt:
            # logger.info(f"🐛 [DEBUG] System Prompt for {agent.name}:\n{full_system_prompt}\n" + "="*50)
            
            # [Fix] Write to file to bypass terminal limits (Append mode)
            try:
                with open("latest_debug_prompt.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n\n{'='*50}\n")
                    f.write(f"Agent: {agent.name}\nTimestamp: {datetime.datetime.now()}\n{'='*20}\n\n")
                    f.write(full_system_prompt)
            except Exception as e:
                logger.error(f"Failed to write debug file: {e}")

            contents.append({
                "role": "system",
                "parts": [{"text": full_system_prompt}]
            })
            
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        logger.info(f"⚡️ Executing {agent.name} via direct model call (Prompt len: {len(prompt)})")
        
        model = agent.model
        
        # Check for generate_content_async (ADK Model API)
        if hasattr(model, 'generate_content_async'):
             # Create LlmRequest
             # Note: agent.model.model holds the model name (e.g. "azure/gpt-4o")
             request = LlmRequest(
                 model=getattr(model, 'model', "azure/gpt-4o"),
                 contents=contents,
                 config=types.GenerateContentConfig(max_output_tokens=8192)
             )
             
             async for response in model.generate_content_async(request):
                 # response is LlmResponse
                 chunk_text = ""
                 
                 # Capture Token Usage
                 if hasattr(response, 'usage_metadata') and response.usage_metadata:
                     token_info = response.usage_metadata
                     logger.info(f"📊 [Token Usage] Agent: {agent.name} | Input: {getattr(token_info, 'prompt_token_count', 'N/A')} | Output: {getattr(token_info, 'candidates_token_count', 'N/A')} | Total: {getattr(token_info, 'total_token_count', 'N/A')}")
                 
                 # Check content/text fields
                 val = None
                 if hasattr(response, 'content') and response.content:
                     val = response.content
                 elif hasattr(response, 'text') and response.text:
                     val = response.text
                 
                 # Process value
                 if val:
                     if isinstance(val, str):
                         chunk_text = val
                     # Handle ADK Content object (has 'parts')
                     elif hasattr(val, 'parts') and val.parts:
                         # parts is a list of Part objects
                         if hasattr(val.parts[0], 'text'):
                             chunk_text = val.parts[0].text
                         elif isinstance(val.parts[0], dict) and 'text' in val.parts[0]:
                             chunk_text = val.parts[0]['text']
                             
                 # Fallback: check candidates if top-level content was empty
                 if not chunk_text and hasattr(response, 'candidates') and response.candidates:
                      parts = response.candidates[0].content.parts
                      if parts:
                          if hasattr(parts[0], 'text'):
                              chunk_text = parts[0].text
                          elif isinstance(parts[0], dict) and 'text' in parts[0]:
                              chunk_text = parts[0]['text']

                 if chunk_text:
                     response_text += chunk_text

        # Fallback to completion (if somehow generate_content_async is missing but completion exists)
        elif hasattr(model, 'completion'): 
             # OpenAI format
             messages = [{"role": "system", "content": agent.static_instruction}, {"role": "user", "content": prompt}]
             response = await model.completion(messages=messages)
             if isinstance(response, str):
                 response_text = response
             elif hasattr(response, 'choices'):
                 response_text = response.choices[0].message.content
        else:
             logger.error(f"❌ Unknown model interface: {type(agent.model)}")
             return "Error: Unknown model interface"
             
    except Exception as e:
        logger.error(f"❌ Error executing agent model: {e}")
        import traceback
        traceback.print_exc()
        raise e
        
    return response_text
def _validate_stage_0_json(data: dict) -> Tuple[bool, str]:
    """
    [Code Validation] 實作 `07_quality_checklist` 中的 "Checklist 0.1: 分析前置檢查"
    
    即便驗證邏輯是寫死的 (Python Regex)，其規範來源仍應為 Quality Checklist 文件，
    以確保單一真實來源 (Single Source of Truth)。
    """
    errors = []
    
    # 1. 檢查 Title 格式
    title = data.get("report_title", "")
    # Regex: Start with #, contain (), and end with 投資分析報告
    # e.g., "# Apple Inc. (AAPL) - 投資分析報告"
    title_pattern = r"^#\s+.*\s+\(.*\)\s+-\s+.*$"
    if not re.match(title_pattern, title):
        errors.append(f"❌ Invalid 'report_title': '{title}'. Must match format '# Company (Ticker) - ...'")
        
    # 2. 檢查 TOC 完整性
    toc = data.get("table_of_contents", "")
    required_sections = ["Part A:", "Part B:", "Appendix", "目錄"]
    missing_sections = [sec for sec in required_sections if sec not in toc]
    if missing_sections:
        errors.append(f"❌ Missing sections in 'table_of_contents': {missing_sections}")
        
    # [Clean Text Validation] 檢查是否含有 Markdown 符號
    # 檢查 **bold**
    if "**" in toc or "**" in title:
         errors.append(f"❌ Markdown bold syntax '**' found. Use Clean Text format.")
    
    # 檢查 List Bullet '-' (檢查每一行開頭)
    for line in toc.split('\n'):
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            errors.append(f"❌ Markdown list syntax '- ' or '* ' found in TOC. Use indented numbers (e.g., '   1.1 ...').")
            break
        
    if errors:
        return False, "\n".join(errors)
        
    return True, "PASS"

async def _run_stage_0(user_request: str, tool_context=None) -> AnalysisContext:
    """Stage 0: 分析準備 (Context Gathering)"""
    logger.info("🚀 Starting Stage 0: Context Gathering")
    
    # 工具：給予 Context Reader 和 Search 工具
    stage_tools = load_mcp_tools() + [yahoo_finance_tool]
    
    agent = create_stage_agent(
        stage_name="stage_0_context",
        instruction_files=["00_stage_0_instruction.md", "02_data_source_selection.md", "03_analysis_framework_selector.md"],
        include_base_instructions=False, # ❌ 禁止載入 agent_execution.md，避免污染 Prompt
        description_override=f"""
        您是分析流程的指揮官 (Stage 0)。
        **當前系統日期**：{datetime.datetime.now().strftime('%Y-%m-%d')} (以此為基準設定所有日期)
        
        任務：
        1. 解析用戶需求。
        2. 決定分析期間 (Analysis Period) 與 數據截止日。
        3. 選擇最合適的數據源與分析視角。
        4. **最後輸出**：必須 **只輸出** 一個 JSON 格式的 Analysis Context。
        
        👉 **請務必嚴格遵守 `00_stage_0_instruction` 中的「欄位詳細要求」**。
        (特別是 `report_title` 格式與 `table_of_contents` 完整度)
        """ + """
        輸出 JSON 格式範例：
        ```json
        {
            "ticker": "AMD",
            "company_name": "Advanced Micro Devices, Inc.",
            "report_date": "2026-01-13",
            "analysis_start_date": "2025-01-13",
            "analysis_end_date": "2026-01-13",
            "data_source": "Morningstar (Primary) + Yahoo Finance (Secondary)",
            "analysis_angles": ["競爭格局", "供需分析", "技術替代風險"],
            "report_type": "標準成長框架",
            "report_title": "# Advanced Micro Devices (AMD) - 投資分析報告",
            "table_of_contents": "目錄\\n\\n1. Part A: 深度分析報告\\n   1.1 重要訊息\\n   1.2 評論及分析\\n   1.3 估值與目標價\\n   1.4 投資建議\\n   1.5 投資風險\\n\\n2. Part B: 重點摘要表格\\n   2.1 財務概要\\n   2.2 估值指標\\n\\n3. 附錄 (Appendix)\\n   3.1 數據來源聲明\\n   3.2 定義與方法論"
        }
        ```
        請確保您的回答僅包含 JSON，不要有任何其他文字。
        """,
        tools=stage_tools
    )
    
    
    
    MAX_RETRIES = 3
    last_error = ""
    current_prompt = user_request

    for i in range(MAX_RETRIES):
        logger.info(f"🤖 Stage 0 Agent Executing (Attempt {i+1}/{MAX_RETRIES})...")
        response_text = await _execute_agent_and_get_text(agent, current_prompt, parent_context=tool_context)
        
        try:
            # JSON 解析
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            # 簡單的括號提取防護
            idx_start = clean_json.find('{')
            idx_end = clean_json.rfind('}')
            if idx_start != -1 and idx_end != -1:
                clean_json = clean_json[idx_start:idx_end+1]
                
            context_data = json.loads(clean_json)
            
            # 驗證
            is_valid, validation_msg = _validate_stage_0_json(context_data)
            
            if is_valid:
                logger.info(f"✅ Stage 0 JSON Validated & Passed.")
                # 補全欄位並回傳
                return {
                    "ticker": context_data.get("ticker", "UNKNOWN"),
                    "company_name": context_data.get("company_name", "Unknown Company"),
                    "report_date": context_data.get("report_date", datetime.datetime.now().strftime("%Y-%m-%d")),
                    "analysis_start_date": context_data.get("analysis_start_date", ""),
                    "analysis_end_date": context_data.get("analysis_end_date", ""),
                    "data_source": context_data.get("data_source", "Unknown"),
                    "analysis_angles": context_data.get("analysis_angles", []),
                    "report_type": context_data.get("report_type", "Standard"),
                    "report_title": context_data.get("report_title", ""),
                    "table_of_contents": context_data.get("table_of_contents", ""),
                    "part_a_content": None,
                    "part_b_content": None,
                    "appendix_content": None
                }
            else:
                logger.warning(f"❌ Stage 0 Validation Failed:\n{validation_msg}")
                last_error = validation_msg
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Decode Error: {e}")
            last_error = f"JSON Parsing Error: {e}"
        except Exception as e:
            logger.error(f"❌ Unexpected Error: {e}")
            last_error = str(e)
        
    # Retry with feedback
    current_prompt = f"{user_request}\n\n⚠️ 上一次輸出有誤，請修正:\n{last_error}\n\n請務必輸出合法的 JSON，並符合所有格式要求。"
    
    raise ValueError(f"Stage 0 failed after {MAX_RETRIES} attempts. Last error: {last_error}")

async def _validate_and_rewrite(stage_name: str, content: str, criteria_file: str, tool_context=None) -> Tuple[bool, str]:
    """
    通用驗證邏輯 (Self-Correction Loop)
    1. 檢查內容是否符合 criteria_file (通常是 quality_checklist)
    2. 若失敗，讓 Agent 進行修正
    
    Returns:
        (is_valid, content): 驗證通過與否及最終內容
    """
    max_retries = 5
    current_content = content
    
    for i in range(max_retries + 1):
        logger.info(f"🔍 Validating {stage_name} (Attempt {i+1})...")
        
        # 創建一個專門的 Quality Assurance Agent
        validator = create_stage_agent(
            stage_name=f"{stage_name}_validator",
            instruction_files=["07_quality_checklist_v3_4_0.md", "01_core_principles.md"],
            include_base_instructions=False,
            description_override="你是嚴格的品質檢查員 (QA)。你的任務是根據檢查清單審查內容，並給出通過(PASS)或失敗(FAIL)的判定。"
        )
        
        # 構建驗證 Prompt
        validation_prompt = f"""
        請針對以下內容執行 `{criteria_file}` 中的檢查項目：

        **當前系統日期**：{datetime.datetime.now().strftime('%Y-%m-%d')}
        (請務必檢查報告中的日期是否為今日或合理的近期日期)
        
        {current_content}
        
        請判斷是否符合規範。
        如果完全符合，請只回答 "PASS"。
        如果有任何不符合之處，請回答 "FAIL: [失敗原因]"，並列出具體修改建議。
        """
        
        
        
        
        # 調用 QA Agent
        validation_result = await _execute_agent_and_get_text(validator, validation_prompt, parent_context=tool_context)
        
        if "PASS" in validation_result:
            logger.info(f"✅ {stage_name} Passed Validation.")
            return True, current_content
        else:
            logger.warning(f"❌ {stage_name} Validation Failed: {validation_result}")
            if i < max_retries:
                logger.info(f"🔄 Attempting Self-Correction for {stage_name}...")
                
                # 創建修正者 Agent (Corrector)
                corrector = create_stage_agent(
                   stage_name=f"{stage_name}_corrector",
                   instruction_files=[criteria_file, "01_core_principles.md"], # 讓他讀這個規則來改
                   include_base_instructions=False,
                   description_override="您是內容修訂員。請根據 QA 檢查員的並改進內容。",
                   tools=[yahoo_finance_tool] # 修正時可能需要補查資料
                )

                rewrite_prompt = f"""
                原內容如下：
                {current_content}

                QA 檢查員指出以下問題：
                {validation_result}

                請根據以上問題，**修正並重寫** 完整的內容。
                請直接輸出修正後的完整 Markdown，不要解釋。
                """
                
                # 更新 current_content
                current_content = await _execute_agent_and_get_text(corrector, rewrite_prompt, parent_context=tool_context)
                
    # Loop exhausted
    logger.warning(f"⚠️ {stage_name} failed validation after {max_retries} attempts.")
    return False, current_content

# ============================================================================
# Stage 0.5: Mandatory Data Collection (Tool Usage Enforcement)
# ============================================================================

async def _run_stage_0_5_data_collection(context: AnalysisContext, tool_context=None) -> dict:
    """
    Stage 0.5: 強制前置數據收集
    
    根據 Stage 0 的 TOC 規劃，預先收集所有必要的真實數據，
    確保後續寫作階段不會產生幻覺 (Hallucination)。
    
    所有工具呼叫會記錄到檔案中供驗證，不輸出至 console。
    """
    import os
    from datetime import datetime
    
    # 建立 Log 目錄
    log_dir = os.path.join(os.path.dirname(__file__), ".adk", "data_collection_logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 建立本次執行的 Log 檔案
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"data_collection_{context['ticker']}_{timestamp}.log")
    
    def log_tool_call(tool_name: str, source_url: str, raw_data: str, status: str = "SUCCESS"):
        """記錄工具呼叫詳情到檔案"""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{datetime.now().isoformat()}] Tool Call: {tool_name}\n")
            f.write(f"Status: {status}\n")
            f.write(f"Source: {source_url}\n")
            f.write(f"Raw Data:\n{raw_data}\n")
    
    logger.info(f"🔍 Starting Stage 0.5: Data Collection (Log: {log_file})")
    
    ticker = context['ticker']
    toc = context.get('table_of_contents', '')
    
    # 記錄查詢時間
    from datetime import datetime
    fetch_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data_bundle = {
        'log_file': log_file,  # 供後續驗證使用
        'fetch_timestamp': fetch_timestamp,  # 資料查詢時間
        'current_price': 'N/A',
        'pe_ratio': 'N/A',
        'market_cap': 'N/A',
        'financials': {},
        'analyst_reports': None,
        'data_sources': []  # 記錄所有資料來源
    }
    
    # 1. 必定呼叫：基礎股價數據 (Yahoo Finance)
    try:
        from stock.tools.yahoo_finance_tool import get_stock_info
        ticker_formatted = f"{ticker}.TW" if not ticker.endswith('.TW') else ticker
        
        raw_response = get_stock_info(ticker_formatted)
        log_tool_call(
            tool_name="get_stock_info (Yahoo Finance)",
            source_url=f"https://finance.yahoo.com/quote/{ticker_formatted}",
            raw_data=raw_response[:2000]  # 限制長度
        )
        
        # 解析 JSON
        import json
        stock_data = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
        
        if 'info' in stock_data:
            info = stock_data['info']
            
            # ⚠️ 關鍵驗證：檢查公司名稱是否匹配
            actual_company_name = info.get('longName', 'Unknown')
            expected_company_name = context.get('company_name', '')
            
            # 簡單的模糊匹配（檢查是否有共同關鍵字）
            name_match = False
            if expected_company_name:
                # 移除常見後綴進行比對
                expected_keywords = expected_company_name.replace('股份有限公司', '').replace('有限公司', '').strip()
                if expected_keywords in actual_company_name or actual_company_name in expected_company_name:
                    name_match = True
            
            # 記錄驗證結果
            verification_status = "✅ PASS" if name_match else "❌ FAIL"
            log_tool_call(
                tool_name="verify_ticker",
                source_url=f"https://finance.yahoo.com/quote/{ticker_formatted}",
                raw_data=f"""
Ticker 驗證結果: {verification_status}

預期公司名稱: {expected_company_name}
實際公司名稱: {actual_company_name}
Ticker: {ticker_formatted}

{f"⚠️ 警告：公司名稱不匹配！請確認 Ticker 是否正確。" if not name_match else "✓ 驗證通過"}
                """.strip(),
                status="PASS" if name_match else "WARNING"
            )
            
            if not name_match:
                logger.warning(f"⚠️ Ticker 驗證警告：預期 '{expected_company_name}'，實際為 '{actual_company_name}'")
                data_bundle['ticker_verification'] = f"WARNING: Name mismatch"
            else:
                data_bundle['ticker_verification'] = "PASS"
            
            # 繼續提取數據
            data_bundle['current_price'] = info.get('currentPrice', 'N/A')
            data_bundle['pe_ratio'] = info.get('trailingPE', 'N/A')
            data_bundle['market_cap'] = info.get('marketCap', 'N/A')
            
            # 擴充：提取更多財務數據
            data_bundle['revenue'] = info.get('totalRevenue', 'N/A')
            data_bundle['gross_margin'] = info.get('grossMargins', 'N/A')
            data_bundle['ebitda'] = info.get('ebitda', 'N/A')
            data_bundle['operating_cash_flow'] = info.get('operatingCashflow', 'N/A')
            data_bundle['revenue_growth'] = info.get('revenueGrowth', 'N/A')
            data_bundle['debt_to_equity'] = info.get('debtToEquity', 'N/A')
            
            # 記錄完整可用欄位（供驗證）
            available_keys = list(info.keys())
            log_tool_call(
                tool_name="get_stock_info (Available Fields)",
                source_url=f"https://finance.yahoo.com/quote/{ticker_formatted}",
                raw_data=f"Available data fields: {', '.join(available_keys[:50])}"  # 前50個欄位
            )
            
            data_bundle['financials'] = stock_data.get('financials', {})
            
            # 記錄資料來源
            data_bundle['data_sources'].append({
                'name': 'Yahoo Finance',
                'url': f'https://finance.yahoo.com/quote/{ticker_formatted}',
                'data_types': ['股價', '市盈率', '市值', '財務數據'],
                'fetch_time': fetch_timestamp
            })
        
    except Exception as e:
        log_tool_call(
            tool_name="get_stock_info",
            source_url="N/A",
            raw_data=f"ERROR: {str(e)}",
            status="FAILED"
        )
    
    # 2. 條件呼叫：最新財報新聞與券商報告
    if '估值' in toc or '目標價' in toc or '財務' in toc:
        logger.info("📊 Searching for financial news and analyst reports...")
        
        company_name = context.get('company_name', ticker)
        
        # 2.1 搜尋最新財報新聞
        try:
            search_query = f"{company_name} 財報 2025 Q4"
            logger.info(f"🔍 Searching: {search_query}")
            
            # 載入 MCP 搜尋工具
            mcp_tools = load_mcp_tools()
            
            if mcp_tools:
                # 建立專用搜尋 Agent
                search_agent = create_stage_agent(
                    stage_name="stage_0_5_search",  # 修正：不能有小數點
                    instruction_files=[],
                    include_base_instructions=False,
                    description_override="你是搜尋助手，負責查詢財經新聞。",
                    tools=mcp_tools
                )
                
                # 執行搜尋
                search_prompt = f"請搜尋：{search_query}"
                search_results = await _execute_agent_and_get_text(search_agent, search_prompt)
                
                log_tool_call(
                    tool_name="search_web (Financial News)",
                    source_url=f"Query: {search_query}",
                    raw_data=f"Search Results: {search_results[:1000]}",
                    status="SUCCESS"
                )
                
                data_bundle['financial_news'] = search_results
            else:
                data_bundle['financial_news'] = 'N/A (MCP tools not loaded)'
                log_tool_call(
                    tool_name="search_web",
                    source_url="N/A",
                    raw_data="MCP tools not available",
                    status="SKIPPED"
                )
                
        except Exception as e:
            logger.warning(f"⚠️ Search failed: {e}")
            log_tool_call(
                tool_name="search_web",
                source_url="N/A",
                raw_data=f"ERROR: {str(e)}",
                status="FAILED"
            )
            data_bundle['financial_news'] = 'N/A'
        
        # 2.2 搜尋券商目標價
        data_bundle['analyst_reports'] = "N/A (查無公開券商預測數據)"
    
    logger.info(f"✅ Stage 0.5 Complete. Collected: Price={data_bundle['current_price']}, P/E={data_bundle['pe_ratio']}, Revenue={data_bundle.get('revenue', 'N/A')}")
    return data_bundle

async def _run_stage_1(context: AnalysisContext, tool_context=None) -> str:
    """Stage 1: 深度分析 (Part A)"""
    logger.info("🚀 Starting Stage 1: Part A Generation")
    
    # Load tools for real-time data access
    stage_tools = load_mcp_tools() + [yahoo_finance_tool]
    
    agent = create_stage_agent(
        stage_name="stage_1_part_a",
        instruction_files=["04_part_a_writing_guide.md", "01_core_principles.md"],
        include_base_instructions=False,
        description_override="您是資深的股票分析師，負責撰寫深度分析報告 (Part A)。您必須使用工具查詢最新股價與市場資訊。",
        tools=stage_tools
    )
    
    prompt = f"""
    請根據以下上下文撰寫 Part A 報告：
    
    - 股票：{context['ticker']} ({context['company_name']})
    - 報告日期：{context['report_date']}
    - 分析視角：{context['analysis_angles']}
    
    ⚠️ 以下是已查詢的真實數據，嚴禁自行創造任何數字 ⚠️
    
    **基礎數據 (Yahoo Finance)**：
    - 當前股價：{context.get('real_data', {}).get('current_price', 'N/A')}
    - 市盈率 (P/E)：{context.get('real_data', {}).get('pe_ratio', 'N/A')}
    - 市值：{context.get('real_data', {}).get('market_cap', 'N/A')}
    
    **財務數據 (Yahoo Finance)**：
    - 營收 (Revenue)：{context.get('real_data', {}).get('revenue', 'N/A')}
    - 毛利率 (Gross Margin)：{context.get('real_data', {}).get('gross_margin', 'N/A')}
    - EBITDA：{context.get('real_data', {}).get('ebitda', 'N/A')}
    - 營運現金流 (Operating Cash Flow)：{context.get('real_data', {}).get('operating_cash_flow', 'N/A')}
    - 營收增長率 (Revenue Growth)：{context.get('real_data', {}).get('revenue_growth', 'N/A')}
    - 負債權益比 (Debt-to-Equity)：{context.get('real_data', {}).get('debt_to_equity', 'N/A')}
    
    **分析師數據**：
    - 券商預測：{context.get('real_data', {}).get('analyst_reports', 'N/A (查無數據)')}
    
    🚫 嚴格規則：
    1. 若某項數據為 "N/A"，絕對不可用 "約XX%" 或 "估計XX億" 等模糊表述。
    2. 若某個主題（如客戶結構、產業平均）完全沒有數據支撐，**整段省略不寫**。
    3. 禁止編造任何「行業平均」、「一般而言」、「通常情況下」等無來源陳述。
    
    📊 資料來源標註要求：
    - 在「重要訊息」段落最後，必須加入以下格式的來源說明：
    
    ---
    📊 資料來源：Yahoo Finance (https://finance.yahoo.com/quote/{context['ticker']}.TW)
    資料更新時間：{context.get('real_data', {}).get('fetch_timestamp', 'N/A')}
    ---
    
    ⛔️ 絕對禁止輸出以下內容（會與 Stage 0 重複）：
    - 報告標題 (已在 Stage 0 產出)
    - 報告日期、分析期間 (已在 Stage 0 產出)
    - 目錄 (已在 Stage 0 產出)
    
    ✅ 必須依序包含以下章節 (使用 ##):
    ## 重要訊息
    ## 評論及分析
    ## 估值與目標價
    ## 投資建議
    ## 投資風險

    ⚠️ CRITICAL DATA INTEGRITY RULE ⚠️
    1. **Tool First**: 在撰寫任何內容前，必須先呼叫 `get_stock_info` 取得最新股價。
    2. **Zero Hallucination**: 若工具回傳失敗或查無數據，嚴禁自行填寫數字，必須標註 "N/A"。
    3. **No Fake Citations**: 嚴禁使用 "AAA證券" 等假名。若查不到券商預測，該表格留空並註明 "N/A"。
    
    📋 數據來源聲明 (必須在報告最後加入)：
    
    ---
    ## 數據來源聲明
    
    本報告數據來源如下：
    
    **1. Yahoo Finance**
    - 連結：https://finance.yahoo.com/quote/{context['ticker']}.TW
    - 數據類型：股價、市盈率、市值、財務數據
    - 查詢時間：{context.get('real_data', {}).get('fetch_timestamp', 'N/A')}
    
    {f"**2. 網路搜尋**\\n- 查詢關鍵字：{context.get('company_name', '')} 財報 2025 Q4\\n- 查詢時間：{context.get('real_data', {}).get('fetch_timestamp', 'N/A')}" if context.get('real_data', {}).get('financial_news') and context.get('real_data', {}).get('financial_news') != 'N/A' else ""}
    
    ---
    """
    

    
    
    logger.info("🤖 Stage 1 Agent Executing...")
    part_a_content = await _execute_agent_and_get_text(agent, prompt, parent_context=tool_context)
    
    # 執行品質驗證
    is_valid, validated_content = await _validate_and_rewrite("Part A", part_a_content, "07_quality_checklist_v3_4_0.md", tool_context=tool_context)
    
    if is_valid:
        logger.info("✅ Stage 1 (Part A) Passed Validation.")
    else:
        logger.warning("⚠️ Stage 1 (Part A) Completed with Validation Warnings.")
    
    # 程式強制附加數據來源聲明
    data_source_footer = f"""

---

## 數據來源聲明

本報告數據來源如下：

**1. Yahoo Finance**  
- 連結：https://finance.yahoo.com/quote/{context['ticker']}.TW  
- 數據類型：股價、市盈率、市值、財務數據  
- 查詢時間：{context.get('real_data', {}).get('fetch_timestamp', 'N/A')}  

---
"""
    
    return validated_content + data_source_footer

async def _run_stage_2(context: AnalysisContext, part_a_content: str, tool_context=None) -> str:
    """Stage 2: 摘要與表格 (Part B)"""
    logger.info("🚀 Starting Stage 2: Part B Generation")
    
    agent = create_stage_agent(
        stage_name="stage_2_part_b",
        instruction_files=["05_part_b_table_guide.md", "01_core_principles.md"],
        include_base_instructions=False,
        description_override="您是精準的數據整理專員，負責製作分析摘要表格 (Part B)。",
        tools=[yahoo_finance_tool]
    )
    
    prompt = f"""
    請根據以下 Part A 的內容，製作 Part B 摘要表格：
    
    [Part A Content Start]
    {part_a_content}
    [Part A Content End]
    
    - 股票：{context['ticker']}
    - 目標：
        1. 填寫「價格與目標價」表格 (數據需與 Part A 一致)。
        2. 萃取 4 點「焦點內容」 (必須來自 Part A)。
        3. 製作「交易資料」與「股價表現」表格。
        
        ⚠️ 重要提示：
        - Part A 中可能缺少部分交易數據（如市值、流通股數、3M Avg Volume 等）。
        - 若發現數據缺失，請 **立即使用 `yahoo_finance_tool`** 查詢補足。
        - 嚴禁留下 "N/A"，除非工具也查不到。
    
    請嚴格遵循 `05_part_b_table_guide` 的格式。
    """
    

    
    
    logger.info("🤖 Stage 2 Agent Executing...")
    part_b_content = await _execute_agent_and_get_text(agent, prompt, parent_context=tool_context)
    
    # 執行品質驗證
    is_valid, validated_content = await _validate_and_rewrite("Part B", part_b_content, "07_quality_checklist_v3_4_0.md", tool_context=tool_context)
    
    if is_valid:
        logger.info("✅ Stage 2 (Part B) Passed Validation.")
    else:
        logger.warning("⚠️ Stage 2 (Part B) Completed with Validation Warnings.")
        
    return validated_content


    
async def _run_stage_3(context: AnalysisContext, tool_context=None) -> str:
    """Stage 3: 附錄與組裝 (Appendix)"""
    logger.info("🚀 Starting Stage 3: Appendix Generation")
    
    agent = create_stage_agent(
        stage_name="stage_3_appendix",
        instruction_files=["06_appendix_reference_guide.md", "02_data_source_selection.md", "01_core_principles.md"],
        include_base_instructions=False,
        description_override="您是嚴謹的文檔管理員，負責製作附錄與參考文獻。"
    )
    
    prompt = f"""
    請根據本次分析使用的數據源與規範，製作報告附錄：
    
    - 數據源配置：{context['data_source']}
    - 報告日期：{context['report_date']}
    - 數據截止日：{context['analysis_end_date']}
    
    任務：
    1. 製作「數據來源與免責聲明」 (含長版法律聲明)。
    2. 製作「參考文獻與數據來源」表格 (嚴格遵循 `06_appendix` 格式，需列出 Morningstar、財報等具體項目)。
    
    請注意：Part B 下方已包含短版聲明，此處為 **完整附錄**。
    """
    

    
    
    logger.info("🤖 Stage 3 Agent Executing...")
    appendix_content = await _execute_agent_and_get_text(agent, prompt, parent_context=tool_context)
    
    # 執行品質驗證
    is_valid, validated_content = await _validate_and_rewrite("Appendix", appendix_content, "07_quality_checklist_v3_4_0.md", tool_context=tool_context)
    
    if is_valid:
        logger.info("✅ Stage 3 (Appendix) Passed Validation.")
    else:
        logger.warning("⚠️ Stage 3 (Appendix) Completed with Validation Warnings.")
        
    return validated_content

async def run_analysis_pipeline(user_request: str, tool_context=None):
    """
    執行完整分析流水線
    """
    logger.info("🔥 Initializing Analysis Pipeline...")

    # 清空 debug log
    try:
        with open("latest_debug_prompt.txt", "w", encoding="utf-8") as f:
             f.write(f"Pipeline Started at {datetime.datetime.now()}\n")
    except:
        pass
    
    
    # Stage 0
    context = await _run_stage_0(user_request, tool_context=tool_context)
    logger.info(f"✅ Stage 0 Complete. Context: {context}")
    
    # Stage 0.5: Mandatory Data Collection
    real_data = await _run_stage_0_5_data_collection(context, tool_context=tool_context)
    context['real_data'] = real_data
    logger.info(f"✅ Stage 0.5 Complete. Data Log: {real_data.get('log_file')}")
    
    # [TEST MODE] Skipping Stages 2-3 for Part A Verification
    logger.info("🚧 [TEST MODE] Skipping Stage 2, 3. Using placeholders.")
    
    # Stage 1 (Part A)
    context['part_a_content'] = await _run_stage_1(context, tool_context=tool_context)
    # context['part_a_content'] = "### (Part A Skipped for Testing)"
    logger.info("✅ Stage 1 (Part A) Complete.")
    
    # Stage 2 (Part B)
    # context['part_b_content'] = await _run_stage_2(context, context['part_a_content'], tool_context=tool_context)
    context['part_b_content'] = "### (Part B Skipped for Testing)"
    logger.info("✅ Stage 2 (Part B) Skipped.")
    
    # Stage 3 (Appendix)
    # context['appendix_content'] = await _run_stage_3(context, tool_context=tool_context)
    context['appendix_content'] = "### (Appendix Skipped for Testing)"
    logger.info("✅ Stage 3 (Appendix) Skipped.")
    
    # Final Assembly
    logger.info("📦 Assembling Final Report...")
    
    # 構建包含標題、目錄、各部分內容的完整報告
    title = context.get('report_title', f"# {context.get('company_name', 'Unknown')} 分析報告")
    toc = context.get('table_of_contents', "")

    final_report = f"""
{title}

報告日期: {context.get('report_date')}
分析期間: {context.get('analysis_start_date')} - {context.get('analysis_end_date')}
資料來源: {context.get('data_source')}

---

{toc}

---

## Part A: 深度分析報告

{context['part_a_content']}

---

## Part B: 重點摘要表格

{context['part_b_content']}

---

## 附錄 (Appendix)

{context['appendix_content']}
    """
    
    logger.info("🎉 Analysis Pipeline Completed Successfully!")
    
    # [Clean Text Policy] 強制移除所有 Markdown Code Block 標記 (```)
    # 先移除語言標記，再移除 backticks，避免留下 stray text
    final_report = final_report.replace("```markdown", "").replace("```json", "").replace("```", "").strip()
    
    return final_report

# 將 Pipeline 包裝為工具
pipeline_tool = FunctionTool(run_analysis_pipeline)

# ============================================================================
# Root Agent Configuration (Tool Swapping Strategy)
# ============================================================================

# 我們不再使用自定義 Class，而是使用標準 Agent，但只給它一個工具：Pipeline Tool
# 並透過 System Prompt 強制它使用這個工具

root_agent = Agent(
    model=LiteLlm(model="azure/gpt-4o"),
    name="stock_analyst",
    description="Stock Analyst Agent",
    # 只提供 Pipeline 工具，強迫 Agent 進入我們的 Python 邏輯
    tools=[pipeline_tool], 
    static_instruction="""
    您是股票分析報告生成器的入口。
    
    **唯一任務**：
    當收到任何股票代號或公司名稱時（例如 "AMD", "TSMC", "分析 Apple"），
    您必須**立即**調用 `run_analysis_pipeline` 工具。
    
    **輸出規則**：
    該工具會返回完整的繁體中文分析報告。
    您必須**原封不動**地將工具的輸出呈現給用戶。
    
    - ❌ 禁止自行撰寫摘要。
    - ❌ 禁止使用自己的知識庫回答。
    - ✅ 必須且只能呼叫 `run_analysis_pipeline`。
    """,
    include_contents='none'
)



# ============================================================================
# 開發工具函數
# ============================================================================

def show_loaded_modules():
    """顯示當前已載入的模組資訊"""
    instruction_dir = os.path.join(os.path.dirname(__file__), "instructions")
    modules = extract_modules_from_instructions(instruction_dir)
    
    logger.info("\n" + "="*60)
    logger.info(f"📦 已載入 {len(modules)} 個模組")
    logger.info("="*60)
    
    for module_id, info in sorted(modules.items(), key=lambda x: x[1]['order']):
        logger.info(f"\n{info['order']:02d}. {info['name']} ({module_id})")
        logger.info(f"    文件: {info['file']}")
        if info['aliases']:
            aliases_str = '、'.join(f'"{a}"' for a in info['aliases'][:5])
            logger.info(f"    別名: {aliases_str}")
        if info['description']:
            logger.info(f"    說明: {info['description']}")
    
    logger.info("\n" + "="*60 + "\n")


# [DEBUG] Force run load_instructions on module import to ensure logging
logger.info("[DEBUG] Agent module initialized, forcing instruction load + logging...")
load_instructions()
