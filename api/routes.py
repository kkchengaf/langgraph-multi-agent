"""
API 路由 - 定義所有 API 端點
"""
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from api.models import (
    ChatRequest,
    ChatResponse,
    TokenCountResponse,
    ModelListResponse,
    OllamaModel,
    StreamChunk,
    ErrorResponse
)
from api.services import (
    ollama_service,
    chat,
    chat_stream,
    stream_agent,
    get_token_info,
    conversation_context
)


# ============================================
# 路由器
# ============================================

router = APIRouter()


# ============================================
# 依賴項
# ============================================

def get_ollama_service():
    """獲取 Ollama 服務"""
    return ollama_service


# ============================================
# 端點
# ============================================

@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """
    獲取所有可用的 Ollama 模型列表
    
    Returns:
        可用模型列表
    """
    try:
        models = ollama_service.list_models()
        
        model_list = []
        for m in models:
            model_list.append(OllamaModel(
                name=m.get("name", ""),
                size=m.get("size"),
                modified_at=m.get("modified_at"),
                digest=m.get("digest")
            ))
        
        return ModelListResponse(
            models=model_list,
            count=len(model_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def send_chat(request: ChatRequest):
    """
    發送聊天消息
    
    支援流式輸出 (SSE) 和非流式輸出
    
    Args:
        request: 聊天請求
    
    Returns:
        AI 回應 (流式或非流式)
    """
    # 驗證模型
    available_models = ollama_service.list_models()
    model_names = [m.get("name") for m in available_models]
    
    if request.model and model_names and request.model not in model_names:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not found. Available models: {model_names}"
        )
    
    if request.stream:
        # 流式輸出
        return StreamingResponse(
            stream_chat_sse(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # 非流式輸出
        try:
            content, token_count = chat(
                message=request.message,
                model=request.model or "llama3.2",
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature or 0.7,
                stream=False,
                thread_id=request.thread_id or "default"
            )
            
            return ChatResponse(
                message=content,
                model=request.model or "llama3.2",
                token_count=token_count,
                done=True
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_sse(request: ChatRequest):
    """
    流式聊天 SSE 輸出
    
    Args:
        request: 聊天請求
    
    Yields:
        SSE 事件
    """
    token_count = 0
    
    try:
        async for chunk in chat_stream(
            message=request.message,
            model=request.model or "llama3.2",
            max_tokens=request.max_tokens or 2048,
            temperature=request.temperature or 0.7,
            thread_id=request.thread_id or "default"
        ):
            # 檢查是否為完成信號
            if chunk.startswith("[DONE:") and chunk.endswith("]"):
                # 確保格式正確 [DONE:X]
                try:
                    token_count_str = chunk[6:-1]  # [6:-1] to get the number between ":" and "]"
                    if token_count_str:  # Ensure not empty
                        token_count = int(token_count_str)
                except (ValueError, IndexError):
                    token_count = 0
                yield f"data: {json.dumps({'done': True, 'token_count': token_count})}\n\n"
                break
            
            # 發送內容片段
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/agent/chat")
async def agent_chat(request: ChatRequest):
    """
    使用 LangGraph Agent 發送聊天消息
    
    支援流式輸出 (SSE)，包含完整的中間過程：
    - Deep Reasoning 輸出
    - Tool 調用請求
    - Tool 執行結果
    - 最終答案
    
    Args:
        request: 聊天請求 (model 默認為 qwen3.5:9b)
    
    Returns:
        SSE 流式輸出
    """
    # 默認使用 qwen3.5:9b
    model = request.model or "qwen3.5:9b"
    
    return StreamingResponse(
        stream_agent_sse(request, model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def stream_agent_sse(request: ChatRequest, model: str):
    """
    LangGraph Agent 流式聊天 SSE 輸出
    
    事件格式:
    - {"type": "reasoning", "content": "..."}
    - {"type": "tool_call", "tool": "get_weather", "args": {...}, "reasoning": "..."}
    - {"type": "tool_result", "tool": "get_weather", "result": "..."}
    - {"type": "final", "content": "..."}
    - {"type": "done", "token_count": n, "tool_calls": m}
    
    Args:
        request: 聊天請求
        model: 模型名稱
    
    Yields:
        SSE 事件
    """
    try:
        for event in stream_agent(
            message=request.message,
            model=model,
            thread_id=request.thread_id or "default"
        ):
            yield f"data: {event}\n\n"
    
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@router.get("/token-count", response_model=TokenCountResponse)
async def get_context_token_count(
    thread_id: str = Query(default="default", description="對話線程 ID")
):
    """
    獲取當前上下文窗口的 token 數
    
    Args:
        thread_id: 對話線程 ID
    
    Returns:
        Token 計數資訊
    """
    try:
        info = get_token_info(thread_id)
        
        return TokenCountResponse(
            total_tokens=info["total_tokens"],
            max_tokens=info["max_tokens"],
            usage_percentage=info["usage_percentage"],
            messages_count=info["messages_count"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/clear")
async def clear_conversation(
    thread_id: str = Query(default="default", description="對話線程 ID")
):
    """
    清除對話上下文
    
    Args:
        thread_id: 對話線程 ID
    
    Returns:
        確認訊息
    """
    try:
        conversation_context.clear_session(thread_id)
        return {"status": "success", "message": f"Conversation '{thread_id}' cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/model/set")
async def set_default_model(
    model: str = Query(..., description="要設置的默認模型名稱")
):
    """
   設置默認模型
    
    Args:
        model: 模型名稱
    
    Returns:
        確認訊息
    """
    # 驗證模型是否存在
    available_models = ollama_service.list_models()
    model_names = [m.get("name") for m in available_models]
    
    if model_names and model not in model_names:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not found. Available models: {model_names}"
        )
    
    ollama_service.set_model(model)
    
    return {
        "status": "success",
        "message": f"Default model set to '{model}'",
        "current_model": model
    }


@router.get("/model/current")
async def get_current_model():
    """
    獲取當前設置的模型
    
    Returns:
        當前模型名稱
    """
    return {
        "model": ollama_service.current_model
    }
