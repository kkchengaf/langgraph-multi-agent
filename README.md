# LangGraph Agents Project

第三個作業：Week 6 - LangGraph Agents

## 目標

構建能自主規劃和調用工具的 AI 系統，實現：
- 天氣搜索 (使用 OpenWeather API)
- 數學計算
- 網絡搜索 (使用 DuckDuckGo)
- 根據任務自主選擇工具
- Deep Reasoning (任務分解)

## 技術棧

- **LangGraph**: 狀態機、循環工作流
- **LangChain**: Tool Calling
- **ReAct 模式**: 推理 + 行動的混合模式
- **Ollama**: 本地 LLM (qwen3.5:9b)

## 模型說明

- **qwen3.5:9b**: 預設模型，支援 Tool Calling 和 Reasoning
- **gemma3:12b**: 不支援 Tool Calling，僅用於基本對話

## 項目結構

```
langgraph_agent/
├── venv/                      # 虛擬環境
├── src/                       # 源代码模块
│   ├── __init__.py           # 模組初始化
│   ├── tools.py              # 工具定义 (get_weather, calculate, web_search, get_current_time)
│   ├── prompts.py            # 系統提示詞
│   ├── utils.py              # 驗證、重試、上下文管理
│   ├── nodes.py              # LangGraph 節點
│   └── agent.py              # Agent 工廠
├── agent.py                   # 主程式入口
├── requirements.txt           # 依賴列表
├── .env                      # 環境變量 (需要自行創建)
├── .env.example              # 環境變量模板
└── README.md                 # 說明文檔
```

## 安裝

```bash
# 激活虛擬環境
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 確保 Ollama 服務運行
ollama serve

# 下載模型（如果還沒有的話）
ollama pull qwen3.5:9b
```

## 環境變量

在 `.env` 文件中設置以下變量：

```bash
# 複製模板
cp .env.example .env

# 編輯 .env 文件:
# LangSmith 調試 (可選)
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true

# OpenWeather API (用於天氣查詢)
OPEN_WEATHER_API_KEY=your_openweather_api_key
```

## 運行

```bash
python agent.py
```

## 功能

1. **天氣搜索** (`get_weather`)
   - 使用 OpenWeather API 獲取即時天氣數據
   - 支援全球城市 (使用英文名稱，如 "Taipei", "Tokyo")

2. **數學計算** (`calculate`)
   - 支援基本運算：+、-、*、/、**
   - 支援函數：sqrt、sin、cos、tan、log、pi、e

3. **網絡搜索** (`web_search`)
   - 使用 DuckDuckGo 免費 API
   - 搜尋最新資訊、新聞、價格等
   - ⚠️ 搜尋結果取決於 DuckDuckGo 服務供應商

4. **獲取時間** (`get_current_time`)
   - 支援時區查詢
   - 預設 UTC 時間

## 模組說明

### src/tools.py
- `get_weather(city)`: 獲取城市天氣
- `calculate(expression)`: 數學計算
- `web_search(query)`: 網絡搜索
- `get_current_time(timezone)`: 獲取時間

### src/prompts.py
- `AGENT_SYSTEM_PROMPT`: Agent 系統提示
- `DEEP_REASONING_SYSTEM_PROMPT`: 深度推理提示

### src/utils.py
- `validate_and_parse_output()`: 輸出驗證
- `agent_execute_with_retry()`: 智能重試
- `manage_context_window()`: 上下文管理

### src/nodes.py
- `call_model()`: LLM 調用節點
- `deep_reasoning()`: 深度推理節點
- `should_continue()`: 條件邊判斷

### src/agent.py
- `create_agent()`: 創建 LangGraph Agent
- `stream_agent_response()`: 流式輸出

## Agent 架構

### 節點說明

1. **Deep Reasoning 節點**
   - 在主要工具調用前執行
   - 分析用戶請求並分解為子任務
   - 識別需要的工具
   - 制定執行計劃

2. **Agent 節點**
   - 負責決定是否調用工具
   - 每次只調用一個工具
   - 使用 system prompt 控制行為

3. **Tools 節點**
   - 執行工具並返回結果

### 工作流程

```
User Query
    ↓
┌─────────────────────────────────────────┐
│         Deep Reasoning 節點             │
│  - 任務分析                              │
│  - 工具規劃                              │
│  - 執行計劃                              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│           Agent 節點                     │
│  - 決定是否調用工具                      │
│  - 一次只調用一個工具                    │
│  - 推理過程                              │
└─────────────────────────────────────────┘
    ↓
    ├──────────┐
    ↓          ↓
 需要工具    結束
    ↓
┌─────────────────────────────────────────┐
│          Tools 節點                       │
│  - get_weather                          │
│  - calculate                            │
│  - web_search                           │
└─────────────────────────────────────────┘
    ↓
    回到 Agent 節點 (循環)
```

## 輸出示例

```
🚀 LangGraph Agent - 天氣搜索 + 計算工具 + 網絡搜索
===========================================================

測試 1: 香港現在的天氣如何？
===========================================================

🔄 ReAct 推理過程:
----------------------------------------

🧠 [Deep Reasoning]
   ### 任務分析
   用戶詢問香港的天氣狀況...
   
   ### 所需工具
   - get_weather: 獲取即時天氣資訊
   
   ### 執行計劃
   1. 調用 get_weather 工具

💭 [Thought]
   用戶想要知道香港的天氣，我需要使用 get_weather 工具來獲取天氣資訊。

🔧 [Action]
   工具: get_weather
   參數: {'city': 'Hong Kong'}

👁️ [Observation]
   🌡️ Hong Kong 天氣資訊:
   天氣：few clouds
   溫度：24°C (體感 26°C)
   濕度：69%
   風速：4.6 m/s

----------------------------------------

✅ Agent 回應:
   香港目前的天氣是...
```

## 學習重點

1. **LangGraph 基礎**: 狀態機、節點、邊
2. **Tool Calling**: 讓 Agent 調用外部函數
3. **ReAct 模式**: Reasoning + Acting
4. **Deep Reasoning**: 任務分解與規劃
5. **狀態管理**: 多輪對話的狀態保持
6. **System Prompt**: 控制 LLM 行為
7. **模組化設計**: 代碼組織與重用
