"""
HTTP客户端模块，用于与Live Server通信
"""
import logging
import ssl
import requests
import gzip
import io
from typing import Dict, Optional, Any
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from src.config.config import config_manager

logger = logging.getLogger(__name__)


class _LegacySSLAdapter(HTTPAdapter):
    """允许弱密钥/SHA1 证书的 HTTPS 适配器（用于老旧测试服）。

    OpenSSL 3.0 默认 security level 是 2，会拒绝 1024-bit RSA、SHA1
    签名等老证书，报 'EE certificate key too weak'。本适配器把 level
    降到 1，但保留 CA 链、有效期、hostname 等正常校验。
    """

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        except ssl.SSLError as e:
            logger.warning("设置 SECLEVEL=1 失败: %s", e)
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


class LiveServerClient:
    """Live Server HTTP客户端"""
    
    def __init__(self, base_url: str, token: str, timeout: int = None):
        """
        初始化客户端
        
        Args:
            base_url: Live Server基础URL（如：https://192.168.199.182）
            token: 认证Token
            timeout: 请求超时时间（秒），默认从配置文件中读取（默认600秒=10分钟）
            注：input.gz生成可能需要1-3分钟，所以设置较长的超时时间
        """
        # 如果没有指定超时时间，从配置中读取
        http_cfg = config_manager.get_config().http_client
        if timeout is None:
            timeout = http_cfg.timeout
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.verify = http_cfg.ssl_verify
        self.session = requests.Session()

        # 测试环境兼容：允许弱密钥/SHA1 证书的老服务器
        if http_cfg.legacy_ssl:
            adapter = _LegacySSLAdapter()
            self.session.mount("https://", adapter)
            logger.warning("HTTP 客户端已启用 legacy_ssl（OpenSSL SECLEVEL=1），仅供测试环境")

        if not self.verify:
            logger.warning("HTTP 客户端已禁用 SSL 证书校验（ssl_verify=false），仅供测试环境")
            # 关闭 urllib3 的不安全请求警告刷屏
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

        # 设置默认请求头
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Apache-HttpClient/4.5.2 (Java/1.8.0_111)',
            'Accept-Encoding': 'gzip,deflate',
            'Connection': 'Keep-Alive'
        })
    
    def _build_url(self, airline: str, path: str) -> str:
        """
        构建完整URL
        
        URL格式: {base_url}{path}
        例如: http://localhost/api/orengine/po/comptxt
        
        直接使用请求参数中的url作为base_url，不再添加航司和admin前缀
        
        Args:
            airline: 航司二字码（保留参数但不使用）
            path: API路径（如：/api/orengine/po/comptxt）
            
        Returns:
            完整URL
        """
        # 直接使用base_url + path，不再添加额外前缀
        # base_url应该已经是完整的地址，如 http://localhost
        full_url = f"{self.base_url}{path}"
        return full_url
    
    def get_input_data(self, airline: str, url_path: str, 
                       data: Optional[Any] = None,
                       extra_headers: Optional[Dict[str, str]] = None) -> bytes:
        """
        从Live Server获取输入数据
        
        Args:
            airline: 航司二字码
            url_path: 输入URL路径（如：/api/orengine/po/comptxt）
            data: 请求数据（可选，支持字符串或字典）
            extra_headers: 额外的请求头
            
        Returns:
            输入数据（gzip压缩的字节）
        """
        url = self._build_url(airline, url_path)
        
        # 设置请求头
        headers = {
            'Content-Type': 'application/json',
            'Flag': 'Rule'
        }
        if extra_headers:
            headers.update(extra_headers)
        
        # 准备请求体
        request_data = data
        
        try:
            # 根据数据类型选择发送方式
            if isinstance(request_data, dict):
                # 字典类型使用json参数
                response = self.session.post(
                    url,
                    json=request_data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify
                )
            elif isinstance(request_data, int):
                # 整数类型直接作为原始body发送
                headers['Content-Type'] = 'application/json'
                response = self.session.post(
                    url,
                    data=str(request_data),
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify
                )
            else:
                # 其他类型使用data参数
                response = self.session.post(
                    url,
                    data=request_data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify
                )
            response.raise_for_status()
            
            # 返回响应内容（可能是gzip压缩的）
            return response.content
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取输入数据失败: {str(e)}")
    
    def submit_output_data(self, airline: str, url_path: str, 
                          data: bytes,
                          extra_headers: Optional[Dict[str, str]] = None) -> bool:
        """
        向Live Server提交输出数据
        
        Args:
            airline: 航司二字码
            url_path: 输出URL路径（如：/api/orengine/po/solution）
            data: 输出数据（gzip压缩的字节）
            extra_headers: 额外的请求头
            
        Returns:
            是否提交成功
        """
        url = self._build_url(airline, url_path)
        
        # 设置请求头
        headers = {
            'Content-Type': 'application/octet-stream',
            'Flag': 'Rule'
        }
        if extra_headers:
            headers.update(extra_headers)
        
        try:
            response = self.session.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return True
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"提交输出数据失败: {str(e)}")
    
    def close(self):
        """关闭HTTP会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_live_server_client(base_url: str, token: str, 
                              timeout: int = None) -> LiveServerClient:
    """
    创建Live Server客户端
    
    Args:
        base_url: Live Server基础URL
        token: 认证Token
        timeout: 请求超时时间（秒），默认从配置文件中读取（默认600秒=10分钟）
        注：input.gz生成可能需要1-3分钟，所以设置较长的超时时间
        可在config.yaml中调整http_client.timeout配置
        
    Returns:
        LiveServerClient实例
    """
    return LiveServerClient(base_url, token, timeout)
