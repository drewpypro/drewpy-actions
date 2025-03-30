# Drewpy Actions
![drewpy-actions](./img/drewpy-actions.png)

# Repo Structure
```
drewpy-actions/
└── .github/
    ├── workflows/
    │   └── firewall_rule_issue_workflow.yml
    └── ISSUE_TEMPLATE/
        └── firewall_rule_request.yml
├── rule_validation/
    ├── action.yml
    ├── validate.py
    └── requirements.txt
├── rule_conversion/
    ├── action.yml
    ├── convert.py
    └── requirements.txt
```

# Rule Validation and Conversion Action workflow
1. issue workflow
    * user submits issue with csv in declared and required format
    * issue validates format and rejects or allows 
    * issue creates new branch and PR and appends input to the firewall_rules.csv 
2. validation workflow
    * runs validate.py on the newly merged firewall_rules.csv
    * if fails, issue responds to user with script error (not sure how the feedback is handled here)
    * if succeeds, then allows next step to run
3. conversion workflow
    * loads existing sg_rules folder and runs convert.py on the newly merged and validated firewall_rules.csv 
    * creates/updates existing sg_rules file in branch
4. PR workflow
    * PR is created.
    * Discord is notified. 
