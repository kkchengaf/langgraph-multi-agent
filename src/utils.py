"""
工具函數模組 - 驗證、重試、上下文管理
"""
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================
# 輸出驗證層
# ============================================
def validate_and_parse_output(raw_output, has_tool_calls=False):
    """
    驗證和解析 LLM 輸出
    
    Args:
        raw_output: LLM 原始輸出
        has_tool_calls: 是否有 tool_calls（優先於 content 驗證）
        
    Returns:
        驗證結果字典
    """
    # 如果有 tool_calls，直接通過驗證
    if has_tool_calls:
        return {
            "status": "valid",
            "parsed": "工具調用請求"
        }
    
    # 處理 None 或空輸出
    if raw_output is None or (isinstance(raw_output, str) and raw_output.strip() == ""):
        return {
            "status": "empty", 
            "retry": True, 
            "fallback": "輸出為空，請繼續完成推理並提供有效回應"
        }
    
    output_str = str(raw_output)
    output_lower = output_str.lower()
    
    # 檢查是否為無數據情況
    if "no data" in output_lower or "沒有找到" in output_str or "沒有結果" in output_str:
        return {
            "status": "no_data", 
            "retry": True, 
            "fallback": "搜索未找到結果，請如實告知用戶並嘗試建議不同的關鍵詞"
        }
    
    # 檢查必需字段
    has_action = "Action:" in output_str
    has_final = "Final Answer:" in output_str
    
    if not has_action and not has_final:
        return {
            "status": "incomplete",
            "retry": False,
            "reason": "輸出缺少必要字段 (Action 或 Final Answer)",
            "fallback": "請提供有效的 Action 或 Final Answer"
        }
    
    return {
        "status": "valid",
        "parsed": output_str
    }


# ============================================
# 智能重試與恢復機制
# ============================================
def agent_execute_with_retry(messages, llm, max_retries=3):
    """
    帶恢復機制的 Agent 執行
    
    Args:
        messages: 對話消息列表
        llm: LLM 實例
        max_retries: 最大重試次數
        
    Returns:
        LLM 響應
    """
    for attempt in range(max_retries):
        try:
            response = llm.invoke(messages)
            
            # 獲取內容
            raw_output = response.content if hasattr(response, 'content') else str(response)
            
            # 檢查是否有 tool_calls
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
            
            # 驗證輸出
            validation = validate_and_parse_output(raw_output, has_tool_calls)
            
            if validation["status"] == "valid":
                return response
            
            elif validation["status"] in ["empty", "no_data"]:
                # 注入糾正提示
                correction_msg = HumanMessage(
                    content=f"""
上一條輸出無效: {raw_output}

{validation['fallback']}

請重新生成，確保輸出完整且有效。
"""
                )
                messages = list(messages) + [response, correction_msg]
                print(f"\n🔄 [重試 {attempt + 1}/{max_retries}] 注入糾正提示")
            
            elif validation["status"] == "incomplete":
                print(f"\n⚠️ [警告] {validation['reason']}")
                return response
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\n❌ [錯誤] 執行失敗: {str(e)}")
                raise
            print(f"\n🔄 [重試 {attempt + 1}/{max_retries}] 異常: {str(e)}")
    
    print(f"\n❌ 超過最大重試次數 ({max_retries})")
    return None


# ============================================
# 上下文滑動窗口
# ============================================
MAX_TOKENS = 4000


def estimate_tokens(text):
    """
    簡單估計 token 數量
    """
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len(text.split())
    return int(chinese_chars * 1.5 + english_words * 1.3)


def calculate_token_count(messages):
    """計算消息列表的總 token 數"""
    total = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total += estimate_tokens(msg.content)
    return total


def compress_message(msg):
    """壓縮單條消息"""
    if not hasattr(msg, 'content'):
        return msg
    
    content = msg.content
    if hasattr(msg, 'type') and msg.type == 'tool':
        return msg
    
    if len(content) > 500:
        compressed = content[:250] + "\n...[省略]...\n" + content[-200:]
        return AIMessage(content=compressed)
    return msg


def manage_context_window(messages, max_tokens=MAX_TOKENS):
    """
    管理對話上下文，避免超出限制
    
    Args:
        messages: 消息列表
        max_tokens: 最大 token 限制
        
    Returns:
        管理後的消息列表
    """
    if not messages:
        return messages
    
    current_tokens = calculate_token_count(messages)
    
    if current_tokens <= max_tokens:
        return messages
    
    print(f"\n📊 [上下文管理] 當前 {current_tokens} tokens，壓縮至 {max_tokens} tokens")
    
    system_prompt = messages[0] if hasattr(messages[0], 'content') and "system" in str(type(messages[0])).lower() else None
    
    if system_prompt:
        compressed_history = [compress_message(msg) for msg in messages[1:-5]]
        recent = messages[-5:]
        return [system_prompt] + compressed_history + recent
    else:
        return messages[-8:]
