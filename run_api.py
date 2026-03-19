"""
API 服務啟動腳本
"""
import os
import sys

# 確保 src 目錄在路徑中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    # 載入環境變量
    load_dotenv()
    
    # 獲取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    
    print(f"\n{'=' * 50}")
    print(f"🌐 啟動 API 服務: http://{host}:{port}")
    print(f"{'=' * 50}\n")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload
    )
