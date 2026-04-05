"""
认证和错误路径测试

覆盖:
- API Key 认证成功/失败
- Bearer Token 认证成功/失败
- 认证禁用模式
- 航司特定认证
- 缺少必须 header
- 无效的优化器类型
- 缺少必须参数
- 并发数超限
"""
import pytest


# ============================================================
# 认证禁用测试 (auth.enabled = false)
# ============================================================

class TestAuthDisabled:
    """认证禁用时所有请求应直接通过"""

    def test_request_without_any_auth(self, api_client, test_config):
        """禁用认证时，无需任何认证 header"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 200

    def test_request_without_airline_header(self, api_client, test_config):
        """禁用认证时，没有 X-Airline 也不报 401（返回 airline=None）"""
        resp = api_client.get("/api/system/info")
        assert resp.status_code == 200


# ============================================================
# API Key 认证测试
# ============================================================

class TestAPIKeyAuth:
    """API Key 认证模式"""

    @pytest.fixture(autouse=True)
    def enable_api_key_auth(self, test_config):
        """临时启用 API Key 认证"""
        from src.config.config import config_manager
        cfg = config_manager.get_config()
        old_auth_enabled = cfg.auth.enabled
        old_api_key_enabled = cfg.auth.api_key.enabled
        old_key = cfg.auth.api_key.key

        cfg.auth.enabled = True
        cfg.auth.api_key.enabled = True
        cfg.auth.api_key.key = "test_api_key_12345"

        yield

        cfg.auth.enabled = old_auth_enabled
        cfg.auth.api_key.enabled = old_api_key_enabled
        cfg.auth.api_key.key = old_key

    def test_valid_api_key(self, api_client):
        """正确的 API Key 应通过认证"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR", "X-API-Key": "test_api_key_12345"},
        )
        assert resp.status_code == 200

    def test_invalid_api_key(self, api_client):
        """错误的 API Key 应返回 401"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR", "X-API-Key": "wrong_key"},
        )
        assert resp.status_code == 401

    def test_missing_api_key(self, api_client):
        """缺少 API Key 应返回 401"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 401

    def test_missing_airline_header(self, api_client):
        """缺少 X-Airline header 应返回 400"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-API-Key": "test_api_key_12345"},
        )
        assert resp.status_code == 400
        assert "X-Airline" in resp.json()['detail']


# ============================================================
# Bearer Token 认证测试
# ============================================================

class TestBearerTokenAuth:
    """Bearer Token 认证模式"""

    @pytest.fixture(autouse=True)
    def enable_bearer_auth(self, test_config):
        """临时启用 Bearer Token 认证"""
        from src.config.config import config_manager
        cfg = config_manager.get_config()
        old_auth_enabled = cfg.auth.enabled
        old_api_key_enabled = cfg.auth.api_key.enabled
        old_bearer_enabled = cfg.auth.bearer_token.enabled
        old_token = cfg.auth.bearer_token.token

        cfg.auth.enabled = True
        cfg.auth.api_key.enabled = False
        cfg.auth.bearer_token.enabled = True
        cfg.auth.bearer_token.token = "test_bearer_token_xyz"

        yield

        cfg.auth.enabled = old_auth_enabled
        cfg.auth.api_key.enabled = old_api_key_enabled
        cfg.auth.bearer_token.enabled = old_bearer_enabled
        cfg.auth.bearer_token.token = old_token

    def test_valid_bearer_token(self, api_client):
        """正确的 Bearer Token 应通过认证"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "Bearer test_bearer_token_xyz",
            },
        )
        assert resp.status_code == 200

    def test_invalid_bearer_token(self, api_client):
        """错误的 Bearer Token 应返回 401"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "Bearer wrong_token",
            },
        )
        assert resp.status_code == 401

    def test_malformed_authorization_header(self, api_client):
        """格式错误的 Authorization header"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "InvalidFormat token_value",
            },
        )
        assert resp.status_code == 401

    def test_bearer_without_token_value(self, api_client):
        """只有 Bearer 前缀没有 token 值"""
        resp = api_client.get(
            "/api/system/info",
            headers={
                "X-Airline": "BR",
                "Authorization": "Bearer",
            },
        )
        assert resp.status_code == 401


# ============================================================
# 航司特定认证测试
# ============================================================

class TestAirlineSpecificAuth:
    """航司特定 API Key 认证"""

    @pytest.fixture(autouse=True)
    def enable_airline_auth(self, test_config):
        """临时启用航司认证"""
        from src.config.config import config_manager, AirlineAuthConfig
        cfg = config_manager.get_config()
        old_auth_enabled = cfg.auth.enabled
        old_api_key_enabled = cfg.auth.api_key.enabled
        old_airline_auth = cfg.auth.airline_auth.copy()

        cfg.auth.enabled = True
        cfg.auth.api_key.enabled = True
        cfg.auth.api_key.key = "global_key"
        cfg.auth.airline_auth = {
            "BR": AirlineAuthConfig(api_key="br_specific_key", bearer_token=""),
            "F8": AirlineAuthConfig(api_key="f8_specific_key", bearer_token=""),
        }

        yield

        cfg.auth.enabled = old_auth_enabled
        cfg.auth.api_key.enabled = old_api_key_enabled
        cfg.auth.airline_auth = old_airline_auth

    def test_airline_specific_key_br(self, api_client):
        """BR 航司特定 Key 应通过"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR", "X-API-Key": "br_specific_key"},
        )
        assert resp.status_code == 200

    def test_airline_specific_key_f8(self, api_client):
        """F8 航司特定 Key 应通过"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "F8", "X-API-Key": "f8_specific_key"},
        )
        assert resp.status_code == 200

    def test_global_key_fallback(self, api_client):
        """全局 Key 在航司 Key 不匹配时应作为 fallback"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "BR", "X-API-Key": "global_key"},
        )
        assert resp.status_code == 200

    def test_wrong_airline_key(self, api_client):
        """BR 的 Key 用于 F8 应失败"""
        resp = api_client.get(
            "/api/system/info",
            headers={"X-Airline": "F8", "X-API-Key": "br_specific_key"},
        )
        assert resp.status_code == 401


# ============================================================
# 请求参数验证错误测试
# ============================================================

class TestRequestValidation:
    """请求参数验证"""

    def test_invalid_optimizer_type(self, api_client, test_config):
        """不支持的优化器类型"""
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "INVALID_TYPE",
                "parameters": {},
                "url": test_config['live_server_url'],
            },
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 400
        assert "不支持的优化器类型" in resp.json()['detail']

    def test_rule_missing_category(self, api_client, test_config):
        """Rule 类型缺少 category 参数"""
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "Rule",
                "parameters": {},  # 缺少 category
                "url": test_config['live_server_url'],
            },
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 400
        assert "category" in resp.json()['detail']

    def test_po_missing_scenario_id(self, api_client, test_config):
        """PO 类型缺少 scenarioId 参数"""
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "PO",
                "parameters": {},  # 缺少 scenarioId
                "url": test_config['live_server_url'],
            },
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 400
        assert "scenarioId" in resp.json()['detail']

    def test_ro_missing_scenario_id(self, api_client, test_config):
        """RO 类型缺少 scenarioId 参数"""
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "RO",
                "parameters": {},
                "url": test_config['live_server_url'],
            },
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 400
        assert "scenarioId" in resp.json()['detail']

    def test_to_missing_scenario_id(self, api_client, test_config):
        """TO 类型缺少 scenarioId 参数"""
        resp = api_client.post(
            "/api/optimize/start",
            json={
                "airline": "BR",
                "type": "TO",
                "parameters": {},
                "url": test_config['live_server_url'],
            },
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 400
        assert "scenarioId" in resp.json()['detail']

    def test_stop_nonexistent_task(self, api_client, test_config):
        """停止不存在的任务"""
        resp = api_client.post(
            "/api/optimize/stop/nonexistent-id",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 400

    def test_status_nonexistent_task(self, api_client, test_config):
        """查询不存在的任务状态"""
        resp = api_client.get(
            "/api/optimize/status/nonexistent-id",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 404

    def test_progress_nonexistent_task(self, api_client, test_config):
        """查询不存在的任务进度"""
        resp = api_client.get(
            "/api/optimize/progress/nonexistent-id",
            headers={"X-Airline": "BR"},
        )
        assert resp.status_code == 404


# ============================================================
# 健康检查
# ============================================================

class TestHealthCheck:
    """健康检查端点"""

    def test_health_check(self, api_client, test_config):
        """健康检查应返回 healthy"""
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'healthy'

    def test_root_endpoint(self, api_client, test_config):
        """根路径应返回服务信息"""
        resp = api_client.get("/")
        assert resp.status_code == 200
