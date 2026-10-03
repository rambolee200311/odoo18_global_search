import json
import re
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation"
RESULTS = ROOT / "results"
corpus = json.loads((RESULTS / "query_corpus.json").read_text())

TIME_WORDS = {
    "今年6月": "2026-06",
    "今年 6月": "2026-06",
    "上个月": "上个月",
    "本周": "本周",
}
STATE_WORDS = {"没完成": "未完成", "未完成": "未完成"}
RESOURCE_WORDS = {"出库单": "出库", "出库": "出库"}
ENTITY_WORDS = ("A客户", "张三")
LOCATION_WORDS = ("Rotterdam",)


def tokenize(text):
    remaining = text
    units = []

    for word, value in sorted(TIME_WORDS.items(), key=lambda item: -len(item[0])):
        if word in remaining:
            units.append(["Time", value])
            remaining = remaining.replace(word, " ")
    identifier_matches = re.findall(r"\b[A-Z]{4}\d{7}\b", remaining)
    for value in identifier_matches:
        units.append(["Identifier", value])
        remaining = remaining.replace(value, " ")
    for word in ENTITY_WORDS:
        if word in remaining:
            units.append(["Entity", word])
            remaining = remaining.replace(word, " ")
    for word in LOCATION_WORDS:
        if word in remaining:
            units.append(["Location", word])
            remaining = remaining.replace(word, " ")
    for word, value in sorted(STATE_WORDS.items(), key=lambda item: -len(item[0])):
        if word in remaining:
            units.append(["State", value])
            remaining = remaining.replace(word, " ")
    for word, value in sorted(RESOURCE_WORDS.items(), key=lambda item: -len(item[0])):
        if word in remaining:
            units.append(["Resource", value])
            remaining = remaining.replace(word, " ")

    if units:
        remaining = remaining.replace("的", " ").replace("了", " ")
    free_text = re.sub(r"\s+", " ", remaining).strip()
    units.sort(key=lambda item: (item[0], item[1]))
    return {"units": units, "free_text": free_text}


def expected_normalized(case):
    return sorted(case["expected"])


results = []
for case in corpus["cases"]:
    first = tokenize(case["text"])
    second = tokenize(case["text"])
    expected = expected_normalized(case)
    correct_units = sorted(first["units"]) == expected
    expected_free_text = case.get("free_text", "")
    safe_free_text = first["free_text"] == expected_free_text
    results.append(
        {
            "id": case["id"],
            "text": case["text"],
            "parsed": first,
            "expected_units": expected,
            "correct_units": correct_units,
            "safe_free_text": safe_free_text,
            "stable_repeat": first == second,
        }
    )

recognized = sum(item["correct_units"] for item in results)
free_text_safe = sum(item["safe_free_text"] for item in results)
stable = all(item["stable_repeat"] for item in results)
output = {
    "spike": "SPIKE-GS-07",
    "case_count": len(results),
    "recognized_case_count": recognized,
    "recognition_rate": recognized / len(results),
    "free_text_safe_case_count": free_text_safe,
    "free_text_safe": free_text_safe == len(results),
    "stable_repeat": stable,
    "examples": results[:4],
    "failed_cases": [item for item in results if not item["correct_units"]],
    "results": results,
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")
