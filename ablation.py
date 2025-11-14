import os
import csv
from analyze_coverage import analyze_test_logs, calculate_averages

MAIN_FOLDERS = ["llm4cpp", "no_reflect", "no_context"]


def round2(x):
    if x is None:
        return None
    try:
        return round(x, 2)
    except:
        return x


def avg_row(values):
    """Tính average của cả hàng (list), bỏ None, trả về round(2)."""
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return round2(sum(nums) / len(nums))


def load_project_file_averages(base_path):
    data = {}
    results = analyze_test_logs(base_path)

    for r in results:
        mf = r['Main Folder']
        proj = r['Project']
        fname = r['File Name']

        if mf not in MAIN_FOLDERS:
            continue

        data.setdefault(mf, {})
        data[mf].setdefault(proj, {})
        data[mf][proj].setdefault(fname, [])
        data[mf][proj][fname].append(r)

    for mf in data:
        for proj in data[mf]:
            for fname in data[mf][proj]:
                data[mf][proj][fname] = calculate_averages(data[mf][proj][fname])

    return data


def collect_all_files(data):
    files = set()
    for mf in data.values():
        for proj in mf.values():
            for fname in proj:
                files.add(fname)
    return sorted(files)


def average_across_projects(data, mf, fname):
    rows = []
    for proj in data[mf]:
        if fname in data[mf][proj]:
            rows.append(data[mf][proj][fname])
    if not rows:
        return None
    return calculate_averages(rows)


def create_ablation_tables(base_path, output_path):

    data = load_project_file_averages(base_path)
    all_files = collect_all_files(data)

    row_llm_stmt, row_llm_branch = [], []
    row_iter_stmt, row_iter_branch = [], []
    row_reflect_stmt, row_reflect_branch = [], []
    row_nocontext_stmt, row_nocontext_branch = [], []

    for f in all_files:
        llm = average_across_projects(data, "llm4cpp", f)
        ref = average_across_projects(data, "no_reflect", f)
        nct = average_across_projects(data, "no_context", f)

        llm_stmt = llm["Total Statement Coverage"] if llm else None
        llm_branch = llm["Total Branch Coverage"] if llm else None

        llm_init_stmt = llm["Initial Statement Coverage"] if llm else None
        llm_init_branch = llm["Initial Branch Coverage"] if llm else None

        wo_iter_stmt = - (llm_stmt - llm_init_stmt) if (llm_stmt and llm_init_stmt) else None
        wo_iter_branch = - (llm_branch - llm_init_branch) if (llm_branch and llm_init_branch) else None

        ref_stmt = (ref["Total Statement Coverage"] - llm_stmt) if (llm and ref) else None
        ref_branch = (ref["Total Branch Coverage"] - llm_branch) if (llm and ref) else None

        nct_stmt = (nct["Total Statement Coverage"] - llm_stmt) if (llm and nct) else None
        nct_branch = (nct["Total Branch Coverage"] - llm_branch) if (llm and nct) else None

        row_llm_stmt.append(round2(llm_stmt))
        row_llm_branch.append(round2(llm_branch))

        row_iter_stmt.append(round2(wo_iter_stmt))
        row_iter_branch.append(round2(wo_iter_branch))

        row_reflect_stmt.append(round2(ref_stmt))
        row_reflect_branch.append(round2(ref_branch))

        row_nocontext_stmt.append(round2(nct_stmt))
        row_nocontext_branch.append(round2(nct_branch))

    os.makedirs(output_path, exist_ok=True)

    # ----------- STATEMENT TABLE --------------
    with open(os.path.join(output_path, "ablation_statement.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([""] + all_files + ["Avg"])

        w.writerow(["llm4cpp"] + row_llm_stmt + [avg_row(row_llm_stmt)])
        w.writerow(["W/o iteration"] + row_iter_stmt + [avg_row(row_iter_stmt)])
        w.writerow(["W/o reflect"] + row_reflect_stmt + [avg_row(row_reflect_stmt)])
        w.writerow(["W/o context"] + row_nocontext_stmt + [avg_row(row_nocontext_stmt)])

    # ----------- BRANCH TABLE ------------------
    with open(os.path.join(output_path, "ablation_branch.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([""] + all_files + ["Avg"])

        w.writerow(["llm4cpp"] + row_llm_branch + [avg_row(row_llm_branch)])
        w.writerow(["W/o iteration"] + row_iter_branch + [avg_row(row_iter_branch)])
        w.writerow(["W/o reflect"] + row_reflect_branch + [avg_row(row_reflect_branch)])
        w.writerow(["W/o context"] + row_nocontext_branch + [avg_row(row_nocontext_branch)])

    print("Generated:")
    print(" - ablation_statement.csv")
    print(" - ablation_branch.csv")



if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(script_dir, "ai_test_logs")
    out = os.path.join(script_dir, "coverage_results")
    create_ablation_tables(base, out)
