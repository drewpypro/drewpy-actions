import os
import glob
import subprocess
import requests 

SCRIPT_PATH = "../../yaml-duplicate-validator/yaml-duplicate-validator.py"
REQUESTS_DIR = "requests"
OUTPUTS_DIR = "outputs"
POLICIES_DIR = "policies"
EXISTING_POLICY = os.path.join(POLICIES_DIR, "existing-policy.yaml")
POLICY_LIST = "policies/policy-list.txt"

def get_expected_output_file(request_file):
    base = os.path.splitext(os.path.basename(request_file))[0]
    return os.path.join(OUTPUTS_DIR, base + ".txt")

def needs_existing_policy(request_file):
    return "with-existing" in request_file

def run_test(request_file):
    expected_output_file = get_expected_output_file(request_file)
    if not os.path.exists(expected_output_file):
        print(f"[SKIP] No expected output for {request_file}")
        return "SKIP"
    
    # # DEBUG PRINTS
    # print("\n==================== DEBUG INFO ====================")
    # print(f"Current Working Directory: {os.getcwd()}")
    # print("Files in .:", os.listdir("."))
    # print("Files in requests:", os.listdir(REQUESTS_DIR) if os.path.exists(REQUESTS_DIR) else "No such directory")
    # print("Files in outputs:", os.listdir(OUTPUTS_DIR) if os.path.exists(OUTPUTS_DIR) else "No such directory")
    # print("Files in policies:", os.listdir(POLICIES_DIR) if os.path.exists(POLICIES_DIR) else "No such directory")
    # print(f"About to run: python3 {SCRIPT_PATH} {request_file}{' ' + POLICY_LIST if needs_existing_policy(request_file) else ''}")
    # print(f"Looking for expected output file: {expected_output_file} (Exists: {os.path.exists(expected_output_file)})")
    # print("====================================================\n")
    
    cmd = ["python3", SCRIPT_PATH, request_file]
    if needs_existing_policy(request_file):
        cmd.append(POLICY_LIST)
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Subprocess STDOUT:")
    print(result.stdout)
    print("Subprocess STDERR:")
    print(result.stderr)
    
    actual_output = result.stdout.strip()
    with open(expected_output_file, "r") as f:
        expected_output = f.read().strip()
    
    if actual_output == expected_output:
        print(f"\033[92m[PASS]\033[0m {os.path.basename(request_file)}")
        return "PASS"
    else:
        print(f"\033[91m[FAIL]\033[0m {os.path.basename(request_file)}")
        import difflib
        diff = "\n".join(difflib.unified_diff(
            expected_output.splitlines(),
            actual_output.splitlines(),
            fromfile='expected',
            tofile='actual',
            lineterm=''
        ))
        print("---- DIFF ----")
        print(diff)
        print("--------------")
        return "FAIL"

def main():
    print("==== Running Duplicate Policy Script Tests ====")
    print(f"Current Working Directory at Start: {os.getcwd()}")
    print("Files in .:", os.listdir("."))
    print("Files in requests:", os.listdir(REQUESTS_DIR) if os.path.exists(REQUESTS_DIR) else "No such directory")
    print("Files in outputs:", os.listdir(OUTPUTS_DIR) if os.path.exists(OUTPUTS_DIR) else "No such directory")
    print("Files in policies:", os.listdir(POLICIES_DIR) if os.path.exists(POLICIES_DIR) else "No such directory")
    print("---------------------------------------------------")
    request_files = sorted(glob.glob(os.path.join(REQUESTS_DIR, "*.yaml")))
    print(f"Request files found: {request_files}")
    results = []
    total = len(request_files)
    passed = 0
    failed = 0

    for req in request_files:
        status = run_test(req)
        results.append((os.path.basename(req), status))
        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1

    print("==============================================")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")

    print("\nTest Results:")
    col1 = "Test Case"
    col2 = "Status"
    width1 = max(len(col1), max(len(x[0]) for x in results)) + 2
    width2 = len(col2) + 2
    header = f"{col1:<{width1}} {col2:<{width2}}"
    print(header)
    print("-" * (width1 + width2))

    for filename, status in results:
        status_str = status
        if status == "PASS":
            status_str = "\033[92mPASS\033[0m"
        elif status == "FAIL":
            status_str = "\033[91mFAIL\033[0m"
        elif status == "SKIP":
            status_str = "\033[93mSKIP\033[0m"
        print(f"{filename:<{width1}} {status_str:<{width2}}")

    if failed > 0:
        exit(1)

if __name__ == "__main__":
    main()
