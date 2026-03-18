"""
LangGraph Agent - 天氣搜索 + 計算工具 + 網絡搜索

這是一個使用 LangGraph 構建的 AI Agent，具備以下能力：
1. 天氣搜索 - 獲取指定城市的天氣資訊
2. 數學計算 - 執行數學運算
3. 網絡搜索 - 搜索互聯網獲取最新資訊
4. 根據任務自主選擇合適的工具

使用 LangGraph 的 ReAct 模式實現 Tool Calling
"""

import operator
import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
import json

# 載入 .env 文件
load_dotenv()

# ============================================
# Deep Reasoning System Prompt
# ============================================
DEEP_REASONING_SYSTEM_PROMPT = """你是一個專業的 AI 任務規劃師。你的職責是分析用戶請求並將其分解為可執行的子任務。

## 可用工具：
1. get_weather(city) - 獲取城市即時天氣資訊，city為城市名稱，例如 "Taipei"、"Tokyo"、"New York"
2. calculate(expression) - 執行數學計算
3. web_search(query) - 搜索互聯網獲取最新資訊
4. get_current_time(timezone) - 獲取當前時間，timezone為時區例如 "UTC"、"Asia/Taipei"、"America/New_York"

## 重要提醒：
- 你必須知道「當前時間」，這對於回答時間相關的問題很重要
- 如果用戶問「現在幾點」、「今天日期」等，必須先調用 get_current_time
- 你沒有內建的時間知識，必須使用工具獲取

## 任務分解原則：
1. 識別用戶的核心需求
2. 判斷需要哪些工具來完成任務
3. 確定任務的執行順序
4. 預測可能的複雜情況

## 輸出格式：
請用以下格式回應：

### 任務分析
[對用戶請求的初步理解]

### 所需工具
- [工具1]: [原因]
- [工具2]: [原因]

### 執行計劃
1. [第一步]
2. [第二步]
..."""

# ============================================
# LangSmith 配置 (用於調試)
# ============================================
# 只需要設置環境變量即可自動追蹤:
# - LANGCHAIN_API_KEY
# - LANGCHAIN_TRACING_V2=true
# 查看追蹤: https://smith.langchain.com/

# 可選：啟用 LangChain 調試模式
# set_debug(True)

# 檢查 LangSmith 是否正確配置
if os.getenv("LANGCHAIN_API_KEY"):
    print("=" * 60)
    print("🔍 LangSmith 調試模式已啟用")
    print("   查看追蹤: https://smith.langchain.com/")
    print("=" * 60)
    print()
else:
    print("=" * 60)
    print("⚠️  LangSmith API Key 未設置")
    print("   請在 .env 文件中設置:")
    print("   LANGCHAIN_API_KEY=your_api_key")
    print("   LANGCHAIN_TRACING_V2=true")
    print("=" * 60)
    print()


# ============================================
# 1. 定義工具 (Tools)
# ============================================

@tool
def get_weather(city: str) -> str:
    """
    獲取指定城市的即時天氣資訊。

    Args:
        city: 城市名稱，例如 "Taipei"、"Tokyo"、"New York"

    Returns:
        天氣資訊字符串
    """
    import requests
    
    api_key = os.getenv("OPEN_WEATHER_API_KEY")
    if not api_key:
        return "錯誤：未設置 OPEN_WEATHER_API_KEY 環境變量"
    
    try:
        # OpenWeatherMap API
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric"  # 使用攝氏度
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            return f"抱歉，沒有找到 {city} 的天氣資訊"
        elif response.status_code == 401:
            return "錯誤：API Key 無效"
        elif response.status_code != 200:
            return f"錯誤：API 請求失敗 (狀態碼: {response.status_code})"
        
        data = response.json()
        
        # 解析天氣數據
        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        feels_like = data["main"]["feels_like"]
        wind_speed = data["wind"]["speed"]
        city_name = data["name"]
        
        # 天氣圖標映射
        weather_icons = {
            "01d": "☀️", "01n": "🌙",
            "02d": "⛅", "02n": "☁️",
            "03d": "☁️", "03n": "☁️",
            "04d": "☁️", "04n": "☁️",
            "09d": "🌧️", "09n": "🌧️",
            "10d": "🌧️", "10n": "🌧️",
            "11d": "⛈️", "11n": "⛈️",
            "13d": "❄️", "13n": "❄️",
            "50d": "🌫️", "50n": "🌫️",
        }
        icon = data["weather"][0].get("icon", "")
        icon_emoji = weather_icons.get(icon, "🌡️")
        
        return (
            f"{icon_emoji} {city_name} 天氣資訊:\n"
            f"   天氣：{weather}\n"
            f"   溫度：{temp}°C (體感 {feels_like}°C)\n"
            f"   濕度：{humidity}%\n"
            f"   風速：{wind_speed} m/s"
        )
        
    except requests.exceptions.Timeout:
        return "錯誤：API 請求超時"
    except requests.exceptions.RequestException as e:
        return f"錯誤：網絡請求失敗 - {str(e)}"
    except Exception as e:
        return f"錯誤：{str(e)}"


@tool
def calculate(expression: str) -> str:
    """
    執行數學計算。

    Args:
        expression: 數學表達式，例如 "2 + 2", "10 * 5", "sqrt(16)"

    Returns:
        計算結果
    """
    try:
        # 安全處理常見數學運算
        expression = expression.replace("^", "**")

        # 處理常見數學函數
        allowed_names = {
            "sqrt": "** 0.5",
            "sin": "math.sin",
            "cos": "math.cos",
            "tan": "math.tan",
            "log": "math.log",
            "pi": "math.pi",
            "e": "math.e",
        }

        # 檢查是否只包含安全的字符
        safe_chars = set("0123456789+-*/.()** ")
        if not all(c in safe_chars or c.isalnum() for c in expression):
            return "錯誤：表達式包含不安全字符"

        # 執行計算
        import math
        result = eval(expression, {"__builtins__": {}, "math": math}, allowed_names)
        return f"計算結果：{expression} = {result}"
    except Exception as e:
        return f"計算錯誤：{str(e)}"


@tool
def web_search(query: str) -> str:
    """
    搜索互聯網獲取最新資訊。
    當用戶詢問天氣、計算以外的信息時使用，例如：
    - 新聞時事
    - 股票價格
    - 運動比賽結果
    - 最新技術資訊
    - 任何實時信息

    Args:
        query: 搜索關鍵詞，例如 "2026年最新AI新聞"、"比特幣價格"

    Returns:
        搜索結果摘要
    """
    try:
        from ddgs import DDGS
        
        with DDGS() as ddgs:
            results = ddgs.text(
                query, 
                max_results=8
            )
            
        if not results:
            return f"沒有找到關於 '{query}' 的結果"
        
        # 格式化結果
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            href = result.get('href', '')
            body = result.get('body', 'No description')
            
            formatted_results.append(
                f"{i}. {title}\n"
                f"   URL: {href}\n"
                f"   摘要: {body[:200]}..." if len(body) > 200 else f"   摘要: {body}"
            )
        
        return "搜索結果：\n\n" + "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"搜索錯誤：{str(e)}"


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """
    獲取當前時間。

    Args:
        timezone: 時區名稱，例如 "UTC", "Asia/Taipei", "America/New_York", "Europe/London"
                 默認為 "UTC"

    Returns:
        格式化當前時間字符串
    """
    from datetime import datetime
    import pytz
    
    try:
        # 如果沒有指定時區，使用本地時間
        if timezone == "UTC" or not timezone:
            now = datetime.now()
            tz = pytz.utc
            timezone_str = "UTC"
        else:
            # 嘗試解析時區
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
                timezone_str = timezone
            except pytz.exceptions.UnknownTimeZoneError:
                # 如果時區無效，返回 UTC 時間
                now = datetime.now(pytz.utc)
                timezone_str = "UTC (invalid timezone, defaulted)"
        
        # 格式化輸出
        return (
            f"🕐 當前時間\n"
            f"   時區: {timezone_str}\n"
            f"   日期時間: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   星期: {now.strftime('%A')}"
        )
        
    except Exception as e:
        return f"獲取時間錯誤：{str(e)}"


# 工具列表
tools = [get_weather, calculate, web_search, get_current_time]

# 將 Tool 轉換為 ToolNode
tool_node = ToolNode(tools)


# ============================================
# 輸出驗證層
# ============================================
def validate_and_parse_output(raw_output, has_tool_calls=False):
    """
    驗證和解析 LLM 輸出
    
    Args:
        raw_output: LLM 原始輸出
        has_tool_calls: 是否有 tool_calls（優先於 content 驗證）
        
    Returns:
        驗證結果字典
    """
    # 如果有 tool_calls，直接通過驗證（這是有效的工具調用請求）
    if has_tool_calls:
        return {
            "status": "valid",
            "parsed": "工具調用請求"
        }
    
    # 處理 None 或空輸出
    if raw_output is None or (isinstance(raw_output, str) and raw_output.strip() == ""):
        return {
            "status": "empty", 
            "retry": True, 
            "fallback": "輸出為空，請繼續完成推理並提供有效回應"
        }
    
    output_str = str(raw_output)
    output_lower = output_str.lower()
    
    # 檢查是否為無數據情況
    if "no data" in output_lower or "沒有找到" in output_str or "沒有結果" in output_str:
        return {
            "status": "no_data", 
            "retry": True, 
            "fallback": "搜索未找到結果，請如實告知用戶並嘗試建議不同的關鍵詞"
        }
    
    # 檢查必需字段（Action 或 Final Answer）
    has_action = "Action:" in output_str
    has_final = "Final Answer:" in output_str
    
    if not has_action and not has_final:
        return {
            "status": "incomplete",
            "retry": False,
            "reason": "輸出缺少必要字段 (Action 或 Final Answer)",
            "fallback": "請提供有效的 Action 或 Final Answer"
        }
    
    # 驗證通過
    return {
        "status": "valid",
        "parsed": output_str
    }


# ============================================
# 智能重試與恢復機制
# ============================================
def agent_execute_with_retry(messages, llm, max_retries=3):
    """
    帶恢復機制的 Agent 執行
    
    Args:
        messages: 對話消息列表
        llm: LLM 實例
        max_retries: 最大重試次數
        
    Returns:
        LLM 響應
    """
    for attempt in range(max_retries):
        try:
            # 調用 LLM
            response = llm.invoke(messages)
            
            # 獲取內容
            raw_output = response.content if hasattr(response, 'content') else str(response)
            
            # 檢查是否有 tool_calls
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
            
            # 驗證輸出（傳入 tool_calls 信息）
            validation = validate_and_parse_output(raw_output, has_tool_calls)
            
            if validation["status"] == "valid":
                return response
            
            elif validation["status"] in ["empty", "no_data"]:
                # 注入糾正提示
                correction_msg = HumanMessage(
                    content=f"""
                    上一條輸出無效: {raw_output}

                    {validation['fallback']}

                    請重新生成，確保輸出完整且有效。
                    """
                )
                messages = list(messages) + [response, correction_msg]
                print(f"\n🔄 [重試 {attempt + 1}/{max_retries}] 注入糾正提示")
            
            elif validation["status"] == "incomplete":
                # 不完整但可接受，返回響應讓流程繼續
                print(f"\n⚠️ [警告] {validation['reason']}")
                return response
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\n❌ [錯誤] 執行失敗: {str(e)}")
                raise
            print(f"\n🔄 [重試 {attempt + 1}/{max_retries}] 異常: {str(e)}")
    
    # 超過最大重試次數
    print(f"\n❌ 超過最大重試次數 ({max_retries})")
    return None


# ============================================
# 上下文滑動窗口
# ============================================
MAX_TOKENS = 4000  # 設定最大 token 限制


def estimate_tokens(text):
    """
    簡單估計 token 數量 (中文字約每字 1.5 token，英文約每詞 1.3 token)
    """
    if not text:
        return 0
    # 粗略估計：中文 * 1.5 + 英文單詞 * 1.3
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len(text.split())
    return int(chinese_chars * 1.5 + english_words * 1.3)


def calculate_token_count(messages):
    """
    計算消息列表的總 token 數
    """
    total = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total += estimate_tokens(msg.content)
    return total


def compress_message(msg):
    """
    壓縮單條消息，保留關鍵信息
    """
    if not hasattr(msg, 'content'):
        return msg
    
    content = msg.content
    # 如果消息包含工具結果，保留完整
    if hasattr(msg, 'type') and msg.type == 'tool':
        return msg
    
    # 如果是 AI 消息且太長，壓縮
    if len(content) > 500:
        # 保留開頭和結尾
        compressed = content[:250] + "\n...[省略]...\n" + content[-200:]
        # 創建新消息
        from langchain_core.messages import AIMessage
        return AIMessage(content=compressed)
    return msg


def manage_context_window(messages, max_tokens=MAX_TOKENS):
    """
    管理對話上下文，避免超出限制
    
    Args:
        messages: 消息列表
        max_tokens: 最大 token 限制
        
    Returns:
        管理後的消息列表
    """
    if not messages:
        return messages
    
    current_tokens = calculate_token_count(messages)
    
    if current_tokens <= max_tokens:
        return messages
    
    print(f"\n📊 [上下文管理] 當前 {current_tokens} tokens，壓縮至 {max_tokens} tokens")
    
    # 保留：第一條（系統提示）+ 最後 N 條
    # 壓縮：中間的歷史消息
    
    system_prompt = messages[0] if hasattr(messages[0], 'content') and "system" in str(type(messages[0])).lower() else None
    
    if system_prompt:
        # 壓縮中間部分
        compressed_history = []
        for msg in messages[1:-5]:
            compressed_history.append(compress_message(msg))
        
        # 保留最近 5 條
        recent = messages[-5:]
        
        return [system_prompt] + compressed_history + recent
    else:
        # 沒有系統提示，直接保留最後 8 條
        return messages[-8:]


# ============================================
# 2. 定義 Agent 狀態
# ============================================

class AgentState(TypedDict):
    """Agent 的狀態類型"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    should_continue: bool


# ============================================
# 3. 定義 Agent 節點
# ============================================

def should_continue(state: AgentState) -> bool:
    """
    判斷是否應該繼續執行工具調用

    Returns:
        True 如果需要繼續（調用工具），False 如果結束
    """
    messages = state["messages"]
    last_message = messages[-1]

    # 如果最後一條消息是 ToolMessage（工具執行結果），則需要再次調用 LLM 生成回應
    from langchain_core.messages import ToolMessage
    if isinstance(last_message, ToolMessage):
        return True

    # 如果最後一條消息有 tool_calls，說明模型請求調用工具
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return True

    return False


# ============================================
# Agent Node System Prompt - 限制一次只調用一個工具
# ============================================
AGENT_SYSTEM_PROMPT = """你是一個專業的 AI 助手，擅長使用工具來完成任務。

## 可用工具：
- get_weather(city) - 獲取城市天氣資訊，例如 "Taipei"、"Tokyo"、"New York"
- calculate(expression) - 執行數學計算  
- web_search(query) - 搜索互聯網獲取最新資訊
- get_current_time(timezone) - 獲取當前時間，timezone 可選如 "UTC"、"Asia/Taipei"、"America/New_York"

## 執行流程：

1. 閱讀 Deep Reasoning 的任務分析和執行計劃

2. 如果步驟需要調用工具，請使用以下格式調用工具（一次一個）；如果不需要，則跳到第 5 步：

Action: [工具名稱]
Action Input: [輸入參數]
Thought: [解釋為什麼需要這個工具]

3. 獲得工具結果後，必須：
   - 解釋工具返回的關鍵信息
   - 明確説明下一步要做什麼
   - 如果結果為空，説明原因並提供替代方案

4. **步驟限制**：最多執行 5 次工具調用，超過後必須輸出最終結果

5. 如果不需要繼續調用工具，生成最終回答：

Final Answer: [完整且有價值的回答]

"""


def call_model(state: AgentState):
    """
    調用 LLM 模型 (使用驗證、重試和上下文管理)
    """
    messages = state["messages"]

    # 初始化 LLM
    llm = ChatOllama(
        model="qwen3.5:9b",
        temperature=0.3,
    )

    # 綁定工具
    llm_with_tools = llm.bind_tools(tools)

    # 插入 system prompt 到消息開頭
    full_messages = [
        SystemMessage(content=AGENT_SYSTEM_PROMPT)
    ] + list(messages)

    # 管理上下文窗口（避免超限）
    full_messages = manage_context_window(full_messages)

    # 使用帶重試的機制執行
    response = agent_execute_with_retry(full_messages, llm_with_tools, max_retries=3)
    
    if response is None:
        # 返回錯誤訊息
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content="抱歉，處理過程中遇到問題，請嘗試更簡單的任務")]}

    return {"messages": [response]}


def deep_reasoning(state: AgentState):
    """
    Deep Reasoning 節點：分析任務並分解為子任務
    
    這個節點在主要 LLM 調用之前執行，
    對用戶請求進行深度分析和任務規劃。
    """
    messages = state["messages"]
    
    # 獲取用戶最新的問題
    user_query = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
    
    if not user_query:
        return {"messages": []}
    
    # 初始化 LLM (用於推理)
    llm = ChatOllama(
        model="qwen3.5:9b",
        temperature=0.5,  # 較高的溫度以獲得更多樣化的推理
    )
    
    # 構建推理 prompt
    reasoning_prompt = [
        SystemMessage(content=DEEP_REASONING_SYSTEM_PROMPT),
        HumanMessage(content=f"請分析以下用戶請求：\n{user_query}")
    ]
    
    # 調用 LLM 進行深度推理
    response = llm.invoke(reasoning_prompt)
    
    # 返回推理結果作為一條 AI 消息
    return {"messages": [response]}


# ============================================
# 4. 構建 LangGraph
# ============================================

def create_agent():
    """
    創建 LangGraph Agent

    使用 ReAct 模式 + Deep Reasoning：
    1. Deep Reasoning -> 分析任務並分解為子任務
    2. Model -> 決定是否調用工具
    3. 如果需要調用工具 -> Tool Node
    4. 工具執行後 -> 回到 Model
    5. 如果不需要調用工具 -> 結束
    """
    # 創建狀態圖
    workflow = StateGraph(AgentState)

    # 添加節點
    workflow.add_node("reasoning", deep_reasoning)  # Deep Reasoning 節點
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # 設置入口點
    workflow.set_entry_point("reasoning")
    
    # Deep Reasoning 後進入 agent
    workflow.add_edge("reasoning", "agent")

    # 添加條件邊
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            True: "tools",   # 繼續調用工具
            False: END,      # 結束
        }
    )

    # 工具執行後回到 agent
    workflow.add_edge("tools", "agent")

    # 編譯圖
    return workflow.compile()


# ============================================
# 5. 主程式
# ============================================

def main():
    """
    主程式 - 演示 Agent 功能
    """
    print("=" * 60)
    print("🚀 LangGraph Agent - 天氣搜索 + 計算工具 + 網絡搜索")
    print("=" * 60)
    print()

    # 創建 Agent
    agent = create_agent()

    # 測試案例
    test_queries = [
        #"香港現在的天氣如何？",
        #"請幫我計算 125 * 8 的結果",
        #"東京的天氣怎麼樣？",
        #"計算 (15 + 25) * 2",
        #"新加坡的天氣和溫度是多少？",
        #"誰是現在的特斯拉CEO？",  # 測試網絡搜索
        #"比特幣現在多少錢？",    # 測試網絡搜索
        #"請幫我分析一下，未來一周台北的天氣趨勢如何？",  # 複雜任務，需要多次工具調用
        #"香港現在的天氣如何？幫我查一下附近有什麼合適的活動可以做？",  # 複雜任務，需要多次工具調用
        "66+43人民幣等於多少港元？",  # 複合任務：需要先計算人民幣金額，然後搜索當前匯率進行換算
        #"請幫我查一下現在的時間"  # 複合任務：需要先獲取當前時間，然後使用 web_search 查詢倫敦當前時間
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"測試 {i}: {query}")
        print("=" * 60)

        # 創建初始消息
        initial_state = {
            "messages": [
                HumanMessage(content=query)
            ],
        }

        # 執行 Agent (使用 streaming)
        try:
            print("\n" + "-" * 40)
            print("🔄 ReAct 推理過程:")
            print("-" * 40)
            
            all_messages = []
            
            # 使用 streaming 模式
            for event in agent.stream(initial_state):
                # event 是一個字典，包含節點名稱和輸出
                for node_name, node_output in event.items():
                    if node_name == "reasoning":
                        # Deep Reasoning 節點的輸出
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
                                all_messages.append(msg)
                                if hasattr(msg, "content") and msg.content:
                                    print(f"\n🧠 [Deep Reasoning]")
                                    print(f"   {msg.content}")
                    elif node_name == "agent":
                        # Agent 節點的輸出
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
                                all_messages.append(msg)
                                # 顯示 reasoning (tool calls)
                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    for tc in msg.tool_calls:
                                        reasoning = tc.get("reasoning", "")
                                        if reasoning:
                                            print(f"\n💭 [Thought]")
                                            print(f"   {reasoning}")
                                        
                                        tool_name = tc.get("name", "unknown")
                                        tool_args = tc.get("args", {})
                                        print(f"\n🔧 [Action]")
                                        print(f"   工具: {tool_name}")
                                        print(f"   參數: {tool_args}")
                                
                                # 顯示 content (可能是中間回應或最終回應)
                                if hasattr(msg, "content") and msg.content:
                                    # 檢查是否包含 tool 調用結果的引用
                                    if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                                        # 純 content，顯示為回應
                                        print("\n" + "-" * 40)
                                        print(f"\n✅ [Agent Response]")
                                        print(f"   {msg.content}")                                    

                    
                    elif node_name == "tools":
                        # Tools 節點的輸出
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
                                all_messages.append(msg)
                                from langchain_core.messages import ToolMessage
                                if isinstance(msg, ToolMessage):
                                    content = msg.content if len(msg.content) < 300 else msg.content[:300] + "..."
                                    print(f"\n👁️ [Observation]")
                                    print(f"   {content}")
            """
            print("\n" + "-" * 40)

            # 調試：顯示所有消息
            print("\n📋 [Debug] 所有消息:")
            for idx, m in enumerate(all_messages):
                msg_type = type(m).__name__
                if hasattr(m, "tool_calls") and m.tool_calls:
                    print(f"  {idx}: {msg_type} - tool_calls: {[tc.get('name') for tc in m.tool_calls]}")
                elif hasattr(m, "content") and m.content:
                    content_preview = m.content[:100] + "..." if len(m.content) > 100 else m.content
                    print(f"  {idx}: {msg_type} - {content_preview}")
                else:
                    print(f"  {idx}: {msg_type} - (empty)")
            """
        except Exception as e:
            print(f"\n❌ 錯誤: {str(e)}")

    print("\n" + "=" * 60)
    print("✨ 測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
