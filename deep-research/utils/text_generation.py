import os
import json
import httpx
import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict
from tenacity import retry, stop_after_attempt, wait_exponential
import traceback

logger = logging.getLogger(__name__)

class TextGenerator:
    def __init__(self, *, api_token: str, deepseek_api_key: str, siliconflow_key: str, ark_key: str):
        self.openai_key = api_token
        self.deepseek_key = deepseek_api_key
        self.siliconflow_key = siliconflow_key
        self.ark_key = ark_key

    async def generate_text(self, prompt: str, image_data: Optional[str] = None) -> Dict[str, str]:
        """Generate text with multiple provider fallback"""
        providers = ["openai", "doubao", "siliconflow", "deepseek_official"]
        last_exception = None
        
        messages = [{"role": "user", "content": prompt}]
        if image_data:
            messages[0]["content"] = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
            
        for provider in providers:
            try:
                if provider == "openai":
                    payload = {
                        "model": "gpt-4o" if image_data else "o3-mini",
                        "messages": messages,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    }
                    response = await self._try_provider_http(
                        "https://api.openai.com/v1/chat/completions",
                        payload,
                        headers
                    )
                    return response
                elif provider == "doubao":
                    payload = {
                        "model": "ep-20250206131705-gtthc",
                        "messages": messages,
                        "stream": False,
                        "max_tokens": 8192,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.ark_key}",
                        "Content-Type": "application/json"
                    }
                    response = await self._try_provider_http(
                        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                        payload,
                        headers
                    )
                    return response
                elif provider == "siliconflow":
                    payload = {
                        "model": "deepseek-ai/DeepSeek-R1",
                        "messages": messages,
                        "stream": False,
                        "max_tokens": 8192,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.siliconflow_key}",
                        "Content-Type": "application/json"
                    }
                    response = await self._try_provider_http(
                        "https://api.siliconflow.cn/v1/chat/completions",
                        payload,
                        headers
                    )
                    return response
                elif provider == "deepseek_official":
                    payload = {
                        "model": "deepseek-reasoner",
                        "messages": messages,
                        "stream": False,
                        "max_tokens": 8192,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.deepseek_key}",
                        "Content-Type": "application/json"
                    }
                    response = await self._try_provider_http(
                        "https://api.deepseek.com/v1/chat/completions",
                        payload,
                        headers
                    )
                    return response
            except Exception as e:
                last_exception = e
                logger.error(f"Provider {provider} failed: {str(e)}\n{traceback.format_exc()}")
                continue
                
        raise Exception(f"All providers failed: {str(last_exception)}")
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _try_provider_http(self, url: str, payload: Dict, headers: Dict) -> Dict[str, str]:
        """Try generating text using HTTP API"""
        timeout = httpx.Timeout(30.0, connect=10.0)  # 30s timeout for whole operation, 10s for connection
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                logger.info(f"API Response Status: {response.status_code}")
                logger.info(f"API Response Headers: {dict(response.headers)}")
                try:
                    response_body = response.json()
                    logger.info(f"API Response Body: {json.dumps(response_body, indent=2)}")
                except:
                    logger.info(f"API Response Text: {response.text}")
                response.raise_for_status()
                data = response.json()
                
                # Handle different response formats
                if "choices" in data and len(data["choices"]) > 0:
                    if "message" in data["choices"][0]:
                        content = data["choices"][0]["message"]["content"]
                    else:
                        content = data["choices"][0].get("text", "")
                else:
                    content = data.get("response", "")
                    
                return {
                    "content": content,
                    "intermediate_reasoning": data.get("intermediate_reasoning", "")
                }
            except httpx.TimeoutException as e:
                logger.error(f"Timeout error for {url}: {str(e)}")
                logger.error(f"Request payload: {json.dumps(payload, indent=2)}")
                raise
            except httpx.HTTPError as e:
                logger.error(f"HTTP error for {url}: {str(e)}")
                logger.error(f"Response status: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
                logger.error(f"Response body: {e.response.text if hasattr(e, 'response') else 'N/A'}")
                logger.error(f"Request payload: {json.dumps(payload, indent=2)}")
                raise
            except Exception as e:
                logger.error(f"API call failed: {str(e)}")
                logger.error(f"URL: {url}")
                logger.error(f"Payload: {json.dumps(payload, indent=2)}")
                logger.error(traceback.format_exc())
                raise
            
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _try_provider_doubao(self, prompt: str, model: str) -> Dict[str, str]:
        """Try generating text using Doubao API"""
        # Implement Doubao API call if needed
        raise NotImplementedError("Doubao provider not implemented")
        
    def generate_text_sync(self, prompt: str, image_data: Optional[str] = None) -> Dict[str, str]:
        """Synchronous wrapper for generate_text"""
        return asyncio.run(self.generate_text(prompt, image_data=image_data)) 