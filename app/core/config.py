from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "eyedance-2api"
    APP_VERSION: str = "2.0.0"
    DESCRIPTION: str = "一个将 eyedance.net 转换为兼容 OpenAI 格式 API 的高性能并发代理。"

    API_MASTER_KEY: Optional[str] = None
    NGINX_PORT: int = 8089

    # 上游请求配置
    API_REQUEST_TIMEOUT: int = 180
    UPSTREAM_MAX_RETRIES: int = 3
    UPSTREAM_RETRY_DELAY: int = 2 # 秒

    # 模型配置
    DEFAULT_MODEL: str = "eyedance-qwen-image"
    # 新增 "Flux-Krea" 模型
    KNOWN_MODELS: List[str] = ["eyedance-qwen-image", "Flux-Krea"]
    UPSTREAM_MODEL_NAME: str = "Qwen-Image"

settings = Settings()
