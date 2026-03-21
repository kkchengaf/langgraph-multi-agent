# LangGraph Agent Project

AI Agent System with LangGraph, FastAPI Backend, and Vue.js Frontend

## 目標

構建能自主規劃和調用工具的 AI 系統，實現：
- 天氣搜索 (使用 OpenWeather API)
- 數學計算
- 網絡搜索 (使用 DuckDuckGo)
- 根據任務自主選擇工具
- Deep Reasoning (任務分解)
- 評估系統 (Evaluation)

## 技術棧

- **LangGraph**: 狀態機、循環工作流
- **LangChain**: Tool Calling
- **FastAPI**: REST API 伺服器
- **MongoDB**: 訊息與執行緒持久化
- **Ollama**: 本地 LLM (qwen3.5:9b)

## 項目結構

```
langgraph_agent/
├── src/                       # LangGraph 核心模組
│   ├── __init__.py
│   ├── tools.py              # 工具定義
│   ├── prompts.py            # 系統提示詞
│   ├── utils.py             # 驗證、重試、上下文管理
│   ├── nodes.py             # LangGraph 節點
│   └── agent.py             # Agent 工廠
├── api/                       # FastAPI 後端
│   ├── __init__.py
│   ├── main.py              # FastAPI 應用
│   ├── routes.py            # API 路由
│   ├── services.py          # 服務層
│   ├── models.py            # Pydantic 模型
│   └── database.py          # MongoDB 連接
├── frontend/                  # Vue.js 前端
│   ├── index.html
│   └── src/
│       ├── app.js           # 主應用邏輯
│       ├── api.js           # API 客戶端
│       ├── components.js    # UI 組件
│       ├── styles.css       # 樣式
│       └── config.js        # 配置
├── agent.py                   # CLI 主程式
├── run_api.py                # API 伺服器啟動
├── evaluate_api.py           # 評估腳本
├── requirements.txt           # 依賴列表
├── .env.example              # 環境變量模板
└── README.md                 # 說明文檔
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 環境變量

```bash
cp .env.example .env
```

編輯 `.env` 文件:
```bash
# OpenWeather API (用於天氣查詢)
OPEN_WEATHER_API_KEY=your_openweather_api_key

# LangSmith 調試 (可選)
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true

# MongoDB (可選，使用本地訊息儲存)
MONGODB_URI=mongodb://localhost:27017
```

### 3. 啟動服務

```bash
# 確保 Ollama 服務運行
ollama serve

# 下載模型
ollama pull qwen3.5:9b

# 啟動 API 伺服器
python run_api.py

# 啟動前端 (新終端)
cd frontend
python -m http.server 8080
```

訪問 `http://localhost:8080`

## API 端點

| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/agent/chat` | POST | LangGraph Agent 對話 (SSE 流式) |
| `/api/chat` | POST | 簡單對話 (非 Agent) |
| `/api/models` | GET | 獲取可用模型列表 |
| `/api/token-count` | GET | 獲取上下文 token 使用量 |
| `/api/chat/clear` | POST | 清除對話上下文 |
| `/api/model/set` | POST | 設置默認模型 |
| `/api/model/current` | GET | 獲取當前模型 |

## 功能

### 1. 天氣搜索 (`get_weather`)
- 使用 OpenWeather API
- 支援全球城市 (英文名稱)

### 2. 數學計算 (`calculate`)
- 基本運算：+、-、*、/、**
- 函數：sqrt、sin、cos、tan、log

### 3. 網絡搜索 (`web_search`)
- 使用 DuckDuckGo API

### 4. 獲取時間 (`get_current_time`)
- 支援時區查詢

### 5. Deep Reasoning
- 任務分析與分解
- 工具規劃

### 6. 評估系統
- LLM 自評估
- 多維度指標追蹤

## Agent 架構

```
User Query
    ↓
┌─────────────────────────────────────────┐
│         Deep Reasoning 節點             │
│  - 任務分析                              │
│  - 工具規劃                              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│           Agent 節點                     │
│  - 決定是否調用工具                      │
│  - 推理過程                              │
└─────────────────────────────────────────┘
    ↓
    ├──────────┐
    ↓          ↓
 需要工具    結束
    ↓
┌─────────────────────────────────────────┐
│          Tools 節點                      │
│  - get_weather                          │
│  - calculate                            │
│  - web_search                           │
└─────────────────────────────────────────┘
    ↓
    回到 Agent 節點 (循環)
```

## 評估系統

### 運行評估

```bash
python evaluate_api.py
```

### 評估指標

- **準確性 (Accuracy)**: 回覆是否正確回答問題
- **完整性 (Completeness)**: 是否包含所有必要資訊
- **工具使用 (Tool Usage)**: 是否正確使用工具
- **意圖識別 (Intent Recognition)**: 是否正確理解用戶意圖

## LangSmith 調試

1. 在 [LangSmith](https://smith.langchain.com/) 創建帳戶
2. 獲取 API Key
3. 在 `.env` 中設置:
   ```
   LANGCHAIN_API_KEY=your_key
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=langgraph-agent
   ```
4. 訪問 LangSmith Dashboard 查看追蹤

## 學習重點

1. **LangGraph 基礎**: 狀態機、節點、邊
2. **Tool Calling**: 外部函數調用
3. **ReAct 模式**: Reasoning + Acting
4. **Deep Reasoning**: 任務分解與規劃
5. **FastAPI**: REST API 開發
6. **SSE**: 服務端推送
7. **MongoDB**: 數據持久化
8. **評估系統**: LLM 自評估
