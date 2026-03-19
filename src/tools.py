"""
工具模組 - 所有可用的工具定義
"""
import os
from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """
    獲取指定城市的即時天氣資訊。

    Args:
        city: 城市名稱，例如 "Taipei"、"Tokyo"、"New York"

    Returns:
        天氣資訊字符串
    """
    import requests
    
    api_key = os.getenv("OPEN_WEATHER_API_KEY")
    if not api_key:
        return "錯誤：未設置 OPEN_WEATHER_API_KEY 環境變量"
    
    try:
        # OpenWeatherMap API
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric"  # 使用攝氏度
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            return f"抱歉，沒有找到 {city} 的天氣資訊"
        elif response.status_code == 401:
            return "錯誤：API Key 無效"
        elif response.status_code != 200:
            return f"錯誤：API 請求失敗 (狀態碼: {response.status_code})"
        
        data = response.json()
        
        # 解析天氣數據
        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        feels_like = data["main"]["feels_like"]
        wind_speed = data["wind"]["speed"]
        city_name = data["name"]
        
        # 天氣圖標映射
        weather_icons = {
            "01d": "☀️", "01n": "🌙",
            "02d": "⛅", "02n": "☁️",
            "03d": "☁️", "03n": "☁️",
            "04d": "☁️", "04n": "☁️",
            "09d": "🌧️", "09n": "🌧️",
            "10d": "🌧️", "10n": "🌧️",
            "11d": "⛈️", "11n": "⛈️",
            "13d": "❄️", "13n": "❄️",
            "50d": "🌫️", "50n": "🌫️",
        }
        icon = data["weather"][0].get("icon", "")
        icon_emoji = weather_icons.get(icon, "🌡️")
        
        return (
            f"{icon_emoji} {city_name} 天氣資訊:\n"
            f"   天氣：{weather}\n"
            f"   溫度：{temp}°C (體感 {feels_like}°C)\n"
            f"   濕度：{humidity}%\n"
            f"   風速：{wind_speed} m/s"
        )
        
    except requests.exceptions.Timeout:
        return "錯誤：API 請求超時"
    except requests.exceptions.RequestException as e:
        return f"錯誤：網絡請求失敗 - {str(e)}"
    except Exception as e:
        return f"錯誤：{str(e)}"


@tool
def calculate(expression: str) -> str:
    """
    執行數學計算。

    Args:
        expression: 數學表達式，例如 "2 + 2", "10 * 5", "sqrt(16)"

    Returns:
        計算結果
    """
    try:
        # 安全處理常見數學運算
        expression = expression.replace("^", "**")

        # 處理常見數學函數
        allowed_names = {
            "sqrt": "** 0.5",
            "sin": "math.sin",
            "cos": "math.cos",
            "tan": "math.tan",
            "log": "math.log",
            "pi": "math.pi",
            "e": "math.e",
        }

        # 檢查是否只包含安全的字符
        safe_chars = set("0123456789+-*/.()** ")
        if not all(c in safe_chars or c.isalnum() for c in expression):
            return "錯誤：表達式包含不安全字符"

        # 執行計算
        import math
        result = eval(expression, {"__builtins__": {}, "math": math}, allowed_names)
        return f"計算結果：{expression} = {result}"
    except Exception as e:
        return f"計算錯誤：{str(e)}"


@tool
def web_search(query: str) -> str:
    """
    搜索互聯網獲取最新資訊。

    Args:
        query: 搜索關鍵詞

    Returns:
        搜索結果摘要
    """
    try:
        from ddgs import DDGS
        
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            
        if not results:
            return f"沒有找到關於 '{query}' 的結果"
        
        # 格式化結果
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            href = result.get('href', '')
            body = result.get('body', 'No description')
            
            formatted_results.append(
                f"{i}. {title}\n"
                f"   URL: {href}\n"
                f"   摘要: {body[:200]}..." if len(body) > 200 else f"   摘要: {body}"
            )
        
        return "搜索結果：\n\n" + "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"搜索錯誤：{str(e)}"


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """
    獲取當前時間。

    Args:
        timezone: 時區名稱，例如 "UTC", "Asia/Taipei", "America/New_York"

    Returns:
        格式化當前時間字符串
    """
    from datetime import datetime
    import pytz
    
    try:
        if timezone == "UTC" or not timezone:
            now = datetime.now()
            tz = pytz.utc
            timezone_str = "UTC"
        else:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
                timezone_str = timezone
            except pytz.exceptions.UnknownTimeZoneError:
                now = datetime.now(pytz.utc)
                timezone_str = "UTC (invalid timezone, defaulted)"
        
        return (
            f"🕐 當前時間\n"
            f"   時區: {timezone_str}\n"
            f"   日期時間: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   星期: {now.strftime('%A')}"
        )
        
    except Exception as e:
        return f"獲取時間錯誤：{str(e)}"


# 工具列表
TOOLS = [get_weather, calculate, web_search, get_current_time]
