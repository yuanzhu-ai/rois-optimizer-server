import hmac
import logging
from fastapi import HTTPException, status, Header
from fastapi.security import HTTPBearer
from src.config.config import config_manager

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def _safe_compare(a: str, b: str) -> bool:
    """常量时间字符串比较，防止时序攻击"""
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


def verify_token(x_api_key: str = Header(None), 
                 authorization: str = Header(None, alias="Authorization"),
                 x_airline: str = Header(None, alias="X-Airline")):
    """验证认证信息
    
    支持两种认证方式:
    1. API Key认证: Header中传入 X-API-Key
    2. Bearer Token认证: Header中传入 Authorization: Bearer <token>
    """
    config = config_manager.get_config()
    if not config.auth.enabled:
        return x_airline
    
    # 检查航司二字码是否存在
    if not x_airline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求头中缺少 X-Airline 字段",
        )
    
    # 检查API Key认证（优先级最高）
    if config.auth.api_key.enabled:
        # 先检查航司API Key
        if x_airline in config.auth.airline_auth:
            airline_auth = config.auth.airline_auth[x_airline]
            if airline_auth.api_key and _safe_compare(x_api_key or "", airline_auth.api_key):
                return x_airline
        # 再检查全局API Key
        if _safe_compare(x_api_key or "", config.auth.api_key.key):
            return x_airline
    
    # 检查Bearer Token认证
    if config.auth.bearer_token.enabled and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            # 先检查航司Bearer Token
            if x_airline in config.auth.airline_auth:
                airline_auth = config.auth.airline_auth[x_airline]
                if airline_auth.bearer_token and _safe_compare(token, airline_auth.bearer_token):
                    return x_airline
            # 再检查全局Bearer Token
            if _safe_compare(token, config.auth.bearer_token.token):
                return x_airline
    
    logger.warning("认证失败: airline=%s, has_api_key=%s, has_auth=%s", 
                   x_airline, bool(x_api_key), bool(authorization))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证信息",
        headers={"WWW-Authenticate": "Bearer"},
    )
