"""Session project snapshots. Imports never trust saved computed results."""
import csv
import io
import json
import math
from .calculations import ENGINE_VERSION, make_record, material_totals, procurement_quantity

MAX_RECORDS = 100


def export_project(name, records, rates, currency):
    return json.dumps(dict(schema_version=2, engine_version=ENGINE_VERSION, name=name,
                           currency=currency, rates=rates, records=records),
                      ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def import_project(data):
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("Project JSON must be at most 2 MB.")
    try:
        obj = json.loads(data)
        if not isinstance(obj, dict) or obj.get("schema_version") != 2:
            raise ValueError("Use a Civil QuantEstimate v2 JSON export.")
        rows = obj["records"]
        if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
            raise ValueError("A project can contain at most 100 takeoffs.")
        records = [make_record(r["module"], r["inputs"], r.get("label", "")) for r in rows]
        rates = obj.get("rates", {})
        if not isinstance(rates, dict) or len(rates) > 50:
            raise ValueError("Invalid material rates.")
        allowed = material_totals(records)
        clean_rates = {}
        for key, value in rates.items():
            if key not in allowed:
                continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 1e9:
                raise ValueError("Rates must be finite non-negative numbers.")
            clean_rates[key] = float(value)
        name = obj.get("name", "Imported project")
        currency = obj.get("currency", "PKR")
        if not isinstance(name, str) or not isinstance(currency, str):
            raise ValueError("Invalid project name or currency.")
        if currency not in ("PKR", "USD", "EUR", "GBP", "AED", "SAR"):
            raise ValueError("Unsupported currency. No automatic currency conversion is performed.")
        return dict(name=name[:100], records=records, rates=clean_rates, currency=currency)
    except (KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid project file. Please choose an exported v2 JSON file.") from exc


def boq_rows(records, rates):
    rows = []
    for material, amount in sorted(material_totals(records).items()):
        order = procurement_quantity(material, amount)
        rate = rates.get(material, 0.0)
        rows.append({"Material / unit": material, "Calculated quantity": round(amount, 4),
                     "Order quantity": round(order, 4), "Your unit rate": rate or None,
                     "Material amount": round(order * rate, 2) if rate else None})
    return rows


def boq_csv(records, rates):
    buffer = io.StringIO()
    rows = boq_rows(records, rates)
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
