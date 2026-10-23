"""Read-only M2 TV probe; execute inside `odoo-bin shell -c odoo.conf -d odoo18ce`.

Uses only synthetic prompts and the already-configured OpenAI provider/model.
Never prints the configured API key or provider base URL.
"""
import json
import os
import pathlib
import sys
import time
import traceback


OUT = pathlib.Path(
    "docs/verification/evidence/TV_Office_Engine_M2/direct_sdk_runs.json"
)


def main():
    # Resolve the configured record, but never access/print api_key directly.
    model_recs = env["llm.model"].search(
        [("name", "=", "gpt-5.6-luna"), ("active", "=", True)]
    )
    candidates = model_recs.filtered(
        lambda rec: rec.provider_id.service == "openai" and rec.model_use == "chat"
    )
    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one active OpenAI chat model named gpt-5.6-luna; "
            f"found {len(candidates)} (candidate_count={len(model_recs)})."
        )
    model_rec = candidates[0]
    client = model_rec.provider_id.client
    model_name = model_rec.name

    fields = [
        {"field_id": "partner_id.name", "label": "Customer name", "type": "string", "sample": "Synthetic Customer"},
        {"field_id": "date_order", "label": "Order date", "type": "string", "sample": "2026-10-01"},
        {"field_id": "amount_total", "label": "Total amount", "type": "number", "sample": 123456.78},
        {"field_id": "state", "label": "Order status", "type": "string", "sample": "draft"},
        {"field_id": "currency_id.name", "label": "Currency", "type": "string", "sample": "EUR"},
    ]
    for i in range(6, 51):
        fields.append({
            "field_id": f"synthetic_field_{i:02d}",
            "label": f"Synthetic field {i:02d}",
            "type": "number" if i % 3 == 0 else "string",
            "sample": i if i % 3 == 0 else f"synthetic-{i:02d}",
        })

    labels = [
        ("Customer name", "partner_id.name", "string"),
        ("Order date", "date_order", "string"),
        ("Total amount", "amount_total", "number"),
        ("Order status", "state", "string"),
        ("Currency", "currency_id.name", "string"),
    ] + [
        (f"Synthetic target {i:02d}", f"synthetic_field_{i:02d}", "number" if i % 3 == 0 else "string")
        for i in range(6, 21)
    ]
    targets = [
        {"element_id": f"xlsx:Sheet1!{chr(64 + i)}1", "label": label}
        for i, (label, _field, _type) in enumerate(labels, 1)
    ]
    expected = {
        f"xlsx:Sheet1!{chr(64 + i)}1": (field, value_type)
        for i, (_label, field, value_type) in enumerate(labels, 1)
    }

    order = json.loads(
        pathlib.Path(
            "docs/verification/evidence/TV_Office_Engine_M2/mock_sale_order_50_lines.json"
        ).read_text(encoding="utf-8")
    )
    user_payload = {
        "field_dictionary": fields,
        "template_targets": targets,
        "synthetic_order": order,
    }
    system_prompt = (
        "Return exactly one JSON object, without Markdown fences or prose, with shape "
        '{"mappings":[{"element_id":"...","source_field":"...",'
        '"value_type":"string|number"}],"clarifications":[]}. '
        "Use only field_id values and element_id values provided in the input. "
        "Map each target to the field with the same business label; do not infer absent fields."
    )
    user_prompt = json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    records = []

    def call(run_id, run_messages, kind):
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=model_name,
            messages=run_messages,
            stream=False,
        )
        elapsed = time.perf_counter() - start
        raw = response.choices[0].message.content or ""
        fenced = "```" in raw
        parsed = None
        parse_error = None
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
        unknown_fields = []
        unknown_targets = []
        missing_targets = []
        wrong_value_types = []
        gold_exact = None
        if isinstance(parsed, dict):
            mappings = parsed.get("mappings")
            if isinstance(mappings, list):
                source_ids = {entry["field_id"] for entry in fields}
                target_ids = {entry["element_id"] for entry in targets}
                observed = {}
                for item in mappings:
                    if not isinstance(item, dict):
                        continue
                    element = item.get("element_id")
                    source = item.get("source_field")
                    if element not in target_ids:
                        unknown_targets.append(element)
                    if source not in source_ids:
                        unknown_fields.append(source)
                    if element in target_ids:
                        observed[element] = (source, item.get("value_type"))
                        if item.get("value_type") not in {"string", "number"}:
                            wrong_value_types.append(element)
                missing_targets = sorted(target_ids - set(observed))
                gold_exact = observed == expected
        usage = getattr(response, "usage", None)
        usage_data = usage.model_dump() if usage is not None else None
        result = {
            "run_id": run_id,
            "kind": kind,
            "request_model": model_name,
            "response_model": response.model,
            "response_id": response.id,
            "elapsed_seconds": round(elapsed, 4),
            "prompt_chars": len(user_prompt),
            "raw_content": raw,
            "contains_markdown_fence": fenced,
            "strict_json_parse": parsed is not None,
            "json_parse_error": parse_error,
            "usage": usage_data,
            "unknown_fields": unknown_fields,
            "unknown_targets": unknown_targets,
            "missing_targets": missing_targets,
            "wrong_value_types": wrong_value_types,
            "exact_gold_match": gold_exact,
        }
        records.append(result)
        print("RUN_RESULT=" + json.dumps(result, ensure_ascii=False), flush=True)
        return result

    # Three small-sample calls for TV-M2-001.
    for i in range(1, 4):
        call(f"TV-M2-001-DIRECT-{i:02d}", messages, "baseline")

    # One explicit malformed-response repair experiment using the same model.
    repair_messages = [
        *messages,
        {"role": "assistant", "content": '{"mappings":[ invalid'},
        {"role": "user", "content": "The previous response was not valid JSON: unexpected token after mappings array. Return the corrected JSON object only; follow the original field and target allowlists."},
    ]
    call("TV-M2-001-DIRECT-REPAIR-01", repair_messages, "simulated_repair")

    # One TV-M2-002 call includes the full 50-line synthetic order payload.
    t2_start = time.perf_counter()
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Produce the JSON mapping for this request. Use the supplied 50-line synthetic order data only.\n" + user_prompt},
        ],
        stream=False,
    )
    t2_elapsed = time.perf_counter() - t2_start
    raw = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    usage_data = usage.model_dump() if usage is not None else None
    try:
        parsed = json.loads(raw)
        parse_error = None
    except Exception as exc:
        parsed = None
        parse_error = f"{type(exc).__name__}: {exc}"
    records.append({
        "run_id": "TV-M2-002-DIRECT-01",
        "kind": "synthetic_50_line_snapshot",
        "request_model": model_name,
        "response_model": response.model,
        "response_id": response.id,
        "elapsed_seconds": round(t2_elapsed, 4),
        "prompt_chars": len(user_prompt) + len("Produce the JSON mapping for this request. Use the supplied 50-line synthetic order data only.\n"),
        "raw_content": raw,
        "contains_markdown_fence": "```" in raw,
        "strict_json_parse": parsed is not None,
        "json_parse_error": parse_error,
        "usage": usage_data,
    })
    print("RUN_RESULT=" + json.dumps(records[-1], ensure_ascii=False), flush=True)

    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SAVED={OUT}", flush=True)
    print(f"ODOO_SHELL_UID={env.uid}; COMPANY_ID={env.company.id}", flush=True)


try:
    main()
except BaseException:
    traceback.print_exc()
finally:
    try:
        env.cr.rollback()
    except Exception:
        pass
    sys.stdout.flush()
    # The local Odoo shutdown hook can fail enumerating unrelated macOS job
    # processes; all DB work here is read-only and rolled back before exit.
    os._exit(0)
