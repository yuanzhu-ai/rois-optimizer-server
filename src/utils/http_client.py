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
    降到 1。如果 verify=False 同时启用，还会关闭 hostname / 证书校验
    （否则与 urllib3 的 verify_mode=CERT_NONE 冲突）。
    """

    def __init__(self, verify: bool = True, *args, **kwargs):
        self._verify = verify
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        except ssl.SSLError as e:
            logger.warning("设置 SECLEVEL=1 失败: %s", e)
        if not self._verify:
            # 必须先关闭 check_hostname，再把 verify_mode 设成 CERT_NONE，
            # 否则 OpenSSL 会拒绝这个组合
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
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
            adapter = _LegacySSLAdapter(verify=self.verify)
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
    
    def _post(self, airline: str, url_path: str, *,
              body: Any = None,
              content_type: str = 'application/json',
              extra_headers: Optional[Dict[str, str]] = None,
              error_prefix: str = "HTTP 请求失败") -> requests.Response:
        """统一的 POST 请求入口，集中处理 URL 构建、请求头、TLS 设置、超时、异常包装

        Args:
            airline: 航司二字码（保留参数，由 _build_url 消费）
            url_path: API 路径
            body: 请求体。dict -> json 发送；int -> str(int) 作为原始 body；
                  bytes/str/None -> data 参数
            content_type: Content-Type 头，默认 application/json
            extra_headers: 额外请求头，会覆盖默认值
            error_prefix: 异常消息前缀，便于定位调用点

        Returns:
            requests.Response（已 raise_for_status）
        """
        url = self._build_url(airline, url_path)

        headers = {
            'Content-Type': content_type,
            'Flag': 'Rule',
        }
        if extra_headers:
            headers.update(extra_headers)

        kwargs: Dict[str, Any] = {
            'headers': headers,
            'timeout': self.timeout,
            'verify': self.verify,
        }
        if isinstance(body, dict):
            kwargs['json'] = body
        elif isinstance(body, int):
            kwargs['data'] = str(body)
        else:
            # bytes / str / None 走 data 参数
            kwargs['data'] = body

        try:
            response = self.session.post(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"{error_prefix}: {str(e)}")

    def get_input_data(self, airline: str, url_path: str,
                       data: Optional[Any] = None,
                       extra_headers: Optional[Dict[str, str]] = None) -> bytes:
        """从 Live Server 获取输入数据（gzip 压缩字节）"""
        response = self._post(
            airline,
            url_path,
            body=data,
            content_type='application/json',
            extra_headers=extra_headers,
            error_prefix="获取输入数据失败",
        )
        return response.content

    def submit_output_data(self, airline: str, url_path: str,
                           data: bytes,
                           extra_headers: Optional[Dict[str, str]] = None) -> bool:
        """向 Live Server 提交输出数据（gzip 压缩字节）"""
        self._post(
            airline,
            url_path,
            body=data,
            content_type='application/octet-stream',
            extra_headers=extra_headers,
            error_prefix="提交输出数据失败",
        )
        return True
    
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
