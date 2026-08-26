"""Regression test for MammotionHTTP.logout() clearing cached credential state.

Before this fix, logout() reset only `login_info` and the Authorization header,
leaving `mqtt_credentials`, `expires_in`, and `jwt_info` populated with values
bound to the just-invalidated session. After a `logout()` + `login_v2()`
sequence (the path `_full_relogin` takes), anything reading `_http.mqtt_credentials`
got a stale JWT that the MQTT broker would reject — feeding the auth-retry
loop the broker rejections were supposed to break out of.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from pymammotion.http.http import MammotionHTTP
from pymammotion.http.model.http import JWTTokenInfo, MQTTConnection, Response


class _FakeResponse:
    def __init__(self, status: int, body: str, content_type: str = "application/json") -> None:
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._body = body

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def text(self) -> str:
        return self._body


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _http_for_stream(responses: list[_FakeResponse]) -> tuple[MammotionHTTP, _FakeSession]:
    http = MammotionHTTP(account="video@example.com", password="secret")
    http.login_info = MagicMock(access_token="old-token")  # type: ignore[assignment]
    http.expires_in = 9_999_999_999.0
    session = _FakeSession(responses)

    @asynccontextmanager
    async def _fake_session() -> object:  # type: ignore[misc]
        yield session

    http._client_session = _fake_session  # type: ignore[method-assign]
    return http, session


def _make_http_with_session() -> MammotionHTTP:
    """Build a MammotionHTTP whose _client_session yields a mock session."""
    http = MammotionHTTP()
    mock_session = MagicMock()
    mock_session.post = AsyncMock()

    @asynccontextmanager
    async def _fake_session() -> object:  # type: ignore[misc]
        yield mock_session

    http._client_session = _fake_session  # type: ignore[method-assign]
    return http


@pytest.mark.asyncio
async def test_logout_invalidates_cached_mqtt_credentials_and_expiry() -> None:
    http = _make_http_with_session()
    # Populate the state that logout() previously left stale.
    http.login_info = MagicMock(access_token="tok")  # type: ignore[assignment]
    http.mqtt_credentials = MQTTConnection(host="h", jwt="stale-jwt", client_id="c", username="u")
    http.expires_in = 9999999999.0
    http.jwt_info = JWTTokenInfo(iot="https://iot.example", robot="https://robot.example")
    http._headers["Authorization"] = "Bearer stale"

    await http.logout()

    assert http.login_info is None, "login_info must be cleared"
    assert http.mqtt_credentials is None, "stale MQTT JWT must not survive logout"
    assert http.expires_in == 0.0, "expires_in must be reset so the next request triggers a refresh"
    assert http.jwt_info == JWTTokenInfo("", ""), "jwt_info (iot/robot URLs) must be cleared"
    assert "Authorization" not in http._headers, "Authorization header must be removed"


@pytest.mark.asyncio
async def test_logout_is_a_noop_when_already_logged_out() -> None:
    """logout() with login_info=None must not blow up or touch other state."""
    http = MammotionHTTP()
    http.mqtt_credentials = MQTTConnection(host="h", jwt="kept", client_id="c", username="u")

    await http.logout()

    # No login_info means no server-side logout call; cached creds are untouched.
    assert http.mqtt_credentials is not None
    assert http.mqtt_credentials.jwt == "kept"


@pytest.mark.asyncio
async def test_legacy_stream_subscription_uses_legacy_endpoint_and_response_shape() -> None:
    http, session = _http_for_stream(
        [
            _FakeResponse(
                200, '{"code":0,"msg":"success","data":{"appid":"app","channelName":"hallon","token":"token","uid":7}}'
            )
        ]
    )

    response = await http.get_stream_subscription("iot-id", is_yuka=True, legacy=True)

    assert response.data is not None
    assert response.data.channelName == "hallon"
    assert response.data.cameras == []
    url, kwargs = session.calls[0]
    assert url.endswith("/device-server/v1/stream/subscription")
    assert kwargs["json"] == {"deviceId": "iot-id"}
    assert kwargs["headers"]["Authorization"] == "Bearer old-token"  # type: ignore[index]


@pytest.mark.asyncio
async def test_stream_subscription_refreshes_rejected_token_and_retries() -> None:
    http, session = _http_for_stream(
        [
            _FakeResponse(401, '{"code":40105,"msg":"expired"}'),
            _FakeResponse(
                200, '{"code":0,"msg":"success","data":{"appid":"app","channelName":"channel","token":"token","uid":7}}'
            ),
        ]
    )

    async def _refresh() -> Response[object]:
        assert http.login_info is not None
        http.login_info.access_token = "new-token"
        return Response(code=0, msg="success")

    http.refresh_login = AsyncMock(side_effect=_refresh)  # type: ignore[method-assign]

    response = await http.get_stream_subscription("iot-id", is_yuka=True, legacy=True)

    assert response.data is not None
    http.refresh_login.assert_awaited_once()  # type: ignore[attr-defined]
    assert len(session.calls) == 2
    assert session.calls[1][1]["headers"]["Authorization"] == "Bearer new-token"  # type: ignore[index]


@pytest.mark.asyncio
async def test_new_yuka_stream_falls_back_to_legacy_when_unsupported() -> None:
    http, session = _http_for_stream(
        [
            _FakeResponse(200, '{"code":40200,"msg":"the device does not support video"}'),
            _FakeResponse(
                200, '{"code":0,"msg":"success","data":{"appid":"app","channelName":"channel","token":"token","uid":7}}'
            ),
        ]
    )

    response = await http.get_stream_subscription("iot-id", is_yuka=True)

    assert response.data is not None
    assert session.calls[0][0].endswith("/device-server/v1/stream/token")
    assert session.calls[0][1]["json"] == {
        "deviceId": "iot-id",
        "mode": 0,
        "cameraStates": [{"cameraState": 1}, {"cameraState": 0}, {"cameraState": 1}],
    }
    assert session.calls[1][0].endswith("/device-server/v1/stream/subscription")
