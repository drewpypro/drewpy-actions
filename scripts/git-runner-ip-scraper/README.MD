# git-runner-ip-scraper

## Goal

Restrict API keys associated with Cloudflare and other public cloud resources to specific GitHub Actions runner IPs for purposes of mitigating blast radius of exposed API keys and secrets.

### The Problem

GitHub's meta API (`https://api.github.com/meta`) provides **5,436 subnet ranges** that GitHub Actions runners can use. This is too many to be effective for WAF rules or API token restrictions - it would essentially allow access from most of Azure's IP space.

### The Solution

Instead of allowing all possible GitHub runner IPs, this tool **tracks only the actual IPs** that your specific workflows use over time. By running daily, it builds a minimal, targeted list of IPs (typically 5-20) that can be used for tight security controls.

## How It Works

1. **Daily Execution**: Workflow runs daily via GitHub Actions cron
2. **IP Detection**: Curls `ifconfig.me` to get current runner's IP address
3. **Map Management**: Maintains a JSON map of `{"date": "ip"}` entries
4. **Automatic Rotation**: Removes entries older than 30 days
5. **Output Generation**: Creates Terraform-compatible variable files
6. **Commit & Push**: Automatically commits updated files to repo

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow (runs daily)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Detect current git-runner IP (ifconfig.me)                │  │
│  │ 2. Load existing git-runner-ip-map.json                      │  │
│  │ 3. Remove entries > 30 days old                          │  │
│  │ 4. Add today's IP                                        │  │
│  │ 5. Generate Terraform outputs                            │  │
│  │ 6. Commit and push to main                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
           ┌────────────────────────────────────────────┐
           │  Repository Files (committed to main)       │
           ├────────────────────────────────────────────┤
           │  • git-runner-ip-map.json          (state)     │
           │  • git-runner-ips.json             (API)       │
           │  • git-runner-ips.auto.tfvars (TF)      │
           └────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐      ┌──────────────────────────┐
        │ Cloudflare Repo        │      │ AWS Testing Repo         │
        │ Uses git-runner-ips.tf │      │ Uses git-runner-ips.json │
        │ for WAF & API tokens   │      │ for security groups      │
        └───────────────────────┘      └──────────────────────────┘
```

## Output Files

### 1. `git-runner-ip-map.json` (Primary State)
Map of dates to IPs - this is the source of truth:
```json
{
  "2025-10-20": "1.2.3.4",
  "2025-11-21": "5.6.7.8",
  "2025-11-22": "9.10.11.12"
}
```

### 2. `git-runner-ips.json` (API-Friendly)
Simple list with metadata:
```json
{
  "runner_ips": [
    "1.2.3.4",
    "5.6.7.8",
    "9.10.11.12"
  ],
  "count": 3,
  "last_updated": "2025-11-22 11:00:00 UTC"
}
```

### 3. `git-runner-ips.auto.tfvars` (Terraform - Auto-loaded)
Variable assignments that Terraform automatically loads:
```hcl
# GitHub Actions Runner IPs
# Auto-generated - do not edit manually
# Last updated: 2025-11-22 11:00:00 UTC
# This file is automatically loaded by Terraform

git_runner_ips = [
  "1.2.3.4",
  "5.6.7.8",
  "9.10.11.12"
]

git_runner_ip_map = {
  "2025-10-20": "1.2.3.4",
  "2025-11-21": "5.6.7.8",
  "2025-11-22": "9.10.11.12"
}
```

**Note**: `.auto.tfvars` files are automatically loaded by Terraform. You just need to declare the variables in your Terraform code (see usage examples below).

## Usage

### Local Testing

```bash
cd git-runner-ip-scraper

# Manual test
python3 git-runner-ip-scraper.py --test-ip "20.14.5.100"

# Test with different retention period
python3 git-runner-ip-scraper.py --retention-days 7
```

### In GitHub Actions (Automated)

The workflow `.github/workflows/git-runner-ip-scraper.yml` runs automatically:
- **Schedule**: Daily at midnight UTC (or as desired)
- **Trigger**: Also runs on workflow_dispatch or when python code changes

### Consuming in Other Repos

#### Option 1: HTTP Fetch (Recommended)
```bash
# In your Terraform/workflow
curl -sL https://raw.githubusercontent.com/drewpypro/drewpy-actions/main/scripts/git-runner-ip-scraper/git-runner-ips.json
```

#### Option 2: Git Submodule
```bash
git submodule add https://github.com/drewpypro/drewpy-actions scripts/git-runner-ip-scraper
```

#### Option 3: Terraform HTTP Data Source
```hcl
data "http" "git_runner_ips" {
  url = "https://raw.githubusercontent.com/drewpypro/drewpy-actions/main/scripts/git-runner-ip-scraper/git-runner-ips.json"
}

locals {
  git_runner_ips = jsondecode(data.http.git_runner_ips.response_body).git_runner_ips
}

# Use in WAF
resource "cloudflare_waf_rule" "allow_git_runners" {
  # ... use local.git_runner_ips
}
```

## Example: Cloudflare WAF with Runner IPs

### Option 1: Using .auto.tfvars File (Recommended)

In your Terraform repo, fetch the `.auto.tfvars` file:

```bash
# In your Terraform repo's GitHub Actions workflow
- name: Fetch GitHub Runner IPs
  run: |
    curl -sL https://raw.githubusercontent.com/drewpypro/drewpy-actions/main/scripts/git-runner-ip-scraper/git-runner-ips.auto.tfvars \
      -o git-runner-ips.auto.tfvars
```

Then in your Terraform code, just declare the variables:

```hcl
# variables.tf
variable "git_runner_ips" {
  type        = list(string)
  description = "GitHub Actions runner IPs"
}

variable "git_runner_ip_map" {
  type        = map(string)
  description = "Map of dates to runner IPs"
}

# main.tf - use the variables directly
resource "cloudflare_waf_rule" "allow_github_actions" {
  zone_id     = var.zone_id
  description = "Allow GitHub Actions runners"

  filter      = "ip.src in {${join(" ", var.git_runner_ips)}}"
  action      = "allow"
}

resource "cloudflare_api_token" "github_actions" {
  name = "github-actions-token"

  condition {
    request_ip {
      in = var.git_runner_ips
    }
  }
}
```

### Option 2: Using HTTP Data Source

```hcl
data "http" "git_runner_ips" {
  url = "https://raw.githubusercontent.com/drewpypro/drewpy-actions/main/scripts/git-runner-ip-scraper/runner-ips.json"
}

locals {
  git_runner_ips = jsondecode(data.http.git_runner_ips.response_body).runner_ips
}

resource "cloudflare_waf_rule" "allow_git_actions" {
  zone_id     = var.zone_id
  description = "Allow GitHub Actions runners"

  filter      = "ip.src in {${join(" ", local.git_runner_ips)}}"
  action      = "allow"
}
```

## Command Line Options

```
--map-file TEXT          Path to runner IP map file (default: runner-ip-map.json)
--retention-days INT     Number of days to retain IPs (default: 30)
--output-dir PATH        Directory for output files (default: .)
--test-ip IP            Test with a specific IP instead of detecting
```
