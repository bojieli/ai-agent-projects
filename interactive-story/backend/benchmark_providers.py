import os
import sys
import asyncio
import httpx
import json
import time
from statistics import mean, stdev

async def try_provider_http_stream(api_url, payload, headers):
    """Stream version that measures TTFT and TPOT"""
    metrics = {
        "ttft": None,
        "total_tokens": 0,
        "total_time": 0,
        "token_times": [],
        "output": ""  # Add output tracking
    }
    
    start_time = time.time()
    first_token_time = None
    last_token_time = None

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", api_url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"HTTP {response.status_code}: {error_body.decode()}")
                
                print("\nStreaming output:", flush=True)
                print("-" * 50, flush=True)
                
                async for chunk in response.aiter_text():
                    for line in chunk.splitlines():
                        line = line.strip()
                        if line.startswith("data:"):
                            line = line[len("data:"):].strip()
                        if not line or line == "[DONE]":
                            continue
                            
                        try:
                            delta = json.loads(line)
                            for choice in delta.get("choices", []):
                                if token := choice.get("delta", {}).get("content", ""):
                                    current_time = time.time()
                                    
                                    if first_token_time is None:
                                        first_token_time = current_time
                                        metrics["ttft"] = first_token_time - start_time
                                    
                                    metrics["total_tokens"] += 1
                                    last_token_time = current_time
                                    metrics["token_times"].append(current_time)
                                    
                                    # Print token in real-time
                                    print(token, end="", flush=True)
                                    metrics["output"] += token
                                    
                        except json.JSONDecodeError:
                            continue

    except Exception as e:
        print(f"\nError during streaming: {e}")
        return metrics

    print("\n" + "-" * 50)  # Add separator after output

    if metrics["total_tokens"] > 0 and len(metrics["token_times"]) > 1:
        # Calculate TPOT using time differences between consecutive tokens
        token_intervals = []
        for i in range(1, len(metrics["token_times"])):
            interval = metrics["token_times"][i] - metrics["token_times"][i-1]
            token_intervals.append(interval)
        
        metrics["tpot"] = mean(token_intervals)
        metrics["tpot_stdev"] = stdev(token_intervals) if len(token_intervals) > 1 else 0
    
    metrics["total_time"] = last_token_time - start_time if last_token_time else 0
    return metrics

async def benchmark_provider(name, api_url, payload, headers):
    print(f"\nTesting provider: {name}")
    print("-" * 50)
    
    try:
        metrics = await try_provider_http_stream(api_url, payload, headers)
        
        # Print metrics after the streaming output
        print("\nMetrics:")
        print("-" * 50)
        print(f"TTFT: {metrics['ttft']:.3f}s")
        print(f"Total tokens: {metrics['total_tokens']}")
        print(f"Total time: {metrics['total_time']:.3f}s")
        if "tpot" in metrics:
            print(f"Average TPOT: {metrics['tpot']*1000:.2f}ms ± {metrics['tpot_stdev']*1000:.2f}ms")
        print(f"Average throughput: {metrics['total_tokens']/metrics['total_time']:.1f} tokens/sec")
        
        # Add character count metrics
        char_count = len(metrics["output"])
        print(f"Character count: {char_count}")
        print(f"Chars per token: {char_count/metrics['total_tokens']:.1f}")
        
        return metrics
    except Exception as e:
        print(f"Provider failed: {e}")
        return None

async def main():
    # Load environment variables
    API_TOKEN = os.environ.get("API_TOKEN")
    ARK_API_KEY = os.environ.get("ARK_API_KEY")
    
    if not API_TOKEN or not ARK_API_KEY:
        print("Error: Required environment variables not set")
        sys.exit(1)

    # Test prompt
    prompt = "写一首绝句，不要做任何解释"
    
    # Configure providers
    providers = [
        {
            "name": "Doubao",
            "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "payload": {
                "model": "ep-20250206203431-bql9h",
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": 4096,
            },
            "headers": {
                "Authorization": f"Bearer {ARK_API_KEY}",
                "Content-Type": "application/json"
            }
        },
        {
            "name": "SiliconFlow",
            "url": "https://api.siliconflow.cn/v1/chat/completions",
            "payload": {
                "model": "deepseek-ai/DeepSeek-V3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": 4096,
            },
            "headers": {
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json"
            }
        }
    ]

    print("Starting benchmark...")
    print(f"Test prompt: {prompt}")
    
    results = []
    for provider in providers:
        metrics = await benchmark_provider(
            provider["name"],
            provider["url"],
            provider["payload"],
            provider["headers"]
        )
        if metrics:
            results.append({
                "provider": provider["name"],
                **metrics
            })
    
    # Print comparison if we have multiple results
    if len(results) > 1:
        print("\nComparison Summary:")
        print("-" * 50)
        for metric in ["ttft", "total_tokens", "total_time"]:
            values = [r[metric] for r in results]
            providers = [r["provider"] for r in results]
            best_idx = min(range(len(values)), key=lambda i: values[i])
            print(f"\nBest {metric}:")
            print(f"Winner: {providers[best_idx]} ({values[best_idx]:.3f})")

if __name__ == "__main__":
    asyncio.run(main()) 