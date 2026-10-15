import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


AUTH_DIRECTORY = Path(__file__).resolve().parent / ".auth"
ROLES = ("operator",)


def main():
    parser = argparse.ArgumentParser(
        description="Save a local Odoo login state without entering credentials in the terminal."
    )
    parser.add_argument("--role", choices=ROLES, required=True)
    args = parser.parse_args()

    base_url = os.environ.get("ODOO_BASE_URL", "")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.port != 8091
    ):
        parser.error("ODOO_BASE_URL must point to local odoo18ce on port 8091")

    AUTH_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output_path = AUTH_DIRECTORY / f"{args.role}.json"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{base_url.rstrip('/')}/web/login")
        print(
            "Log in through the opened browser as a normal authorized operator. "
            "The state will be saved after Odoo redirects from the login page."
        )
        try:
            page.wait_for_url(lambda url: "/web/login" not in url, timeout=300_000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Odoo login was not completed within five minutes") from exc
        page.goto(f"{base_url.rstrip('/')}/web", wait_until="domcontentloaded")
        if "/web/login" in page.url:
            raise RuntimeError("Odoo did not establish an authenticated session")
        context.storage_state(path=str(output_path))
        output_path.chmod(0o600)
        browser.close()

    print(f"Saved protected local browser state for role {args.role!r}.")


if __name__ == "__main__":
    main()
