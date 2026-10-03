"""Quantity takeoff in SI units. All assumptions are explicit and editable.

These are NEW v2 formulas, not a reconstruction of the missing v1 utils files.
Nominal mixes and brick geometry are estimating assumptions, not design approval.
"""
import math
from datetime import datetime, timezone
from uuid import uuid4

ENGINE_VERSION = "2.0.0"


def number(label, default, minimum=0.001, maximum=1000000.0, step=0.1, integer=False):
    return dict(label=label, default=default, minimum=minimum, maximum=maximum,
                step=step, integer=integer)


WASTE = number("Wastage allowance (%)", 5.0, 0.0, 50.0, 0.5)
COUNT = number("Number of identical elements", 1, 1, 100000, 1, True)
OPENINGS = number("Total openings across ALL elements (m²)", 0.0, 0.0)
MORTAR = dict(label="Cement : sand (by volume)", options=["1:3", "1:4", "1:5", "1:6"], default="1:4")
SPECS = {
    "Brickwork": {
        "length": number("Wall length (m)", 10.0),
        "height": number("Wall height (m)", 3.0),
        "thickness": number("Wall thickness (m)", 0.23, step=0.01),
        "quantity": COUNT, "opening_area": OPENINGS, "mortar_ratio": MORTAR,
        "wastage": WASTE,
        "brick_length_mm": number("Actual brick length (mm)", 230.0, 1.0, 1000.0, 1.0),
        "brick_width_mm": number("Actual brick width (mm)", 110.0, 1.0, 1000.0, 1.0),
        "brick_height_mm": number("Actual brick height (mm)", 75.0, 1.0, 1000.0, 1.0),
        "joint_mm": number("Joint allowance on each brick dimension (mm)", 10.0, 0.0, 50.0, 1.0),
        "dry_factor": number("Mortar dry-volume factor", 1.33, 1.0, 2.0, 0.01),
        "cement_density": number("Assumed cement bulk density (kg/m³)", 1440.0, 500.0, 2000.0, 10.0),
        "bag_kg": number("Cement bag mass (kg)", 50.0, 1.0, 100.0, 1.0),
    },
    "Plaster": {
        "length": number("Surface length (m)", 10.0),
        "height": number("Surface height (m)", 3.0),
        "quantity": COUNT, "opening_area": OPENINGS,
        "thickness_mm": number("Plaster thickness (mm)", 12.0, 1.0, 100.0, 1.0),
        "mortar_ratio": MORTAR, "wastage": WASTE,
        "dry_factor": number("Mortar dry-volume factor", 1.33, 1.0, 2.0, 0.01),
        "cement_density": number("Assumed cement bulk density (kg/m³)", 1440.0, 500.0, 2000.0, 10.0),
        "bag_kg": number("Cement bag mass (kg)", 50.0, 1.0, 100.0, 1.0),
    },
    "Concrete": {
        "length": number("Element length (m)", 5.0),
        "width": number("Element width (m)", 3.0),
        "thickness": number("Depth / thickness (m)", 0.15, step=0.01),
        "quantity": COUNT,
        "mix_ratio": dict(label="Nominal cement : sand : aggregate (volume)",
                          options=["1:1.5:3", "1:2:4", "1:3:6"], default="1:2:4"),
        "wastage": WASTE,
        "dry_factor": number("Concrete dry-volume factor", 1.54, 1.0, 2.0, 0.01),
        "cement_density": number("Assumed cement bulk density (kg/m³)", 1440.0, 500.0, 2000.0, 10.0),
        "bag_kg": number("Cement bag mass (kg)", 50.0, 1.0, 100.0, 1.0),
    },
    "Steel": {
        "bar_dia": number("Bar diameter (mm)", 12.0, 1.0, 100.0, 1.0),
        "bar_length": number("Cut length per bar including approved bends/laps (m)", 6.0),
        "no_of_bars": number("Number of bars", 10, 1, 1000000, 1, True),
        "wastage": number("Wastage allowance (%)", 3.0, 0.0, 50.0, 0.5),
        "steel_density": number("Steel density (kg/m³)", 7850.0, 7000.0, 8500.0, 10.0),
    },
}


def default_inputs(module):
    return {key: field["default"] for key, field in SPECS[module].items()}


def validate_inputs(module, inputs):
    if module not in SPECS:
        raise ValueError("Choose a supported takeoff module.")
    if not isinstance(inputs, dict) or set(inputs) != set(SPECS[module]):
        raise ValueError("Inputs are incomplete or contain unexpected fields.")
    clean = {}
    for key, spec in SPECS[module].items():
        value = inputs[key]
        if "options" in spec:
            if value not in spec["options"]:
                raise ValueError(f"Invalid selection for {spec['label']}.")
        else:
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f"{spec['label']} must be a finite number.")
            if not spec["minimum"] <= value <= spec["maximum"]:
                raise ValueError(f"{spec['label']} must be between {spec['minimum']} and {spec['maximum']}.")
            if spec["integer"] and int(value) != value:
                raise ValueError(f"{spec['label']} must be a whole number.")
            value = int(value) if spec["integer"] else float(value)
        clean[key] = value
    return clean


def calculate(module, inputs):
    p = validate_inputs(module, inputs)
    factor = 1 + p["wastage"] / 100
    metrics, materials, formulas, notes = {}, {}, [], []
    if module in ("Brickwork", "Plaster"):
        gross = p["length"] * p["height"] * p["quantity"]
        if p["opening_area"] > gross:
            raise ValueError("Total openings cannot exceed the gross area of all elements.")
        area = gross - p["opening_area"]
        metrics["Net area (m²)"] = area
        formulas.append("Net area = length × height × count − total opening area.")
        notes.append("Opening area is the total across all elements. Each plaster face is a separate surface.")
        cement_part, sand_part = map(float, p["mortar_ratio"].split(":"))
        if module == "Brickwork":
            volume = area * p["thickness"]
            dims = [p[k] / 1000 for k in ("brick_length_mm", "brick_width_mm", "brick_height_mm")]
            joint = p["joint_mm"] / 1000
            actual = math.prod(dims)
            nominal = math.prod(d + joint for d in dims)
            theoretical_bricks = volume / nominal
            wet = max(0.0, volume - theoretical_bricks * actual)
            metrics.update({"Masonry volume (m³)": volume, "Theoretical bricks": theoretical_bricks,
                            "Bricks to order": math.ceil(theoretical_bricks * factor),
                            "Wet mortar before wastage (m³)": wet})
            materials["Bricks (each)"] = math.ceil(theoretical_bricks * factor)
            formulas.extend(["Theoretical bricks = masonry volume / nominal brick volume.",
                             "Nominal brick volume = (length + joint) × (width + joint) × (height + joint).",
                             "Wet mortar = masonry volume − theoretical bricks × actual brick volume."])
            notes.append("Idealized brick-and-joint geometry; bond, frogs, breakage pattern and edge effects are not modelled.")
        else:
            wet = area * p["thickness_mm"] / 1000
            metrics["Wet plaster before wastage (m³)"] = wet
            formulas.append("Wet plaster = net area × thickness in metres.")
        dry = wet * p["dry_factor"] * factor
        cement_volume = dry * cement_part / (cement_part + sand_part)
        materials[f"Cement ({p['bag_kg']:g} kg bags)"] = cement_volume * p["cement_density"] / p["bag_kg"]
        materials["Sand (m³)"] = dry * sand_part / (cement_part + sand_part)
        metrics["Dry mortar incl. wastage (m³)"] = dry
    elif module == "Concrete":
        wet = p["length"] * p["width"] * p["thickness"] * p["quantity"]
        dry = wet * p["dry_factor"] * factor
        c, s, a = map(float, p["mix_ratio"].split(":"))
        materials[f"Cement ({p['bag_kg']:g} kg bags)"] = dry * c / (c + s + a) * p["cement_density"] / p["bag_kg"]
        materials["Sand (m³)"] = dry * s / (c + s + a)
        materials["Aggregate (m³)"] = dry * a / (c + s + a)
        metrics = {"Net concrete (m³)": wet, "Concrete incl. wastage (m³)": wet * factor,
                   "Dry ingredients incl. wastage (m³)": dry}
        formulas.extend(["Wet volume = length × width × depth × count.",
                         "Dry ingredients = wet volume × dry-volume factor × (1 + wastage/100).",
                         "Ingredient volume = dry ingredients × its ratio part / sum of all parts."])
        notes.append("Nominal volumetric takeoff only. No strength-grade guarantee, mix design, water, admixtures or structural reinforcement design.")
    else:
        total_length = p["bar_length"] * p["no_of_bars"]
        per_metre = math.pi / 4 * (p["bar_dia"] / 1000) ** 2 * p["steel_density"]
        materials["Steel (kg)"] = total_length * per_metre * factor
        metrics = {"Total cut length (m)": total_length, "Unit mass (kg/m)": per_metre,
                   "Mass before wastage (kg)": total_length * per_metre}
        formulas.append("Mass = π/4 × diameter² (metres) × density × total cut length × (1 + wastage/100).")
        notes.append("Bar mass takeoff only. Enter the approved total cut length per bar; bend shapes, laps, hooks and cutting-stock optimization are not generated.")
    if module != "Steel":
        formulas.append("Cement bags = cement volume × assumed bulk density / bag mass.")
        if module != "Concrete":
            formulas.append("Dry mortar = wet mortar × dry-volume factor × (1 + wastage/100), split by the selected ratio.")
        notes.append("Dry-volume factor, cement density, bag mass and nominal ratios are user-selected estimating assumptions.")
    notes.append("Wastage is applied once. No automatic code-specific measurement deductions are made.")
    return dict(metrics=metrics, materials=materials, formulas=formulas, notes=notes)


def make_record(module, inputs, label=""):
    inputs = validate_inputs(module, inputs)
    return dict(id=uuid4().hex[:12], label=(str(label).strip() or module)[:100], module=module,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                engine_version=ENGINE_VERSION, inputs=inputs, result=calculate(module, inputs))


def material_totals(records):
    totals = {}
    for record in records:
        # Recompute from inputs rather than trusting stored/AI-generated totals.
        for material, amount in calculate(record["module"], record["inputs"])["materials"].items():
            totals[material] = totals.get(material, 0.0) + amount
    return totals


def procurement_quantity(material, amount):
    return math.ceil(amount) if "bags)" in material or "(each)" in material else amount
