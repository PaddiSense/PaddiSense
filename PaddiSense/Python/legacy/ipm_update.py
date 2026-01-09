#!/usr/bin/env python3
"""
ipm_update.py  (Inventory Product Manager)

v2 Goals:
- One product master record per product_id
- Multiple storage locations per product
- Stock movements always occur at (product_id, location)
- Immutable transaction ledger with (ts, product_id, location, qty, user)

JSON Path (dev): /config/PaddiSense/JSON/ipm_products.json

Commands:
1) Migrate legacy file-in-place (best done once):
   python3 ipm_update.py migrate_v1

2) Upsert product master + ensure location exists:
   python3 ipm_update.py upsert_product \
     --mode add|edit \
     --category "Fertiliser" \
     --id "UREA" \
     --name "Urea" \
     --unit "kg" \
     --application-unit "kg/ha" \
     --subcategory "Fertiliser" \
     --chemical-group "None / Unknown" \
     --default-container-size 1000 \
     --min-stock-default 0 \
     --location "Silo 10" \
     --container-size 0 \
     --min-stock 0 \
     --initial-stock 13930 \
     --a1-name "Nitrogen" --a1-conc 46 --a1-unit "%"

3) Stock movement at a location:
   python3 ipm_update.py move_stock \
     --product "UREA" \
     --category "Fertiliser" \
     --location "Silo 10" \
     --action use|topup|adjust \
     --quantity 500 \
     --note "Spread on SW6" \
     --user-id "..." --user-name "..."

Notes:
- "adjust" will set absolute on_hand to quantity (not delta).
- "use" and "topup" treat quantity as positive magnitude.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# >>> IMPORTANT: This is your dev JSON file
INVENTORY_PATH = Path("/config/PaddiSense/JSON/ipm_products.json")

DEFAULT_GROUP = "None / Unknown"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def load_json():
    if not INVENTORY_PATH.exists():
        return {"version": 2, "products": {}, "transactions": []}

    try:
        with INVENTORY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Do not crash; start empty to keep HA stable
        return {"version": 2, "products": {}, "transactions": []}

    # Normalize root structure
    if isinstance(data, dict) and data.get("version") == 2 and "products" in data:
        data.setdefault("products", {})
        data.setdefault("transactions", [])
        return data

    # Legacy (your current structure): chemicals/fertiliser/seed + transactions
    if isinstance(data, dict) and any(k in data for k in ("chemicals", "fertiliser", "seed")):
        data.setdefault("transactions", [])
        return data

    # Unknown shape
    return {"version": 2, "products": {}, "transactions": []}


def save_json(data):
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INVENTORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False, ensure_ascii=False)


def slugify_id(raw_id: str, name: str) -> str:
    base = (raw_id or "").strip() or (name or "").strip()
    cleaned = []
    for ch in base.upper():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in (" ", "-", "/", "."):
            cleaned.append("_")
    slug = "".join(cleaned)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "UNKNOWN_PRODUCT"


def fnum(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def add_tx(store, *, product_id, product_name, category, location, tx_type, qty, unit, note, user_id="", user_name=""):
    store.setdefault("transactions", []).append(
        {
            "ts": now_iso(),
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "location": location,
            "type": tx_type,
            "qty": float(qty),
            "unit": unit or "",
            "note": note or "",
            "user_id": user_id or "",
            "user_name": user_name or "",
        }
    )


# -----------------------------
# Migration from legacy schema
# -----------------------------
def migrate_v1_to_v2(data):
    """
    Converts legacy structure:
      {chemicals:{}, fertiliser:{}, seed:{}, transactions:[...]}
    into v2:
      {version:2, products:{...}, transactions:[...]}
    """
    if isinstance(data, dict) and data.get("version") == 2 and "products" in data:
        return data  # already v2

    legacy_tx = data.get("transactions", []) if isinstance(data, dict) else []
    v2 = {"version": 2, "products": {}, "transactions": legacy_tx[:]}

    def upsert_from_legacy(product_dict, fallback_id):
        pid = slugify_id(product_dict.get("id", fallback_id), product_dict.get("name", fallback_id))
        name = product_dict.get("name", pid)
        category = product_dict.get("category", "")
        subcategory = product_dict.get("subcategory", "")
        unit = product_dict.get("unit", "")
        app_unit = product_dict.get("application_unit", "")
        chem_group = product_dict.get("chemical_group", DEFAULT_GROUP)
        actives = product_dict.get("actives") or []
        default_container = fnum(product_dict.get("container_size", product_dict.get("default_pack_size", 0.0)), 0.0)
        min_stock_default = fnum(product_dict.get("min_stock", 0.0), 0.0)

        location = (product_dict.get("storage_location") or "").strip() or "Unknown"
        on_hand = fnum(product_dict.get("stock_on_hand", 0.0), 0.0)
        loc_container = fnum(product_dict.get("container_size", product_dict.get("default_pack_size", 0.0)), 0.0)

        p = v2["products"].get(pid)
        if not p:
            p = {
                "id": pid,
                "name": name,
                "category": category,
                "subcategory": subcategory,
                "unit": unit,
                "application_unit": app_unit,
                "chemical_group": chem_group,
                "actives": actives,
                "default_container_size": default_container,
                "min_stock_default": min_stock_default,
                "locations": {},
            }

        # Merge location balance
        loc = p["locations"].get(location) or {"on_hand": 0.0, "container_size": loc_container, "min_stock": min_stock_default, "last_added_ts": ""}
        loc["on_hand"] = loc.get("on_hand", 0.0) + on_hand
        loc["container_size"] = loc_container
        p["locations"][location] = loc

        v2["products"][pid] = p

    for section in ("chemicals", "fertiliser", "seed"):
        cat = data.get(section, {}) if isinstance(data, dict) else {}
        if isinstance(cat, dict):
            for k, v in cat.items():
                if isinstance(v, dict):
                    upsert_from_legacy(v, k)

    return v2


# -----------------------------
# Commands
# -----------------------------
def cmd_migrate(args):
    data = load_json()
    v2 = migrate_v1_to_v2(data)
    save_json(v2)
    return 0


def cmd_upsert_product(args):
    data = load_json()
    if not (isinstance(data, dict) and data.get("version") == 2 and "products" in data):
        data = migrate_v1_to_v2(data)

    pid = slugify_id(args.id, args.name)
    products = data.setdefault("products", {})
    existing = products.get(pid, {})

    # Build actives (up to 6)
    actives = []
    for i in range(1, 7):
        n = (getattr(args, f"a{i}_name") or "").strip()
        if not n:
            continue
        actives.append(
            {
                "name": n,
                "concentration": fnum(getattr(args, f"a{i}_conc"), 0.0),
                "concentration_unit": getattr(args, f"a{i}_unit") or "",
            }
        )

    p = dict(existing) if existing else {}
    p["id"] = pid
    p["name"] = args.name
    p["category"] = args.category
    p["subcategory"] = args.subcategory or ""
    p["unit"] = args.unit or ""
    p["application_unit"] = args.application_unit or ""
    p["chemical_group"] = args.chemical_group or DEFAULT_GROUP
    p["actives"] = actives
    p["default_container_size"] = fnum(args.default_container_size, 0.0)
    p["min_stock_default"] = fnum(args.min_stock_default, 0.0)
    p.setdefault("locations", {})

    # Ensure location exists
    location = (args.location or "").strip() or "Unknown"
    loc = p["locations"].get(location) or {}
    loc.setdefault("on_hand", 0.0)
    loc["container_size"] = fnum(args.container_size, fnum(p.get("default_container_size", 0.0), 0.0))
    loc["min_stock"] = fnum(args.min_stock, fnum(p.get("min_stock_default", 0.0), 0.0))

    # Initial stock only if this is a new location record and currently 0
    init = fnum(args.initial_stock, 0.0)
    if init and fnum(loc.get("on_hand", 0.0), 0.0) == 0.0:
        loc["on_hand"] = init
        loc["last_added_ts"] = now_iso()
        add_tx(
            data,
            product_id=pid,
            product_name=p["name"],
            category=p["category"],
            location=location,
            tx_type="init",
            qty=init,
            unit=p.get("unit", ""),
            note=f"Initial stock on upsert ({args.mode})",
            user_id=args.user_id,
            user_name=args.user_name,
        )

    p["locations"][location] = loc
    products[pid] = p

    # Audit record of the edit/add
    add_tx(
        data,
        product_id=pid,
        product_name=p["name"],
        category=p["category"],
        location=location,
        tx_type=f"upsert_{(args.mode or 'unknown').lower()}",
        qty=0.0,
        unit=p.get("unit", ""),
        note=args.note or f"Upsert via HA UI (location={location})",
        user_id=args.user_id,
        user_name=args.user_name,
    )

    save_json(data)
    return 0


def cmd_move_stock(args):
    data = load_json()
    if not (isinstance(data, dict) and data.get("version") == 2 and "products" in data):
        data = migrate_v1_to_v2(data)

    pid = args.product.strip()
    location = (args.location or "").strip()
    if not location:
        print("ERROR: --location is required for move_stock", file=sys.stderr)
        return 2

    products = data.setdefault("products", {})
    if pid not in products:
        # create minimal stub so movements don't vanish
        products[pid] = {
            "id": pid,
            "name": pid,
            "category": args.category or "Unknown",
            "subcategory": "",
            "unit": "",
            "application_unit": "",
            "chemical_group": DEFAULT_GROUP,
            "actives": [],
            "default_container_size": 0.0,
            "min_stock_default": 0.0,
            "locations": {},
        }

    p = products[pid]
    p.setdefault("locations", {})
    loc = p["locations"].get(location) or {"on_hand": 0.0, "container_size": 0.0, "min_stock": fnum(p.get("min_stock_default", 0.0), 0.0), "last_added_ts": ""}

    qty = fnum(args.quantity, 0.0)
    if qty == 0.0:
        return 0

    action = (args.action or "").strip().lower()
    current = fnum(loc.get("on_hand", 0.0), 0.0)

    if action == "adjust":
        new_stock = max(0.0, qty)  # absolute set
        qty_logged = new_stock - current
        tx_type = "adjust"
    elif action == "use":
        adj = abs(qty)
        new_stock = max(0.0, current - adj)
        qty_logged = adj
        tx_type = "use"
    else:
        # default to topup
        adj = abs(qty)
        new_stock = current + adj
        qty_logged = adj
        tx_type = "topup"
        loc["last_added_ts"] = now_iso()

    loc["on_hand"] = new_stock
    p["locations"][location] = loc
    products[pid] = p

    add_tx(
        data,
        product_id=p.get("id", pid),
        product_name=p.get("name", pid),
        category=p.get("category", args.category or ""),
        location=location,
        tx_type=tx_type,
        qty=qty_logged,
        unit=p.get("unit", ""),
        note=args.note or "",
        user_id=args.user_id,
        user_name=args.user_name,
    )

    save_json(data)
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="ipm_update.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # migrate
    s = sub.add_parser("migrate_v1", help="Convert legacy schema to v2 in-place")
    s.set_defaults(func=cmd_migrate)

    # upsert
    s = sub.add_parser("upsert_product", help="Add/edit product master + ensure location exists")
    s.add_argument("--mode", required=True, choices=["add", "edit"])
    s.add_argument("--category", required=True)
    s.add_argument("--id", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--unit", default="")
    s.add_argument("--application-unit", dest="application_unit", default="")
    s.add_argument("--subcategory", default="")
    s.add_argument("--chemical-group", dest="chemical_group", default=DEFAULT_GROUP)
    s.add_argument("--default-container-size", dest="default_container_size", default=0.0)
    s.add_argument("--min-stock-default", dest="min_stock_default", default=0.0)

    s.add_argument("--location", default="Unknown")
    s.add_argument("--container-size", dest="container_size", default=None)
    s.add_argument("--min-stock", dest="min_stock", default=None)
    s.add_argument("--initial-stock", dest="initial_stock", default=0.0)
    s.add_argument("--note", default="")

    s.add_argument("--user-id", dest="user_id", default="")
    s.add_argument("--user-name", dest="user_name", default="")

    for i in range(1, 7):
        s.add_argument(f"--a{i}-name", dest=f"a{i}_name", default="")
        s.add_argument(f"--a{i}-conc", dest=f"a{i}_conc", default=0.0)
        s.add_argument(f"--a{i}-unit", dest=f"a{i}_unit", default="")

    s.set_defaults(func=cmd_upsert_product)

    # move
    s = sub.add_parser("move_stock", help="Stock movement at a specific location")
    s.add_argument("--category", default="")  # optional; product master is source of truth
    s.add_argument("--product", required=True)
    s.add_argument("--location", required=True)
    s.add_argument("--action", default="topup", choices=["topup", "use", "adjust"])
    s.add_argument("--quantity", required=True)
    s.add_argument("--note", default="")
    s.add_argument("--user-id", dest="user_id", default="")
    s.add_argument("--user-name", dest="user_name", default="")
    s.set_defaults(func=cmd_move_stock)

    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
