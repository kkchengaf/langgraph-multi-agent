#!/usr/bin/env python3
"""
Automatic Evaluation Script for LangGraph Agent API

This script automatically:
1. Sends test queries to the API
2. Collects responses
3. Evaluates each response using multiple approaches
4. Generates a comprehensive evaluation report

Usage:
    python evaluate_api.py
    
    # With custom API URL
    python evaluate_api.py --api-url http://192.168.0.100:8000
    
    # Run specific test categories
    python evaluate_api.py --categories weather calculation
    
    # Save results to file
    python evaluate_api.py --output evaluation_results.json
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

# Test cases for evaluation
TEST_CASES = [
    # Weather queries
    {
        "category": "weather",
        "query": "What's the weather in Taipei?",
        "expected_tools": ["get_weather"],
        "expected_keywords": ["temperature", "weather", "taipei", "°c", "°f", "celsius", "fahrenheit"],
    },
    {
        "category": "weather",
        "query": "香港現在天氣如何？",
        "expected_tools": ["get_weather"],
        "expected_keywords": ["天氣", "溫度", "香港", "°c", "攝氏"],
    },
    {
        "category": "weather",
        "query": "東京的天氣怎麼樣？",
        "expected_tools": ["get_weather"],
        "expected_keywords": ["天氣", "溫度", "東京", "°c"],
    },
    
    # Calculation queries
    {
        "category": "calculation",
        "query": "Calculate 123 * 456",
        "expected_tools": ["calculate"],
        "expected_keywords": ["56088", "123*456"],
    },
    {
        "category": "calculation",
        "query": "請幫我計算 66 + 43",
        "expected_tools": ["calculate"],
        "expected_keywords": ["109", "66+43", "計算"],
    },
    {
        "category": "calculation",
        "query": "What is the square root of 144?",
        "expected_tools": ["calculate"],
        "expected_keywords": ["12", "sqrt", "根號"],
    },
    {
        "category": "calculation",
        "query": "Calculate 2^10",
        "expected_tools": ["calculate"],
        "expected_keywords": ["1024", "2^10"],
    },
    
    # Search queries
    {
        "category": "search",
        "query": "誰是現在的特斯拉CEO？",
        "expected_tools": ["web_search"],
        "expected_keywords": ["elon musk", "馬斯克", "ceo", "特斯拉"],
    },
    {
        "category": "search",
        "query": "比特幣現在多少錢？",
        "expected_tools": ["web_search"],
        "expected_keywords": ["比特幣", "bitcoin", "價格", "price", "$", "usd"],
    },
    {
        "category": "search",
        "query": "What is the latest news about AI?",
        "expected_tools": ["web_search"],
        "expected_keywords": ["news", "ai", "article", "report"],
    },
    
    # Time queries
    {
        "category": "time",
        "query": "現在東京幾點？",
        "expected_tools": ["get_current_time"],
        "expected_keywords": ["時間", "東京", "time", "tokyo", ":"],
    },
    {
        "category": "time",
        "query": "What time is it in London?",
        "expected_tools": ["get_current_time"],
        "expected_keywords": ["time", "london", "時間"],
    },
    
    # Multi-step reasoning
    {
        "category": "reasoning",
        "query": "66+43元人民币等于多少港元？",  # 66+43=109 RMB
        "expected_tools": ["calculate", "web_search"],
        "expected_keywords": ["港幣", "港元", "hkd", "109", "汇率", "匯率"],
    },
    {
        "category": "reasoning",
        "query": "香港現在天氣如何？幫我查一下附近有什麼合適的活動可以做？",
        "expected_tools": ["get_weather", "web_search"],
        "expected_keywords": ["天氣", "活動", "activity", "建議"],
    },
    
    # Simple conversation
    {
        "category": "general",
        "query": "你好，請問你是誰？",
        "expected_tools": [],
        "expected_keywords": ["你好", "hello", "hi", "我是", "assistant", "agent"],
    },
    {
        "category": "general",
        "query": "Thank you!",
        "expected_tools": [],
        "expected_keywords": ["不客气", "welcome", "謝謝", "thank"],
    },
]


class APIEvaluator:
    """Evaluates the LangGraph Agent API automatically"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')
        self.results: List[Dict[str, Any]] = []
        
    def send_message(self, query: str, thread_id: str = "eval-test") -> Dict[str, Any]:
        """Send a message to the API and get response"""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.api_url}/api/agent/chat",
                json={
                    "message": query,
                    "model": "qwen3.5:9b",
                    "thread_id": thread_id
                },
                timeout=120,
                stream=True
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": "",
                    "tool_calls": [],
                    "duration_ms": (time.time() - start_time) * 1000
                }
            
            # Collect streaming response - only get FINAL answer
            final_response = ""
            tool_calls = []
            reasoning_content = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            chunk_type = chunk.get('type', '')
                            
                            if chunk_type == 'final':
                                # This is the FINAL answer
                                final_response += chunk.get('content', '')
                            elif chunk_type == 'tool_call':
                                tool_calls.append(chunk)
                            elif chunk_type == 'reasoning':
                                reasoning_content += chunk.get('content', '') + '\n'
                        except json.JSONDecodeError:
                            pass
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "response_text": final_response,
                "tool_calls": tool_calls,
                "reasoning": reasoning_content.strip(),
                "duration_ms": duration_ms
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Timeout",
                "response_text": "",
                "tool_calls": [],
                "duration_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_text": "",
                "tool_calls": [],
                "duration_ms": (time.time() - start_time) * 1000
            }
    
    def _clear_conversation(self, thread_id: str) -> bool:
        """Clear conversation context using the clear API"""
        try:
            response = requests.post(
                f"{self.api_url}/api/chat/clear",
                params={"thread_id": thread_id}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def evaluate_response(
        self,
        query: str,
        response_text: str,
        tool_calls: List[Dict],
        test_case: Dict
    ) -> Dict[str, Any]:
        """Evaluate a single response"""
        
        # Extract tool names from tool_calls
        tool_names = [tc.get('tool', '') for tc in tool_calls]
        
        # Calculate scores
        scores = {
            "success": True,
            "query": query,
            "response_length": len(response_text),
            "duration_ms": 0,
            
            # Tool usage score
            "tool_usage_score": 0,
            "expected_tools_used": len([t for t in test_case.get("expected_tools", []) if t in tool_names]),
            "total_expected_tools": len(test_case.get("expected_tools", [])),
            
            # Keyword score
            "keyword_score": 0,
            "keywords_found": 0,
            "total_keywords": len(test_case.get("expected_keywords", [])),
            
            # Response quality
            "has_response": len(response_text.strip()) > 10,
            "has_error_indicators": any(e in response_text.lower() for e in ["error", "錯誤", "failed", "失敗"]),
        }
        
        # Calculate tool usage score
        if scores["total_expected_tools"] > 0:
            scores["tool_usage_score"] = (scores["expected_tools_used"] / scores["total_expected_tools"]) * 100
        elif len(tool_names) == 0:
            scores["tool_usage_score"] = 100
        else:
            scores["tool_usage_score"] = 50
        
        # Calculate keyword score
        response_lower = response_text.lower()
        for keyword in test_case.get("expected_keywords", []):
            if keyword.lower() in response_lower:
                scores["keywords_found"] += 1
        
        if scores["total_keywords"] > 0:
            scores["keyword_score"] = (scores["keywords_found"] / scores["total_keywords"]) * 100
        else:
            scores["keyword_score"] = 100 if scores["has_response"] else 0
        
        # Overall score
        scores["overall_score"] = (
            scores["tool_usage_score"] * 0.4 +
            scores["keyword_score"] * 0.4 +
            (100 if scores["has_response"] else 0) * 0.2
        )
        
        # Error penalty
        if scores["has_error_indicators"]:
            scores["overall_score"] *= 0.5
        
        return scores
    
    async def run_evaluation(
        self,
        categories: Optional[List[str]] = None,
        delay_between_tests: float = 2.0
    ) -> Dict[str, Any]:
        """Run the full evaluation"""
        
        print("=" * 60)
        print("LangGraph Agent API - Automatic Evaluation")
        print("=" * 60)
        print(f"API URL: {self.api_url}")
        print()
        
        # Filter test cases
        filtered_cases = TEST_CASES
        if categories:
            filtered_cases = [tc for tc in TEST_CASES if tc.get("category") in categories]
        
        print(f"Running {len(filtered_cases)} test cases...")
        print()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "api_url": self.api_url,
            "total_tests": len(filtered_cases),
            "tests": [],
            "summary": {}
        }
        
        # Use single evaluation thread and clear it before each test
        eval_thread_id = "eval-thread"
        
        for i, test_case in enumerate(filtered_cases, 1):
            query = test_case["query"]
            category = test_case.get("category", "unknown")
            
            # Clear conversation context before each test
            self._clear_conversation(eval_thread_id)
            
            print(f"[{i}/{len(filtered_cases)}] Testing: {query[:50]}...")
            
            # Send request with cleared thread
            api_result = self.send_message(query, thread_id=eval_thread_id)
            
            # Evaluate response
            eval_result = self.evaluate_response(
                query=query,
                response_text=api_result.get("response_text", ""),
                tool_calls=api_result.get("tool_calls", []),
                test_case=test_case
            )
            
            eval_result["category"] = category
            eval_result["api_success"] = api_result["success"]
            eval_result["api_error"] = api_result.get("error", "")
            eval_result["duration_ms"] = api_result.get("duration_ms", 0)
            eval_result["response_text"] = api_result.get("response_text", "")[:500]
            eval_result["reasoning"] = api_result.get("reasoning", "")[:200]
            
            results["tests"].append(eval_result)
            
            # Print result
            status = "OK" if eval_result["overall_score"] >= 60 else "FAIL"
            print(f"  [{status}] Score: {eval_result['overall_score']:.1f}/100 | "
                  f"Tools: {eval_result['expected_tools_used']}/{eval_result['total_expected_tools']} | "
                  f"Keywords: {eval_result['keywords_found']}/{eval_result['total_keywords']}")
            
            # Delay between tests
            if i < len(filtered_cases):
                await asyncio.sleep(delay_between_tests)
        
        print()
        
        # Calculate summary
        results["summary"] = self._calculate_summary(results["tests"])
        
        return results
    
    def _calculate_summary(self, tests: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        
        if not tests:
            return {}
        
        total = len(tests)
        successful = sum(1 for t in tests if t.get("api_success", False))
        passed = sum(1 for t in tests if t.get("overall_score", 0) >= 60)
        
        # Category statistics
        categories = {}
        for test in tests:
            cat = test.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {
                    "total": 0,
                    "passed": 0,
                    "avg_score": 0,
                    "scores": []
                }
            categories[cat]["total"] += 1
            if test.get("overall_score", 0) >= 60:
                categories[cat]["passed"] += 1
            categories[cat]["scores"].append(test.get("overall_score", 0))
        
        # Calculate averages
        for cat in categories:
            scores = categories[cat]["scores"]
            categories[cat]["avg_score"] = sum(scores) / len(scores) if scores else 0
            del categories[cat]["scores"]
        
        return {
            "total_tests": total,
            "api_success_rate": (successful / total * 100) if total > 0 else 0,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "average_score": sum(t.get("overall_score", 0) for t in tests) / total if total > 0 else 0,
            "average_duration_ms": sum(t.get("duration_ms", 0) for t in tests) / total if total > 0 else 0,
            "by_category": categories
        }
    
    def print_report(self, results: Dict[str, Any]):
        """Print a nice report"""
        
        summary = results["summary"]
        
        print("=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"API URL: {results['api_url']}")
        print()
        
        print("--- Overall Statistics ---")
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"API Success Rate: {summary.get('api_success_rate', 0):.1f}%")
        print(f"Pass Rate: {summary.get('pass_rate', 0):.1f}%")
        print(f"Average Score: {summary.get('average_score', 0):.1f}/100")
        print(f"Average Duration: {summary.get('average_duration_ms', 0):.0f}ms")
        print()
        
        print("--- By Category ---")
        for cat, stats in summary.get("by_category", {}).items():
            print(f"  {cat}:")
            print(f"    Tests: {stats['total']} | Passed: {stats['passed']} | "
                  f"Avg Score: {stats['avg_score']:.1f}")
        print()
        
        # Print failed tests
        failed = [t for t in results["tests"] if t.get("overall_score", 0) < 60]
        if failed:
            print("--- Failed Tests ---")
            for test in failed:
                print(f"  - {test['query'][:60]}...")
                print(f"    Score: {test.get('overall_score', 0):.1f}/100")
                if test.get("api_error"):
                    print(f"    Error: {test['api_error']}")
            print()
        
        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Evaluate LangGraph Agent API")
    parser.add_argument("--api-url", default="http://localhost:8000",
                        help="API base URL")
    parser.add_argument("--categories", nargs="*",
                        help="Filter by categories: weather, calculation, search, time, reasoning, general")
    parser.add_argument("--output", "-o",
                        help="Save results to JSON file")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between tests in seconds")
    
    args = parser.parse_args()
    
    # Create evaluator
    evaluator = APIEvaluator(api_url=args.api_url)
    
    # Run evaluation
    results = await evaluator.run_evaluation(
        categories=args.categories,
        delay_between_tests=args.delay
    )
    
    # Print report
    evaluator.print_report(results)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
