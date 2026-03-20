"""
服務層 - Ollama LLM 和 Agent 服務
"""
import json
import operator
from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any, Generator, AsyncGenerator
from datetime import datetime
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import requests

from src.tools import TOOLS
from src.prompts import AGENT_SYSTEM_PROMPT, DEEP_REASONING_SYSTEM_PROMPT
from src.utils import estimate_tokens, calculate_token_count, manage_context_window, MAX_TOKENS, agent_execute_with_retry
from api.database import get_threads_collection, get_messages_collection


# ============================================
# Ollama 服務
# ============================================

class OllamaService:
    """Ollama LLM 服務類"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._current_model = "llama3.2"
        self._llm_instance = None
    
    @property
    def current_model(self) -> str:
        return self._current_model
    
    def set_model(self, model: str) -> None:
        """設置當前使用的模型"""
        self._current_model = model
        self._llm_instance = None  # 重置 LLM 實例
    
    def get_llm(self, model: Optional[str] = None, **kwargs) -> ChatOllama:
        """獲取 LLM 實例"""
        model = model or self._current_model
        
        # 如果模型改變了，重置實例
        if self._llm_instance is None or self._current_model != model:
            self._current_model = model
            self._llm_instance = ChatOllama(
                model=model,
                base_url=self.base_url,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2048),
                streaming=kwargs.get("streaming", True),
            )
        
        return self._llm_instance
    
    def list_models(self) -> List[Dict[str, Any]]:
        """列出所有可用的 Ollama 模型"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """獲取特定模型的資訊"""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting model info: {e}")
            return None


# ============================================
# 全域實例
# ============================================

ollama_service = OllamaService()


# ============================================
# 對話上下文管理
# ============================================

class ConversationContext:
    """對話上下文管理類"""
    
    def __init__(self, max_tokens: int = MAX_TOKENS):
        self.max_tokens = max_tokens
        self._sessions: Dict[str, List[Any]] = {}
    
    def get_messages(self, thread_id: str) -> List[Any]:
        """獲取會話消息"""
        return self._sessions.get(thread_id, [])
    
    def add_message(self, thread_id: str, message: Any) -> None:
        """添加消息到會話"""
        if thread_id not in self._sessions:
            self._sessions[thread_id] = []
        self._sessions[thread_id].append(message)
    
    def clear_session(self, thread_id: str) -> None:
        """清除會話"""
        if thread_id in self._sessions:
            del self._sessions[thread_id]
    
    def get_token_count(self, thread_id: str) -> int:
        """獲取會話的 token 數"""
        messages = self.get_messages(thread_id)
        return calculate_token_count(messages)
    
    def manage_context(self, thread_id: str) -> List[Any]:
        """管理上下文窗口"""
        messages = self.get_messages(thread_id)
        managed = manage_context_window(messages, self.max_tokens)
        self._sessions[thread_id] = managed
        return managed


# 全域對話上下文實例
conversation_context = ConversationContext()


# ============================================
# Message Saving Functions
# ============================================


def save_message_to_db(thread_id: str, role: str, content: str):
    """
    Save a message to MongoDB
    
    Args:
        thread_id: Thread ID
        role: Message role (user, assistant)
        content: Message content
    """
    try:
        messages = get_messages_collection()
        threads = get_threads_collection()
        
        message_doc = {
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow()
        }
        
        messages.insert_one(message_doc)
        
        # Update thread's updated_at
        threads.update_one(
            {"_id": thread_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
    except Exception as e:
        print(f"Error saving message to DB: {e}")


# ============================================
# LangGraph Agent
# ============================================

# 將 Tool 轉換為 ToolNode
tool_node = ToolNode(TOOLS)


class AgentState(TypedDict):
    """Agent 的狀態類型"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    should_continue: bool


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


def call_model(state: AgentState, model: str = "qwen3.5:9b"):
    """
    調用 LLM 模型 (使用驗證、重試和上下文管理)
    """
    messages = state["messages"]

    # 初始化 LLM
    llm = ChatOllama(
        model=model,
        temperature=0.3,
    )

    # 綁定工具
    llm_with_tools = llm.bind_tools(TOOLS)

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


def deep_reasoning(state: AgentState, model: str = "qwen3.5:9b"):
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
        model=model,
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


def create_agent(model: str = "qwen3.5:9b"):
    """
    創建 LangGraph Agent

    使用 ReAct 模式 + Deep Reasoning：
    1. Deep Reasoning -> 分析任務並分解為子任務
    2. Model -> 決定是否調用工具
    3. 如果需要調用工具 -> Tool Node
    4. 工具執行後 -> 回到 Model
    5. 如果不需要調用工具 -> 結束
    """
    from typing import TypedDict, Annotated, Sequence
    
    class AgentState(TypedDict):
        """Agent 的狀態類型"""
        messages: Annotated[Sequence[BaseMessage], operator.add]
        should_continue: bool
    
    # 創建狀態圖
    workflow = StateGraph(AgentState)

    # 添加節點
    workflow.add_node("reasoning", lambda state: deep_reasoning(state, model))  # Deep Reasoning 節點
    workflow.add_node("agent", lambda state: call_model(state, model))
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
# LangGraph Agent streaming 服務
# ============================================

async def stream_agent(
    message: str,
    model: str = "qwen3.5:9b",
    thread_id: str = "default"
):
    """
    使用 LangGraph Agent 執行流式輸出
    
    Args:
        message: 用戶消息
        model: 模型名稱 (默認: qwen3.5:9b)
        thread_id: 會話 ID
    
    Yields:
        流式輸出事件
    """
    # Save user message to MongoDB
    save_message_to_db(thread_id, "user", message)
    
    # 創建 Agent
    agent = create_agent(model)
    
    # 獲取會話歷史消息（用於上下文）
    history_messages = conversation_context.get_messages(thread_id)
    
    # 構建初始狀態
    # 將歷史消息與新消息結合
    initial_messages = list(history_messages)
    initial_messages.append(HumanMessage(content=message))
    
    initial_state = {
        "messages": initial_messages,
    }
    
    total_tokens = 0
    tool_call_count = 0
    final_response = ""  # Accumulate final response
    
    try:
        # 使用 streaming 模式
        for event in agent.stream(initial_state):
            # event 是一個字典，包含節點名稱和輸出
            for node_name, node_output in event.items():
                if node_name == "reasoning":
                    # Deep Reasoning 節點的輸出
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if hasattr(msg, "content") and msg.content:
                                content = msg.content
                                total_tokens += estimate_tokens(content)
                                yield json.dumps({
                                    "type": "reasoning",
                                    "content": content
                                })
                
                elif node_name == "agent":
                    # Agent 節點的輸出
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            # 顯示 tool_calls
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tool_name = tc.get("name", "unknown")
                                    tool_args = tc.get("args", {})
                                    reasoning = tc.get("reasoning", "")
                                    
                                    tool_call_count += 1
                                    yield json.dumps({
                                        "type": "tool_call",
                                        "tool": tool_name,
                                        "args": tool_args,
                                        "reasoning": reasoning
                                    })
                            
                            # 顯示 content
                            if hasattr(msg, "content") and msg.content:
                                content = msg.content
                                # 檢查是否為最終答案 (沒有 tool_calls)
                                if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                                    total_tokens += estimate_tokens(content)
                                    final_response += content  # Accumulate final response
                                    yield json.dumps({
                                        "type": "final",
                                        "content": content
                                    })

                elif node_name == "tools":
                    # Tools 節點的輸出
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if isinstance(msg, ToolMessage):
                                tool_name = msg.name if hasattr(msg, 'name') else "unknown"
                                content = msg.content
                                total_tokens += estimate_tokens(content)
                                yield json.dumps({
                                    "type": "tool_result",
                                    "tool": tool_name,
                                    "result": content
                                })

    except Exception as e:
        yield json.dumps({
            "type": "error",
            "error": str(e)
        })
    
    # 保存消息到上下文
    conversation_context.add_message(thread_id, HumanMessage(content=message))
    
    # Save assistant response to MongoDB
    if final_response:
        save_message_to_db(thread_id, "assistant", final_response)
    
    # 發送完成信號
    yield json.dumps({
        "type": "done",
        "token_count": total_tokens,
        "tool_calls": tool_call_count
    }) + "\n"


# ============================================
# 聊天服務 (非 LangGraph)
# ============================================

def chat(
    message: str,
    model: str = "llama3.2",
    max_tokens: int = 2048,
    temperature: float = 0.7,
    stream: bool = True,
    thread_id: str = "default"
) -> tuple[str, int]:
    """
    執行聊天請求
    
    Args:
        message: 用戶消息
        model: 模型名稱
        max_tokens: 最大 token 數
        temperature: 溫度
        stream: 是否流式輸出
        thread_id: 會話 ID
    
    Returns:
        (回應內容, token 數)
    """
    # 獲取 LLM
    llm = ollama_service.get_llm(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        streaming=stream
    )
    
    # 綁定工具
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # 獲取並管理上下文
    messages = conversation_context.manage_context(thread_id)
    
    # 系統提示
    if not messages or not isinstance(messages[0], SystemMessage):
        system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
        messages = [system_msg] + messages
    
    # 添加用戶消息
    user_message = HumanMessage(content=message)
    messages = messages + [user_message]
    
    # 執行調用
    response = llm_with_tools.invoke(messages)
    
    # 獲取回應內容
    content = response.content if hasattr(response, 'content') else str(response)
    
    # 計算 token
    token_count = estimate_tokens(content)
    
    # 保存到上下文
    conversation_context.add_message(thread_id, user_message)
    conversation_context.add_message(thread_id, response)
    
    return content, token_count


async def chat_stream(
    message: str,
    model: str = "llama3.2",
    max_tokens: int = 2048,
    temperature: float = 0.7,
    thread_id: str = "default"
) -> AsyncGenerator[str, None]:
    """
    流式聊天請求
    
    Args:
        message: 用戶消息
        model: 模型名稱
        max_tokens: 最大 token 數
        temperature: 溫度
        thread_id: 會話 ID
    
    Yields:
        流式輸出片段
    """
    # 獲取 LLM
    llm = ollama_service.get_llm(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        streaming=True
    )
    
    # 綁定工具
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # 獲取並管理上下文
    messages = conversation_context.manage_context(thread_id)
    
    # 系統提示
    if not messages or not isinstance(messages[0], SystemMessage):
        system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
        messages = [system_msg] + messages
    
    # 添加用戶消息
    user_message = HumanMessage(content=message)
    request_messages = messages + [user_message]
    
    # 流式調用
    accumulated_content = ""
    
    async for chunk in llm_with_tools.astream(request_messages):
        if hasattr(chunk, 'content') and chunk.content:
            content_chunk = chunk.content
            accumulated_content += content_chunk
            yield content_chunk
    
    # 計算 token
    token_count = estimate_tokens(accumulated_content)
    
    # 保存到上下文
    conversation_context.add_message(thread_id, user_message)
    ai_message = AIMessage(content=accumulated_content)
    conversation_context.add_message(thread_id, ai_message)
    
    # 發送完成信號
    yield f"[DONE:{token_count}]"


def get_token_info(thread_id: str = "default") -> Dict[str, Any]:
    """獲取當前上下文窗口的 token 資訊"""
    current_tokens = conversation_context.get_token_count(thread_id)
    max_tokens = conversation_context.max_tokens
    usage_percentage = (current_tokens / max_tokens * 100) if max_tokens > 0 else 0
    
    return {
        "total_tokens": current_tokens,
        "max_tokens": max_tokens,
        "usage_percentage": round(usage_percentage, 2),
        "messages_count": len(conversation_context.get_messages(thread_id))
    }
