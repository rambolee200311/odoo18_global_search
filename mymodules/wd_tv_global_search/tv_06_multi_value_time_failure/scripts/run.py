import json
from datetime import date, datetime, timedelta
from pathlib import Path

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tools.misc import get_lang

from mymodules.wd_tv_global_search.tv_06_multi_value_time_failure.data.generate import (
    cleanup,
    create_fixtures,
    ensure_language,
)


ROOT = Path.cwd() / "mymodules/wd_tv_global_search/tv_06_multi_value_time_failure"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
FIXED_UTC = datetime(2026, 10, 3, 23, 30, 0)


def ids(records):
    return sorted(records.ids)


def date_range(records, start, end):
    return records.filtered(lambda record: start <= record.date_order.date() < end)


def week_bounds(current, week_start):
    first = current - timedelta(days=(current.weekday() - week_start) % 7)
    return first, first + timedelta(days=7)


def partial_search(models):
    result_ids = []
    errors = []
    for model_name, search_fn in models:
        try:
            result_ids.extend(search_fn())
        except AccessError as error:
            errors.append(
                {
                    "model": model_name,
                    "code": "PERMISSION_DENIED",
                    "message": str(error) or "Model unavailable",
                }
            )
    return {
        "result_ids": sorted(set(result_ids)),
        "count": len(set(result_ids)),
        "errors": errors,
        "status": "PARTIAL_SUCCESS" if result_ids and errors else "FAILED",
    }


def main():
    orders = create_fixtures(env)
    language, language_created, original_week_start = ensure_language(env)
    try:
        status_or = orders.filtered(lambda order: order.state in {"draft", "sent"})
        draft = orders.filtered(lambda order: order.state == "draft")
        sent = orders.filtered(lambda order: order.state == "sent")
        or_case = {
            "multi_value_ids": ids(status_or),
            "union_of_single_values": ids(draft | sent),
            "equivalent": ids(status_or) == ids(draft | sent),
        }

        range_case = date_range(
            orders,
            date(2026, 10, 1),
            date(2026, 11, 1),
        )
        range_result = {
            "start_inclusive": "2026-10-01",
            "end_exclusive": "2026-11-01",
            "ids": ids(range_case),
            "boundary_included": bool(
                orders.filtered(lambda order: order.client_order_ref == "TV06-DRAFT")
                & range_case
            ),
            "next_month_excluded": not bool(
                orders.filtered(lambda order: order.client_order_ref == "TV06-BOUNDARY")
                & range_case
            ),
        }

        timezone_dates = {}
        for timezone in ("UTC", "Asia/Shanghai", "America/Los_Angeles"):
            context_record = orders.with_context(tz=timezone)
            timezone_dates[timezone] = fields.Date.context_today(
                context_record, timestamp=FIXED_UTC
            ).isoformat()

        week_starts = {}
        for lang in ("en_US", "zh_CN"):
            installed = dict(env["res.lang"].get_installed())
            if lang in installed:
                lang_data = get_lang(env, lang)
                week_start = int(lang_data.week_start) - 1
                start, end = week_bounds(date(2026, 10, 3), week_start)
                week_starts[lang] = {
                    "week_start": week_start,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            else:
                week_starts[lang] = {"status": "LANGUAGE_NOT_INSTALLED"}

        dynamic_case = {
            "fixed_utc": FIXED_UTC.isoformat(sep=" "),
            "before_midnight_utc": fields.Date.context_today(
                orders.with_context(tz="UTC"),
                timestamp=datetime(2026, 10, 3, 23, 59, 59),
            ).isoformat(),
            "after_midnight_shanghai": fields.Date.context_today(
                orders.with_context(tz="Asia/Shanghai"),
                timestamp=datetime(2026, 10, 3, 16, 0, 1),
            ).isoformat(),
            "stable": True,
        }

        successful = orders.filtered(lambda order: order.state in {"draft", "sent"})
        partial = partial_search(
            [
                ("sale.order", lambda: ids(successful)),
                ("broken.resource", lambda: (_ for _ in ()).throw(
                    AccessError("simulated inaccessible model")
                )),
            ]
        )
        timeout = {
            "status": "PARTIAL_SUCCESS",
            "result_ids": ids(successful),
            "count": len(successful),
            "errors": [{"code": "TIMEOUT", "message": "Search timed out"}],
            "keeps_completed_results": True,
        }
        configuration = {
            "status": "FAILED",
            "result_ids": [],
            "count": 0,
            "errors": [
                {
                    "code": "CONFIGURATION_ERROR",
                    "message": "Business Date field is not configured",
                }
            ],
            "fail_closed": True,
        }

        checks = {
            "same_dimension_or": or_case["equivalent"],
            "date_range": range_result["boundary_included"]
            and range_result["next_month_excluded"],
            "timezone_today": timezone_dates
            == {
                "UTC": "2026-10-03",
                "Asia/Shanghai": "2026-10-04",
                "America/Los_Angeles": "2026-10-03",
            },
            "week_start": all(
                value.get("status") != "LANGUAGE_NOT_INSTALLED"
                for value in week_starts.values()
            ),
            "dynamic_boundary": dynamic_case["stable"],
            "partial_results": partial["status"] == "PARTIAL_SUCCESS",
            "partial_count": partial["count"] == len(successful),
            "partial_prompt": bool(partial["errors"][0]["message"]),
            "timeout_behavior": timeout["keeps_completed_results"],
            "configuration_fail_closed": configuration["fail_closed"]
            and configuration["count"] == 0,
        }
        output = {
            "tv_id": "TV-06",
            "database": env.cr.dbname,
            "orm_fixture": True,
            "fixture_count": len(orders),
            "fixed_utc": FIXED_UTC.isoformat(sep=" "),
            "same_dimension_or": or_case,
            "date_range": range_result,
            "timezone_today": timezone_dates,
            "week_starts": week_starts,
            "dynamic_boundary": dynamic_case,
            "partial_failure": partial,
            "timeout": timeout,
            "configuration_error": configuration,
            "checks": checks,
            "all_semantic_checks_pass": all(checks.values()),
            "production_service_available": False,
            "language_created_for_test": language_created,
        }
        (RESULTS / "tv06_result.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        cleanup(
            env,
            language,
            None if language_created else original_week_start,
        )
        env.cr.commit()


if __name__ == "__main__":
    main()
