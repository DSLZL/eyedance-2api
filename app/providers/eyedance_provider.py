import time
import logging
import random
import asyncio
from typing import Dict, Any, Optional, Tuple

import cloudscraper
from fastapi import HTTPException

from app.core.config import settings
from app.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)

class EyeDanceProvider(BaseProvider):
    BASE_URL = "https://eyedance.net/api/generate"

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    def _prepare_headers(self, model_name: str) -> Dict[str, str]:
        """根据模型名称动态生成请求头"""
        referer = "https://eyedance.net/"
        cookie = None

        # 为 Flux-Krea 模型设置特定的 Referer 和 Cookie
        if model_name == "Flux-Krea":
            referer = "https://eyedance.net/es/flux-krea"
            cookie = "NEXT_LOCALE=es; active_theme=default"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://eyedance.net",
            "Referer": referer,
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def _parse_size(self, size: Optional[str]) -> Tuple[int, int]:
        if not size or 'x' not in size:
            return 600, 450
        try:
            width, height = map(int, size.split('x'))
            return width, height
        except (ValueError, TypeError):
            logger.warning(f"无效的 size 参数: '{size}', 使用默认值 600x450")
            return 600, 450

    async def _send_single_request(self, payload: Dict[str, Any]) -> str:
        loop = asyncio.get_running_loop()
        # 从 payload 中获取模型名称以生成正确的请求头
        model_name = payload.get("model", settings.DEFAULT_MODEL)
        headers = self._prepare_headers(model_name)
        
        for attempt in range(settings.UPSTREAM_MAX_RETRIES):
            try:
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.scraper.post(
                        self.BASE_URL,
                        headers=headers,
                        json=payload,
                        timeout=settings.API_REQUEST_TIMEOUT
                    )
                )
                
                if response.status_code >= 500:
                    logger.warning(f"上游返回 {response.status_code} 错误，正在重试... (尝试 {attempt + 1}/{settings.UPSTREAM_MAX_RETRIES})")
                    raise ConnectionError(f"Upstream {response.status_code} Error")

                response.raise_for_status()
                response_json = response.json()

                if "error" in response_json and response_json["error"] == "fetch failed":
                    logger.warning(f"上游返回 'fetch failed'，正在重试... (尝试 {attempt + 1}/{settings.UPSTREAM_MAX_RETRIES})")
                    raise ConnectionError("Upstream fetch failed")

                image_url = response_json.get("imageUrl")
                if not image_url or not image_url.startswith("data:image/png;base64,"):
                    raise ValueError("上游 API 未返回有效的 Base64 图像数据。")

                return image_url.split(',', 1)[1]

            except Exception as e:
                logger.error(f"请求上游失败 (尝试 {attempt + 1}): {e}")
                if attempt < settings.UPSTREAM_MAX_RETRIES - 1:
                    await asyncio.sleep(settings.UPSTREAM_RETRY_DELAY)
                else:
                    raise e
        
        raise ConnectionError("所有重试均失败。")

    async def generate_image(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = request_data.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="参数 'prompt' 不能为空。")

        # 从请求中获取模型，如果未提供则使用默认模型
        model_name = request_data.get("model", settings.DEFAULT_MODEL)
        if model_name not in settings.KNOWN_MODELS:
            raise HTTPException(status_code=400, detail=f"不支持的模型: '{model_name}'. 可用模型: {settings.KNOWN_MODELS}")

        # 如果是 Flux-Krea 模型，记录一个警告（因为该模型主要用于英文）
        if model_name == "Flux-Krea":
            try:
                prompt.encode('ascii')
            except UnicodeEncodeError:
                logger.warning("模型 'Flux-Krea' 强烈建议使用英文提示词，检测到非英文字符，生成效果可能不佳。")

        width, height = self._parse_size(request_data.get("size"))
        num_images = request_data.get("n", 1)
        steps = request_data.get("steps", 20)

        tasks = []
        for _ in range(num_images):
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": 1,
                "model": model_name,  # 使用从请求中获取的动态模型
                "seed": random.randint(0, 1_000_000)
            }
            tasks.append(self._send_single_request(payload))
        
        logger.info(f"准备向上游并发发送 {num_images} 个 '{model_name}' 模型请求...")

        try:
            results = await asyncio.gather(*tasks)
            
            response_data = {
                "created": int(time.time()),
                "data": [{"b64_json": b64_json} for b64_json in results]
            }
            return response_data

        except Exception as e:
            logger.error(f"处理并发请求时发生严重错误: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"上游服务错误或所有重试均失败: {str(e)}")

    async def get_models(self) -> Dict[str, Any]:
        model_data = {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
        return model_data
