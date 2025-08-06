# Installation and Usage Guide

##  Installation

### Prerequisites

Before installing the AWS CloudFormation to Terraform Migrator, ensure you have:

- **Python 3.8+** installed
- **AWS CLI** configured with appropriate credentials
- **Terraform 1.0+** installed (for running generated code)
- **Git** (for cloning the repository)

### Step 1: Install Python Dependencies

```bash
# Check Python version
python --version  # Should be 3.8 or higher

# Install pip if not available
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

### Step 2: Extract and Install the Tool

```bash
# Extract the zip file
unzip aws-cf-terraform-migrator-v1.0.0-final.zip
cd aws-cf-terraform-migrator

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Choose Your Installation Method

#### Option A: Direct Python Execution (Recommended - Works on all platforms)

```bash
# Test the tool
python run_cfmigrate.py --version

# Use the tool
python run_cfmigrate.py convert-all --regions us-east-1 --output ./terraform
```

#### Option B: Platform-Specific Scripts

**Linux/Mac:**
```bash
# Make executable and run
chmod +x cfmigrate.sh
./cfmigrate.sh --version
./cfmigrate.sh convert-all --regions us-east-1 --output ./terraform
```

**Windows:**
```cmd
REM Use the batch file
cfmigrate.bat --version
cfmigrate.bat convert-all --regions us-east-1 --output ./terraform
```

#### Option C: Traditional pip install (if PATH is configured)

```bash
# Install the package
pip install -e .

# Use CLI commands (if scripts are in PATH)
aws-cf-tf-migrate --version
cfmigrate --version
```

### Step 4: Configure AWS Credentials

```bash
# Configure AWS CLI (if not already done)
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Test AWS access
aws sts get-caller-identity
```

##  Quick Start Usage

### Option 1: One-Command Migration (Recommended)

```bash
# Complete migration in one command
python run_cfmigrate.py convert-all \
  --regions us-east-1,us-west-2 \
  --output ./my-terraform-project

# This will:
# 1. Discover all AWS resources
# 2. Convert to Terraform modules
# 3. Generate import scripts
# 4. Create documentation
```

### Option 2: Step-by-Step Process

```bash
# Step 1: Discover resources
python run_cfmigrate.py discover \
  --regions us-east-1,us-west-2 \
  --output discovery.json \
  --include-independent

# Step 2: Convert to Terraform
python run_cfmigrate.py convert \
  --input discovery.json \
  --output ./my-terraform-project \
  --strategy hybrid

# Step 3: Generate import scripts
python run_cfmigrate.py generate-imports \
  --terraform-dir ./my-terraform-project \
  --discovery-file discovery.json
```

##  Complete Usage Example

Let's walk through a complete migration example:

### 1. Initial Setup

```bash
# Create a working directory
mkdir my-migration-project
cd my-migration-project

# Run the migration
cfmigrate convert-all \
  --regions us-east-1 \
  --output ./terraform \
  --strategy hybrid \
  --module-prefix mycompany \
  --verbose
```

### 2. Review Generated Structure

```bash
# Check what was generated
tree terraform/

# Should show:
# terraform/
# ├── main.tf
# ├── variables.tf
# ├── outputs.tf
# ├── versions.tf
# ├── terraform.tfvars.example
# ├── import_resources.sh
# ├── GETTING_STARTED.md
# └── modules/
#     ├── networking/
#     ├── compute/
#     ├── storage/
#     └── database/
```

### 3. Configure Variables

```bash
cd terraform

# Copy example variables and customize
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
nano terraform.tfvars
```

Example `terraform.tfvars`:
```hcl
# Required variables
aws_region  = "us-east-1"
environment = "prod"

# Optional variables
name_prefix = "mycompany"

common_tags = {
  Environment = "prod"
  Project     = "infrastructure-migration"
  ManagedBy   = "terraform"
  Owner       = "platform-team"
}

# Module-specific variables (customize as needed)
# networking_main_vpc_cidr_block = "10.0.0.0/16"
# compute_web_instance_type = "t3.medium"
```

### 4. Initialize Terraform

```bash
# Initialize Terraform
terraform init

# Should output successful initialization
```

### 5. Import Existing Resources

```bash
# Make import script executable
chmod +x import_resources.sh

# Run the import (this is safe - read-only operation)
./import_resources.sh

# Should import all existing resources without errors
```

### 6. Verify Migration

```bash
# Run terraform plan - should show NO changes
terraform plan

# If you see changes, review the variables and adjust as needed
# The goal is zero changes after import
```

### 7. Test and Validate

```bash
# Validate configuration
terraform validate

# Check formatting
terraform fmt -check

# Run validation command
cfmigrate validate --terraform-dir .
```

##  Advanced Usage

### Using Configuration Files

Create a `migration-config.yaml`:

```yaml
discovery:
  regions:
    - us-east-1
    - us-west-2
  max_workers: 15
  stack_filter: "prod-*"
  services_to_scan:
    - ec2
    - s3
    - rds
    - lambda
    - iam

conversion:
  preserve_original_names: true
  terraform_version: ">=1.0"

modules:
  organization_strategy: "hybrid"
  module_prefix: "mycompany"
  include_readme: true

output:
  output_directory: "./terraform"
  generate_documentation: true
```

Use the configuration:

```bash
cfmigrate convert-all --config migration-config.yaml
```

### Filtering Resources

```bash
# Filter by CloudFormation stack names
cfmigrate convert-all \
  --regions us-east-1 \
  --stack-filter "prod-*" \
  --output ./terraform

# Filter by AWS services
cfmigrate discover \
  --regions us-east-1 \
  --services ec2,s3,rds \
  --output discovery.json
```

### Multi-Region Migration

```bash
# Migrate resources from multiple regions
cfmigrate convert-all \
  --regions us-east-1,us-west-2,eu-west-1 \
  --output ./terraform \
  --strategy hybrid \
  --module-prefix global
```

##  CLI Command Reference

### Main Commands

```bash
# Complete migration
cfmigrate convert-all [OPTIONS]

# Discover resources
cfmigrate discover [OPTIONS]

# Convert to Terraform
cfmigrate convert [OPTIONS]

# Generate import scripts
cfmigrate generate-imports [OPTIONS]

# Validate configuration
cfmigrate validate [OPTIONS]

# Show status
cfmigrate status [OPTIONS]
```

### Common Options

```bash
--regions, -r          # AWS regions (comma-separated)
--output, -o           # Output directory
--config, -c           # Configuration file
--profile              # AWS profile
--strategy             # Organization strategy
--module-prefix        # Module name prefix
--stack-filter         # Stack name filter
--verbose, -v          # Verbose output
--dry-run              # Preview without changes
--help                 # Show help
```

### Examples

```bash
# Get help for any command
cfmigrate convert-all --help
cfmigrate discover --help

# Verbose output for debugging
cfmigrate convert-all --regions us-east-1 --output ./terraform --verbose

# Dry run to see what would be done
cfmigrate convert-all --regions us-east-1 --output ./terraform --dry-run

# Use specific AWS profile
cfmigrate convert-all --regions us-east-1 --output ./terraform --profile production
```

##  Troubleshooting

### Common Issues

**1. AWS Credentials Not Found**
```bash
# Error: Unable to locate credentials
# Solution: Configure AWS credentials
aws configure
# or
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**2. Permission Denied**
```bash
# Error: Access denied for CloudFormation operations
# Solution: Ensure your AWS user/role has required permissions:
# - cloudformation:DescribeStacks
# - cloudformation:DescribeStackResources
# - cloudformation:GetTemplate
# - ec2:Describe*
# - s3:ListAllMyBuckets
# - rds:Describe*
```

**3. No Resources Found**
```bash
# Error: No resources discovered
# Solution: Check region and filters
cfmigrate discover --regions us-east-1 --verbose
```

**4. Import Failures**
```bash
# Error: Resource not found during import
# Solution: Check if resources still exist
aws ec2 describe-instances --instance-ids i-1234567890abcdef0
```

**5. Terraform Plan Shows Changes**
```bash
# Issue: terraform plan shows changes after import
# Solution: Review and adjust variables in terraform.tfvars
# Ensure all hardcoded values are properly parameterized
```

### Getting Help

```bash
# Check tool version
cfmigrate --version

# Get command help
cfmigrate --help
cfmigrate convert-all --help

# Enable verbose logging
cfmigrate convert-all --regions us-east-1 --output ./terraform --verbose

# Validate generated configuration
cfmigrate validate --terraform-dir ./terraform --verbose
```

## 📚 Next Steps

After successful migration:

1. **Set Up Version Control**
   ```bash
   git init
   git add .
   git commit -m "Initial Terraform migration from CloudFormation"
   ```

2. **Configure Remote State**
   ```hcl
   # Add to versions.tf
   terraform {
     backend "s3" {
       bucket = "my-terraform-state"
       key    = "infrastructure/terraform.tfstate"
       region = "us-east-1"
     }
   }
   ```

3. **Set Up CI/CD Pipeline**
   - Integrate with GitHub Actions, GitLab CI, or Jenkins
   - Add terraform plan/apply automation
   - Set up approval workflows

4. **Team Training**
   - Train team on Terraform workflows
   - Establish code review processes
   - Document operational procedures

5. **Monitoring and Maintenance**
   - Set up Terraform state monitoring
   - Regular plan checks for drift detection
   - Update and maintain modules

##  Best Practices

### Security
- Never commit `terraform.tfvars` to version control
- Use AWS IAM roles instead of access keys when possible
- Enable state file encryption
- Regularly rotate credentials

### Organization
- Use consistent naming conventions
- Document module interfaces
- Keep modules focused and single-purpose
- Use semantic versioning for modules

### Operations
- Always run `terraform plan` before `apply`
- Use workspaces for environment separation
- Implement proper backup strategies
- Monitor for configuration drift

---

This installation guide provides everything you need to successfully install and use the AWS CloudFormation to Terraform Migrator. For additional help, refer to the comprehensive documentation in the `docs/` directory.

