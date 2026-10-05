import base64
import hashlib
import hmac
import json
import time


def _canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def encode(data, secret):
    payload = dict(data)
    payload.setdefault("expires_at", int(time.time()) + 3600)
    raw = base64.urlsafe_b64encode(_canonical(payload)).decode().rstrip("=")
    signature = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (raw, signature)


def decode(cursor, secret, expected):
    try:
        raw, signature = cursor.split(".", 1)
        expected_signature = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("invalid signature")
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if payload.get("expires_at", 0) < int(time.time()):
            raise TimeoutError("expired cursor")
        for key, value in expected.items():
            if payload.get(key) != value:
                raise ValueError("cursor binding mismatch")
        return payload
    except TimeoutError:
        raise
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("invalid cursor") from exc
