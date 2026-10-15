"""Private loopback-only ComfyUI transport for one fixed prompt workflow."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

from manga_director.production.future_real_delivery_i01 import StrictPngStructuralValidatorV1
from manga_director.production.next_generation_comfyui_fixed_workflow import (
    COMFYUI_FIXED_NODE_TYPES,
    COMFYUI_OUTPUT_NODE_ID,
    build_comfyui_fixed_workflow,
    validate_comfyui_checkpoint_name,
    validate_comfyui_fixed_workflow,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
    ProviderPrivateTransportResult,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingReport,
)

COMFYUI_BASE_ENDPOINT: Final = "http://127.0.0.1:8188"
_COMFYUI_PROVIDER_ID = "comfyui"
_JSON_LIMIT_BYTES = 2 * 1024 * 1024
_PNG_LIMIT_BYTES = 25 * 1024 * 1024
_TIMEOUT_SECONDS = 5.0
_POLL_LIMIT = 20
_POLL_INTERVAL_SECONDS = 0.25
_PROMPT_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_OUTPUT_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}\.png$")


class ComfyUIHttpClientPort(Protocol):
    """Minimal same-origin HTTP surface used by the private transport."""

    @property
    def origin(self) -> str: ...

    def get_json(self, path: str) -> object: ...

    def post_json(self, path: str, payload: Mapping[str, object]) -> object: ...

    def get_png(self, path: str, query: Mapping[str, str]) -> bytes: ...


@dataclass(frozen=True, slots=True)
class ComfyUIInMemoryGeneratedImageMaterial:
    """Validated ComfyUI bytes carried only through an opaque runtime handle."""

    image_bytes: bytes = field(repr=False, compare=False)
    media_type: str = "image/png"


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        del req, fp, code, msg, headers, newurl
        return None


class StandardLibraryComfyUIHttpClient:
    """Bounded urllib client with redirects and environment proxies disabled."""

    def __init__(
        self,
        endpoint: str = COMFYUI_BASE_ENDPOINT,
        *,
        timeout_seconds: float = _TIMEOUT_SECONDS,
    ) -> None:
        self._origin = validate_comfyui_endpoint(endpoint)
        if not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 30:
            raise ValueError("ComfyUI timeout is unavailable")
        self._timeout_seconds = float(timeout_seconds)
        self._opener: OpenerDirector = build_opener(ProxyHandler({}), _RejectRedirects())

    @property
    def origin(self) -> str:
        return self._origin

    def get_json(self, path: str) -> object:
        return self._json_request("GET", path, None)

    def post_json(self, path: str, payload: Mapping[str, object]) -> object:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return self._json_request("POST", path, body)

    def get_png(self, path: str, query: Mapping[str, str]) -> bytes:
        request = Request(
            self._url(path, query),
            method="GET",
            headers={"Accept": "image/png"},
        )
        response = self._open(request)
        try:
            if _status(response) != 200 or _media_type(response) != "image/png":
                raise ValueError("ComfyUI image response is unavailable")
            declared = _content_length(response)
            if declared is not None and not 0 < declared <= _PNG_LIMIT_BYTES:
                raise ValueError("ComfyUI image response is unavailable")
            data = cast(Any, response).read(_PNG_LIMIT_BYTES + 1)
            if not isinstance(data, bytes) or not 0 < len(data) <= _PNG_LIMIT_BYTES:
                raise ValueError("ComfyUI image response is unavailable")
            return data
        finally:
            cast(Any, response).close()

    def _json_request(self, method: str, path: str, body: bytes | None) -> object:
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self._url(path), data=body, method=method, headers=headers)
        response = self._open(request)
        try:
            if _status(response) != 200 or _media_type(response) != "application/json":
                raise ValueError("ComfyUI JSON response is unavailable")
            declared = _content_length(response)
            if declared is not None and not 0 <= declared <= _JSON_LIMIT_BYTES:
                raise ValueError("ComfyUI JSON response is unavailable")
            data = cast(Any, response).read(_JSON_LIMIT_BYTES + 1)
            if not isinstance(data, bytes) or len(data) > _JSON_LIMIT_BYTES:
                raise ValueError("ComfyUI JSON response is unavailable")
            value = json.loads(data.decode("utf-8"))
            if not isinstance(value, (dict, list)):
                raise ValueError("ComfyUI JSON response is unavailable")
            return value
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("ComfyUI JSON response is unavailable") from error
        finally:
            cast(Any, response).close()

    def _open(self, request: Request) -> object:
        try:
            response = self._opener.open(request, timeout=self._timeout_seconds)
        except (HTTPError, URLError, OSError, TimeoutError) as error:
            raise ValueError("ComfyUI request is unavailable") from error
        if _origin(cast(Any, response).geturl()) != self._origin:
            cast(Any, response).close()
            raise ValueError("ComfyUI response origin is unavailable")
        return response

    def _url(self, path: str, query: Mapping[str, str] | None = None) -> str:
        if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
            raise ValueError("ComfyUI request path is unavailable")
        suffix = f"?{urlencode(query)}" if query else ""
        return f"{self._origin}{path}{suffix}"


class ComfyUIImagePrivateTransport:
    """One preflighted, fixed-graph ComfyUI invocation with no retry or fallback."""

    def __init__(
        self,
        checkpoint_name: str,
        output_configuration_binding_report: ProviderOutputConfigurationBindingReport | None,
        *,
        http_client: ComfyUIHttpClientPort | None = None,
        poll_limit: int = _POLL_LIMIT,
        poll_interval_seconds: float = _POLL_INTERVAL_SECONDS,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._checkpoint_name = validate_comfyui_checkpoint_name(checkpoint_name)
        self._output_configuration = _capture_ready_output_configuration(
            output_configuration_binding_report
        )
        self._http = http_client or StandardLibraryComfyUIHttpClient()
        if not isinstance(poll_limit, int) or isinstance(poll_limit, bool) or not 1 <= poll_limit <= 120:
            raise ValueError("ComfyUI polling limit is unavailable")
        if (
            not isinstance(poll_interval_seconds, (int, float))
            or not 0 <= poll_interval_seconds <= 5
        ):
            raise ValueError("ComfyUI polling interval is unavailable")
        self._poll_limit = poll_limit
        self._poll_interval_seconds = float(poll_interval_seconds)
        self._sleeper = sleeper
        self._preflight_ready = False
        self._invocation_lock = threading.Lock()
        self._invocation_consumed = False

    def preflight(self) -> None:
        """Perform bounded read-only server, core-node, and checkpoint checks."""

        self._preflight_ready = False
        system_stats = self._http.get_json("/system_stats")
        if not isinstance(system_stats, dict):
            raise ValueError("ComfyUI preflight failed")
        for node_type in COMFYUI_FIXED_NODE_TYPES:
            payload = self._http.get_json(f"/object_info/{quote(node_type, safe='')}")
            info = payload.get(node_type) if isinstance(payload, dict) else None
            if not isinstance(info, dict) or info.get("python_module") != "nodes":
                raise ValueError("ComfyUI preflight failed")
            if node_type == "CheckpointLoaderSimple" and not _checkpoint_is_available(
                info, self._checkpoint_name
            ):
                raise ValueError("ComfyUI preflight failed")
        self._preflight_ready = True

    def invoke(self, request: ProviderPrivateTransportRequest) -> ProviderPrivateTransportResult:
        """Submit once, poll one prompt id, fetch one PNG, or fail ambiguously."""

        output_configuration = self._output_configuration
        if (
            not self._preflight_ready
            or not _is_valid_request_binding(
                request, output_configuration, self._checkpoint_name
            )
            or request.reference_asset_handles
        ):
            return _runtime_failure()
        seed = int(hashlib.sha256(request.attempt_id.encode()).hexdigest()[:16], 16) % (2**63)
        try:
            graph = build_comfyui_fixed_workflow(
                request.raw_prompt,
                self._checkpoint_name,
                seed=seed,
            )
            validate_comfyui_fixed_workflow(
                graph,
                prompt=request.raw_prompt,
                checkpoint_name=self._checkpoint_name,
                seed=seed,
            )
        except (TypeError, ValueError):
            return _runtime_failure()

        # Consume the one in-memory submission opportunity immediately before POST.
        with self._invocation_lock:
            if self._invocation_consumed:
                return _runtime_failure()
            self._invocation_consumed = True

        # From this point on every failure is ambiguous.  There is deliberately no retry.
        try:
            response = self._http.post_json(
                "/prompt",
                {
                    "prompt": graph,
                    "client_id": f"manga-director-{hashlib.sha256(request.attempt_id.encode()).hexdigest()[:24]}",
                },
            )
            prompt_id = _submitted_prompt_id(response)
            descriptor = self._poll_for_descriptor(prompt_id)
            image_bytes = self._http.get_png("/view", descriptor)
            StrictPngStructuralValidatorV1().validate(image_bytes)
        except Exception:
            return _runtime_failure()
        return ProviderPrivateTransportResult(
            "succeeded",
            ComfyUIInMemoryGeneratedImageMaterial(image_bytes=image_bytes),
        )

    def _poll_for_descriptor(self, prompt_id: str) -> dict[str, str]:
        for index in range(self._poll_limit):
            history = self._http.get_json(f"/history/{quote(prompt_id, safe='')}")
            descriptor = _history_descriptor(history, prompt_id)
            if descriptor is not None:
                return descriptor
            if index + 1 < self._poll_limit and self._poll_interval_seconds:
                self._sleeper(self._poll_interval_seconds)
        raise ValueError("ComfyUI result observation is unavailable")


def validate_comfyui_endpoint(value: object) -> str:
    """Accept only a canonical HTTP 127.0.0.1 origin with an explicit port."""

    if not isinstance(value, str) or value != value.strip():
        raise ValueError("ComfyUI endpoint is unavailable")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("ComfyUI endpoint is unavailable") from error
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or port is None
        or not 1 <= port <= 65535
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.netloc != f"127.0.0.1:{port}"
    ):
        raise ValueError("ComfyUI endpoint is unavailable")
    return f"http://127.0.0.1:{port}"


def _capture_ready_output_configuration(
    report: ProviderOutputConfigurationBindingReport | None,
) -> ProviderOutputConfigurationBindingDTO | None:
    if (
        report is None
        or report.status != "ready"
        or report.ready is not True
        or report.output_configuration is None
    ):
        return None
    output = report.output_configuration
    selection = report.provider_configuration_normalization_report.selection
    if (
        selection is None
        or report.provider_configuration_normalization_report.status != "ready"
        or report.provider_configuration_normalization_report.ready is not True
        or selection.provider_id.availability != "known"
        or selection.provider_id.value != _COMFYUI_PROVIDER_ID
        or selection.model_id.availability != "known"
        or selection.model_id.value != output.model_id
        or output.attempt_id != selection.attempt_id
        or output.provider_reference != selection.provider_reference
        or output.profile_id != selection.profile_id
        or output.profile_version != selection.profile_version
        or output.output_size != "1024x1024"
        or output.output_quality != "medium"
    ):
        return None
    return output


def _is_valid_request_binding(
    request: ProviderPrivateTransportRequest,
    output: ProviderOutputConfigurationBindingDTO | None,
    checkpoint_name: str,
) -> bool:
    selection = request.configuration_selection
    return bool(
        output is not None
        and request.attempt_id == selection.attempt_id == output.attempt_id
        and request.provider_reference == selection.provider_reference == output.provider_reference
        and request.profile_id == selection.profile_id == output.profile_id
        and request.profile_version == selection.profile_version == output.profile_version
        and selection.provider_id.availability == "known"
        and selection.provider_id.value == _COMFYUI_PROVIDER_ID
        and selection.model_id.availability == "known"
        and selection.model_id.value == checkpoint_name == output.model_id
        and isinstance(request.raw_prompt, str)
        and bool(request.raw_prompt.strip())
    )


def _checkpoint_is_available(info: Mapping[str, object], checkpoint_name: str) -> bool:
    inputs = info.get("input")
    required = inputs.get("required") if isinstance(inputs, dict) else None
    checkpoint = required.get("ckpt_name") if isinstance(required, dict) else None
    choices = checkpoint[0] if isinstance(checkpoint, list) and checkpoint else None
    return isinstance(choices, list) and checkpoint_name in choices


def _submitted_prompt_id(response: object) -> str:
    prompt_id = response.get("prompt_id") if isinstance(response, dict) else None
    node_errors = response.get("node_errors") if isinstance(response, dict) else None
    if (
        not isinstance(prompt_id, str)
        or not _PROMPT_ID.fullmatch(prompt_id)
        or node_errors not in (None, {})
    ):
        raise ValueError("ComfyUI submission result is unavailable")
    return prompt_id


def _history_descriptor(history: object, prompt_id: str) -> dict[str, str] | None:
    entry = history.get(prompt_id) if isinstance(history, dict) else None
    if entry is None:
        return None
    if not isinstance(entry, dict):
        raise ValueError("ComfyUI history result is unavailable")
    status = entry.get("status")
    if isinstance(status, dict):
        if status.get("status_str") in {"error", "failed"}:
            raise ValueError("ComfyUI history result is unavailable")
    outputs = entry.get("outputs")
    if outputs is None:
        if isinstance(status, dict) and status.get("completed") is True:
            raise ValueError("ComfyUI history result is unavailable")
        return None
    if not isinstance(outputs, dict) or set(outputs) != {COMFYUI_OUTPUT_NODE_ID}:
        raise ValueError("ComfyUI history result is unavailable")
    output = outputs.get(COMFYUI_OUTPUT_NODE_ID)
    images = output.get("images") if isinstance(output, dict) else None
    if not isinstance(images, list) or len(images) != 1:
        raise ValueError("ComfyUI history result is unavailable")
    return _validated_output_descriptor(images[0])


def _validated_output_descriptor(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"filename", "subfolder", "type"}:
        raise ValueError("ComfyUI output descriptor is unavailable")
    filename = value.get("filename")
    subfolder = value.get("subfolder")
    output_type = value.get("type")
    if (
        not isinstance(filename, str)
        or not _OUTPUT_FILENAME.fullmatch(filename)
        or ".." in filename
        or subfolder != ""
        or output_type != "output"
    ):
        raise ValueError("ComfyUI output descriptor is unavailable")
    return {"filename": filename, "subfolder": "", "type": "output"}


def _origin(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("ComfyUI response origin is unavailable")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("ComfyUI response origin is unavailable") from error
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or port is None:
        raise ValueError("ComfyUI response origin is unavailable")
    return f"http://127.0.0.1:{port}"


def _status(response: object) -> int:
    return int(getattr(response, "status", 0))


def _media_type(response: object) -> str:
    headers = getattr(response, "headers", None)
    value = headers.get("Content-Type", "") if headers is not None else ""
    return str(value).split(";", 1)[0].strip().lower()


def _content_length(response: object) -> int | None:
    headers = getattr(response, "headers", None)
    value = headers.get("Content-Length") if headers is not None else None
    if value is None:
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("ComfyUI response length is unavailable") from error
    return result


def _runtime_failure() -> ProviderPrivateTransportResult:
    return ProviderPrivateTransportResult("runtime_failed")
