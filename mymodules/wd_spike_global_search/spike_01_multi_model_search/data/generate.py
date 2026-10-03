import json
import random
from pathlib import Path

SEED = 20261001
OUTPUT = Path(__file__).resolve().parents[1] / "results" / "query_corpus.json"


def build_corpus():
    random.seed(SEED)
    return {
        "seed": SEED,
        "queries": [
            {
                "name": "identifier_exact",
                "model": "res.partner",
                "field": "ref",
                "operator": "=",
                "value": "GS01-CUST-000001",
            },
            {
                "name": "identifier_prefix",
                "model": "res.partner",
                "field": "ref",
                "operator": "=ilike",
                "value": "GS01-CUST-000001%",
            },
            {
                "name": "identifier_contains",
                "model": "res.partner",
                "field": "ref",
                "operator": "ilike",
                "value": "%GS01-CUST%",
            },
            {
                "name": "entity_exact",
                "model": "res.partner",
                "field": "name",
                "operator": "=",
                "value": "GS01 Customer 000001",
            },
            {
                "name": "entity_contains",
                "model": "res.partner",
                "field": "name",
                "operator": "ilike",
                "value": "%GS01 Customer%",
            },
            {
                "name": "product_identifier_contains",
                "model": "product.product",
                "field": "default_code",
                "operator": "ilike",
                "value": "%GS01%",
            },
            {
                "name": "sale_identifier_contains",
                "model": "sale.order",
                "field": "client_order_ref",
                "operator": "ilike",
                "value": "%GS01-SALE%",
            },
            {
                "name": "purchase_identifier_contains",
                "model": "purchase.order",
                "field": "partner_ref",
                "operator": "ilike",
                "value": "%GS01-PURCHASE%",
            },
        ],
    }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build_corpus(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
