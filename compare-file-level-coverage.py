import os
import csv
from analyze_coverage import analyze_test_logs, calculate_averages

"""
Produce CSV exports like `analyze_coverage.py` but compute averages per FILE
(rather than per project). For each project we will append an `AVERAGE - <file>`
row summarizing the functions in that file. We also produce a combined file per
main folder where per-file averages across all projects under that main folder
are appended.

This variant writes only one row per file (the average row). Individual function
rows are omitted as requested.

Additionally, produce a comparison CSV that compares two main folders
(e.g. llm4cpp vs no_reflect) file-by-file side-by-side for total statement and
branch coverage.

The comparison table now contains a "Project" column next to "File Name" so
that identical file names in different projects are distinguished.
"""

FIELDNAMES = [
    'File Name',
    'Project',
    'Initial Statement Coverage',
    'Total Statement Coverage',
    'Statement Coverage Change',
    'Initial Branch Coverage',
    'Total Branch Coverage',
    'Branch Coverage Change'
]


def export_to_csv_by_file(results, output_base_dir):
    if not results:
        print("No data to export")
        return

    # Group by main folder -> project -> file name -> list of results
    main_folders = {}
    for r in results:
        mf = r['Main Folder']
        proj = r['Project']
        fname = r['File Name']

        main_folders.setdefault(mf, {})
        main_folders[mf].setdefault(proj, {})
        main_folders[mf][proj].setdefault(fname, [])
        main_folders[mf][proj][fname].append(r)

    for main_folder, projects in main_folders.items():
        main_folder_dir = os.path.join(output_base_dir, main_folder)
        os.makedirs(main_folder_dir, exist_ok=True)

        # For combined/main-folder level per-file averages
        # combined_file_groups maps file_name -> {'funcs': [...], 'projects': set([...])}
        combined_file_groups = {}

        # Export per-project CSVs
        for project_name, files in projects.items():
            rows_to_write = []

            for file_name, funcs in files.items():
                # Compute the file-level average for this file (within this project)
                avg_row = calculate_averages(funcs)
                if avg_row:
                    # Set file and project in the average row
                    avg_row['File Name'] = file_name
                    avg_row['Project'] = project_name
                    # Remove Main Folder if present
                    avg_row.pop('Main Folder', None)

                    # Only keep fields matching FIELDNAMES
                    filtered = {k: avg_row.get(k, '') for k in FIELDNAMES}
                    rows_to_write.append(filtered)

                # Add to combined grouping across this main folder and track which projects contributed
                combined_file_groups.setdefault(file_name, {'funcs': [], 'projects': set()})
                combined_file_groups[file_name]['funcs'].extend(funcs)
                combined_file_groups[file_name]['projects'].add(project_name)

            safe_project_name = project_name.replace('/', '_').replace('\\', '_')
            output_file = os.path.join(main_folder_dir, f'coverage_{safe_project_name}_by_file.csv')
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(rows_to_write)

            print(f"Exported per-file averages for project '{project_name}' to {output_file}")

        # Create combined file for this main folder: per-file averages across projects
        # Use (project, file_name) as the unique key so identical file names in different
        # projects are NOT merged into a single row.
        combined_rows = []
        # combined_file_groups currently maps file_name -> {'funcs': [...], 'projects': set([...])}
        # We'll iterate projects -> files to ensure (project, file) distinction
        for project_name, files in projects.items():
            for file_name, funcs in files.items():
                avg_row = calculate_averages(funcs)
                if not avg_row:
                    continue
                avg_row['File Name'] = file_name
                # For combined we set Project to the single contributing project name
                avg_row['Project'] = project_name
                avg_row.pop('Main Folder', None)

                filtered = {k: avg_row.get(k, '') for k in FIELDNAMES}
                combined_rows.append(filtered)

        # Optionally sort combined_rows for stable output (by project then file)
        combined_rows.sort(key=lambda r: (str(r.get('Project','')).lower(), str(r.get('File Name','')).lower()))

        combined_file = os.path.join(main_folder_dir, f'coverage_all_by_file_{main_folder}.csv')
        with open(combined_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(combined_rows)

        print(f"Exported combined file-by-file for {main_folder} to {combined_file}\n")


    # After exporting per-main-folder files, create a compare CSV between two main folders
    create_main_folder_comparison(main_folders, output_base_dir)


def create_main_folder_comparison(main_folders, output_base_dir):
    """
    Create a comparison CSV that lists, for each (project, file name) pair, the total
    statement and total branch coverage for two main folders side-by-side.

    COLUMN ORDER (required):
      File Name, Project,
      no_reflect Total Statement Coverage,
      llm4cpp Total Statement Coverage,
      no_reflect Total Branch Coverage,
      llm4cpp Total Branch Coverage

    This function distinguishes identical file names in different projects by
    treating (project, file) as the unique key.
    """

    if not main_folders:
        return

    # Ensure no_reflect and llm4cpp are the two in correct order
    if 'no_reflect' in main_folders and 'llm4cpp' in main_folders:
        mf_city, mf_llm = 'no_reflect', 'llm4cpp'
    else:
        # Fallback: pick first two (sorted)
        mf_names = sorted(main_folders.keys())
        if len(mf_names) < 2:
            print("Not enough main folders to compare.")
            return
        # Use first as "no_reflect-like" and second as "llm4cpp-like"
        mf_city, mf_llm = mf_names[0], mf_names[1]

    # Build mapping: main_folder -> (project, file_name) -> list of funcs (across all projects)
    mf_key_funcs = {mf_city: {}, mf_llm: {}}
    for mf, projects in ((mf_city, main_folders.get(mf_city, {})), (mf_llm, main_folders.get(mf_llm, {}))):
        for proj_name, files in projects.items():
            for fname, funcs in files.items():
                key = (proj_name, fname)  # distinguishes same file names across projects
                mf_key_funcs[mf].setdefault(key, [])
                mf_key_funcs[mf][key].extend(funcs)

    # Union of (project, file) keys across both main folders
    keys = set(list(mf_key_funcs[mf_city].keys()) + list(mf_key_funcs[mf_llm].keys()))

    # Column order EXACTLY as requested
    compare_fieldnames = [
        'File Name',
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

    # Sort keys by project then file for stable output
    for proj_name, fname in sorted(keys, key=lambda x: (x[0].lower(), x[1].lower())):
        mf_city_funcs = mf_key_funcs[mf_city].get((proj_name, fname), [])
        mf_llm_funcs = mf_key_funcs[mf_llm].get((proj_name, fname), [])

        mf_city_avg = calculate_averages(mf_city_funcs) if mf_city_funcs else None
        mf_llm_avg = calculate_averages(mf_llm_funcs) if mf_llm_funcs else None

        row = {
            'File Name': fname,
            'Project': proj_name,
            f'{mf_city} Total Statement Coverage': fmt_total_stmt(mf_city_avg),
            f'{mf_llm} Total Statement Coverage': fmt_total_stmt(mf_llm_avg),
            f'{mf_city} Total Branch Coverage': fmt_total_branch(mf_city_avg),
            f'{mf_llm} Total Branch Coverage': fmt_total_branch(mf_llm_avg)
        }
        compare_rows.append(row)

    # Write comparison CSV to the output_base_dir
    safe_city = mf_city.replace('/', '_').replace('\\', '_')
    safe_llm = mf_llm.replace('/', '_').replace('\\', '_')
    compare_file = os.path.join(output_base_dir, f'coverage_compare_{safe_city}_vs_{safe_llm}_by_file.csv')
    with open(compare_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=compare_fieldnames)
        writer.writeheader()
        writer.writerows(compare_rows)

    print(f"Comparison table written to: {compare_file}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, 'ai_test_logs')

    print(f"Analyzing test logs in: {base_path}")
    results = analyze_test_logs(base_path)
    print(f"Found {len(results)} functions with coverage data\n")

    output_dir = os.path.join(script_dir, 'coverage_results')
    os.makedirs(output_dir, exist_ok=True)

    export_to_csv_by_file(results, output_dir)

    print('Done.')


if __name__ == '__main__':
    main()
