# Formula assumptions

These formulas were implemented for v2 because the original utility files were unavailable. They are explicit modelling choices for preliminary quantity takeoff, not clauses quoted from an engineering standard.

All length inputs are metres except fields explicitly labelled millimetres. Area is m², volume is m³ and mass is kg. Ratios are **by volume**.

Let the wastage multiplier be `f = 1 + wastage_percent / 100`. It is applied once to material quantities.

## Brickwork

```text
net_area = length × height × wall_count − TOTAL_opening_area
masonry_volume = net_area × wall_thickness
actual_brick_volume = brick_length × brick_width × brick_height
nominal_brick_volume = (brick_length + joint) × (brick_width + joint) × (brick_height + joint)
theoretical_bricks = masonry_volume / nominal_brick_volume
bricks_to_order = ceil(theoretical_bricks × f)
wet_mortar = masonry_volume − theoretical_bricks × actual_brick_volume
dry_mortar = wet_mortar × dry_factor × f
```

Millimetres are converted to metres first. Actual brick size, joints and mortar ratio are editable. The idealized repeating brick geometry does not model boundary effects, bond patterns, frogs or workmanship. Mortar is calculated from the theoretical brick count before rounding or wastage.

## Plaster

```text
net_area = length × height × surface_count − TOTAL_opening_area
wet_mortar = net_area × thickness_mm / 1000
dry_mortar = wet_mortar × dry_factor × f
```

Each plaster face is a surface. For two faces with the same door opening, include that opening on both faces in the total deducted area. There are no automatic code-specific small-opening deduction rules.

For mortar ratio `c:s`:

```text
cement_volume = dry_mortar × c / (c + s)
sand_volume = dry_mortar × s / (c + s)
cement_bags = cement_volume × cement_bulk_density / bag_mass
```

## Concrete

```text
wet_volume = length × width × depth × count
dry_volume = wet_volume × dry_factor × f
cement_volume = dry_volume × c / (c + s + a)
sand_volume = dry_volume × s / (c + s + a)
aggregate_volume = dry_volume × a / (c + s + a)
```

Ratios are nominal ingredient proportions. No strength grade is assigned from them. Water content, compaction, moisture/bulking corrections, mix design and reinforcement design are outside the calculation.

## Steel

```text
diameter_m = diameter_mm / 1000
unit_mass_kg_per_m = pi / 4 × diameter_m² × steel_density
net_mass = unit_mass_kg_per_m × cut_length_per_bar × bar_count
order_mass = net_mass × f
```

At a density of 7850 kg/m³ this is close to the familiar `d²/162` approximation, but the implementation uses the physical cylinder formula directly. Enter approved bends, laps and hooks in the cut length. A full shape-code BBS is not produced.

## Defaults and pricing

| Assumption | Starting value | Treatment |
| --- | --- | --- |
| Actual brick size | 230 × 110 × 75 mm | Editable; confirm local material |
| Joint allowance | 10 mm | Editable idealized geometry |
| Mortar dry factor | 1.33 | Editable estimating assumption |
| Concrete dry factor | 1.54 | Editable estimating assumption |
| Cement bulk density | 1440 kg/m³ | Editable, not an asserted universal density |
| Cement bag | 50 kg | Editable; different bag sizes aggregate separately |
| Steel density | 7850 kg/m³ | Editable |
| Wastage | 5% masonry/plaster/concrete; 3% steel | Editable |
| Material rates | Unpriced | User supplies quotations; no invented market prices |

Cement bags are rounded up only after aggregation by bag size. Bricks are rounded up for each takeoff. Pricing uses the resulting order quantities. The material subtotal excludes labour, equipment, transport, taxes and overheads.
