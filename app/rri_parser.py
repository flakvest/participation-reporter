import re

from app.schemas import MONTH_ORDER, ParsedReport, infer_year

FIELD_DEFS_PLATOON = [
    ("Call Sign", "X"),
    ("Month", "JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC"),
    ("All MARS Equipment and Software Operational", "YES,NO"),
    ("Possess Required MARS Skills", "YES,NO"),
    ("Total HF Operational Hours", "#"),
    ("J0G Hours in the HF Total", "#"),
    ("GST or Message Center Hours in the HF Total", "#"),
    ("Other HF hours including AFMARS or other regions and SHARES in the HF Total", "#"),
    ("Sum of Total HF Operational Hours plus other MARS Hours such as Admin and Training and Equip maintenance", "#"),
    ("Notes and Training Needs", "X"),
]

KNOWN_SETS = {"1PLTPARTRPT", "2PLTPARTRPT"}

MONTHS = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"}
YES_NO = {"YES", "NO"}


def validate_field(value: str, mask: str) -> list[str]:
    errors = []
    if mask == "X":
        pass
    elif mask == "#":
        if not value.isdigit():
            errors.append(f"Expected numeric value, got '{value}'")
    elif "," in mask:
        allowed = {x.strip().upper() for x in mask.split(",")}
        if value.strip().upper() not in allowed:
            errors.append(f"Expected one of [{mask}], got '{value}'")
    else:
        errors.append(f"Unknown mask '{mask}'")
    return errors


def parse_strip(strip: str) -> tuple[list[str] | None, list[str]]:
    errors = []
    strip = strip.strip()
    if not strip:
        return None, errors

    parts = strip.split("/")
    set_id = parts[0].strip().upper()

    if set_id not in KNOWN_SETS:
        errors.append(f"Unknown set identifier '{set_id}'")
        return None, errors

    value_parts = parts[1:]

    if len(value_parts) != len(FIELD_DEFS_PLATOON):
        errors.append(
            f"Expected {len(FIELD_DEFS_PLATOON)} fields for {set_id}, "
            f"got {len(value_parts)}"
        )
        return None, errors

    field_values = []
    for i, (field_name, mask) in enumerate(FIELD_DEFS_PLATOON):
        val = value_parts[i].strip()
        field_errors = validate_field(val, mask)
        for e in field_errors:
            errors.append(f"Field '{field_name}': {e}")
        field_values.append(val)

    if errors:
        return None, errors

    return field_values, errors


def parse_text(text: str) -> list[tuple[ParsedReport | None, list[str]]]:
    text = text.strip()
    if not text:
        return [(None, ["No data provided"])]

    raw_strips = text.split("//")
    raw_strips = [s.strip() for s in raw_strips if s.strip()]

    results = []
    for raw in raw_strips:
        full_strip = raw + "//"
        field_values, errors = parse_strip(raw)
        if field_values is None:
            results.append((None, errors or ["Failed to parse strip"]))
        else:
            set_id = raw.split("/")[0].strip().upper()
            platoon = "1PLT" if set_id == "1PLTPARTRPT" else "2PLT"
            month_val = field_values[1].upper()
            report = ParsedReport(
                platoon=platoon,
                callsign=field_values[0].upper(),
                month=month_val,
                year=infer_year(month_val),
                equipment_ok=field_values[2].upper(),
                skills_ok=field_values[3].upper(),
                total_hf_hours=int(field_values[4]),
                j0g_hours=int(field_values[5]),
                gst_hours=int(field_values[6]),
                other_hf_hours=int(field_values[7]),
                total_mars_hours=int(field_values[8]),
                notes=field_values[9],
                raw_strip=full_strip,
            )
            results.append((report, errors))
    return results
