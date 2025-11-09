import os
import json
import csv

def analyze_test_logs(base_path):
    """
    Analyze test logs and extract coverage information.

    Args:
        base_path: Path to the ai_test_logs folder

    Returns:
        List of dictionaries containing coverage data
    """
    results = []

    # Iterate through main folders (llm4cpp and citywalk)
    for main_folder in os.listdir(base_path):
        main_path = os.path.join(base_path, main_folder)

        if not os.path.isdir(main_path):
            continue

        # Iterate through project folders
        for project_folder in os.listdir(main_path):
            project_path = os.path.join(main_path, project_folder)

            if not os.path.isdir(project_path):
                continue

            # Iterate through file folders within the project
            for file_folder in os.listdir(project_path):
                file_path = os.path.join(project_path, file_folder)

                if not os.path.isdir(file_path):
                    continue

                # Iterate through function folders
                for function_folder in os.listdir(file_path):
                    function_path = os.path.join(file_path, function_folder)

                    if not os.path.isdir(function_path):
                        continue

                    # Find coverage and ai_0_logs files
                    coverage_file = None
                    ai_0_logs_file = None

                    for file in os.listdir(function_path):
                        if file.startswith('coverage_'):
                            coverage_file = os.path.join(function_path, file)
                        elif 'ai_0_logs' in file:
                            ai_0_logs_file = os.path.join(function_path, file)

                    # Process if both files are found
                    if coverage_file and ai_0_logs_file:
                        try:
                            # Read coverage file with utf-8 encoding
                            with open(coverage_file, 'r', encoding='utf-8', errors='ignore') as f:
                                coverage_data = json.load(f)

                            # Read ai_0_logs file with utf-8 encoding
                            with open(ai_0_logs_file, 'r', encoding='utf-8', errors='ignore') as f:
                                ai_0_data = json.load(f)

                            # Extract data
                            function_name = function_folder
                            # Convert file name: _cpp -> .cpp, _h -> .h
                            file_name = file_folder
                            if file_name.endswith('_cpp'):
                                file_name = file_name[:-4] + '.cpp'
                            elif file_name.endswith('_h'):
                                file_name = file_name[:-2] + '.h'
                            # Store project without main folder prefix for display
                            project_name = project_folder
                            # But track main folder separately for organization
                            main_folder_name = main_folder

                            # Helper function to convert coverage values, preserving NaN
                            def to_coverage_value(value):
                                if value is None:
                                    return 0.0
                                if isinstance(value, str):
                                    if value.lower() in ['nan', 'n/a']:
                                        return 'NaN'
                                    if value == '':
                                        return 0.0
                                    try:
                                        return float(value)
                                    except ValueError:
                                        return 0.0
                                return float(value)

                            initial_stmt_cov = to_coverage_value(ai_0_data.get('statementCoverage', 0))
                            initial_branch_cov = to_coverage_value(ai_0_data.get('branchCoverage', 0))

                            total_stmt_cov = to_coverage_value(coverage_data.get('statementCoverage', 0))
                            total_branch_cov = to_coverage_value(coverage_data.get('branchCoverage', 0))

                            # Calculate changes, handling NaN values
                            def calc_change(total, initial):
                                if total == 'NaN' or initial == 'NaN':
                                    return 'NaN'
                                return total - initial

                            stmt_change = calc_change(total_stmt_cov, initial_stmt_cov)
                            branch_change = calc_change(total_branch_cov, initial_branch_cov)

                            results.append({
                                'Function Name': function_name,
                                'File Name': file_name,
                                'Project': project_name,
                                'Main Folder': main_folder_name,
                                'Initial Statement Coverage': initial_stmt_cov,
                                'Total Statement Coverage': total_stmt_cov,
                                'Statement Coverage Change': stmt_change,
                                'Initial Branch Coverage': initial_branch_cov,
                                'Total Branch Coverage': total_branch_cov,
                                'Branch Coverage Change': branch_change
                            })
                        except Exception as e:
                            print(f"Error processing {function_path}: {e}")

    return results

def calculate_averages(results):
    """
    Calculate average values for coverage metrics.
    Skips NaN values when calculating averages.

    Args:
        results: List of result dictionaries

    Returns:
        Dictionary with average values
    """
    if not results:
        return None

    # Helper to filter out NaN values and calculate average
    def avg_skip_nan(values):
        numeric_values = [v for v in values if v != 'NaN' and isinstance(v, (int, float))]
        if not numeric_values:
            return 'NaN'
        return sum(numeric_values) / len(numeric_values)

    avg_initial_stmt = avg_skip_nan([r['Initial Statement Coverage'] for r in results])
    avg_total_stmt = avg_skip_nan([r['Total Statement Coverage'] for r in results])
    avg_stmt_change = avg_skip_nan([r['Statement Coverage Change'] for r in results])

    avg_initial_branch = avg_skip_nan([r['Initial Branch Coverage'] for r in results])
    avg_total_branch = avg_skip_nan([r['Total Branch Coverage'] for r in results])
    avg_branch_change = avg_skip_nan([r['Branch Coverage Change'] for r in results])

    return {
        'Function Name': 'AVERAGE',
        'File Name': '',
        'Project': '',
        'Initial Statement Coverage': avg_initial_stmt,
        'Total Statement Coverage': avg_total_stmt,
        'Statement Coverage Change': avg_stmt_change,
        'Initial Branch Coverage': avg_initial_branch,
        'Total Branch Coverage': avg_total_branch,
        'Branch Coverage Change': avg_branch_change
    }

def export_to_csv_by_project(results, output_base_dir):
    """
    Export results to separate CSV files for each project and a combined file.
    Organizes by main folder (llm4cpp/citywalk).

    Args:
        results: List of result dictionaries
        output_base_dir: Base directory to save output CSV files
    """
    if not results:
        print("No data to export")
        return

    # Group results by main folder and then by project
    main_folders = {}
    for result in results:
        project_name = result['Project']
        main_folder = result['Main Folder']

        if main_folder not in main_folders:
            main_folders[main_folder] = {}

        if project_name not in main_folders[main_folder]:
            main_folders[main_folder][project_name] = []

        main_folders[main_folder][project_name].append(result)

    # Fieldnames without 'Main Folder' (internal use only)
    fieldnames = [
        'Function Name',
        'File Name',
        'Project',
        'Initial Statement Coverage',
        'Total Statement Coverage',
        'Statement Coverage Change',
        'Initial Branch Coverage',
        'Total Branch Coverage',
        'Branch Coverage Change'
    ]

    # Export for each main folder
    for main_folder, projects in main_folders.items():
        # Create directory for this main folder
        main_folder_dir = os.path.join(output_base_dir, main_folder)
        os.makedirs(main_folder_dir, exist_ok=True)

        # Collect all results for this main folder
        main_folder_results = []

        # Export each project to its own CSV file
        for project_name, project_results in projects.items():
            # Create clean results without Main Folder field for CSV export
            clean_project_results = []
            for r in project_results:
                clean_r = {k: v for k, v in r.items() if k != 'Main Folder'}
                clean_project_results.append(clean_r)

            main_folder_results.extend(project_results)

            # Add project average
            avg_row = calculate_averages(project_results)
            if avg_row:
                avg_row['Function Name'] = f'AVERAGE - {project_name}'
                avg_row['Project'] = project_name
                # Remove Main Folder from avg_row
                avg_row.pop('Main Folder', None)
                project_results_with_avg = clean_project_results + [avg_row]
            else:
                project_results_with_avg = clean_project_results

            # Create safe filename
            safe_project_name = project_name.replace('/', '_').replace('\\', '_')
            output_file = os.path.join(main_folder_dir, f'coverage_{safe_project_name}.csv')

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(project_results_with_avg)

            print(f"Exported {len(clean_project_results)} functions for '{project_name}' to {output_file}")

        # Export combined file for this main folder
        main_folder_avg = calculate_averages(main_folder_results)
        if main_folder_avg:
            main_folder_avg['Function Name'] = f'AVERAGE - {main_folder.upper()}'
            main_folder_avg['Project'] = main_folder
            main_folder_avg.pop('Main Folder', None)

            # Clean all results
            clean_all_results = [{k: v for k, v in r.items() if k != 'Main Folder'} for r in main_folder_results]
            main_folder_all_results = clean_all_results + [main_folder_avg]
        else:
            main_folder_all_results = [{k: v for k, v in r.items() if k != 'Main Folder'} for r in main_folder_results]

        combined_file = os.path.join(main_folder_dir, f'coverage_all_{main_folder}.csv')
        with open(combined_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(main_folder_all_results)

        print(f"Exported combined {main_folder} file with {len(main_folder_results)} functions to {combined_file}\n")


def main():
    # Get the base path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, 'ai_test_logs')

    print(f"Analyzing test logs in: {base_path}")

    # Analyze logs
    results = analyze_test_logs(base_path)

    print(f"Found {len(results)} functions with coverage data\n")

    # Create output directory
    output_dir = os.path.join(script_dir, 'coverage_results')
    os.makedirs(output_dir, exist_ok=True)

    # Export to CSV files
    export_to_csv_by_project(results, output_dir)

    # Print summary
    if results:
        # Group by main folder and project for summary
        main_folders = {}
        for result in results:
            project_name = result['Project']
            main_folder = result['Main Folder']

            if main_folder not in main_folders:
                main_folders[main_folder] = {}

            if project_name not in main_folders[main_folder]:
                main_folders[main_folder][project_name] = []

            main_folders[main_folder][project_name].append(result)

        print("\n" + "="*80)
        print("=== SUMMARY ===")
        print("="*80)
        print(f"Total functions analyzed: {len(results)}")

        # For each main folder (llm4cpp, citywalk) print a section
        for main_folder, projects in main_folders.items():
            all_main_folder_results = []
            for project_results in projects.values():
                all_main_folder_results.extend(project_results)

            print(f"\n{'='*80}")
            print(f"=== {main_folder.upper()} ===")
            print(f"{'='*80}")
            print(f"Total functions: {len(all_main_folder_results)}")
            print(f"Number of projects: {len(projects)}")

            # Helper to format values (handle NaN)
            def fmt(val):
                return 'NaN' if val == 'NaN' else f"{val:.2f}%"

            # Print project-level summaries
            for project_name, project_results in projects.items():
                avg = calculate_averages(project_results)

                print(f"\n  {project_name}:")
                print(f"    Functions: {len(project_results)}")
                print(f"    Avg Initial Statement Coverage: {fmt(avg['Initial Statement Coverage'])}")
                print(f"    Avg Total Statement Coverage: {fmt(avg['Total Statement Coverage'])}")
                print(f"    Avg Statement Coverage Change: {fmt(avg['Statement Coverage Change'])}")
                print(f"    Avg Initial Branch Coverage: {fmt(avg['Initial Branch Coverage'])}")
                print(f"    Avg Total Branch Coverage: {fmt(avg['Total Branch Coverage'])}")
                print(f"    Avg Branch Coverage Change: {fmt(avg['Branch Coverage Change'])}")

            # Main folder average
            main_folder_avg = calculate_averages(all_main_folder_results)
            print(f"\n  {main_folder.upper()} AVERAGE:")
            print(f"    Initial Statement Coverage: {fmt(main_folder_avg['Initial Statement Coverage'])}")
            print(f"    Total Statement Coverage: {fmt(main_folder_avg['Total Statement Coverage'])}")
            print(f"    Statement Coverage Change: {fmt(main_folder_avg['Statement Coverage Change'])}")
            print(f"    Initial Branch Coverage: {fmt(main_folder_avg['Initial Branch Coverage'])}")
            print(f"    Total Branch Coverage: {fmt(main_folder_avg['Total Branch Coverage'])}")
            print(f"    Branch Coverage Change: {fmt(main_folder_avg['Branch Coverage Change'])}")

        print("="*80)

if __name__ == '__main__':
    main()
