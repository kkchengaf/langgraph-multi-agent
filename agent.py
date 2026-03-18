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
    獲取指定城市的天氣資訊。

    Args:
        city: 城市名稱，例如 "台北"、"東京"、"紐約"

    Returns:
        天氣資訊字符串
    """
    # 模擬天氣數據（實際使用時可以接入天氣 API）
    weather_data = {
        "台北": "☀️ 天氣：晴朗，溫度 28°C，濕度 65%",
        "東京": "🌧️ 天氣：多雲有小雨，溫度 18°C，濕度 80%",
        "紐約": "🌤️ 天氣：局部多雲，溫度 15°C，濕度 55%",
        "倫敦": "🌧️ 天氣：陰天有雨，溫度 12°C，濕度 85%",
        "巴黎": "🌤️ 天氣：多雲，溫度 16°C，濕度 60%",
        "悉尼": "☀️ 天氣：晴朗，溫度 24°C，濕度 50%",
        "香港": "🌡️ 天氣：炎熱，溫度 30°C，濕度 75%",
        "新加坡": "🌧️ 天氣：雷陣雨，溫度 32°C，濕度 90%",
        "首爾": "🌤️ 天氣：晴朗，溫度 20°C，濕度 45%",
        "上海": "🌧️ 天氣：多雲，溫度 22°C，濕度 70%",
    }

    return weather_data.get(city, f"抱歉，沒有找到 {city} 的天氣資訊")


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


def call_model(state: AgentState):
    """
    調用 LLM 模型
    """
    messages = state["messages"]

    # 初始化 LLM
    llm = ChatOllama(
        model="qwen3.5:9b",#"gemma3:12b",
        temperature=0.3,
    )

    # 綁定工具
    llm_with_tools = llm.bind_tools(tools)

    # 調用模型
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


# ============================================
# 4. 構建 LangGraph
# ============================================

def create_agent():
    """
    創建 LangGraph Agent

    使用 ReAct 模式：
    1. Model -> 決定是否調用工具
    2. 如果需要調用工具 -> Tool Node
    3. 工具執行後 -> 回到 Model
    4. 如果不需要調用工具 -> 結束
    """
    # 創建狀態圖
    workflow = StateGraph(AgentState)

    # 添加節點
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # 設置入口點
    workflow.set_entry_point("agent")

    # 添加條件邊
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            True: "tools",   # 繼續調用工具
            False: END,      # 結束 (添加False處理)
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
        "台北現在的天氣如何？",
        "請幫我計算 125 * 8 的結果",
        #"東京的天氣怎麼樣？",
        #"計算 (15 + 25) * 2",
        #"新加坡的天氣和溫度是多少？",
        "誰是現在的特斯拉CEO？",  # 測試網絡搜索
        "比特幣現在多少錢？",    # 測試網絡搜索
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

        # 執行 Agent
        try:
            result = agent.invoke(initial_state)

            # 獲取最終回應
            final_message = result["messages"][-1]
            print(f"\n✅ Agent 回應:")
            print(f"   {final_message.content}")

        except Exception as e:
            print(f"\n❌ 錯誤: {str(e)}")

    print("\n" + "=" * 60)
    print("✨ 測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
