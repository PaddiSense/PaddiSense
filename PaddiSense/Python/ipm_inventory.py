#!/usr/bin/env python3
"""
ipm_inventory.py

Inventory backend for PaddiSense Inventory Manager (IPM).

Design goals
- Application code is transferable via GitHub.
- Inventory data is NOT in git (each grower maintains their own products/stock).
- Minimal, stable interfaces for Home Assistant:
  - upsert_product (add/edit product metadata + optional initial stock)
  - move_stock (apply stock delta to a specific location)
  - list (debug)

Data file (NOT in git):
  /config/PaddiSense/data/ipm_inventory.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_PATH = Path("/config/PaddiSense/data/ipm_inventory.json")

CATEGORY_CANON = {
    "chemical": "Chemical",
    "chemicals": "Chemical",
    "fertiliser": "Fertiliser",
    "fertilisers": "Fertiliser",
    "fertilizer": "Fertiliser",
    "fertilizers": "Fertiliser",
    "seed": "Seed",
    "seeds": "Seed",
}


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def norm_category(s: str) -> str:
    k = (s or "").strip().lower()
    return CATEGORY_CANON.get(k, (s or "").strip() or "Chemical")


def slugify_id(raw_id: str, name: str) -> str:
    base = (raw_id or "").strip() or (name or "").strip() or "UNKNOWN_PRODUCT"
    out: List[str] = []
    for ch in base.upper():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "/"):
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "UNKNOWN_PRODUCT"


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def load_data() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        return {"products": {}, "transactions": []}
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        # Corrupt file: start fresh but do not crash HA
        return {"products": {}, "transactions": []}


def save_data(data: Dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def tx_append(
    data: Dict[str, Any],
    *,
    type_: str,
    product_id: str,
    name: str,
    category: str,
    location: str,
    delta: float,
    unit: str,
    note: str,
) -> None:
    data.setdefault("transactions", []).append(
        {
            "ts": now_ts(),
            "type": type_,
            "id": product_id,
            "name": name,
            "category": category,
            "location": location,
            "delta": delta,
            "unit": unit,
            "note": note or "",
        }
    )


def ensure_product(data: Dict[str, Any], pid: str) -> Dict[str, Any]:
    products = data.setdefault("products", {})
    if pid not in products:
        products[pid] = {
            "id": pid,
            "name": pid,
            "category": "Chemical",
            "subcategory": "",
            "unit": "",
            "container_size": 0.0,
            "min_stock": 0.0,
            "chemical_group": "",
            "application_unit": "",
            "stock_by_location": {},  # location -> float
            "actives": [],  # list of {name, concentration, concentration_unit}
        }
    return products[pid]


def cmd_upsert_product(args: argparse.Namespace) -> int:
    data = load_data()

    category = norm_category(args.category)
    pid = slugify_id(args.id, args.name)

    p = ensure_product(data, pid)
    is_new = (p.get("name") == pid and p.get("unit") == "" and not p.get("stock_by_location"))

    p["id"] = pid
    p["name"] = (args.name or "").strip()
    p["category"] = category
    p["subcategory"] = (args.subcategory or "").strip()
    p["unit"] = (args.unit or "").strip()
    p["container_size"] = fnum(args.container_size, 0.0)
    p["min_stock"] = fnum(args.min_stock, 0.0)
    p["chemical_group"] = (args.chemical_group or "").strip()
    p["application_unit"] = (args.application_unit or "").strip()

    # If new and initial_stock provided, allocate to storage_location
    initial_stock = fnum(args.initial_stock, 0.0)
    storage_location = (args.storage_location or "").strip()
    if is_new and initial_stock > 0 and storage_location:
        p.setdefault("stock_by_location", {})
        p["stock_by_location"][storage_location] = fnum(p["stock_by_location"].get(storage_location), 0.0) + initial_stock
        tx_append(
            data,
            type_="init_stock",
            product_id=pid,
            name=p["name"],
            category=category,
            location=storage_location,
            delta=initial_stock,
            unit=p.get("unit", ""),
            note="Initial stock on product creation",
        )

    save_data(data)
    print(pid)
    return 0


def cmd_move_stock(args: argparse.Namespace) -> int:
    data = load_data()

    pid = slugify_id(args.id, args.id)
    location = (args.location or "").strip()
    delta = fnum(args.delta, 0.0)

    if not pid or not location or delta == 0:
        return 0

    p = ensure_product(data, pid)
    p.setdefault("stock_by_location", {})
    current = fnum(p["stock_by_location"].get(location, 0.0), 0.0)
    new_val = current + delta
    if new_val < 0:
        new_val = 0.0

    p["stock_by_location"][location] = new_val

    tx_append(
        data,
        type_="move",
        product_id=pid,
        name=p.get("name", pid),
        category=p.get("category", ""),
        location=location,
        delta=delta,
        unit=p.get("unit", ""),
        note=args.note or "",
    )

    save_data(data)
    print(new_val)
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    data = load_data()
    products = data.get("products", {})
    for pid, p in products.items():
        total = sum(fnum(v, 0.0) for v in (p.get("stock_by_location") or {}).values())
        print(f"{pid}\t{p.get('name','')}\t{p.get('category','')}\tTOTAL={total}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ipm_inventory.py", description="IPM inventory backend")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_up = sub.add_parser("upsert_product", help="Add/edit a product (and optionally set initial stock)")
    p_up.add_argument("--mode", choices=["add", "edit"], default="add")  # kept for HA compatibility
    p_up.add_argument("--category", required=True)
    p_up.add_argument("--id", required=True)
    p_up.add_argument("--name", required=True)
    p_up.add_argument("--subcategory", default="")
    p_up.add_argument("--unit", default="")
    p_up.add_argument("--container_size", type=float, default=0.0)
    p_up.add_argument("--min_stock", type=float, default=0.0)
    p_up.add_argument("--initial_stock", type=float, default=0.0)
    p_up.add_argument("--storage_location", default="")
    p_up.add_argument("--chemical_group", default="")
    p_up.add_argument("--application_unit", default="")
    p_up.set_defaults(func=cmd_upsert_product)

    p_mv = sub.add_parser("move_stock", help="Move/adjust stock by delta in a location")
    p_mv.add_argument("--id", required=True)
    p_mv.add_argument("--location", required=True)
    p_mv.add_argument("--delta", type=float, required=True)
    p_mv.add_argument("--note", default="")
    p_mv.set_defaults(func=cmd_move_stock)

    p_ls = sub.add_parser("list", help="List products (debug)")
    p_ls.set_defaults(func=cmd_list)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
