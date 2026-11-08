"""Synthetic regressions for release privacy and credential boundaries."""

import asyncio
import json
import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import paho.mqtt.client as mqtt
import pytest
from aiointercept import aiointercept
from yarl import URL

from whirlpool.auth import Auth
from whirlpool.awsiot.auth import COGNITO_URL, AuthException
from whirlpool.awsiot.auth import Auth as AwsAuth
from whirlpool.awsiot.mqttclient import MqttClient
from whirlpool.backendselector import BackendSelector

SENTINEL = "PRIVATE-SENTINEL-DO-NOT-LOG"


@pytest.mark.parametrize("status", [301, 302, 307, 308])
async def test_oauth_redirect_cannot_replay_credentials(
    auth: Auth,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    status: int,
) -> None:
    target = "https://third-party.invalid/token"
    aiointercept_mock.post(
        backend_selector.oauth_token_url, status=status, headers={"Location": target}
    )
    aiointercept_mock.post(target, payload={"access_token": SENTINEL})
    assert await auth.do_auth() is False
    assert ("POST", URL(target)) not in aiointercept_mock.requests


@pytest.mark.parametrize("status", [307, 308])
async def test_cognito_redirect_cannot_replay_token(
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    status: int,
) -> None:
    auth = AwsAuth(MagicMock(), client_session_fixture)
    auth.get_cognito_identity_id = AsyncMock(return_value=SENTINEL)
    auth._cognito_token = SENTINEL
    target = "https://third-party.invalid/token"
    aiointercept_mock.post(COGNITO_URL, status=status, headers={"Location": target})
    aiointercept_mock.post(target, payload={"Credentials": {"SecretKey": SENTINEL}})
    with pytest.raises(AuthException):
        await auth.get_aws_credentials()
    assert ("POST", URL(target)) not in aiointercept_mock.requests


async def test_mqtt_debug_does_not_log_topics_payloads_or_decode_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    callback = MagicMock()
    client = MqttClient(AsyncMock(), callback)
    active = MagicMock(spec=mqtt.Client)
    client._client = active
    for body in [{"downloadUrl": SENTINEL}, [SENTINEL], SENTINEL]:
        message = mqtt.MQTTMessage(topic=SENTINEL.encode())
        message.payload = json.dumps(body).encode()
        client._on_message(active, None, message)
    invalid = mqtt.MQTTMessage(topic=SENTINEL.encode())
    invalid.payload = b'"' + SENTINEL.encode() + b'\xff"'
    client._on_message(active, None, invalid)
    client._on_message(MagicMock(spec=mqtt.Client), None, invalid)
    await asyncio.sleep(0)
    callback.assert_called_once_with(SENTINEL, {"downloadUrl": SENTINEL})
    assert SENTINEL not in caplog.text
    await client.disconnect()


def test_auth_cache_is_private_and_atomic(
    auth: Auth, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destination = tmp_path / "auth.json"
    monkeypatch.setattr("whirlpool.auth.AUTH_JSON_FILE", str(destination))
    auth._auth_dict = {"access_token": SENTINEL}
    auth._save_auth_data()
    assert json.loads(destination.read_text()) == auth._auth_dict
    if os.name == "posix":
        assert destination.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [destination]


def test_auth_cache_refuses_symlink_without_touching_target(
    auth: Auth, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destination = tmp_path / "auth.json"
    target = tmp_path / "unrelated"
    target.write_text(SENTINEL)
    destination.symlink_to(target)
    monkeypatch.setattr("whirlpool.auth.AUTH_JSON_FILE", str(destination))
    with pytest.raises(ValueError):
        auth._save_auth_data()
    assert target.read_text() == SENTINEL


async def test_auth_cache_load_refuses_nonregular_or_public_file(
    auth: Auth, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destination = tmp_path / "auth.json"
    destination.write_text("{}")
    destination.chmod(0o644)
    monkeypatch.setattr("whirlpool.auth.AUTH_JSON_FILE", str(destination))
    if os.name == "posix":
        with pytest.raises(ValueError):
            await auth.load_auth_file()


@pytest.mark.parametrize(
    "url",
    [
        "http://caps.whrcloud.com/profile",
        "https://caps.whrcloud.com.evil.invalid/profile",
        "https://user:pass@caps.whrcloud.com/profile",
        "https://caps.whrcloud.com:444/profile",
        "https://127.0.0.1/profile",
        "https://[::1]/profile",
        "https://caps.whrcloud.com/#private",
        "https://caps.whrcloud.com:invalid/profile",
        "https://example.com/profile",
        42,
        "x" * 4097,
    ],
)
async def test_capability_unsafe_location_rejected_before_request(url: str) -> None:
    from whirlpool.awsiot.capabilities import (
        CapabilityDownloader,
        CapabilityDownloadError,
    )

    session = MagicMock(spec=aiohttp.ClientSession)
    downloader = CapabilityDownloader(MagicMock(), session)
    with pytest.raises(CapabilityDownloadError):
        await downloader._download_file({"downloadUrl": url})
    session.get.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 307, 308])
async def test_capability_redirect_not_followed(
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    status: int,
) -> None:
    from whirlpool.awsiot.capabilities import (
        CapabilityDownloader,
        CapabilityDownloadError,
    )

    url = "https://caps.whrcloud.com/profile"
    target = "https://third-party.invalid/target"
    aiointercept_mock.get(url, status=status, headers={"Location": target})
    aiointercept_mock.get(target, payload={"partNumber": "X"})
    downloader = CapabilityDownloader(MagicMock(), client_session_fixture)
    with pytest.raises(CapabilityDownloadError):
        await downloader._download_file({"downloadUrl": url})
    assert ("GET", URL(target)) not in aiointercept_mock.requests


@pytest.mark.parametrize("declared_length", [None, 1000])
async def test_capability_body_limit_applies_to_stream_and_content_length(
    monkeypatch: pytest.MonkeyPatch, declared_length: int | None
) -> None:
    from whirlpool.awsiot.capabilities import (
        CapabilityDownloader,
        CapabilityDownloadError,
    )

    monkeypatch.setattr("whirlpool.awsiot.capabilities.CAPABILITY_MAX_BYTES", 20)
    response = MagicMock()
    response.status = 200
    response.content_length = declared_length

    async def chunks(size: int):
        yield b"a" * 15
        yield b"b" * 15
        raise AssertionError("Downloader must stop when limit is exceeded")

    response.content.iter_chunked.side_effect = chunks
    context = AsyncMock()
    context.__aenter__.return_value = response
    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value = context
    downloader = CapabilityDownloader(MagicMock(), session)
    with pytest.raises(CapabilityDownloadError, match="exceeds limit"):
        await downloader._download_file({"downloadUrl": "https://caps.whrcloud.com/x"})
    if declared_length is not None:
        response.content.iter_chunked.assert_not_called()


async def test_capability_stream_has_total_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from whirlpool.awsiot.capabilities import (
        CapabilityDownloader,
        CapabilityDownloadError,
    )

    monkeypatch.setattr(
        "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 0.01
    )
    response = MagicMock()
    response.status = 200
    response.content_length = None

    async def chunks(size: int):
        while True:
            await asyncio.sleep(0.001)
            yield b" "

    response.content.iter_chunked.side_effect = chunks
    context = AsyncMock()
    context.__aenter__.return_value = response
    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value = context
    downloader = CapabilityDownloader(MagicMock(), session)
    with pytest.raises(CapabilityDownloadError, match="HTTP request failed"):
        await downloader._download_file({"downloadUrl": "https://caps.whrcloud.com/x"})


async def test_capability_network_error_does_not_expose_presigned_url() -> None:
    from whirlpool.awsiot.capabilities import (
        CapabilityDownloader,
        CapabilityDownloadError,
    )

    context = AsyncMock()
    context.__aenter__.side_effect = aiohttp.ClientError(SENTINEL)
    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value = context
    downloader = CapabilityDownloader(MagicMock(), session)
    with pytest.raises(CapabilityDownloadError) as result:
        await downloader._download_file({"downloadUrl": "https://caps.whrcloud.com/x"})
    assert SENTINEL not in str(result.value)
    assert result.value.__suppress_context__


async def test_discovery_and_laundry_warnings_do_not_log_device_fields(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from whirlpool.awsiot.appliancesmanager import AppliancesManager

    caplog.set_level(logging.DEBUG)
    manager = AppliancesManager(auth, client_session_fixture, lambda: None)
    manager._capability_downloader.get = AsyncMock(
        return_value={"partNumber": SENTINEL, "cavities": {SENTINEL: {}}}
    )
    await manager._add_appliance(
        {
            "thingName": SENTINEL,
            "thingTypeName": SENTINEL,
            "attributes": {
                "Name": SENTINEL.encode().hex(),
                "Serial": SENTINEL,
                "Category": "laundry",
                "CapabilityPartNumber": SENTINEL,
            },
        }
    )
    manager._handle_mqtt_message(
        f"dt/{SENTINEL}/{SENTINEL}/state/update", {"private": SENTINEL}
    )
    assert "Laundry appliance skipped" in caplog.text
    assert SENTINEL not in caplog.text
    await manager.disconnect()


async def test_things_error_body_is_not_logged(
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from whirlpool.awsiot.things import AWS_IOT_ENDPOINT, Things

    caplog.set_level(logging.DEBUG)
    auth = AsyncMock()
    auth.get_cognito_identity_id.return_value = "region:" + SENTINEL
    auth.create_signed_headers.return_value = {}
    endpoint = f"https://{AWS_IOT_ENDPOINT}"
    aiointercept_mock.get(
        f"{endpoint}/thing-groups/{SENTINEL}/things", status=500, body=SENTINEL
    )
    aiointercept_mock.get(f"{endpoint}/things/{SENTINEL}", status=500, body=SENTINEL)
    things = Things(auth, client_session_fixture)
    assert await things.list_things() == []
    assert await things.get_thing(SENTINEL) is None
    # aiointercept's HTTP test server logs request paths itself; only the
    # library's diagnostics are subject to its privacy contract.
    records = [
        record for record in caplog.records if record.name.startswith("whirlpool")
    ]
    assert records
    assert all(SENTINEL not in record.getMessage() for record in records)
