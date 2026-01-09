#!/usr/bin/env python3
"""
ipm_read_v2.py

Read-only helper for Home Assistant.
Reads inventory from:
  /config/PaddiSense/data/ipm_inventory.json

Outputs JSON suitable for command_line sensor:
{
  "total_products": <int>,
  "products": {
    "<ID>": {
      "id": "...",
      "name": "...",
      "category": "...",
      "subcategory": "...",
      "unit": "...",
      "container_size": <float>,
      "min_stock": <float>,
      "chemical_group": "...",
      "application_unit": "...",
      "stock_by_location": { "<location>": <float> },
      "actives": [ ... ],
      "total_stock": <float>
    }
  },
  "product_keys": [ "ID|Location", ... ],
  "locations": [ "Chem Shed", "Silo 1", ... ]
}
"""

import json
from pathlib import Path
import sys

DATA_PATH = Path("/config/PaddiSense/data/ipm_inventory.json")


def main():
    if not DATA_PATH.exists():
        print(json.dumps({
            "total_products": 0,
            "products": {},
            "product_keys": [],
            "locations": []
        }))
        return

    try:
        data = json.loads(DATA_PATH.read_text())
    except Exception:
        print(json.dumps({
            "total_products": 0,
            "products": {},
            "product_keys": [],
            "locations": []
        }))
        return

    products = data.get("products", {})
    product_keys = []
    locations = set()

    for pid, p in products.items():
        stock_by_loc = p.get("stock_by_location", {}) or {}
        total = 0.0

        for loc, qty in stock_by_loc.items():
            try:
                qty_f = float(qty)
            except Exception:
                qty_f = 0.0
            total += qty_f
            locations.add(loc)
            product_keys.append(f"{pid}|{loc}")

        p["total_stock"] = round(total, 3)

    out = {
        "total_products": len(products),
        "products": products,
        "product_keys": sorted(product_keys),
        "locations": sorted(locations),
    }

    print(json.dumps(out))


if __name__ == "__main__":
    main()
