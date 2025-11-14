import os


def check_missing_ai_logs(base_path):
    """
    Traverse the ai_test_logs folder and detect any function folder
    that does NOT contain an *ai_0_logs* file, matching the suffix:

        *_ai_0_logs.json
    """

    missing = []

    # Loop through main folders (llm4cpp, citywalk, etc.)
    for main_folder in os.listdir(base_path):
        main_path = os.path.join(base_path, main_folder)
        if not os.path.isdir(main_path):
            continue

        # Loop through projects
        for project in os.listdir(main_path):
            project_path = os.path.join(main_path, project)
            if not os.path.isdir(project_path):
                continue

            # Loop through files
            for file_folder in os.listdir(project_path):
                file_path = os.path.join(project_path, file_folder)
                if not os.path.isdir(file_path):
                    continue

                # Loop through function folders
                for func_folder in os.listdir(file_path):
                    func_path = os.path.join(file_path, func_folder)
                    if not os.path.isdir(func_path):
                        continue

                    # Check if a *_ai_0_logs.json file exists
                    has_ai_logs = any(
                        filename.endswith("_ai_0_logs.json")
                        for filename in os.listdir(func_path)
                    )

                    if not has_ai_logs:
                        missing.append({
                            "main_folder": main_folder,
                            "project": project,
                            "file": file_folder,
                            "function": func_folder,
                            "path": func_path
                        })

    return missing


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, "ai_test_logs")

    print(f"Checking for missing *_ai_0_logs.json in: {base_path}")

    missing = check_missing_ai_logs(base_path)

    if not missing:
        print("✅ All function folders contain *_ai_0_logs.json")
        return

    print("\n❌ Missing *_ai_0_logs.json in the following function folders:\n")

    for m in missing:
        print(f"- {m['main_folder']}/{m['project']}/{m['file']}/{m['function']}")
        print(f"  Path: {m['path']}\n")

    print(f"Total missing: {len(missing)}")


if __name__ == "__main__":
    main()
