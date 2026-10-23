#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -x "venv/bin/python" ]]; then
    echo "ERROR: project venv/bin/python not found" >&2
    exit 1
fi

# Read provider 2 through Odoo ORM and use its configured OpenAI-compatible client.
# Never print the stored API key or raw exception text.
exec ./venv/bin/python ./odoo-bin shell -c odoo.conf <<'PY'
from openai import APIStatusError, AuthenticationError

provider = env["llm.provider"].browse(2)
if not provider.exists():
    print("FETCH_FAILED: llm.provider id=2 does not exist")
    raise SystemExit(2)

print(f"Provider: id={provider.id}, name={provider.name}, service={provider.service}")
print(f"API Base: {provider.api_base or '(SDK default)'}")

try:
    models = list(provider.list_models())
except AuthenticationError:
    print("FETCH_FAILED: DeepSeek rejected authentication (HTTP 401); API key value hidden")
    raise SystemExit(3)
except APIStatusError as error:
    print(f"FETCH_FAILED: provider returned HTTP {error.status_code}; response body hidden")
    raise SystemExit(4)
except Exception as error:
    print(f"FETCH_FAILED: {type(error).__name__}; exception text hidden to protect credentials")
    raise SystemExit(5)

model_names = [item.get("name") for item in models if item.get("name")]
print(f"FETCH_OK: {len(model_names)} models returned")
for model_name in model_names:
    print(model_name)
PY
