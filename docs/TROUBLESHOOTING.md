# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using the CF2TF converter. It covers installation problems, configuration issues, conversion errors, and import failures.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Discovery Issues](#discovery-issues)
- [Conversion Errors](#conversion-errors)
- [Import Failures](#import-failures)
- [Performance Issues](#performance-issues)
- [AWS-Specific Problems](#aws-specific-problems)
- [Terraform Issues](#terraform-issues)
- [Getting Help](#getting-help)

## Installation Issues

### Python Version Compatibility

**Problem:** CF2TF fails to install or run due to Python version issues.

```
ERROR: Package 'cf2tf-converter' requires a different Python: 3.7.0 not in '>=3.8'
```

**Solution:**
```bash
# Check Python version
python --version
python3 --version

# Install Python 3.8+ if needed (Ubuntu/Debian)
sudo apt update
sudo apt install python3.8 python3.8-pip

# Use specific Python version
python3.8 -m pip install cf2tf-converter

# Create virtual environment with correct Python version
python3.8 -m venv cf2tf-env
source cf2tf-env/bin/activate
pip install cf2tf-converter
```

### Dependency Conflicts

**Problem:** Conflicting package versions during installation.

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

**Solution:**
```bash
# Create clean virtual environment
python -m venv clean-env
source clean-env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install CF2TF in clean environment
pip install cf2tf-converter

# Alternative: Use pipx for isolated installation
pip install pipx
pipx install cf2tf-converter
```

### Permission Errors

**Problem:** Permission denied during installation.

```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Install for current user only
pip install --user cf2tf-converter

# Or use virtual environment
python -m venv cf2tf-env
source cf2tf-env/bin/activate
pip install cf2tf-converter

# On macOS/Linux, avoid sudo with pip
# Instead use virtual environments or --user flag
```

## Configuration Problems

### Invalid Configuration File

**Problem:** Configuration file has syntax errors or invalid values.

```
ERROR: Configuration validation failed: 'invalid_strategy' is not one of ['service_based', 'stack_based', 'lifecycle_based', 'hybrid']
```

**Solution:**
```bash
# Validate configuration file
cfmigrate validate-config --config config.yaml

# Use schema validation
python -c "
import yaml
import jsonschema
from aws_cf_terraform_migrator.config import ConfigManager

with open('config.yaml') as f:
    config = yaml.safe_load(f)

try:
    jsonschema.validate(config, ConfigManager.CONFIG_SCHEMA)
    print('Configuration is valid')
except jsonschema.ValidationError as e:
    print(f'Configuration error: {e.message}')
"
```

**Common configuration fixes:**
```yaml
# Fix invalid organization strategy
modules:
  organization_strategy: "service_based"  # Not "custom" or "invalid"

# Fix invalid region names
discovery:
  regions:
    - "us-east-1"  # Not "us-east-3" (doesn't exist)
    - "us-west-2"

# Fix invalid worker count
discovery:
  max_workers: 10  # Must be between 1 and 50
```

### AWS Credentials Issues

**Problem:** AWS credentials not configured or invalid.

```
ERROR: Unable to locate credentials. You can configure credentials by running "aws configure"
```

**Solution:**
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Test credentials
aws sts get-caller-identity

# Use specific profile
cfmigrate discover --profile production --regions us-east-1

# Use IAM role
cfmigrate discover --role-arn arn:aws:iam::123456789012:role/CF2TFRole
```

## Discovery Issues

### No Stacks Found

**Problem:** Discovery doesn't find any CloudFormation stacks.

```
INFO: Discovery complete: 0 stacks, 0 resources
```

**Diagnostic steps:**
```bash
# Check if stacks exist in the region
aws cloudformation list-stacks --region us-east-1

# Check stack status filter
aws cloudformation list-stacks --region us-east-1 --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Run discovery with debug logging
cfmigrate discover --regions us-east-1 --debug --log-file debug.log

# Check specific stack
aws cloudformation describe-stacks --stack-name your-stack-name --region us-east-1
```

**Common solutions:**
```bash
# Include deleted stacks if needed
cfmigrate discover --regions us-east-1 --include-deleted-stacks

# Remove stack name filter
cfmigrate discover --regions us-east-1 --stack-filter ""

# Check different regions
cfmigrate discover --regions us-east-1,us-west-2,eu-west-1
```

### Permission Denied Errors

**Problem:** Insufficient permissions to discover resources.

```
ERROR: An error occurred (AccessDenied) when calling the ListStacks operation: User is not authorized to perform: cloudformation:ListStacks
```

**Solution:**
```bash
# Check current permissions
aws sts get-caller-identity

# Test specific permissions
aws cloudformation list-stacks --region us-east-1
aws ec2 describe-vpcs --region us-east-1

# Add required permissions to IAM policy
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "cloudformation:ListStacks",
                "ec2:Describe*",
                "s3:ListAllMyBuckets",
                "rds:Describe*"
            ],
            "Resource": "*"
        }
    ]
}
```

### Timeout Issues

**Problem:** Discovery times out for large environments.

```
ERROR: Discovery timed out after 300 seconds
```

**Solution:**
```bash
# Increase timeout and workers
cfmigrate discover \
  --regions us-east-1 \
  --max-workers 20 \
  --timeout 600 \
  --output discovery.json

# Discover regions separately
cfmigrate discover --regions us-east-1 --output us-east-1.json
cfmigrate discover --regions us-west-2 --output us-west-2.json

# Merge discovery results
cf2tf merge-discovery us-east-1.json us-west-2.json --output combined.json
```

## Conversion Errors

### Unsupported Resource Types

**Problem:** CloudFormation template contains unsupported resource types.

```
WARNING: Unsupported CloudFormation resource type: AWS::CustomResource::MyCustomType
```

**Solution:**
```bash
# List all unsupported resources
cfmigrate convert --input discovery.json --list-unsupported

# Convert with custom mappings
cfmigrate convert \
  --input discovery.json \
  --output terraform \
  --custom-mappings custom-mappings.yaml

# Example custom mapping file
cat > custom-mappings.yaml << EOF
resource_mappings:
  "AWS::CustomResource::MyCustomType":
    terraform_type: "null_resource"
    conversion_notes: "Custom resource converted to null_resource - manual configuration required"
EOF
```

### Intrinsic Function Conversion

**Problem:** Complex CloudFormation intrinsic functions can't be converted.

```
WARNING: Complex intrinsic function could not be converted: !Select [0, !Split ['-', !GetAtt MyResource.ComplexAttribute]]
```

**Solution:**
```bash
# Enable advanced intrinsic function handling
cfmigrate convert \
  --input discovery.json \
  --output terraform \
  --handle-intrinsic-functions \
  --preserve-complex-functions

# Manual conversion may be required for complex cases
# Check conversion_report.md for details
```

### Template Parsing Errors

**Problem:** CloudFormation template has syntax errors or unusual structure.

```
ERROR: Failed to parse CloudFormation template: Invalid JSON/YAML syntax
```

**Solution:**
```bash
# Validate CloudFormation template
aws cloudformation validate-template --template-body file://template.yaml

# Check template format
cfmigrate validate-template --template template.yaml

# Convert with error tolerance
cfmigrate convert \
  --input discovery.json \
  --output terraform \
  --ignore-template-errors \
  --continue-on-error
```

## Import Failures

### Resource Not Found

**Problem:** Terraform import fails because resource doesn't exist.

```
Error: resource not found: vpc-12345
```

**Diagnostic steps:**
```bash
# Verify resource exists
aws ec2 describe-vpcs --vpc-ids vpc-12345

# Check resource in correct region
aws ec2 describe-vpcs --vpc-ids vpc-12345 --region us-west-2

# Update import script with correct resource IDs
./import_resources.sh --dry-run --verbose
```

**Solution:**
```bash
# Regenerate import script with current resource IDs
cfmigrate generate-imports \
  --input discovery.json \
  --output terraform \
  --refresh-resource-ids

# Skip missing resources
./import_resources.sh --skip-missing

# Import specific resources only
terraform import aws_vpc.main vpc-12345
```

### State Lock Issues

**Problem:** Terraform state is locked during import.

```
Error: Error locking state: Error acquiring the state lock
```

**Solution:**
```bash
# Check state lock
terraform force-unlock LOCK_ID

# Use different backend for testing
terraform init -backend-config="path=./terraform-test.tfstate"

# Import with retry logic
./import_resources.sh --retry-on-lock --max-retries 5
```

### Import Validation Failures

**Problem:** Resources imported successfully but terraform plan shows changes.

```
Plan: 0 to add, 15 to change, 0 to destroy
```

**Solution:**
```bash
# Check for configuration drift
terraform plan -detailed-exitcode

# Update configuration to match current state
cf2tf sync-config \
  --terraform-dir terraform \
  --update-from-state

# Ignore specific attributes
terraform plan -var="ignore_changes=true"
```

## Performance Issues

### Slow Discovery

**Problem:** Resource discovery takes too long.

```
INFO: Discovery running for 10 minutes...
```

**Optimization strategies:**
```bash
# Increase parallel workers
cfmigrate discover --regions us-east-1 --max-workers 20

# Limit services to scan
cfmigrate discover \
  --regions us-east-1 \
  --services ec2,s3,rds \
  --output discovery.json

# Use regional parallelization
cfmigrate discover --regions us-east-1 --output us-east-1.json &
cfmigrate discover --regions us-west-2 --output us-west-2.json &
wait
cf2tf merge-discovery us-east-1.json us-west-2.json --output combined.json
```

### Memory Issues

**Problem:** CF2TF runs out of memory with large environments.

```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Process regions separately
for region in us-east-1 us-west-2 eu-west-1; do
    cfmigrate discover --regions $region --output ${region}.json
done

# Use streaming processing
cfmigrate convert \
  --input discovery.json \
  --output terraform \
  --streaming-mode \
  --batch-size 100

# Increase system memory or use cloud instance
# Monitor memory usage
cfmigrate convert --input discovery.json --output terraform --monitor-memory
```

## AWS-Specific Problems

### Rate Limiting

**Problem:** AWS API rate limits causing failures.

```
ERROR: Rate exceeded for operation: DescribeStacks
```

**Solution:**
```bash
# Reduce parallel workers
cfmigrate discover --regions us-east-1 --max-workers 5

# Add delays between API calls
cfmigrate discover \
  --regions us-east-1 \
  --api-delay 1000 \
  --output discovery.json

# Use exponential backoff
cfmigrate discover \
  --regions us-east-1 \
  --retry-strategy exponential \
  --max-retries 5
```

### Cross-Account Access

**Problem:** Cannot access resources in different AWS accounts.

```
ERROR: Access denied when assuming role arn:aws:iam::123456789012:role/CF2TFRole
```

**Solution:**
```bash
# Verify role trust policy
aws iam get-role --role-name CF2TFRole

# Test role assumption
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/CF2TFRole \
  --role-session-name CF2TFTest

# Use correct role ARN in configuration
cfmigrate discover \
  --regions us-east-1 \
  --role-arn arn:aws:iam::123456789012:role/CF2TFRole
```

### Service Quotas

**Problem:** Hitting AWS service quotas during discovery.

```
ERROR: Request limit exceeded for service: CloudFormation
```

**Solution:**
```bash
# Check service quotas
aws service-quotas get-service-quota \
  --service-code cloudformation \
  --quota-code L-0485CB21

# Request quota increase through AWS console
# Or reduce discovery scope
cfmigrate discover \
  --regions us-east-1 \
  --stack-filter "prod-*" \
  --max-workers 3
```

## Terraform Issues

### Version Compatibility

**Problem:** Generated Terraform code incompatible with installed version.

```
Error: Unsupported Terraform Core version
```

**Solution:**
```bash
# Check Terraform version
terraform version

# Install compatible version
tfenv install 1.5.0
tfenv use 1.5.0

# Or update generated version constraints
cfmigrate convert \
  --input discovery.json \
  --output terraform \
  --terraform-version ">=1.0,<2.0"
```

### Provider Issues

**Problem:** AWS provider version conflicts.

```
Error: Incompatible provider version
```

**Solution:**
```bash
# Update provider version in generated code
cfmigrate convert \
  --input discovery.json \
  --output terraform \
  --provider-version ">=5.0"

# Or manually update versions.tf
cat > terraform/versions.tf << EOF
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
EOF
```

### State Management

**Problem:** Terraform state corruption or conflicts.

```
Error: State lock info mismatch
```

**Solution:**
```bash
# Backup current state
cp terraform.tfstate terraform.tfstate.backup

# Force unlock if needed
terraform force-unlock LOCK_ID

# Recover from backup
cp terraform.tfstate.backup terraform.tfstate

# Use remote state for better reliability
terraform init -backend-config="bucket=my-terraform-state"
```

## Getting Help

### Enable Debug Logging

```bash
# Enable comprehensive debug logging
cfmigrate convert-all \
  --regions us-east-1 \
  --output terraform \
  --debug \
  --log-file debug.log \
  --verbose

# Check log file for detailed information
tail -f debug.log
```

### Generate Diagnostic Report

```bash
# Generate comprehensive diagnostic report
cf2tf diagnose \
  --config config.yaml \
  --output diagnostic-report.md \
  --include-system-info \
  --include-aws-info

# Include in support requests
cat diagnostic-report.md
```

### Common Support Information

When requesting help, please include:

1. **CF2TF Version:**
   ```bash
   cf2tf --version
   ```

2. **System Information:**
   ```bash
   python --version
   terraform version
   aws --version
   ```

3. **Configuration:**
   ```bash
   # Sanitized configuration (remove sensitive data)
   cat config.yaml
   ```

4. **Error Messages:**
   ```bash
   # Full error output with stack traces
   cfmigrate convert --debug 2>&1 | tee error.log
   ```

5. **AWS Environment:**
   ```bash
   aws sts get-caller-identity
   aws cloudformation list-stacks --region us-east-1 | head -20
   ```

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Comprehensive guides and examples
- **Stack Overflow**: Tag questions with `cf2tf-converter`
- **Discord/Slack**: Real-time community support

### Professional Support

For enterprise customers, professional support is available including:
- Priority bug fixes
- Custom feature development
- Migration consulting
- Training and workshops

Contact support@cf2tf.com for more information.

