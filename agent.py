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
                max_results=10
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


# 工具列表
tools = [get_weather, calculate, web_search]

# 將 Tool 轉換為 ToolNode
tool_node = ToolNode(tools)


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

## 重要規則：一次只能調用一個工具

1. **每次只調用一個工具**：不要一次請求多個工具，必須等工具返回結果後再決定下一步
2. **按順序執行**：如果需要多個工具，請一個一個調用
3. **使用推理**：在調用工具前，說明你的思考過程

## 可用工具：
- get_weather(city) - 獲取城市天氣資訊
- calculate(expression) - 執行數學計算  
- web_search(query) - 搜索互聯網

## 輸出格式：
當你需要使用工具時：
```
Thought: [你的推理過程]
Action: [工具名稱]
Action Input: [輸入參數]
```

當你不需要使用工具時：
```
Thought: [你的推理過程]
Final Answer: [你的最終回答]
```
"""


def call_model(state: AgentState):
    """
    調用 LLM 模型 (使用 system prompt 限制一次一個工具)
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

    # 調用模型
    response = llm_with_tools.invoke(full_messages)

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
        "香港現在的天氣如何？幫我查一下附近有什麼合適的活動可以做？",  # 複雜任務，需要多次工具調用
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
            
            # 使用 streaming 模式
            for event in agent.stream(initial_state):
                # event 是一個字典，包含節點名稱和輸出
                for node_name, node_output in event.items():
                    if node_name == "reasoning":
                        # Deep Reasoning 節點的輸出
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
                                if hasattr(msg, "content") and msg.content:
                                    print(f"\n🧠 [Deep Reasoning]")
                                    print(f"   {msg.content}")
                    elif node_name == "agent":
                        # Agent 節點的輸出
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
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
                                
                                # 顯示 streaming 內容
                                elif hasattr(msg, "content") and msg.content:
                                    print("\n" + "-" * 40)
                                    print(f"\n✅ Agent 回應:")
                                    print(f"   {msg.content}")                                    

                    
                    elif node_name == "tools":
                        # Tools 節點的輸出
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
                                from langchain_core.messages import ToolMessage
                                if isinstance(msg, ToolMessage):
                                    content = msg.content if len(msg.content) < 300 else msg.content[:300] + "..."
                                    print(f"\n👁️ [Observation]")
                                    print(f"   {content}")
            
            print("\n" + "-" * 40)

        except Exception as e:
            print(f"\n❌ 錯誤: {str(e)}")

    print("\n" + "=" * 60)
    print("✨ 測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
