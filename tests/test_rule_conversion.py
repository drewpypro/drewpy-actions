import unittest
import pandas as pd
import os
import json
import logging
from rule_conversion import process_rules, validate_rules, CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TestRuleConversion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.test_output_dir = "./tests/sg_rules_test"
        cls.test_cases_dir = "./tests/test_cases"
        cls.error_output_dir = "./tests/error_outputs"  # Directory to save error outputs
        os.makedirs(cls.test_output_dir, exist_ok=True)
        os.makedirs(cls.error_output_dir, exist_ok=True)
        CONFIG["OUTPUT_DIR"] = cls.test_output_dir  # Dynamically update output directory for testing
        logging.info(f"Test output directory set to {cls.test_output_dir}")
        logging.info(f"Error output directory set to {cls.error_output_dir}")

    def capture_errors(self, test_name, df):
        """Validate rules and write errors to a file for review."""
        issues = validate_rules(df)
        if issues:
            error_file = os.path.join(self.error_output_dir, f"{test_name}_errors.txt")
            with open(error_file, "w") as f:
                for issue_type, rows in issues.items():
                    f.write(f"The following issues were found for {issue_type.replace('_', ' ').title()}:\n\n")
                    for row in rows:
                        f.write(f"Error: {row['error']}\nRow data: {row['row']}\n\n")
            logging.info(f"Errors for {test_name} written to {error_file}")
        return issues

    def test_valid_rules(self):
        """Test with valid rules to ensure successful processing."""
        input_file = os.path.join(self.test_cases_dir, "valid_rules.csv")
        df = pd.read_csv(input_file).fillna("null")
        issues = self.capture_errors("valid_rules", df)
        self.assertFalse(issues, f"Validation failed for valid rules: {issues}")

    def test_invalid_rules(self):
        """Test with invalid rules to ensure detection."""
        input_file = os.path.join(self.test_cases_dir, "invalid_rules.csv")
        df = pd.read_csv(input_file).fillna("null")
        issues = self.capture_errors("invalid_rules", df)
        self.assertTrue(issues, "Invalid rules were not detected as expected")

    def test_duplicate_rules(self):
        """Test with duplicate rules to ensure detection."""
        input_file = os.path.join(self.test_cases_dir, "duplicate_rules.csv")
        df = pd.read_csv(input_file).fillna("null")
        issues = self.capture_errors("duplicate_rules", df)
        self.assertIn("duplicates", issues, "Duplicate rules were not detected")

    def test_invalid_ports(self):
        """Test with invalid port ranges to ensure detection."""
        input_file = os.path.join(self.test_cases_dir, "invalid_ports.csv")
        df = pd.read_csv(input_file).fillna("null")
        issues = self.capture_errors("invalid_ports", df)
        self.assertIn("port_validation", issues, "Invalid port ranges were not flagged")

    def test_invalid_ip(self):
        """Test with invalid IPs to ensure detection."""
        input_file = os.path.join(self.test_cases_dir, "invalid_ip.csv")
        df = pd.read_csv(input_file).fillna("null")
        issues = self.capture_errors("invalid_ip", df)
        self.assertIn("ip_validation", issues, "Invalid IPs were not flagged")

    def test_process_rules(self):
        """Test full rule processing."""
        input_file = os.path.join(self.test_cases_dir, "valid_rules.csv")
        process_rules(input_file)
        output_files = os.listdir(self.test_output_dir)
        self.assertTrue(len(output_files) > 0, "No output files were generated")
        
        # Verify specific output
        expected_file = os.path.join(self.test_output_dir, "worker_nodes.json")
        self.assertTrue(os.path.exists(expected_file), "Expected output file is missing")
        with open(expected_file) as f:
            rules = json.load(f)
        self.assertGreater(len(rules), 0, "Processed rules are empty")

    # @classmethod
    # def tearDownClass(cls):
    #     """Clean up test environment."""
    #     if os.path.exists(cls.test_output_dir):
    #         for file in os.listdir(cls.test_output_dir):
    #             os.remove(os.path.join(cls.test_output_dir, file))
    #         os.rmdir(cls.test_output_dir)
    #     if os.path.exists(cls.error_output_dir):
    #         for file in os.listdir(cls.error_output_dir):
    #             os.remove(os.path.join(cls.error_output_dir, file))
    #         os.rmdir(cls.error_output_dir)


if __name__ == "__main__":
    unittest.main()
