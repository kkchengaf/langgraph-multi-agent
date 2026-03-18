# LangGraph Agents Project

第三個作業：Week 6 - LangGraph Agents

## 目標

構建能自主規劃和調用工具的 AI 系統，實現：
- 天氣搜索
- 數學計算
- 網絡搜索
- 根據任務自主選擇工具

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
langgraph-agents/
├── venv/              # 虛擬環境
├── agent.py           # 主程式
├── requirements.txt   # 依賴列表
├── .env               # 環境變量 (需要自行創建)
├── .env.example       # 環境變量模板
└── README.md         # 說明文檔
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

## 環境變量 (可選)

在 `.env` 文件中設置以下變量以啟用 LangSmith 調試：

```bash
# 複製模板
cp .env.example .env

# 編輯 .env 文件，添加:
# LANGCHAIN_API_KEY=your_api_key_from_https://smith.langchain.com/
# LANGCHAIN_TRACING_V2=true
```

## 運行

```bash
python agent.py
```

## 功能

1. **天氣搜索** (`get_weather`)
   - 支援城市：台北、東京、紐約、倫敦、巴黎、悉尼、香港、新加坡、首爾、上海

2. **數學計算** (`calculate`)
   - 支援基本運算：+、-、*、/、**
   - 支援函數：sqrt、sin、cos、tan、log、pi、e

3. **網絡搜索** (`web_search`)
   - 使用 DuckDuckGo 免費 API
   - 搜尋最新資訊、新聞、價格等
   - ⚠️ 搜尋結果取決於 DuckDuckGo 服務供應商，質量可能不如付費服務

## Agent 工作流程

```
User Query → LLM (決定是否調用工具)
              ↓
        ┌─────┴─────┐
        ↓           ↓
    需要工具    不需要工具
        ↓           ↓
   Tool Node    結束
        ↓
   LLM (基於工具結果生成回應)
```

## 學習重點

1. **LangGraph 基礎**: 狀態機、節點、邊
2. **Tool Calling**: 讓 Agent 調用外部函數
3. **ReAct 模式**: Reasoning + Acting
4. **狀態管理**: 多輪對話的狀態保持
