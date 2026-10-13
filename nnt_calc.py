#!/usr/bin/env python3
"""NNT/NNH and Newcombe–Wilson confidence intervals for two independent groups.

The outcome is an adverse event. Positive control minus treatment risk denotes
benefit (NNT), and a negative difference denotes harm (NNH).
No continuity corrections or arbitrary clinical cutoffs are applied.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import re
import tempfile
from statistics import NormalDist


COLUMNS = ("control_events", "control_total", "treatment_events", "treatment_total")
OUTPUT_COLUMNS = (
    "control_risk", "treatment_risk", "absolute_risk_reduction",
    "arr_ci_lower", "arr_ci_upper", "relative_risk", "relative_risk_reduction",
    "measure", "number_needed", "number_needed_rounded_up",
    "number_needed_ci_lower", "number_needed_ci_upper", "ci_crosses_zero",
)


def _validate_counts(events, total, label):
    for field, value in (("events", events), ("total", total)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label}_{field} must be an integer")
    if total <= 0 or events < 0 or events > total:
        raise ValueError(f"{label} must satisfy 0 <= events <= total and total > 0")


def _wilson(events, total, z):
    p = events / total
    z2 = z * z
    denominator = 1 + z2 / total
    centre = (p + z2 / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def calculate_metrics(
    control_events: int,
    control_total: int,
    treatment_events: int,
    treatment_total: int,
    confidence_level: float = 0.95,
) -> dict:
    """Estimate effect and two-sided Newcombe (1998) method 10 score CI.

    Counts are from two *independent* groups with a common adverse-event
    definition. The reciprocal CI is finite only if the risk-difference
    interval lies strictly on one side of zero.
    """
    _validate_counts(control_events, control_total, "control")
    _validate_counts(treatment_events, treatment_total, "treatment")
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise ValueError("confidence_level must be a finite number between 0 and 1")
    if not math.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be a finite number between 0 and 1")

    z = NormalDist().inv_cdf((1 + confidence_level) / 2)
    pc = control_events / control_total
    pt = treatment_events / treatment_total
    arr = pc - pt
    lc, uc = _wilson(control_events, control_total, z)
    lt, ut = _wilson(treatment_events, treatment_total, z)
    low = max(-1.0, arr - math.hypot(pc - lc, ut - pt))
    high = min(1.0, arr + math.hypot(uc - pc, pt - lt))
    crosses_zero = low <= 0 <= high
    measure = "NNT" if arr > 0 else "NNH" if arr < 0 else "no_difference"
    number = 1 / abs(arr) if arr else None
    # A two-sided reciprocal interval is disconnected/unbounded when it
    # includes the null. Do not report misleading finite endpoints.
    ci = None if crosses_zero else sorted((1 / abs(low), 1 / abs(high)))

    return {
        "control_events": control_events,
        "control_total": control_total,
        "treatment_events": treatment_events,
        "treatment_total": treatment_total,
        "control_risk": pc,
        "treatment_risk": pt,
        "absolute_risk_reduction": arr,
        "risk_difference_ci": [low, high],
        "relative_risk": pt / pc if pc else None,
        "relative_risk_reduction": arr / pc if pc else None,
        "measure": measure,
        "number_needed": number,
        "number_needed_rounded_up": math.ceil(number - 1e-12) if number is not None else None,
        "number_needed_ci": ci,
        "ci_crosses_zero": crosses_zero,
        "confidence_level": confidence_level,
        "method": "Newcombe-Wilson score, no continuity correction",
    }


def _parse_count(value, label):
    if value is None or not re.fullmatch(r"\d+", str(value).strip()):
        raise ValueError(f"{label} must be a non-negative integer")
    return int(str(value).strip())


def process_batch(input_csv: str, output_csv: str, confidence_level: float = 0.95) -> int:
    """Atomically export CSV results; fail the batch if any row is invalid."""
    input_path, output_path = Path(input_csv), Path(output_csv)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("input and output CSV paths must differ")
    temporary = None
    try:
        with input_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            fields = reader.fieldnames or []
            if len(fields) != len(set(fields)):
                raise ValueError("duplicate CSV headers are not supported")
            if any(re.match(r"^\s*[=+\-@]", name) for name in fields):
                raise ValueError("unsafe CSV header name")
            if not set(COLUMNS).issubset(fields):
                raise ValueError("required CSV columns: " + ", ".join(COLUMNS))
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", delete=False,
                dir=output_path.parent, prefix=".nnt-", suffix=".csv"
            ) as tmp:
                temporary = Path(tmp.name)
                writer = csv.DictWriter(
                    tmp, fieldnames=list(dict.fromkeys([*fields, *OUTPUT_COLUMNS])),
                    extrasaction="ignore"
                )
                writer.writeheader()
                count = 0
                for row_num, row in enumerate(reader, start=2):
                    try:
                        values = {key: _parse_count(row.get(key), key) for key in COLUMNS}
                        result = calculate_metrics(**values, confidence_level=confidence_level)
                    except ValueError as exc:
                        raise ValueError(f"CSV row {row_num}: {exc}") from exc
                    # Spreadsheet formula injection: treat original metadata as untrusted.
                    for field in fields:
                        if field not in COLUMNS and field not in OUTPUT_COLUMNS:
                            value = row.get(field)
                            if isinstance(value, str) and re.match(r"^\s*[=+\-@]", value):
                                row[field] = "'" + value
                    row.update({
                        "control_risk": result["control_risk"],
                        "treatment_risk": result["treatment_risk"],
                        "absolute_risk_reduction": result["absolute_risk_reduction"],
                        "arr_ci_lower": result["risk_difference_ci"][0],
                        "arr_ci_upper": result["risk_difference_ci"][1],
                        "relative_risk": result["relative_risk"],
                        "relative_risk_reduction": result["relative_risk_reduction"],
                        "measure": result["measure"],
                        "number_needed": result["number_needed"],
                        "number_needed_rounded_up": result["number_needed_rounded_up"],
                        "number_needed_ci_lower": result["number_needed_ci"][0] if result["number_needed_ci"] else None,
                        "number_needed_ci_upper": result["number_needed_ci"][1] if result["number_needed_ci"] else None,
                        "ci_crosses_zero": result["ci_crosses_zero"],
                    })
                    writer.writerow(row)
                    count += 1
        os.replace(temporary, output_path)
        return count
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description="NNT/NNH for two independent event-rate groups")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Calculate from event counts")
    for column in COLUMNS:
        single.add_argument("--" + column.replace("_", "-"), required=True, type=int)
    batch = commands.add_parser("batch", help="Read event counts from CSV")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    for command in (single, batch):
        command.add_argument("--confidence", type=float, default=0.95, help="Two-sided confidence level, default 0.95")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            result = calculate_metrics(
                **{column: getattr(args, column) for column in COLUMNS},
                confidence_level=args.confidence,
            )
            print(json.dumps(result, indent=2, allow_nan=False))
        else:
            count = process_batch(args.input, args.output, args.confidence)
            print(f"Processed {count} records -> {args.output}")
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
