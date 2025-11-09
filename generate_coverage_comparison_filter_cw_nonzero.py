# Script: generate_coverage_comparison_filter_cw_nonzero.py
# Purpose: Like generate_coverage_comparison.py but also filters out any rows where
# CITYWALK's statement coverage (Statement_CW) equals 0.
import csv
import math
from pathlib import Path
from typing import Optional, Dict

ROOT = Path(__file__).parent
CITYWALK_DIR = ROOT / "coverage_results" / "citywalk"
LLM4CPP_DIR = ROOT / "coverage_results" / "llm4cpp"
OUT_CSV = ROOT / "coverage_results" / "coverage_comparison_all_projects_by_function_cw_nonzero.csv"

TOL = 1e-9


def parse_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    s = s.strip()
    if s == "":
        return None
    try:
        v = float(s)
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None


def read_all_coverage_in_dir(dir_path: Path) -> Dict[str, Dict[str, Optional[float]]]:
    mapping: Dict[str, Dict[str, Optional[float]]] = {}
    if not dir_path.exists():
        raise FileNotFoundError(f"Coverage directory not found: {dir_path}")
    for csv_file in sorted(dir_path.glob("*.csv")):
        try:
            with csv_file.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames:
                    continue
                if "Function Name" not in [h.strip() for h in reader.fieldnames]:
                    continue
                for row in reader:
                    func = (row.get("Function Name") or "").strip()
                    if not func:
                        continue
                    if func.upper().startswith("AVERAGE"):
                        continue
                    stmt = parse_float(row.get("Total Statement Coverage"))
                    branch = parse_float(row.get("Total Branch Coverage"))
                    mapping[func] = {"stmt": stmt, "branch": branch}
        except Exception:
            # ignore malformed files but continue
            continue
    return mapping


def fmt(val: Optional[float]) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    s = f"{val:.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    elif s.endswith("0"):
        s = s.rstrip("0").rstrip(".")
    return s


def nearly_zero(v: Optional[float]) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and math.isnan(v):
        return False
    return abs(v) < TOL


def is_zero_or_nan(v: Optional[float]) -> bool:
    # True when value is missing (None), NaN, or effectively zero
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return abs(v) < TOL


def main():
    cw = read_all_coverage_in_dir(CITYWALK_DIR)
    llm = read_all_coverage_in_dir(LLM4CPP_DIR)

    all_funcs = sorted(set(list(cw.keys()) + list(llm.keys())))

    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "Function Name",
            "Statement_CW",
            "Statement_LLM4Cpp",
            "Statement_Δ",
            "Branch_CW",
            "Branch_LLM4Cpp",
            "Branch_Δ",
        ])

        for func in all_funcs:
            cw_stmt = cw.get(func, {}).get("stmt") if cw.get(func) else None
            llm_stmt = llm.get(func, {}).get("stmt") if llm.get(func) else None
            cw_branch = cw.get(func, {}).get("branch") if cw.get(func) else None
            llm_branch = llm.get(func, {}).get("branch") if llm.get(func) else None

            # Compute deltas only if both sides present
            stmt_delta = None
            if (llm_stmt is not None) and (cw_stmt is not None):
                stmt_delta = llm_stmt - cw_stmt

            branch_delta = None
            if (llm_branch is not None) and (cw_branch is not None):
                branch_delta = llm_branch - cw_branch

            # New rule: filter out entries where CITYWALK statement coverage is exactly 0
            if (cw_stmt is not None) and (abs(cw_stmt) < TOL):
                continue

            # Keep the existing rule: skip row if BOTH deltas are zero or missing
            if is_zero_or_nan(stmt_delta) and is_zero_or_nan(branch_delta):
                continue

            writer.writerow([
                func,
                fmt(cw_stmt),
                fmt(llm_stmt),
                fmt(stmt_delta) if stmt_delta is not None else "",
                fmt(cw_branch),
                fmt(llm_branch),
                fmt(branch_delta) if branch_delta is not None else "",
            ])

    print("Wrote:", OUT_CSV)


if __name__ == "__main__":
    main()

