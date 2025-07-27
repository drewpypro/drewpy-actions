import pytest
import yaml
import glob
import subprocess
import difflib
from pathlib import Path

def load_cases_and_ids():
    all_cases = []
    all_ids = []
    for file in glob.glob("test_harness/*.yaml"):
        with open(file) as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, list):
                for case in loaded:
                    all_cases.append(case)
                    case_name = case.get("name") or file
                    all_ids.append(case_name)
            elif isinstance(loaded, dict):
                all_cases.append(loaded)
                case_name = loaded.get("name") or file
                all_ids.append(case_name)
    return all_cases, all_ids

cases, case_ids = load_cases_and_ids()

@pytest.mark.parametrize("case", cases, ids=case_ids)
def test_policy(case, tmp_path, output_mode):
    req_file = tmp_path / "request.yaml"
    req_file.write_text(case["request"])

    validator_path = Path("../../yaml-duplicate-validator/yaml-duplicate-validator.py")

    cmd = ["python3", str(validator_path), str(req_file)]

    if case.get("existing") and case["existing"] not in [None, "", "null"]:
        existing_file = tmp_path / "existing-policy.yaml"
        existing_file.write_text(case["existing"])
        cmd.append(str(existing_file))

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    actual_output = result.stdout.strip()
    expected_output = case["expected_output"].strip()

    if expected_output != actual_output:
        if output_mode in ("actual", "all"):
            print("\nEXPECTED OUTPUT:\n")
            print(expected_output)
            print("\nACTUAL OUTPUT:\n")
            print(actual_output)
        if output_mode in ("ndiff", "all"):
            print("\nNDIFF (inline):\n")
            for line in difflib.ndiff(expected_output.splitlines(), actual_output.splitlines()):
                if line.startswith('- ') or line.startswith('+ '):
                    print(line)
        if output_mode in ("unified", "all"):
            print("\nUNIFIED DIFF (patch style):\n")
            print('\n'.join(difflib.unified_diff(
                expected_output.splitlines(),
                actual_output.splitlines(),
                fromfile='expected', tofile='actual', lineterm=''
            )))
        assert False, "Output mismatch, see above diff(s)"
