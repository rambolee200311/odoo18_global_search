"""Offline SDK-mock contract tests for the isolated Responses adapter.

These tests intentionally load the pure service module without importing or
booting the Odoo addon. They never construct an authenticated OpenAI client or
make network requests.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError
from openpyxl import Workbook, load_workbook


_ADAPTER_PATH = Path(__file__).parents[1] / "services" / "responses_adapter.py"
_SPEC = importlib.util.spec_from_file_location("cb01_responses_adapter_under_test", _ADAPTER_PATH)
assert _SPEC and _SPEC.loader
adapter_module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = adapter_module
_SPEC.loader.exec_module(adapter_module)

AdapterLimits = adapter_module.AdapterLimits
ResponsesAdapter = adapter_module.ResponsesAdapter


def make_limits(**overrides):
    values = {
        "allowed_models": frozenset({"model-approved-by-caller"}),
        "max_input_bytes": 2_000_000,
        "max_output_bytes": 2_000_000,
        "max_output_tokens": 1200,
        "timeout_seconds": 15,
        "memory_limit": "1g",
        "max_archive_entries": 200,
        "max_uncompressed_bytes": 5_000_000,
    }
    values.update(overrides)
    return AdapterLimits(**values)


def make_xlsx(quantity: int, sheet_name: str = "Inventory") -> bytes:
    workbook = Workbook()
    inventory = workbook.active
    inventory.title = sheet_name
    inventory.append(["Product", "Quantity", "Unit Price", "Amount"])
    inventory.append(["ITEM-A", quantity, 5, "=B2*C2"])
    inventory.append(["ITEM-B", 20, 8, "=B3*C3"])
    inventory["B2"].number_format = "0"
    notes = workbook.create_sheet("Notes")
    notes.append(["Key", "Value"])
    notes.append(["Source", "Synthetic Fixture"])
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


class FakeStream:
    def __init__(self, data: bytes | None = None, error: Exception | None = None):
        self.data = data or b""
        self.error = error
        self.request_id = "req_download_synthetic"

    def __enter__(self):
        if self.error:
            raise self.error
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def iter_bytes(self, chunk_size=None):
        assert chunk_size is not None
        for offset in range(0, len(self.data), chunk_size):
            yield self.data[offset : offset + chunk_size]


def make_response(candidate: bytes | None, *, status="completed", citations=1, usage=None):
    container_id = "cntr_synthetic"
    output = [SimpleNamespace(type="code_interpreter_call", id="ci_synthetic", container_id=container_id)]
    annotations = []
    if candidate is not None:
        for index in range(citations):
            annotations.append(
                SimpleNamespace(
                    type="container_file_citation",
                    filename=f"output-{index}.xlsx",
                    file_id=f"file-synthetic-{index}",
                    container_id=container_id,
                )
            )
    output.append(SimpleNamespace(type="message", content=[SimpleNamespace(annotations=annotations)]))
    return SimpleNamespace(
        id="resp_synthetic",
        _request_id="req_synthetic",
        status=status,
        usage=usage or SimpleNamespace(
            input_tokens=17,
            output_tokens=9,
            total_tokens=26,
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
        output=output,
    )


def make_clients(response=None, candidate=None, *, download_error=None, cleanup_error=None):
    configured_client = Mock(name="configured_provider_client")
    request_client = Mock(name="retry_disabled_client")
    configured_client.with_options.return_value = request_client
    if response is None:
        response = make_response(candidate)
    request_client.responses.create.return_value = response
    request_client.containers.files.content.with_streaming_response.retrieve.return_value = FakeStream(
        candidate, error=download_error
    )
    if cleanup_error:
        request_client.containers.delete.side_effect = cleanup_error
    return configured_client, request_client


def call_adapter(client, source, **kwargs):
    return ResponsesAdapter().execute(
        provider_client=client,
        model="model-approved-by-caller",
        input_xlsx=source,
        instruction="Modify only the authorized synthetic target.",
        limits=make_limits(),
        **kwargs,
    )


def test_candidate_download_request_shape_hashes_and_independent_readback():
    source = make_xlsx(10)
    candidate = make_xlsx(15)
    client, request_client = make_clients(candidate=candidate)

    result = call_adapter(
        client,
        source,
        input_sha256=hashlib.sha256(source).hexdigest(),
        correlation_id="correlation-synthetic-1",
    )

    assert result.operation_status == "candidate_received"
    assert result.candidate_bytes == candidate
    assert result.input_sha256 == hashlib.sha256(source).hexdigest()
    assert result.candidate_sha256 == hashlib.sha256(candidate).hexdigest()
    assert result.provider_response_id == "resp_synthetic"
    assert result.request_id == "req_synthetic"
    assert result.download_request_id == "req_download_synthetic"
    assert result.tool_call_ids == ("ci_synthetic",)
    assert result.provider_file_ids == ("file-synthetic-0",)
    assert result.cleanup_state == "completed"
    assert result.usage == {
        "input_tokens": 17,
        "output_tokens": 9,
        "total_tokens": 26,
        "reasoning_tokens": 0,
    }
    client.with_options.assert_called_once_with(timeout=15, max_retries=0)
    call = request_client.responses.create.call_args.kwargs
    assert call["model"] == "model-approved-by-caller"
    assert call["store"] is False
    assert call["max_output_tokens"] == 1200
    assert call["tool_choice"] == "required"
    assert call["tools"][0]["type"] == "code_interpreter"
    assert call["tools"][0]["container"]["network_policy"] == {"type": "disabled"}
    file_input = call["input"][0]["content"][0]
    assert file_input["type"] == "input_file"
    assert base64.b64decode(file_input["file_data"].split(",", 1)[1]) == source
    request_client.containers.files.content.with_streaming_response.retrieve.assert_called_once_with(
        "file-synthetic-0", container_id="cntr_synthetic", timeout=15
    )
    request_client.containers.delete.assert_called_once_with("cntr_synthetic", timeout=15)

    metadata = result.to_dict()
    json.dumps(metadata)
    assert "candidate_bytes" not in metadata
    book = load_workbook(BytesIO(result.candidate_bytes), data_only=False)
    assert book.sheetnames == ["Inventory", "Notes"]
    assert book["Inventory"]["B2"].value == 15
    assert book["Inventory"]["B3"].value == 20
    assert book["Inventory"]["D2"].value == "=B2*C2"
    assert book["Inventory"]["D3"].value == "=B3*C3"
    assert book["Notes"]["B2"].value == "Synthetic Fixture"
    book.close()
    with zipfile.ZipFile(BytesIO(result.candidate_bytes)) as archive:
        assert archive.testzip() is None


def test_adapter_is_independent_of_worksheet_name_and_cell_layout():
    source = make_xlsx(10, sheet_name="Unrelated Tab Name")
    candidate = make_xlsx(11, sheet_name="Unrelated Tab Name")
    client, _request_client = make_clients(candidate=candidate)
    result = call_adapter(client, source)
    assert result.operation_status == "candidate_received"
    book = load_workbook(BytesIO(result.candidate_bytes), data_only=False)
    assert book.sheetnames == ["Unrelated Tab Name", "Notes"]
    assert book["Unrelated Tab Name"]["B2"].value == 11
    book.close()


@pytest.mark.parametrize(
    ("model", "source", "instruction", "limits", "claimed_digest", "expected"),
    [
        ("unapproved", make_xlsx(1), "edit", make_limits(), None, "model_not_approved"),
        ("model-approved-by-caller", b"", "edit", make_limits(), None, "input_xlsx_invalid"),
        ("model-approved-by-caller", make_xlsx(1), " ", make_limits(), None, "instruction_invalid"),
        (
            "model-approved-by-caller",
            make_xlsx(1),
            "edit",
            make_limits(max_input_bytes=1),
            None,
            "input_size_limit_exceeded",
        ),
        (
            "model-approved-by-caller",
            make_xlsx(1),
            "edit",
            make_limits(remote_cleanup_required=True),
            None,
            "remote_cleanup_guarantee_unsupported",
        ),
        ("model-approved-by-caller", make_xlsx(1), "edit", make_limits(), "0" * 64, "input_sha256_mismatch"),
    ],
    ids=["model-policy", "empty-input", "empty-instruction", "input-limit", "cleanup-guarantee", "hash-mismatch"],
)
def test_preflight_blocks_without_provider_call(model, source, instruction, limits, claimed_digest, expected):
    client, request_client = make_clients(candidate=make_xlsx(2))
    result = ResponsesAdapter().execute(
        provider_client=client,
        model=model,
        input_xlsx=source,
        instruction=instruction,
        limits=limits,
        input_sha256=claimed_digest,
    )
    assert result.operation_status == "blocked"
    assert result.error.category == expected
    client.with_options.assert_not_called()
    request_client.responses.create.assert_not_called()


def test_invalid_input_zip_is_blocked_without_network():
    client, request_client = make_clients(candidate=make_xlsx(2))
    result = call_adapter(client, b"not an xlsx")
    assert result.operation_status == "blocked"
    assert result.error.category == "xlsx_container_invalid"
    request_client.responses.create.assert_not_called()


def test_sdk_retry_option_setup_error_fails_without_request():
    source = make_xlsx(10)
    client, request_client = make_clients(candidate=make_xlsx(15))
    client.with_options.side_effect = RuntimeError("private client detail")
    result = call_adapter(client, source)
    assert result.operation_status == "failed"
    assert result.error.category == "adapter_request_or_download_error"
    assert result.candidate_bytes is None
    request_client.responses.create.assert_not_called()
    assert "private" not in json.dumps(result.to_dict())


def test_provider_connection_error_is_indeterminate_and_not_retried():
    source = make_xlsx(10)
    client, request_client = make_clients(candidate=make_xlsx(15))
    request_client.responses.create.side_effect = APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    result = call_adapter(client, source)
    assert result.operation_status == "indeterminate"
    assert result.error.category == "provider_connection_or_timeout"
    assert result.error.retry_decision == "not_automatic"
    assert request_client.responses.create.call_count == 1
    request_client.containers.delete.assert_not_called()
    assert result.cleanup_state == "unknown"


def test_provider_timeout_is_indeterminate():
    source = make_xlsx(10)
    client, request_client = make_clients(candidate=make_xlsx(15))
    request_client.responses.create.side_effect = APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    result = call_adapter(client, source)
    assert result.operation_status == "indeterminate"
    assert result.error.category == "provider_connection_or_timeout"
    assert request_client.responses.create.call_count == 1


def test_provider_http_error_is_failed_without_raw_error_body():
    source = make_xlsx(10)
    client, request_client = make_clients(candidate=make_xlsx(15))
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    request_client.responses.create.side_effect = APIStatusError(
        "private response body", response=response, body="private"
    )
    result = call_adapter(client, source)
    assert result.operation_status == "failed"
    assert result.error.category == "provider_http_error"
    assert result.error.http_status == 429
    assert "private" not in json.dumps(result.to_dict())
    assert request_client.responses.create.call_count == 1


@pytest.mark.parametrize(
    ("response", "stream", "expected"),
    [
        (make_response(None), FakeStream(), "xlsx_output_missing_or_ambiguous"),
        (make_response(make_xlsx(15), citations=2), FakeStream(make_xlsx(15)), "xlsx_output_missing_or_ambiguous"),
        (make_response(make_xlsx(15), status="incomplete"), FakeStream(make_xlsx(15)), "provider_response_incomplete"),
        (make_response(make_xlsx(15)), FakeStream(b"corrupted"), "xlsx_container_invalid"),
    ],
    ids=["no-file", "ambiguous-files", "incomplete", "corrupt-xlsx"],
)
def test_non_candidate_responses_fail_and_do_not_claim_success(response, stream, expected):
    client, request_client = make_clients(response=response, candidate=make_xlsx(15))
    request_client.containers.files.content.with_streaming_response.retrieve.return_value = stream
    result = call_adapter(client, make_xlsx(10))
    assert result.operation_status == "failed"
    assert result.error.category == expected
    assert result.candidate_bytes is None
    if result.container_id:
        request_client.containers.delete.assert_called_once()


def test_output_byte_limit_stops_stream_and_fails_closed():
    source = make_xlsx(10)
    candidate = make_xlsx(15)
    client, request_client = make_clients(candidate=candidate)
    limits = make_limits(max_output_bytes=100)
    result = ResponsesAdapter().execute(
        provider_client=client,
        model="model-approved-by-caller",
        input_xlsx=source,
        instruction="edit synthetic workbook",
        limits=limits,
    )
    assert result.operation_status == "failed"
    assert result.error.category == "output_size_limit_exceeded"
    assert result.candidate_bytes is None
    assert result.cleanup_state == "completed"


def test_download_failure_and_cleanup_failure_are_reported_without_candidate():
    source = make_xlsx(10)
    client, request_client = make_clients(
        candidate=make_xlsx(15),
        download_error=RuntimeError("private remote detail"),
        cleanup_error=RuntimeError("private cleanup detail"),
    )
    result = call_adapter(client, source)
    assert result.operation_status == "failed"
    assert result.error.category == "adapter_request_or_download_error"
    assert result.cleanup_state == "cleanup_pending"
    assert result.candidate_bytes is None
    assert "private" not in json.dumps(result.to_dict())


def test_download_connection_failure_is_failed_with_file_and_container_ids():
    source = make_xlsx(10)
    client, request_client = make_clients(
        candidate=make_xlsx(15),
        download_error=APIConnectionError(
            request=httpx.Request("GET", "https://api.openai.com/v1/containers/cntr/files/file/content")
        ),
    )
    result = call_adapter(client, source)
    assert result.operation_status == "failed"
    assert result.error.category == "provider_file_download_error"
    assert result.provider_response_id == "resp_synthetic"
    assert result.container_id == "cntr_synthetic"
    assert result.provider_file_ids == ("file-synthetic-0",)
    assert result.cleanup_state == "completed"
    request_client.responses.create.assert_called_once()


def test_download_http_failure_preserves_remote_reference_for_diagnosis():
    source = make_xlsx(10)
    client, request_client = make_clients(candidate=make_xlsx(15))
    response = httpx.Response(404, request=httpx.Request("GET", "https://api.openai.com/v1/containers/files"))
    request_client.containers.files.content.with_streaming_response.retrieve.side_effect = APIStatusError(
        "remote detail", response=response, body="private"
    )
    result = call_adapter(client, source)
    assert result.operation_status == "failed"
    assert result.error.category == "provider_file_download_http_error"
    assert result.error.http_status == 404
    assert result.provider_file_ids == ("file-synthetic-0",)
    assert result.container_id == "cntr_synthetic"
    assert result.cleanup_state == "completed"
    assert "private" not in json.dumps(result.to_dict())


def test_cleanup_failure_does_not_hide_a_downloaded_candidate():
    source = make_xlsx(10)
    candidate = make_xlsx(15)
    client, _request_client = make_clients(candidate=candidate, cleanup_error=RuntimeError("cleanup detail"))
    result = call_adapter(client, source)
    assert result.operation_status == "candidate_received"
    assert result.candidate_bytes == candidate
    assert result.cleanup_state == "cleanup_pending"


def test_unknown_or_invalid_usage_stays_unknown_and_zero_is_not_dropped():
    source = make_xlsx(10)
    candidate = make_xlsx(15)
    usage = SimpleNamespace(
        input_tokens=0,
        output_tokens=False,
        total_tokens=None,
        output_tokens_details=SimpleNamespace(reasoning_tokens=-1),
    )
    client, request_client = make_clients(response=make_response(candidate, usage=usage), candidate=candidate)
    result = call_adapter(client, source)
    assert result.operation_status == "candidate_received"
    assert result.usage == {
        "input_tokens": 0,
        "output_tokens": None,
        "total_tokens": None,
        "reasoning_tokens": None,
    }
    request_client.responses.create.assert_called_once()


def test_conflicting_container_identity_is_rejected_without_guessing():
    source = make_xlsx(10)
    candidate = make_xlsx(15)
    response = make_response(candidate)
    response.output[0].container_id = "cntr_tool"
    response.output[1].content[0].annotations[0].container_id = "cntr_citation"
    client, request_client = make_clients(response=response, candidate=candidate)
    result = call_adapter(client, source)
    assert result.operation_status == "failed"
    assert result.error.category == "output_container_missing"
    assert result.candidate_bytes is None
    assert result.cleanup_state == "unknown"
    request_client.containers.files.content.with_streaming_response.retrieve.assert_not_called()


def test_adapter_has_no_odoo_business_dependency_or_logging_of_content():
    source = _ADAPTER_PATH.read_text()
    assert "from odoo" not in source
    assert "import odoo" not in source
    assert "_logger" not in source
    assert "exec(" not in source
    assert "eval(" not in source


def _load_chat_provider_module():
    """Load unchanged Chat Provider methods with narrow Odoo import stubs.

    This exercises actual source methods without creating an Odoo registry,
    touching the database, or using credentials/network access.
    """
    addon = Path(__file__).parents[1]
    package_name = "_cb01_openai_provider_compat"
    for name, path in (
        (package_name, addon),
        (f"{package_name}.models", addon / "models"),
        (f"{package_name}.utils", addon / "utils"),
    ):
        package = ModuleType(name)
        package.__path__ = [str(path)]
        package.__package__ = name
        sys.modules[name] = package

    validator_module = ModuleType(f"{package_name}.utils.openai_message_validator")
    validator_module.OpenAIMessageValidator = type("OpenAIMessageValidator", (), {})
    sys.modules[validator_module.__name__] = validator_module

    fake_odoo = ModuleType("odoo")
    fake_odoo.api = SimpleNamespace(model=lambda method: method)
    fake_odoo.models = SimpleNamespace(Model=type("Model", (), {}))
    fake_exceptions = ModuleType("odoo.exceptions")
    fake_exceptions.UserError = type("UserError", (Exception,), {})
    previous_odoo = sys.modules.get("odoo")
    previous_exceptions = sys.modules.get("odoo.exceptions")
    sys.modules["odoo"] = fake_odoo
    sys.modules["odoo.exceptions"] = fake_exceptions
    try:
        module_name = f"{package_name}.models.openai_provider"
        spec = importlib.util.spec_from_file_location(
            module_name,
            addon / "models" / "openai_provider.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_odoo is None:
            sys.modules.pop("odoo", None)
        else:
            sys.modules["odoo"] = previous_odoo
        if previous_exceptions is None:
            sys.modules.pop("odoo.exceptions", None)
        else:
            sys.modules["odoo.exceptions"] = previous_exceptions


class _ChatProviderHarness:
    """Supply only inherited ORM conveniences used by openai_chat()."""

    def __init__(self, provider_class):
        self.provider = object.__new__(provider_class)
        self.provider.get_model = Mock(return_value=SimpleNamespace(name="chat-model"))
        self.provider.format_messages = Mock(return_value=[{"role": "user", "content": "hello"}])
        self.provider.client = Mock()


def test_unchanged_chat_completions_content_and_tool_calls_contract():
    module = _load_chat_provider_module()
    harness = _ChatProviderHarness(module.LLMProvider)
    response = SimpleNamespace(
        id="chatcmpl_synthetic",
        usage=SimpleNamespace(
            prompt_tokens=3,
            completion_tokens=4,
            total_tokens=7,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
        choices=[SimpleNamespace(
            message=SimpleNamespace(
                content="response text",
                tool_calls=[SimpleNamespace(
                    id="call_synthetic",
                    type="function",
                    function=SimpleNamespace(name="lookup", arguments='{"id":1}'),
                )],
            ),
        )],
    )
    harness.provider.client.chat.completions.create.return_value = response

    result = harness.provider.openai_chat(["synthetic message"], model="chat-model")

    assert result["content"] == "response text"
    assert result["tool_calls"] == [{
        "id": "call_synthetic",
        "type": "function",
        "function": {"name": "lookup", "arguments": '{"id":1}'},
    }]
    assert result["usage"]["prompt_tokens"] == 3
    harness.provider.client.chat.completions.create.assert_called_once_with(
        model="chat-model",
        stream=False,
        messages=[{"role": "user", "content": "hello"}],
    )


def test_unchanged_chat_completions_streaming_content_and_tool_calls_contract():
    module = _load_chat_provider_module()
    harness = _ChatProviderHarness(module.LLMProvider)
    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content="streamed", tool_calls=None),
            finish_reason=None,
        )]),
        SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content=None, tool_calls=[SimpleNamespace(
                index=0,
                id="call_stream_synthetic",
                type="function",
                function=SimpleNamespace(name="lookup", arguments='{"id":2}'),
            )]),
            finish_reason=None,
        )]),
        SimpleNamespace(choices=[SimpleNamespace(delta=None, finish_reason="tool_calls")]),
    ]
    harness.provider._is_tool_call_complete = lambda function, expected_endings: function[
        "arguments"
    ].endswith(expected_endings)
    harness.provider.client.chat.completions.create.return_value = iter(chunks)

    result = list(harness.provider.openai_chat(["synthetic message"], model="chat-model", stream=True))

    assert result == [
        {"content": "streamed"},
        {"tool_calls": [{
            "id": "call_stream_synthetic",
            "type": "function",
            "function": {"name": "lookup", "arguments": '{"id":2}'},
        }]},
    ]
    harness.provider.client.chat.completions.create.assert_called_once_with(
        model="chat-model",
        stream=True,
        messages=[{"role": "user", "content": "hello"}],
    )


def test_existing_provider_client_factory_keeps_openai_config_contract(monkeypatch):
    module = _load_chat_provider_module()
    harness = _ChatProviderHarness(module.LLMProvider)
    harness.provider.api_key = "synthetic-test-secret"
    harness.provider.api_base = "https://api.openai.com/v1"
    sentinel_client = object()
    constructor = Mock(return_value=sentinel_client)
    monkeypatch.setattr(module, "OpenAI", constructor)

    result = harness.provider.openai_get_client()

    assert result is sentinel_client
    constructor.assert_called_once_with(
        api_key="synthetic-test-secret",
        base_url="https://api.openai.com/v1",
    )
