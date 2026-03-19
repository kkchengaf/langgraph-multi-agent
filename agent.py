"""
LangGraph Agent - 天氣搜索 + 計算工具 + 網絡搜索

這是一個使用 LangGraph 構建的 AI Agent，具備以下能力：
1. 天氣搜索 - 獲取指定城市的天氣資訊
2. 數學計算 - 執行數學運算
3. 網絡搜索 - 搜索互聯網獲取最新資訊
4. 根據任務自主選擇合適的工具

使用 LangGraph 的 ReAct 模式實現 Tool Calling

項目結構：
- src/
│   ├── __init__.py      # 模組初始化
│   ├── tools.py         # 工具定義
│   ├── prompts.py       # 系統提示詞
│   ├── utils.py         # 驗證、重試、上下文管理
│   ├── nodes.py         # LangGraph 節點
│   └── agent.py         # Agent 工廠
- agent.py               # 主程式入口
- README.md              # 項目文檔
"""

import operator
import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

# 載入 .env 文件
load_dotenv()

# ============================================
# 從 src 模組導入
# ============================================
from src.tools import TOOLS, get_weather, calculate, web_search, get_current_time
from src.prompts import AGENT_SYSTEM_PROMPT, DEEP_REASONING_SYSTEM_PROMPT
from src.utils import (
    validate_and_parse_output,
    agent_execute_with_retry,
    manage_context_window,
    MAX_TOKENS,
    estimate_tokens,
    calculate_token_count,
    compress_message
)

# 工具列表
tools = TOOLS

# 將 Tool 轉換為 ToolNode
tool_node = ToolNode(tools)


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
    if isinstance(last_message, ToolMessage):
        return True

    # 如果最後一條消息有 tool_calls，說明模型請求調用工具
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return True

    return False


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
        "請幫我計算 125 * 8 的結果",
        #"誰是現在的特斯拉CEO？",  # 測試網絡搜索
        "比特幣現在多少錢？",    # 測試網絡搜索
        #"請幫我分析一下，未來一周台北的天氣趨勢如何？",  # 複雜任務，需要多次工具調用
        "香港現在的天氣如何？幫我查一下附近有什麼合適的活動可以做？",  # 複雜任務，需要多次工具調用
        "66+43人民幣等於多少港元？",  # 複合任務：需要先計算人民幣金額，然後搜索當前匯率進行換算
        "請幫我查一下現在的時間"  # 複合任務：需要先獲取當前時間
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
                                if isinstance(msg, ToolMessage):
                                    content = msg.content if len(msg.content) < 300 else msg.content[:300] + "..."
                                    print(f"\n👁️ [Observation]")
                                    print(f"   {content}")
            
            print("\n" + "-" * 40)

            # 調試：顯示所有消息
            """
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
