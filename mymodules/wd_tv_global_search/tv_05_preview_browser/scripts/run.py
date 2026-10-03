"""Record the browser verification checklist for TV-05.

The actual browser actions are intentionally performed with the repository's
browser automation, not by bypassing Odoo with direct HTTP/database calls.
"""

from __future__ import annotations

import json
from pathlib import Path


CHECKS = [
    "preview_exists",
    "preview_read_only",
    "edit_save_button_blocked",
    "chatter_blocked",
    "attachment_blocked",
    "activity_blocked",
    "deleted_record_safe",
    "permission_change_safe",
    "record_switch_state",
    "narrow_screen_degradation",
    "keyboard_safety",
    "browser_console",
]


def main() -> None:
    result = {
        "tv_id": "TV-05",
        "status": "NOT_VERIFIED",
        "database": "odoo18ce",
        "url": "http://127.0.0.1:8092/odoo/apps",
        "login_page_reachable": True,
        "login_completed": True,
        "preview_implementation_present": False,
        "checks": {name: "NOT_VERIFIED" for name in CHECKS},
        "evidence": ["evidence/login-page.png", "evidence/logged-in-apps.png"],
        "notes": [
            "The shared-database Odoo login page was reachable.",
            "Authentication completed with the user supplied by the operator.",
            "The applications page contained no Global Search or Preview entry.",
            "mymodules/wd_global_search contains no Preview implementation or route.",
            "Backend Form View evidence from GS-06 is not browser evidence.",
        ],
    }
    output = Path(__file__).parents[1] / "results" / "browser_result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
