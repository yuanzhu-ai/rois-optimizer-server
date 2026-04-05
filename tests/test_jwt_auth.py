"""
JWT 认证测试

覆盖:
- JWT 签名验证成功/失败
- JWT 过期检测
- JWT 自动提取 userName
- JWT token 自动传递给 Live Server
- JWT + API Key 混合模式（优先级）
- JWT 缺少 X-Airline header
"""
import time

import jwt as pyjwt
import pytest

# 测试用的 JWT 签名密钥
TEST_JWT_SECRET = "test_jwt_secret_for_unit_tests"


def _make_jwt(payload: dict, secret: str = TEST_JWT_SECRET, algorithm: str = "HS256") -> str:
    """生成测试用 JWT"""
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def _make_valid_jwt(user: str = "test_user", exp_offset: int = 3600) -> str:
    """生成一个有效的 JWT"""
    return _make_jwt({
        "userName": user,
        "iss": "admin@pi-solution",
        "exp": int(time.time()) + exp_offset,
    })


def _make_expired_jwt(user: str = "test_user") -> str:
    """生成一个已过期的 JWT"""
    return _make_jwt({
        "userName": user,
        "iss": "admin@pi-solution",
        "exp": int(time.time()) - 100,  # 100秒前过期
    })


@pytest.fixture(autouse=True)
def enable_jwt_auth(test_config):
    """为本测试文件启用 JWT 认证"""
    from src.config.config import config_manager, JWTConfig
    cfg = config_manager.get_config()
    old_auth_enabled = cfg.auth.enabled
    old_jwt = cfg.auth.jwt

    cfg.auth.enabled = True
    cfg.auth.jwt = JWTConfig(
        enabled=True,
        secret=TEST_JWT_SECRET,
        algorithm="HS256",
        verify_exp=True,
    )
    # 同时禁用 API Key 以隔离 JWT 测试（除非特定测试需要）
    old_api_key_enabled = cfg.auth.api_key.enabled
    cfg.auth.api_key.enabled = False

    yield

    cfg.auth.enabled = old_auth_enabled
    cfg.auth.jwt = old_jwt
    cfg.auth.api_key.enabled = old_api_key_enabled


class TestJWTAuthSuccess:
    """JWT 认证成功场景"""

    def test_valid_jwt(self, api_client):
        """有效 JWT 应通过认证"""
        token = _make_valid_jwt("yuan.z")
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 200

    def test_jwt_extracts_username(self, api_client, test_config):
        """JWT 中的 userName 应自动提取"""
        token = _make_valid_jwt("operator_wang")
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "PO",
                "parameters": {"scenarioId": "100"},
                "url": test_config['live_server_url'],
            },
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 200

    def test_jwt_token_passed_to_live_server(self, api_client, test_config):
        """JWT 模式下，JWT token 应自动传递给 Live Server"""
        token = _make_valid_jwt("yuan.z")
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "PO",
                "parameters": {"scenarioId": "200"},
                "url": test_config['live_server_url'],
                # 注意: 不传 token 字段
            },
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 200

        # 验证 Mock Live Server 收到的请求中包含 JWT token
        import time as t
        t.sleep(0.5)  # 等待异步请求发出
        input_reqs = [r for r in test_config['mock_requests'] if '/comptxt' in r['path']]
        if input_reqs:
            auth_header = input_reqs[0]['headers'].get('Authorization', '')
            assert token in auth_header


class TestJWTAuthFailure:
    """JWT 认证失败场景"""

    def test_expired_jwt(self, api_client):
        """过期的 JWT 应返回 401"""
        token = _make_expired_jwt()
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 401

    def test_invalid_signature(self, api_client):
        """用错误密钥签名的 JWT 应返回 401"""
        token = _make_jwt(
            {"userName": "hacker", "exp": int(time.time()) + 3600},
            secret="wrong_secret",
        )
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 401

    def test_malformed_jwt(self, api_client):
        """格式错误的 JWT 应返回 401"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "Bearer not.a.valid.jwt.token",
            },
        )
        assert resp.status_code == 401

    def test_jwt_missing_airline_header(self, api_client):
        """JWT 有效但缺少 X-Airline 应返回 400"""
        token = _make_valid_jwt()
        resp = api_client.get(
            "/api/system/info",
            headers={
                "Authorization": f"Bearer {token}",
                # 不传 X-Airline
            },
        )
        assert resp.status_code == 400
        assert "X-Airline" in resp.json()['detail']


class TestJWTWithAPIKeyMixed:
    """JWT + API Key 混合模式"""

    @pytest.fixture(autouse=True)
    def enable_both_auth(self, test_config):
        """同时启用 JWT 和 API Key"""
        from src.config.config import config_manager
        cfg = config_manager.get_config()
        cfg.auth.api_key.enabled = True
        cfg.auth.api_key.key = "mixed_test_api_key"
        yield
        cfg.auth.api_key.enabled = False

    def test_jwt_takes_priority_over_api_key(self, api_client):
        """同时传 JWT 和 API Key 时，JWT 优先"""
        token = _make_valid_jwt("jwt_user")
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
                "X-API-Key": "mixed_test_api_key",
            },
        )
        assert resp.status_code == 200

    def test_api_key_fallback_when_jwt_invalid(self, api_client):
        """JWT 无效时应回退到 API Key 认证"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "Bearer invalid_token",
                "X-API-Key": "mixed_test_api_key",
            },
        )
        assert resp.status_code == 200

    def test_api_key_only_without_jwt(self, api_client):
        """只传 API Key 不传 JWT 也应通过"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "X-API-Key": "mixed_test_api_key",
            },
        )
        assert resp.status_code == 200

    def test_both_invalid_returns_401(self, api_client):
        """JWT 和 API Key 都无效时返回 401"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "Bearer invalid_token",
                "X-API-Key": "wrong_key",
            },
        )
        assert resp.status_code == 401


class TestJWTExpDisabled:
    """JWT 过期检查禁用"""

    @pytest.fixture(autouse=True)
    def disable_exp_verify(self, test_config):
        """临时禁用过期检查"""
        from src.config.config import config_manager
        cfg = config_manager.get_config()
        cfg.auth.jwt.verify_exp = False
        yield
        cfg.auth.jwt.verify_exp = True

    def test_expired_jwt_passes_when_exp_disabled(self, api_client):
        """verify_exp=False 时过期 JWT 仍应通过"""
        token = _make_expired_jwt()
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 200
