# Quick Start Guide

## Prerequisites

1. Python 3.8 or higher installed
2. AWS CLI configured with credentials
3. Terraform installed (optional, for applying the generated configuration)

## Installation

1. Extract the tool to a directory
2. Open terminal/command prompt in that directory
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Windows

```powershell
# Check version
python run_cfmigrate.py --version

# Run migration
python run_cfmigrate.py convert-all --regions us-east-1 --output ./terraform
```

### Linux/macOS

```bash
# Check version
python run_cfmigrate.py --version

# Run migration
python run_cfmigrate.py convert-all --regions us-east-1 --output ./terraform
```

## What the tool does

1. **Discovers** all CloudFormation stacks and AWS resources in specified regions
2. **Converts** them to Terraform configuration files
3. **Generates** import scripts to bring existing resources under Terraform management
4. **Creates** a complete Terraform project with modules and variables

## After running the tool

1. Navigate to the output directory: `cd terraform`
2. Initialize Terraform: `terraform init`
3. Run the import script to import existing resources
4. Verify with: `terraform plan` (should show no changes)

## Support

- See `readme.md` for detailed documentation
- Check `docs/troubleshooting.md` for common issues
- Review `docs/configuration.md` for advanced options

