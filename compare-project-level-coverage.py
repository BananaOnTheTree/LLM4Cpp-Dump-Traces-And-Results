import os
import csv
from analyze_coverage import analyze_test_logs, calculate_averages

"""
Project-level coverage export and comparison.

Produces per-project CSVs (one average row per project), one combined CSV per
main folder listing all projects, and a comparison CSV comparing projects
between two main folders (e.g. no_reflect vs llm4cpp).

Column layout for per-project files / combined files:
  Project, Initial Statement Coverage, Total Statement Coverage,
  Statement Coverage Change, Initial Branch Coverage, Total Branch Coverage,
  Branch Coverage Change

Comparison CSV columns (exact order):
  Project,
  <mf_city> Total Statement Coverage,
  <mf_llm> Total Statement Coverage,
  <mf_city> Total Branch Coverage,
  <mf_llm> Total Branch Coverage
"""

PROJECT_FIELDNAMES = [
    'Project',
    'Initial Statement Coverage',
    'Total Statement Coverage',
    'Statement Coverage Change',
    'Initial Branch Coverage',
    'Total Branch Coverage',
    'Branch Coverage Change'
]


def export_to_csv_by_project(results, output_base_dir):
    if not results:
        print("No data to export")
        return

    # Group by main folder -> project -> list of func results (across files)
    main_folders = {}
    for r in results:
        mf = r['Main Folder']
        proj = r['Project']

        main_folders.setdefault(mf, {})
        main_folders[mf].setdefault(proj, [])
        # store the function-level row (so calculate_averages can compute project averages)
        main_folders[mf][proj].append(r)

    # For each main folder, write per-project CSVs and a combined CSV for that main folder
    for main_folder, projects in main_folders.items():
        main_folder_dir = os.path.join(output_base_dir, main_folder)
        os.makedirs(main_folder_dir, exist_ok=True)

        # Per-project CSVs (one CSV per project, containing a single average row)
        for project_name, funcs in projects.items():
            avg_row = calculate_averages(funcs)
            if not avg_row:
                print(f"No data to compute averages for project '{project_name}' in '{main_folder}'")
                continue

            # Ensure Project field set and remove Main Folder if present
            avg_row['Project'] = project_name
            avg_row.pop('Main Folder', None)

            # Filter to project-level fields
            filtered = {k: avg_row.get(k, '') for k in PROJECT_FIELDNAMES}

            safe_project_name = project_name.replace('/', '_').replace('\\', '_')
            output_file = os.path.join(main_folder_dir, f'coverage_{safe_project_name}_project_avg.csv')
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=PROJECT_FIELDNAMES)
                writer.writeheader()
                writer.writerow(filtered)

            print(f"Exported project average for '{project_name}' to {output_file}")

        # Combined CSV listing all projects under this main folder
        combined_rows = []
        for project_name, funcs in sorted(projects.items(), key=lambda x: x[0].lower()):
            avg_row = calculate_averages(funcs)
            if not avg_row:
                continue
            avg_row['Project'] = project_name
            avg_row.pop('Main Folder', None)
            filtered = {k: avg_row.get(k, '') for k in PROJECT_FIELDNAMES}
            combined_rows.append(filtered)

        combined_file = os.path.join(main_folder_dir, f'coverage_all_projects_{main_folder}.csv')
        with open(combined_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=PROJECT_FIELDNAMES)
            writer.writeheader()
            writer.writerows(combined_rows)

        print(f"Exported combined per-project file for {main_folder} to {combined_file}\n")

    # After exporting per-main-folder project files, create a project-level comparison CSV
    create_main_folder_comparison_projects(main_folders, output_base_dir)


def create_main_folder_comparison_projects(main_folders, output_base_dir):
    """
    Create a comparison CSV that lists, for each project, the total statement and
    total branch coverage for two main folders side-by-side.

    COLUMN ORDER (required):
      Project,
      <mf_city> Total Statement Coverage,
      <mf_llm> Total Statement Coverage,
      <mf_city> Total Branch Coverage,
      <mf_llm> Total Branch Coverage
    """

    if not main_folders:
        return

    # Ensure we pick two main folders in a deterministic order similar to original logic
    if 'no_reflect' in main_folders and 'llm4cpp' in main_folders:
        mf_city, mf_llm = 'no_reflect', 'llm4cpp'
    else:
        mf_names = sorted(main_folders.keys())
        if len(mf_names) < 2:
            print("Not enough main folders to compare.")
            return
        mf_city, mf_llm = mf_names[0], mf_names[1]

    # Build mapping: main_folder -> project -> list of funcs
    mf_project_funcs = {mf_city: {}, mf_llm: {}}
    for mf, projects in ((mf_city, main_folders.get(mf_city, {})), (mf_llm, main_folders.get(mf_llm, {}))):
        for proj_name, funcs in projects.items():
            mf_project_funcs[mf][proj_name] = list(funcs)  # clone list

    # Union of project names across both main folders
    projects_union = set(list(mf_project_funcs[mf_city].keys()) + list(mf_project_funcs[mf_llm].keys()))

    compare_fieldnames = [
        'Project',
        f'{mf_city} Total Statement Coverage',
        f'{mf_llm} Total Statement Coverage',
        f'{mf_city} Total Branch Coverage',
        f'{mf_llm} Total Branch Coverage'
    ]

    def fmt_total_stmt(avg_row):
        if not avg_row:
            return ''
        v = avg_row.get('Total Statement Coverage', '')
        return v if v == 'NaN' else (f"{v:.2f}" if isinstance(v, float) else v)

    def fmt_total_branch(avg_row):
        if not avg_row:
            return ''
        v = avg_row.get('Total Branch Coverage', '')
        return v if v == 'NaN' else (f"{v:.2f}" if isinstance(v, float) else v)

    compare_rows = []

    for proj_name in sorted(projects_union, key=lambda s: s.lower()):
        mf_city_funcs = mf_project_funcs[mf_city].get(proj_name, [])
        mf_llm_funcs = mf_project_funcs[mf_llm].get(proj_name, [])

        mf_city_avg = calculate_averages(mf_city_funcs) if mf_city_funcs else None
        mf_llm_avg = calculate_averages(mf_llm_funcs) if mf_llm_funcs else None

        row = {
            'Project': proj_name,
            f'{mf_city} Total Statement Coverage': fmt_total_stmt(mf_city_avg),
            f'{mf_llm} Total Statement Coverage': fmt_total_stmt(mf_llm_avg),
            f'{mf_city} Total Branch Coverage': fmt_total_branch(mf_city_avg),
            f'{mf_llm} Total Branch Coverage': fmt_total_branch(mf_llm_avg)
        }
        compare_rows.append(row)

    safe_city = mf_city.replace('/', '_').replace('\\', '_')
    safe_llm = mf_llm.replace('/', '_').replace('\\', '_')
    compare_file = os.path.join(output_base_dir, f'coverage_compare_projects_{safe_city}_vs_{safe_llm}.csv')
    with open(compare_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=compare_fieldnames)
        writer.writeheader()
        writer.writerows(compare_rows)

    print(f"Project-level comparison table written to: {compare_file}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, 'ai_test_logs')

    print(f"Analyzing test logs in: {base_path}")
    results = analyze_test_logs(base_path)
    print(f"Found {len(results)} functions with coverage data\n")

    output_dir = os.path.join(script_dir, 'coverage_results')
    os.makedirs(output_dir, exist_ok=True)

    export_to_csv_by_project(results, output_dir)

    print('Done.')


if __name__ == '__main__':
    main()
