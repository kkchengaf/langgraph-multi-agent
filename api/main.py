"""
FastAPI 主應用程序
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from api.services import ollama_service
from api.database import init_indexes, close_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    print("\n" + "=" * 50)
    print("🚀 API Server 啟動中...")
    print("=" * 50)
    
    # 初始化 MongoDB
    try:
        init_indexes()
        print("\n✅ MongoDB 連接成功!")
    except Exception as e:
        print(f"\n⚠️ 警告: 無法連接 MongoDB: {e}")
        print("   請確保 MongoDB 服務正在運行")
    
    # 檢查 Ollama 連接
    try:
        models = ollama_service.list_models()
        print(f"\n✅ Ollama 連接成功! 找到 {len(models)} 個模型:")
        for m in models:
            print(f"   - {m.get('name')}")
    except Exception as e:
        print(f"\n⚠️ 警告: 無法連接 Ollama: {e}")
        print("   請確保 Ollama 服務正在運行 (ollama serve)")
    
    print("\n" + "=" * 50)
    print("📡 API 端點:")
    print("   GET  /models          - 列出可用模型")
    print("   POST /chat            - 發送聊天消息 (支援 SSE 流式)")
    print("   POST /agent/chat      - LangGraph Agent 聊天 (完整中間過程)")
    print("   GET  /token-count     - 獲取上下文 token 數")
    print("   POST /chat/clear     - 清除對話上下文")
    print("   POST /model/set      - 設置默認模型")
    print("   GET  /model/current  - 獲取當前模型")
    print("   Threads:")
    print("   GET    /threads         - 列出所有線程")
    print("   POST   /threads         - 創建新線程")
    print("   GET    /threads/{id}   - 獲取線程詳情")
    print("   PUT    /threads/{id}   - 更新線程名稱")
    print("   DELETE /threads/{id}   - 刪除線程")
    print("=" * 50 + "\n")
    
    yield
    
    # 關閉時
    print("\n👋 API Server 關閉中...")
    close_connection()


# 創建 FastAPI 應用
app = FastAPI(
    title="LangGraph Agent API",
    description="基於 LangGraph 和 Ollama 的 AI Agent API 服務",
    version="1.0.0",
    lifespan=lifespan
)


# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 註冊路由
app.include_router(router, prefix="/api", tags=["Agent"])


# 首頁
@app.get("/")
async def root():
    """首頁"""
    return {
        "name": "LangGraph Agent API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "models": "/api/models",
            "chat": "/api/chat",
            "agent_chat": "/api/agent/chat",
            "token_count": "/api/token-count",
            "clear_chat": "/api/chat/clear",
            "set_model": "/api/model/set",
            "current_model": "/api/model/current"
        }
    }


# 健康檢查
@app.get("/health")
async def health():
    """健康檢查"""
    try:
        models = ollama_service.list_models()
        ollama_status = "connected" if models else "disconnected"
    except:
        ollama_status = "error"
    
    return {
        "status": "healthy",
        "ollama": ollama_status
    }


# 運行服務
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
