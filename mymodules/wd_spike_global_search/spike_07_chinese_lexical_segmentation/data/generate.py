import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

cases = []
for index in range(20):
    cases.append(
        {
            "id": f"continuous-{index + 1:03d}",
            "text": "A客户今年6月没完成的出库单",
            "expected": [
                ["Entity", "A客户"],
                ["Time", "2026-06"],
                ["State", "未完成"],
                ["Resource", "出库"],
            ],
        }
    )
for index in range(20):
    cases.append(
        {
            "id": f"identifier-location-{index + 1:03d}",
            "text": "MSCU1234567 Rotterdam",
            "expected": [
                ["Identifier", "MSCU1234567"],
                ["Location", "Rotterdam"],
            ],
        }
    )
for index in range(20):
    cases.append(
        {
            "id": f"month-resource-{index + 1:03d}",
            "text": "上个月 出库",
            "expected": [
                ["Time", "上个月"],
                ["Resource", "出库"],
            ],
        }
    )
for index in range(20):
    cases.append(
        {
            "id": f"entity-week-{index + 1:03d}",
            "text": "张三 本周",
            "expected": [
                ["Entity", "张三"],
                ["Time", "本周"],
            ],
        }
    )
for index in range(10):
    text = "A客户今年 6月没完成的出库单" if index % 2 else "A客户 今年6月 没完成 的 出库单"
    cases.append(
        {
            "id": f"space-variant-{index + 1:03d}",
            "text": text,
            "expected": [
                ["Entity", "A客户"],
                ["Time", "2026-06"],
                ["State", "未完成"],
                ["Resource", "出库"],
            ],
        }
    )
for index in range(10):
    cases.append(
        {
            "id": f"free-text-{index + 1:03d}",
            "text": f"不存在的自由文本{index + 1:02d}",
            "expected": [],
            "free_text": f"不存在的自由文本{index + 1:02d}",
        }
    )

output = {"spike": "SPIKE-GS-07", "cases": cases, "case_count": len(cases)}
(RESULTS / "query_corpus.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "query_corpus.json")

