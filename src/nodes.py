"""
LangGraph 節點模組
"""
from langgraph.prebuilt import ToolNode
from src.prompts import AGENT_SYSTEM_PROMPT, DEEP_REASONING_SYSTEM_PROMPT
from src.utils import agent_execute_with_retry, manage_context_window


def call_model(state, llm, tools):
    """
    調用 LLM 生成回應
    
    Args:
        state: 圖狀態
        llm: LLM 實例
        tools: 工具列表
        
    Returns:
        更新後的狀態
    """
    messages = state["messages"]
    
    # 管理上下文窗口
    messages = manage_context_window(messages)
    
    # 綁定工具到 LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # 系統提示
    system_message = {"role": "system", "content": AGENT_SYSTEM_PROMPT}
    
    # 構建請求
    request_messages = [system_message] + messages
    
    # 執行並驗證
    response = agent_execute_with_retry(request_messages, llm_with_tools)
    
    return {
        "messages": messages + [response]
    }


def deep_reasoning(state, llm):
    """
    深度推理節點 - 處理複雜問題
    
    Args:
        state: 圖狀態
        llm: LLM 實例
        
    Returns:
        更新後的狀態
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None
    
    if not last_message or not hasattr(last_message, 'content'):
        return {"messages": messages}
    
    user_input = last_message.content
    
    # 構建推理請求
    reasoning_messages = [
        {"role": "system", "content": DEEP_REASONING_SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]
    
    # 調用 LLM 進行深度推理
    reasoning_response = llm.invoke(reasoning_messages)
    
    return {
        "messages": messages + [reasoning_response]
    }


def should_continue(state):
    """
    條件邊：判斷是否繼續
    
    Args:
        state: 圖狀態
        
    Returns:
        "continue" 或 "end"
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None
    
    if not last_message:
        return "end"
    
    # 檢查是否有 tool_calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "continue"
    
    # 檢查是否包含 Final Answer
    content = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    if "Final Answer:" in content:
        return "end"
    
    # 檢查是否包含 Action（需要工具調用）
    if "Action:" in content and "Action Input:" in content:
        return "continue"
    
    return "end"


def create_tool_node(tools):
    """
    創建工具節點
    
    Args:
        tools: 工具列表
        
    Returns:
        ToolNode 實例
    """
    return ToolNode(tools)
