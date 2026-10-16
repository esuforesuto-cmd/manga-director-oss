"""Local-server tests for the private ComfyUI transport."""

from __future__ import annotations

import base64
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from manga_director.production import next_generation_comfyui_provider_adapter as comfy_adapter
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIImagePrivateTransport,
    ComfyUIInMemoryGeneratedImageMaterial,
    StandardLibraryComfyUIHttpClient,
    validate_comfyui_endpoint,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
)
from manga_director.workflow.localfile_comfyui_real_image_generation import _validated_facts

_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_CHECKPOINT = "local-model.safetensors"
_NODE_TYPES = (
    "CheckpointLoaderSimple",
    "CLIPTextEncode",
    "EmptyLatentImage",
    "KSampler",
    "VAEDecode",
    "SaveImage",
)
_DESCRIPTOR_EXTRAS: dict[str, dict[str, object]] = {
    "comfyui-0.40-descriptor": {
        "metadata": {"kind": "image", "width": 1024, "height": 1024},
        "id": "75c88892-bdf7-4d2e-b886-92d0017b9af9",
    },
    "unexpected-descriptor-field": {"path": "ignored.png"},
    "invalid-descriptor-metadata": {"metadata": "image"},
    "invalid-descriptor-id": {"id": "../unsafe"},
}


class _ServerState(SimpleNamespace):
    mode: str
    post_count: int
    history_count: int
    elapsed_seconds: float
    paths: list[str]


def _state(mode: str = "success") -> _ServerState:
    return _ServerState(
        mode=mode,
        post_count=0,
        history_count=0,
        elapsed_seconds=0.0,
        paths=[],
    )


@contextmanager
def _server(state: _ServerState) -> Iterator[str]:  # noqa: C901
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _json(self, value: object, *, status: int = 200) -> None:
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract.
            state.paths.append(self.path)
            if self.path == "/system_stats":
                if state.mode == "redirect":
                    self.send_response(302)
                    self.send_header("Location", "/system_stats-real")
                    self.end_headers()
                    return
                self._json({"system": {"comfyui_version": "test"}})
                return
            if self.path.startswith("/object_info/"):
                node_type = self.path.rsplit("/", 1)[-1]
                module = "custom_nodes.unsafe" if state.mode == "custom-node" else "nodes"
                info: dict[str, object] = {"python_module": module, "input": {"required": {}}}
                if node_type == "CheckpointLoaderSimple":
                    info["input"] = {
                        "required": {
                            "ckpt_name": [
                                [] if state.mode == "missing-checkpoint" else [_CHECKPOINT],
                                {"tooltip": "test"},
                            ]
                        }
                    }
                self._json({node_type: info})
                return
            if self.path == "/history/prompt-1":
                state.history_count += 1
                if state.mode == "never-completes" or (
                    state.mode == "pending-then-success" and state.history_count == 1
                ) or (
                    state.mode == "ten-second-generation" and state.elapsed_seconds < 10.5
                ):
                    self._json({})
                    return
                filename = "../result.png" if state.mode == "unsafe-metadata" else "result.png"
                subfolder = "nested" if state.mode == "unsafe-subfolder" else ""
                images: list[dict[str, object]] = [
                    {"filename": filename, "subfolder": subfolder, "type": "output"}
                ]
                images[0].update(_DESCRIPTOR_EXTRAS.get(state.mode, {}))
                if state.mode == "multiple-outputs":
                    images.append(
                        {"filename": "result-2.png", "subfolder": "", "type": "output"}
                    )
                self._json(
                    {
                        "prompt-1": {
                            "status": {"status_str": "success", "completed": True},
                            "outputs": {"7": {"images": images}},
                        }
                    }
                )
                return
            if self.path.startswith("/view?"):
                body = (
                    b"\x89PNG\r\n\x1a\nmalformed"
                    if state.mode == "malformed-png"
                    else _PNG_BYTES
                )
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "image/jpeg" if state.mode == "wrong-content-type" else "image/png",
                )
                if state.mode == "oversize-stream":
                    body = b"x" * (25 * 1024 * 1024 + 1)
                else:
                    declared = 25 * 1024 * 1024 + 1 if state.mode == "oversize" else len(body)
                    self.send_header("Content-Length", str(declared))
                self.end_headers()
                self.wfile.write(body)
                return
            self._json({}, status=404)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract.
            state.paths.append(self.path)
            if self.path != "/prompt":
                self._json({}, status=404)
                return
            state.post_count += 1
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            assert set(payload) == {"prompt", "client_id"}
            assert set(payload["prompt"]) == {"1", "2", "3", "4", "5", "6", "7"}
            if state.mode == "malformed-submission":
                self._json({"prompt_id": ""})
                return
            self._json({"prompt_id": "prompt-1", "node_errors": {}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request_and_output() -> tuple[ProviderPrivateTransportRequest, object]:
    facts = _validated_facts(
        attempt_id="attempt:v7-04:human:editor:" + "1" * 32,
        request_id="request:v7-04:" + "1" * 32,
        target_reference="target:v7-04:001",
        intent_reference="intent:v7-04:" + "1" * 32,
        input_reference="input:v7-04:" + "1" * 32,
        execution_authorization_id="authorization:v7-04:" + "1" * 32,
        workflow_authorization_id="workflow-authorization:v7-04:human:editor:" + "1" * 32,
        project_id="project-v7-04",
        page_id="1",
        authorized_by="human:editor",
        checkpoint_name=_CHECKPOINT,
        observed_at=datetime(2026, 10, 15, 12, 0, tzinfo=UTC),
    )
    assert facts.configuration.selection is not None
    request = ProviderPrivateTransportRequest(
        attempt_id=facts.reservation.attempt_id,
        provider_reference=facts.reservation.provider_reference,
        profile_id="profile:v7-04:prompt-only-png",
        profile_version="v1",
        configuration_selection=facts.configuration.selection,
        raw_prompt="one monochrome manga panel",
    )
    return request, facts.output_configuration


def _transport(endpoint: str) -> tuple[ComfyUIImagePrivateTransport, ProviderPrivateTransportRequest]:
    request, output = _request_and_output()
    transport = ComfyUIImagePrivateTransport(
        _CHECKPOINT,
        output,  # type: ignore[arg-type]
        http_client=StandardLibraryComfyUIHttpClient(endpoint),
        poll_limit=3,
        poll_interval_seconds=0,
    )
    return transport, request


@pytest.mark.parametrize(
    "endpoint",
    (
        "https://127.0.0.1:8188",
        "http://localhost:8188",
        "http://192.168.1.20:8188",
        "http://0.0.0.0:8188",
        "http://[::1]:8188",
        "http://user:password@127.0.0.1:8188",
        "http://127.0.0.1:8188/prefix",
        "http://127.0.0.1:8188?query=1",
        "http://127.0.0.1:8188#fragment",
    ),
)
def test_endpoint_rejects_dns_lan_remote_wildcard_credentials_and_extras(endpoint: str) -> None:
    with pytest.raises(ValueError, match="endpoint"):
        validate_comfyui_endpoint(endpoint)


def test_read_only_preflight_uses_core_nodes_and_exact_checkpoint() -> None:
    state = _state()
    with _server(state) as endpoint:
        transport, _request = _transport(endpoint)
        transport.preflight()

    assert state.post_count == 0
    assert state.paths == ["/system_stats", *[f"/object_info/{node}" for node in _NODE_TYPES]]


def test_fixed_graph_submits_once_polls_same_id_and_returns_one_png(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state("pending-then-success")
    monkeypatch.setenv("HTTP_PROXY", "http://192.0.2.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://192.0.2.1:9")
    with _server(state) as endpoint:
        transport, request = _transport(endpoint)
        transport.preflight()
        result = transport.invoke(request)
        replay = transport.invoke(request)

    assert result.outcome == "succeeded"
    assert isinstance(result.output_material, ComfyUIInMemoryGeneratedImageMaterial)
    assert result.output_material.image_bytes == _PNG_BYTES
    assert replay.outcome == "runtime_failed"
    assert state.post_count == 1
    assert state.history_count == 2
    assert state.paths.count("/prompt") == 1
    assert state.paths.count("/history/prompt-1") == 2
    assert sum(path.startswith("/view?") for path in state.paths) == 1


def test_default_polling_window_observes_ten_second_generation() -> None:
    state = _state("ten-second-generation")

    def advance_clock(seconds: float) -> None:
        state.elapsed_seconds += seconds

    with _server(state) as endpoint:
        request, output = _request_and_output()
        transport = ComfyUIImagePrivateTransport(
            _CHECKPOINT,
            output,  # type: ignore[arg-type]
            http_client=StandardLibraryComfyUIHttpClient(endpoint),
            sleeper=advance_clock,
        )
        transport.preflight()

        result = transport.invoke(request)

    assert result.outcome == "succeeded"
    assert state.elapsed_seconds == 10.5
    assert state.history_count == 43
    assert state.post_count == 1
    assert state.paths.count("/prompt") == 1


def test_comfyui_040_descriptor_metadata_is_accepted_without_weakening_lookup() -> None:
    state = _state("comfyui-0.40-descriptor")
    with _server(state) as endpoint:
        transport, request = _transport(endpoint)
        transport.preflight()

        result = transport.invoke(request)

    assert result.outcome == "succeeded"
    assert isinstance(result.output_material, ComfyUIInMemoryGeneratedImageMaterial)
    assert result.output_material.image_bytes == _PNG_BYTES
    assert state.post_count == 1
    assert sum(path.startswith("/view?") for path in state.paths) == 1


def test_prepare_completes_graph_work_without_posting() -> None:
    state = _state()
    with _server(state) as endpoint:
        transport, request = _transport(endpoint)
        transport.preflight()

        prepared = transport.prepare(request)

        assert prepared is not None
        assert state.post_count == 0

        result = prepared()

    assert result.outcome == "succeeded"
    assert state.post_count == 1


@pytest.mark.parametrize("stage", ("build", "validation"))
def test_graph_prepare_failure_never_posts(
    stage: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()

    def fail(*_args: object, **_kwargs: object):
        raise ValueError(f"{stage} failed")

    monkeypatch.setattr(
        comfy_adapter,
        "build_comfyui_fixed_workflow"
        if stage == "build"
        else "validate_comfyui_fixed_workflow",
        fail,
    )
    with _server(state) as endpoint:
        transport, request = _transport(endpoint)
        transport.preflight()

        result = transport.invoke(request)

    assert result.outcome == "runtime_failed"
    assert state.post_count == 0


@pytest.mark.parametrize(
    "mode",
    (
        "malformed-submission",
        "multiple-outputs",
        "malformed-png",
        "oversize",
        "oversize-stream",
        "unsafe-metadata",
        "unsafe-subfolder",
        "unexpected-descriptor-field",
        "invalid-descriptor-metadata",
        "invalid-descriptor-id",
        "wrong-content-type",
        "never-completes",
    ),
)
def test_ambiguous_and_invalid_results_never_resubmit(mode: str) -> None:
    state = _state(mode)
    with _server(state) as endpoint:
        transport, request = _transport(endpoint)
        transport.preflight()
        first = transport.invoke(request)
        second = transport.invoke(request)

    assert first.outcome == "runtime_failed"
    assert second.outcome == "runtime_failed"
    assert state.post_count == 1


@pytest.mark.parametrize("mode", ("redirect", "custom-node", "missing-checkpoint"))
def test_redirect_and_custom_node_preflight_fail_before_submission(mode: str) -> None:
    state = _state(mode)
    with _server(state) as endpoint:
        transport, _request = _transport(endpoint)
        with pytest.raises(ValueError, match="ComfyUI"):
            transport.preflight()

    assert state.post_count == 0


def test_transport_source_never_reads_comfyui_output_paths() -> None:
    source = Path(__file__).resolve().parents[1].joinpath(
        "src/manga_director/production/next_generation_comfyui_provider_adapter.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("pathlib", "Path(", ".read_bytes(", "os.open(", "shutil"):
        assert forbidden not in source
