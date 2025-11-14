"""
Compare functions between llm4cpp and no_reflect coverage CSVs.
Reads all .csv files under coverage_results/llm4cpp and coverage_results/no_reflect,
collects values from the "Function Name" column (skipping empty or AVERAGE rows),
and reports functions present in one project but not the other.

Creates an output file at coverage_results/functions_diff_llm4cpp_vs_no_reflect.txt
with the detailed lists.

Usage: python compare_project_functions.py
"""

from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parent
COVERAGE_DIR = ROOT / 'coverage_results'
LLM_DIR = COVERAGE_DIR / 'llm4cpp'
CW_DIR = COVERAGE_DIR / 'no_reflect'

OUTPUT_PATH = COVERAGE_DIR / 'functions_diff_llm4cpp_vs_no_reflect.txt'


def load_functions_from_dir(directory: Path):
    """Return a set of function names found in all CSVs under directory."""
    names = set()
    if not directory.exists():
        print(f"Warning: directory {directory} does not exist.")
        return names

    for csv_path in sorted(directory.glob('*.csv')):
        try:
            with csv_path.open(newline='', encoding='utf-8') as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames:
                    continue
                if 'Function Name' not in reader.fieldnames:
                    # try to handle CSVs where header might be localized or missing
                    # skip these files
                    continue
                for row in reader:
                    raw = row.get('Function Name')
                    if raw is None:
                        continue
                    name = str(raw).strip()
                    if not name:
                        continue
                    # skip summary/average rows
                    if name.upper().startswith('AVERAGE'):
                        continue
                    names.add(name)
        except Exception as e:
            print(f"Failed to read {csv_path}: {e}")
    return names


def write_report(llm_only, cw_only, llm_count, cw_count, out_path: Path):
    lines = []
    lines.append(f"llm4cpp CSVs found functions: {llm_count}")
    lines.append(f"no_reflect CSVs found functions: {cw_count}")
    lines.append("")
    lines.append(f"Functions present only in llm4cpp: {len(llm_only)}")
    for n in sorted(llm_only):
        lines.append(n)
    lines.append("")
    lines.append(f"Functions present only in no_reflect: {len(cw_only)}")
    for n in sorted(cw_only):
        lines.append(n)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open('w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines))
        print(f"Wrote detailed report to: {out_path}")
    except Exception as e:
        print(f"Failed to write report to {out_path}: {e}")


def main():
    llm_funcs = load_functions_from_dir(LLM_DIR)
    cw_funcs = load_functions_from_dir(CW_DIR)

    print(f"Found {len(llm_funcs)} unique functions in llm4cpp CSVs")
    print(f"Found {len(cw_funcs)} unique functions in no_reflect CSVs")

    only_in_llm = llm_funcs - cw_funcs
    only_in_cw = cw_funcs - llm_funcs

    print(f"Functions only in llm4cpp: {len(only_in_llm)}")
    print(f"Functions only in no_reflect: {len(only_in_cw)}")

    write_report(only_in_llm, only_in_cw, len(llm_funcs), len(cw_funcs), OUTPUT_PATH)

    # also print a few examples if results are non-empty
    if only_in_llm:
        print('\nSample functions only in llm4cpp:')
        for s in list(sorted(only_in_llm))[:20]:
            print('  ', s)
    if only_in_cw:
        print('\nSample functions only in no_reflect:')
        for s in list(sorted(only_in_cw))[:20]:
            print('  ', s)


if __name__ == '__main__':
    main()

