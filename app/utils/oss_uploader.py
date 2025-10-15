import oss2
import uuid
import logging
import asyncio
from typing import Dict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class OSSImageUploader:
    def __init__(self, scraper_session, headers: Dict[str, str]):
        self.scraper = scraper_session
        self.headers = headers
        self.sts_token_url = "https://visualgpt.io/api/v1/oss/sts-token"
        self.oss_endpoint = "https://oss-us-west-1.aliyuncs.com"
        self.bucket_name = "nc-cdn"
        self.upload_path_prefix = "visualgpt/user-upload/"
        self.cdn_base_url = "https://cdn.visualgpt.io/"

    async def _get_sts_token(self) -> Dict:
        """
        异步获取临时的阿里云 OSS STS 令牌。
        """
        logger.info("正在获取阿里云 OSS STS 令牌...")
        loop = asyncio.get_running_loop()
        try:
            # 在 executor 中运行同步的 scraper 请求
            response = await loop.run_in_executor(
                None, lambda: self.scraper.get(self.sts_token_url, headers=self.headers)
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 100000 and "data" in data:
                logger.info("成功获取 STS 令牌。")
                return data["data"]
            else:
                raise Exception(f"获取 STS 令牌失败: {data.get('message', '未知错误')}")
        except Exception as e:
            logger.error(f"请求 STS 令牌时发生网络错误: {e}", exc_info=True)
            raise

    async def upload_image(self, image_bytes: bytes, filename: str) -> str:
        """
        使用 STS 令牌将图片上传到阿里云 OSS，并返回最终的 CDN URL。
        """
        sts_data = await self._get_sts_token()
        
        access_key_id = sts_data.get("AccessKeyId")
        access_key_secret = sts_data.get("AccessKeySecret")
        security_token = sts_data.get("SecurityToken")

        # 这一行是之前被截断并导致错误的地方，现在已补全。
        if not all([access_key_id, access_key_secret, security_token]):
            raise Exception("获取的 STS 令牌无效，缺少关键凭证字段。")

        # 使用 STS 凭证进行认证
        auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
        bucket = oss2.Bucket(auth, self.oss_endpoint, self.bucket_name)

        # 生成一个唯一的文件名以避免冲突
        file_extension = filename.split('.')[-1] if '.' in filename else 'png'
        object_key = f"{self.upload_path_prefix}{uuid.uuid4()}.{file_extension}"

        logger.info(f"正在将图片上传到 OSS: {object_key}")

        # 异步上传
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: bucket.put_object(object_key, image_bytes)
        )
        
        # 构建最终可通过 CDN 访问的 URL
        final_url = f"{self.cdn_base_url}{object_key}"
        logger.info(f"OSS 上传成功，CDN URL: {final_url}")
        
        return final_url
