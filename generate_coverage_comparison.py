# Explanation: Treat literal 'nan' (and other NaN floats) as missing values. Import math and
# update parse_float, fmt, nearly_zero, and is_zero_or_nan to handle NaN properly so the output
# CSV won't contain 'nan' strings.
import csv
import math
from pathlib import Path
from typing import Optional, Dict

ROOT = Path(__file__).parent
CITYWALK_DIR = ROOT / "coverage_results" / "citywalk"
LLM4CPP_DIR = ROOT / "coverage_results" / "llm4cpp"
OUT_CSV = ROOT / "coverage_results" / "coverage_comparison_all_projects_by_function.csv"

TOL = 1e-9


def parse_float(s: str) -> Optional[float]:
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


# New helper: true when value is missing (None) or effectively zero
def is_zero_or_nan(v: Optional[float]) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return abs(v) < TOL


def main():
    cw = read_all_coverage_in_dir(CITYWALK_DIR)
    llm = read_all_coverage_in_dir(LLM4CPP_DIR)

    all_funcs = sorted(set(list(cw.keys()) + list(llm.keys())))

    # Prepare CSV only
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

        # Collect deltas for averaging
        stmt_deltas = []
        branch_deltas = []

        for func in all_funcs:
            cw_stmt = cw.get(func, {}).get("stmt") if cw.get(func) else None
            llm_stmt = llm.get(func, {}).get("stmt") if llm.get(func) else None
            cw_branch = cw.get(func, {}).get("branch") if cw.get(func) else None
            llm_branch = llm.get(func, {}).get("branch") if llm.get(func) else None

            stmt_delta = None
            if (llm_stmt is not None) and (cw_stmt is not None):
                stmt_delta = llm_stmt - cw_stmt

            branch_delta = None
            if (llm_branch is not None) and (cw_branch is not None):
                branch_delta = llm_branch - cw_branch

            # Round deltas to 2 decimal places and set close-to-zero to zero
            if stmt_delta is not None:
                stmt_delta = round(stmt_delta, 2)
                if abs(stmt_delta) < 1e-6:
                    stmt_delta = 0.0
            if branch_delta is not None:
                branch_delta = round(branch_delta, 2)
                if abs(branch_delta) < 1e-6:
                    branch_delta = 0.0

            # New filtering rule: skip the row if BOTH deltas are either zero (within tolerance) or missing (NaN)
            if is_zero_or_nan(stmt_delta) and is_zero_or_nan(branch_delta):
                continue

            # Collect deltas for averaging
            if stmt_delta is not None:
                stmt_deltas.append(stmt_delta)
            if branch_delta is not None:
                branch_deltas.append(branch_delta)

            writer.writerow([
                func,
                fmt(cw_stmt),
                fmt(llm_stmt),
                fmt(stmt_delta) if stmt_delta is not None else "",
                fmt(cw_branch),
                fmt(llm_branch),
                fmt(branch_delta) if branch_delta is not None else "",
            ])

        # Add average row
        if stmt_deltas:
            avg_stmt_delta = round(sum(stmt_deltas) / len(stmt_deltas), 2)
        else:
            avg_stmt_delta = None
        if branch_deltas:
            avg_branch_delta = round(sum(branch_deltas) / len(branch_deltas), 2)
        else:
            avg_branch_delta = None

        writer.writerow([
            "AVERAGE",
            "",
            "",
            fmt(avg_stmt_delta) if avg_stmt_delta is not None else "",
            "",
            "",
            fmt(avg_branch_delta) if avg_branch_delta is not None else "",
        ])

    print("Wrote:", OUT_CSV)


if __name__ == "__main__":
    main()
