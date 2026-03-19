"""
LangGraph Agent 工廠模組
"""
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.nodes import call_model, deep_reasoning, should_continue, create_tool_node


def create_agent(llm, tools, checkpointer=None):
    """
    創建 LangGraph Agent
    
    Args:
        llm: LLM 實例
        tools: 工具列表
        checkpointer: 檢查點（可選）
        
    Returns:
        編譯後的圖
    """
    # 定義狀態
    class AgentState(dict):
        pass
    
    # 創建工具節點
    tool_node = ToolNode(tools)
    
    # 構建圖
    workflow = StateGraph(AgentState)
    
    # 添加節點
    workflow.add_node("agent", lambda state: call_model(state, llm, tools))
    workflow.add_node("reasoning", lambda state: deep_reasoning(state, llm))
    workflow.add_node("tools", tool_node)
    
    # 設置入口點
    workflow.set_entry_point("agent")
    
    # 添加條件邊
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    
    # 從工具返回 agent
    workflow.add_edge("tools", "agent")
    
    # 編譯圖
    compiled = workflow.compile(checkpointer=checkpointer)
    
    return compiled


def stream_agent_response(agent, user_input, config=None):
    """
    流式輸出 Agent 響應
    
    Args:
        agent: 編譯後的圖
        user_input: 用戶輸入
        config: 配置（可選）
        
    Yields:
        流式輸出片段
    """
    if config is None:
        config = {"configurable": {"thread_id": "default"}}
    
    inputs = {"messages": [("user", user_input)]}
    
    for chunk in agent.stream(inputs, config):
        if "agent" in chunk:
            content = chunk["agent"].get("messages", [])
            if content and hasattr(content[-1], "content"):
                yield content[-1].content
        elif "tools" in chunk:
            # 工具調用中
            pass
