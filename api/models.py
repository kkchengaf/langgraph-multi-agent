"""
Pydantic 模型 - API 請求和響應模型
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================
# 請求模型
# ============================================


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(default="user", description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息內容")


class ChatRequest(BaseModel):
    """聊天請求"""
    message: str = Field(..., description="用戶消息")
    model: Optional[str] = Field(default="llama3.2", description="Ollama 模型名稱")
    max_tokens: Optional[int] = Field(default=2048, description="最大生成 token 數")
    temperature: Optional[float] = Field(default=0.7, description="生成溫度 (0-2)")
    stream: Optional[bool] = Field(default=True, description="是否啟用流式輸出")
    thread_id: Optional[str] = Field(default="default", description="對話線程 ID")
    device_id: Optional[str] = Field(default=None, description="Device identifier for thread isolation")


class TokenCountRequest(BaseModel):
    """Token 計數請求"""
    messages: List[Dict[str, str]] = Field(..., description="消息列表")


# ============================================
# 響應模型
# ============================================


class OllamaModel(BaseModel):
    """Ollama 模型資訊"""
    name: str = Field(..., description="模型名稱")
    size: Optional[int] = Field(None, description="模型大小 (bytes)")
    modified_at: Optional[str] = Field(None, description="最後修改時間")
    digest: Optional[str] = Field(None, description="模型摘要")


class ModelListResponse(BaseModel):
    """模型列表響應"""
    models: List[OllamaModel] = Field(..., description="可用模型列表")
    count: int = Field(..., description="模型數量")


class ChatResponse(BaseModel):
    """非流式聊天響應"""
    message: str = Field(..., description="AI 回應")
    model: str = Field(..., description="使用的模型")
    token_count: int = Field(..., description="消耗的 token 數")
    done: bool = Field(default=True, description="是否完成")


class TokenCountResponse(BaseModel):
    """Token 計數響應"""
    total_tokens: int = Field(..., description="總 token 數")
    max_tokens: int = Field(..., description="最大 token 限制")
    usage_percentage: float = Field(..., description="使用百分比")
    messages_count: int = Field(..., description="消息數量")


class StreamChunk(BaseModel):
    """流式輸出片段"""
    content: str = Field(..., description="內容片段")
    done: bool = Field(default=False, description="是否為最後一個片段")
    model: Optional[str] = Field(None, description="模型名稱")
    token_count: Optional[int] = Field(None, description="當前累積 token 數")


class ErrorResponse(BaseModel):
    """錯誤響應"""
    error: str = Field(..., description="錯誤訊息")
    detail: Optional[str] = Field(None, description="詳細錯誤資訊")


# ============================================
# Thread Models
# ============================================


class ThreadMessage(BaseModel):
    """Thread message model"""
    id: Optional[str] = Field(None, description="Message ID")
    role: str = Field(default="user", description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Timestamp")


class ThreadCreate(BaseModel):
    """Thread creation request"""
    name: Optional[str] = Field(None, description="Thread name")
    device_id: Optional[str] = Field(None, description="Device identifier for thread isolation")


class ThreadResponse(BaseModel):
    """Thread response"""
    id: str = Field(..., description="Thread ID")
    name: str = Field(..., description="Thread name")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages")


class ThreadMessageListResponse(ThreadResponse):
    """Thread detail with messages"""
    messages: List[ThreadMessage] = Field(default_factory=list, description="Messages")


class ThreadListResponse(BaseModel):
    """Thread list response"""
    threads: List[ThreadResponse] = Field(..., description="Thread list")
    total: int = Field(..., description="Total count")
