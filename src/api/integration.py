import os
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class InterfaceIntegration:
    def __init__(self):
        pass
    
    def get_input_file(self, task_id: str, output_path: str, url: str, token: str) -> bool:
        """从现有系统获取input.gz文件"""
        try:
            headers = {
                "Authorization": f"Bearer {token}"
            }
            params = {
                "task_id": task_id
            }
            
            response = requests.post(
                url,
                headers=headers,
                params=params,
                stream=True
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
            else:
                logger.error("获取input.gz失败: status=%d, task_id=%s", response.status_code, task_id)
                return False
        except Exception as e:
            logger.error("获取input.gz异常: %s, task_id=%s", e, task_id, exc_info=True)
            return False
    
    def send_output_file(self, task_id: str, input_path: str, url: str, token: str) -> bool:
        """向现有系统回传output.gz文件"""
        try:
            headers = {
                "Authorization": f"Bearer {token}"
            }
            params = {
                "task_id": task_id
            }
            
            with open(input_path, "rb") as f:
                files = {
                    "file": ("output.gz", f)
                }
                response = requests.post(
                    url,
                    headers=headers,
                    params=params,
                    files=files
                )
            
            if response.status_code == 200:
                return True
            else:
                logger.error("回传output.gz失败: status=%d, task_id=%s", response.status_code, task_id)
                return False
        except Exception as e:
            logger.error("回传output.gz异常: %s, task_id=%s", e, task_id, exc_info=True)
            return False
    
    def call_external_api(self, url: str, token: str, method: str = "POST", data: Dict[str, Any] = None, files: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """调用外部API"""
        try:
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            if method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    files=files
                )
            elif method.upper() == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    params=data
                )
            else:
                logger.warning("不支持的请求方法: %s", method)
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("调用外部API失败: status=%d, url=%s", response.status_code, url)
                return None
        except Exception as e:
            logger.error("调用外部API异常: %s, url=%s", e, url, exc_info=True)
            return None


# 全局接口集成实例
interface_integration = InterfaceIntegration()
