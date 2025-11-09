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
        combined_rows = []
        for file_name, info in combined_file_groups.items():
            funcs = info['funcs']
            projects_set = info['projects']
            avg_row = calculate_averages(funcs)
            if avg_row:
                avg_row['File Name'] = file_name
                # For combined we set Project to the contributing project names (comma-separated)
                proj_list = sorted(projects_set)
                avg_row['Project'] = ','.join(proj_list) if proj_list else ''
                avg_row.pop('Main Folder', None)

                filtered = {k: avg_row.get(k, '') for k in FIELDNAMES}
                combined_rows.append(filtered)

        combined_file = os.path.join(main_folder_dir, f'coverage_all_by_file_{main_folder}.csv')
        with open(combined_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(combined_rows)

        print(f"Exported combined file-by-file for {main_folder} to {combined_file}\n")


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
