# LangGraph Agents Project

第三個作業：Week 6 - LangGraph Agents

## 目標

構建能自主規劃和調用工具的 AI 系統，實現：
- 天氣搜索
- 數學計算
- 根據任務自主選擇工具

## 技術棧

- **LangGraph**: 狀態機、循環工作流
- **LangChain**: Tool Calling
- **ReAct 模式**: 推理 + 行動的混合模式
- **Ollama**: 本地 LLM (qwen3.5:9b, gemma3:12b)

## 項目結構

```
langgraph-agents/
├── venv/              # 虛擬環境
├── agent.py           # 主程式
├── requirements.txt    # 依賴列表
└── README.md          # 說明文檔
```

## 安裝

```bash
# 激活虛擬環境
source venv/bin/activate

# 確保 Ollama 服務運行
ollama serve

# 下載模型（如果還沒有的話）
ollama pull qwen3.5:9b
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
