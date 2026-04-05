import hmac
import logging
from dataclasses import dataclass, field
from typing import Optional

import jwt
from fastapi import HTTPException, status, Header, Request
from fastapi.security import HTTPBearer
from src.config.config import config_manager

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """认证上下文 — 携带认证结果信息，供后续业务逻辑使用"""
    airline: str
    user: Optional[str] = None
    jwt_token: Optional[str] = None  # 原始 JWT 字符串，可传递给 Live Server
    auth_method: str = "none"  # "jwt" | "api_key" | "bearer_token" | "none"


def _safe_compare(a: str, b: str) -> bool:
    """常量时间字符串比较，防止时序攻击"""
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


def _try_jwt_auth(authorization: str, config) -> Optional[AuthContext]:
    """尝试 JWT 认证

    Returns:
        AuthContext: 认证成功
        None: JWT 未启用或验证失败
    """
    jwt_config = config.auth.jwt
    if not jwt_config.enabled or not jwt_config.secret:
        return None

    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        options = {}
        if not jwt_config.verify_exp:
            options["verify_exp"] = False

        payload = jwt.decode(
            token,
            jwt_config.secret,
            algorithms=[jwt_config.algorithm],
            options=options,
        )

        user_name = payload.get("userName") or payload.get("username") or payload.get("sub")

        logger.info("JWT认证成功: user=%s, iss=%s", user_name, payload.get("iss"))

        return AuthContext(
            airline="",  # JWT 中没有 airline，后续从 header/body 获取
            user=user_name,
            jwt_token=token,
            auth_method="jwt",
        )
    except jwt.ExpiredSignatureError:
        logger.warning("JWT已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("JWT验证失败: %s", e)
        return None


def _try_api_key_auth(x_api_key: str, x_airline: str, config) -> Optional[AuthContext]:
    """尝试 API Key 认证"""
    if not config.auth.api_key.enabled:
        return None

    if not x_api_key:
        return None

    # 先检查航司特定 API Key
    if x_airline and x_airline in config.auth.airline_auth:
        airline_auth = config.auth.airline_auth[x_airline]
        if airline_auth.api_key and _safe_compare(x_api_key, airline_auth.api_key):
            return AuthContext(airline=x_airline, auth_method="api_key")

    # 再检查全局 API Key
    if _safe_compare(x_api_key, config.auth.api_key.key):
        return AuthContext(airline=x_airline or "", auth_method="api_key")

    return None


def _try_bearer_token_auth(authorization: str, x_airline: str, config) -> Optional[AuthContext]:
    """尝试静态 Bearer Token 认证（向后兼容）"""
    if not config.auth.bearer_token.enabled or not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    # 先检查航司特定 Bearer Token
    if x_airline and x_airline in config.auth.airline_auth:
        airline_auth = config.auth.airline_auth[x_airline]
        if airline_auth.bearer_token and _safe_compare(token, airline_auth.bearer_token):
            return AuthContext(airline=x_airline, auth_method="bearer_token")

    # 再检查全局 Bearer Token
    if _safe_compare(token, config.auth.bearer_token.token):
        return AuthContext(airline=x_airline or "", auth_method="bearer_token")

    return None


def verify_token(
    request: Request,
    x_api_key: str = Header(None),
    authorization: str = Header(None, alias="Authorization"),
    x_airline: str = Header(None, alias="X-Airline"),
) -> AuthContext:
    """验证认证信息

    认证优先级:
    1. JWT (HS256 签名验证 + 过期检查)
    2. API Key (航司特定 → 全局)
    3. Bearer Token 静态验证 (航司特定 → 全局)

    Returns:
        AuthContext: 包含 airline, user, jwt_token 等认证信息
    """
    config = config_manager.get_config()

    # 认证未启用时直接放行
    if not config.auth.enabled:
        return AuthContext(airline=x_airline or "", auth_method="none")

    # --- 优先级 1: JWT 认证 ---
    ctx = _try_jwt_auth(authorization, config)
    if ctx is not None:
        # JWT 中没有 airline，从 header 获取
        if not ctx.airline and x_airline:
            ctx.airline = x_airline
        if not ctx.airline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JWT认证成功，但请求头中缺少 X-Airline 字段",
            )
        # 将 AuthContext 存储到 request.state 供后续使用
        request.state.auth_context = ctx
        return ctx

    # --- 优先级 2: API Key 认证 ---
    ctx = _try_api_key_auth(x_api_key, x_airline, config)
    if ctx is not None:
        request.state.auth_context = ctx
        return ctx

    # --- 优先级 3: 静态 Bearer Token 认证 ---
    ctx = _try_bearer_token_auth(authorization, x_airline, config)
    if ctx is not None:
        request.state.auth_context = ctx
        return ctx

    # --- 检查是否缺少 X-Airline ---
    if not x_airline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求头中缺少 X-Airline 字段",
        )

    # --- 全部失败 ---
    logger.warning("认证失败: airline=%s, has_api_key=%s, has_auth=%s",
                    x_airline, bool(x_api_key), bool(authorization))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证信息",
        headers={"WWW-Authenticate": "Bearer"},
    )
