"""
LangGraph 節點模組
"""
from langgraph.prebuilt import ToolNode
from src.prompts import AGENT_SYSTEM_PROMPT, DEEP_REASONING_SYSTEM_PROMPT, DEEP_REASONING_WITH_HISTORY_PROMPT
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


def deep_reasoning(state, llm, max_retries=3, min_response_length=20):
    """
    深度推理節點 - 處理複雜問題，包含對話歷史
    
    Args:
        state: 圖狀態
        llm: LLM 實例
        max_retries: 最大重試次數
        min_response_length: 最小響應長度
        
    Returns:
        更新後的狀態
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None
    
    if not last_message or not hasattr(last_message, 'content'):
        return {"messages": messages}
    
    user_input = last_message.content
    
    # 提取對話歷史中的用戶消息
    user_history = []
    for msg in messages[:-1]:  # 排除最後一條（當前用戶消息）
        if hasattr(msg, 'type') and msg.type == 'human':
            user_history.append(msg.content)
        elif hasattr(msg, 'role') and msg.role == 'user':
            user_history.append(msg.content)
    
    # 構建包含歷史的推理請求
    if user_history:
        # 有歷史，使用增強版 prompt
        history_text = "\n".join([f"- Q{i+1}: {q}" for i, q in enumerate(user_history[-5:])])  # 只取最近5條
        user_content = f"""## 對話歷史（最近5輪）：
{history_text}

## 當前用戶請求：
{user_input}"""
        system_prompt = DEEP_REASONING_WITH_HISTORY_PROMPT
    else:
        # 無歷史，使用標準 prompt
        user_content = user_input
        system_prompt = DEEP_REASONING_SYSTEM_PROMPT
    
    # 構建推理請求
    reasoning_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    # 重試機制
    last_error = None
    for attempt in range(max_retries):
        try:
            # 調用 LLM 進行深度推理
            reasoning_response = llm.invoke(reasoning_messages)
            
            # 檢查響應是否有效
            response_content = ""
            if hasattr(reasoning_response, 'content'):
                response_content = reasoning_response.content
            elif isinstance(reasoning_response, str):
                response_content = reasoning_response
            
            # 檢查響應是否为空或太短
            if response_content and len(response_content.strip()) >= min_response_length:
                # 響應有效，返回結果
                return {
                    "messages": messages + [reasoning_response]
                }
            else:
                # 響應太短，準備重試
                last_error = f"Response too short: {len(response_content)} chars"
                if attempt < max_retries - 1:
                    # 添加額外提示要求更詳細的回复
                    reasoning_messages.append({
                        "role": "user", 
                        "content": "你的回复太簡短了，請提供更詳細的分析，包括任務分析、所需工具和執行計劃。"
                    })
                
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                continue
    
    # 所有重試都失敗了，返回帶有錯誤信息的響應
    error_response = f"[推理失敗: {last_error}] 用戶請求: {user_input}"
    from langchain_core.messages import AIMessage
    return {
        "messages": messages + [AIMessage(content=error_response)]
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
