# Usage Examples

This document provides comprehensive examples of using the CF2TF converter in various scenarios. Each example includes the command, expected output, and explanation of the results.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Advanced Scenarios](#advanced-scenarios)
- [Real-World Use Cases](#real-world-use-cases)
- [Troubleshooting Examples](#troubleshooting-examples)
- [Integration Examples](#integration-examples)

## Basic Examples

### Example 1: Simple Resource Discovery

Discover all CloudFormation stacks and resources in a single region.

```bash
cfmigrate discover --regions us-east-1 --output discovery.json
```

**Expected Output:**
```
CF2TF Converter v1.0.0
Starting resource discovery...

Discovering CloudFormation stacks in us-east-1...
Found 3 stacks:
  - web-app-stack (CREATE_COMPLETE)
  - database-stack (CREATE_COMPLETE)
  - networking-stack (CREATE_COMPLETE)

Discovering independent AWS resources...
Found 15 independent resources:
  - 2 VPCs
  - 5 S3 buckets
  - 3 Lambda functions
  - 5 IAM roles

Discovery completed in 45.2 seconds
Results exported to discovery.json
```

**Generated discovery.json structure:**
```json
{
  "stacks": {
    "web-app-stack": {
      "stack_name": "web-app-stack",
      "stack_id": "arn:aws:cloudformation:us-east-1:123456789012:stack/web-app-stack/12345",
      "stack_status": "CREATE_COMPLETE",
      "region": "us-east-1",
      "resources": [...],
      "template_body": {...}
    }
  },
  "resources": {
    "vpc-12345": {
      "resource_id": "vpc-12345",
      "resource_type": "AWS::EC2::VPC",
      "region": "us-east-1",
      "managed_by_cloudformation": false
    }
  },
  "summary": {
    "total_stacks": 3,
    "total_resources": 45,
    "cloudformation_managed": 30,
    "independent_resources": 15
  }
}
```

### Example 2: Basic Conversion

Convert discovered resources to Terraform modules.

```bash
cfmigrate convert --input discovery.json --output ./terraform --strategy service_based
```

**Expected Output:**
```
CF2TF Converter v1.0.0
Starting CloudFormation to Terraform conversion...

Loading discovery data from discovery.json...
Found 3 stacks with 30 resources
Found 15 independent resources

Converting CloudFormation templates...
  ✓ web-app-stack: 12 resources converted
  ✓ database-stack: 8 resources converted
  ✓ networking-stack: 10 resources converted

Organizing resources into modules...
  ✓ networking: 15 resources
  ✓ compute: 8 resources
  ✓ storage: 7 resources
  ✓ database: 8 resources
  ✓ security: 7 resources

Generating Terraform files...
  ✓ Created 5 modules
  ✓ Generated 25 .tf files
  ✓ Created import script with 45 commands

Conversion completed in 12.3 seconds
Output directory: ./terraform
```

**Generated directory structure:**
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── README.md
├── import_resources.sh
├── conversion_report.md
├── MIGRATION_GUIDE.md
└── modules/
    ├── networking/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── compute/
    ├── storage/
    ├── database/
    └── security/
```

### Example 3: One-Command Conversion

Perform complete discovery and conversion in a single command.

```bash
cfmigrate convert-all --regions us-east-1,us-west-2 --output ./terraform --strategy hybrid
```

**Expected Output:**
```
CF2TF Converter v1.0.0
Starting complete CloudFormation to Terraform conversion...

Phase 1: Discovering AWS resources...
  Scanning regions: us-east-1, us-west-2
  Found 5 stacks across 2 regions
  Found 23 independent resources

Phase 2: Converting CloudFormation to Terraform...
  Converted 5 stacks with 67 resources
  Generated Terraform configurations

Phase 3: Organizing into modules...
  Using hybrid organization strategy
  Created 8 modules based on stack size and service grouping

Phase 4: Generating import scripts...
  Generated import script with 90 commands
  Created parallel import capability

Phase 5: Creating documentation...
  Generated comprehensive README files
  Created migration guide and best practices

Conversion completed successfully in 78.5 seconds
Total resources: 90
Modules created: 8
Files generated: 42
```

## Advanced Scenarios

### Example 4: Multi-Region Discovery with Filtering

Discover resources across multiple regions with stack filtering.

```bash
cfmigrate discover \
  --regions us-east-1,us-west-2,eu-west-1 \
  --stack-filter "prod-*" \
  --profile production \
  --max-workers 15 \
  --output prod-discovery.json
```

**Configuration file approach:**
```yaml
# prod-config.yaml
discovery:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
  stack_name_filter: "prod-*"
  profile: "production"
  max_workers: 15
  services_to_scan:
    - ec2
    - s3
    - rds
    - lambda
    - elbv2
    - autoscaling

output:
  output_directory: "./prod-terraform"
  export_discovery_data: true
```

```bash
cfmigrate discover --config prod-config.yaml
```

### Example 5: Cross-Account Resource Discovery

Discover resources across multiple AWS accounts using IAM roles.

```bash
cfmigrate discover \
  --regions us-east-1 \
  --role-arn "arn:aws:iam::123456789012:role/CF2TFCrossAccountRole" \
  --output cross-account-discovery.json
```

**IAM Role Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::SOURCE-ACCOUNT:user/cf2tf-user"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Example 6: Custom Module Organization

Use different organization strategies for different scenarios.

**Stack-Based Organization:**
```bash
cfmigrate convert \
  --input discovery.json \
  --output ./terraform-stack-based \
  --strategy stack_based \
  --module-prefix "mycompany"
```

**Lifecycle-Based Organization:**
```bash
cfmigrate convert \
  --input discovery.json \
  --output ./terraform-lifecycle \
  --strategy lifecycle_based \
  --include-examples
```

**Hybrid Organization with Configuration:**
```yaml
# hybrid-config.yaml
modules:
  organization_strategy: "hybrid"
  module_prefix: "acme"
  include_examples: true
  include_readme: true
  group_similar_resources: true
  
conversion:
  preserve_original_names: true
  handle_intrinsic_functions: true
  
output:
  generate_documentation: true
  include_metadata: true
```

```bash
cfmigrate convert --config hybrid-config.yaml --input discovery.json
```

## Real-World Use Cases

### Example 7: Large Enterprise Migration

Scenario: Migrating a large enterprise environment with 200+ CloudFormation stacks across multiple regions and accounts.

**Step 1: Discovery Phase**
```bash
# Create discovery configuration
cat > enterprise-discovery.yaml << EOF
discovery:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
    - ap-southeast-1
  max_workers: 20
  services_to_scan:
    - ec2
    - s3
    - rds
    - lambda
    - iam
    - dynamodb
    - elasticache
    - elbv2
    - autoscaling
    - route53
    - cloudfront

output:
  output_directory: "./enterprise-terraform"
  export_discovery_data: true
  export_format: "json"

logging:
  level: "INFO"
  file: "enterprise-discovery.log"
  console: true
EOF

# Run discovery
cfmigrate discover --config enterprise-discovery.yaml
```

**Step 2: Analysis and Planning**
```bash
# Analyze discovery results
cf2tf analyze discovery_results.json --report analysis-report.md

# Generate conversion plan
cf2tf plan --input discovery_results.json --output conversion-plan.json
```

**Step 3: Phased Conversion**
```bash
# Convert non-production environments first
cfmigrate convert \
  --input discovery_results.json \
  --stack-filter "dev-*,test-*,staging-*" \
  --output ./terraform-nonprod \
  --strategy hybrid

# Convert production environments
cfmigrate convert \
  --input discovery_results.json \
  --stack-filter "prod-*" \
  --output ./terraform-prod \
  --strategy service_based \
  --module-prefix "prod"
```

### Example 8: Microservices Architecture Migration

Scenario: Converting a microservices architecture with multiple small stacks per service.

```bash
# Discovery with service-specific filtering
cfmigrate discover \
  --regions us-east-1 \
  --stack-filter "*-service-*" \
  --output microservices-discovery.json

# Convert with service-based organization
cfmigrate convert \
  --input microservices-discovery.json \
  --output ./microservices-terraform \
  --strategy service_based \
  --group-similar-resources
```

**Generated structure for microservices:**
```
microservices-terraform/
├── main.tf
├── modules/
│   ├── api_gateway/          # API Gateway resources
│   ├── compute/              # Lambda functions, ECS services
│   ├── networking/           # VPCs, subnets, load balancers
│   ├── storage/              # S3 buckets, DynamoDB tables
│   ├── monitoring/           # CloudWatch, X-Ray
│   └── security/             # IAM roles, security groups
└── services/                 # Service-specific configurations
    ├── user-service/
    ├── order-service/
    └── payment-service/
```

### Example 9: Disaster Recovery Setup

Scenario: Converting disaster recovery infrastructure across multiple regions.

```bash
# Discover primary region
cfmigrate discover \
  --regions us-east-1 \
  --stack-filter "prod-*" \
  --output primary-discovery.json

# Discover DR region
cfmigrate discover \
  --regions us-west-2 \
  --stack-filter "dr-*" \
  --output dr-discovery.json

# Convert with region-aware organization
cfmigrate convert \
  --input primary-discovery.json \
  --output ./terraform-primary \
  --strategy lifecycle_based \
  --module-prefix "primary"

cfmigrate convert \
  --input dr-discovery.json \
  --output ./terraform-dr \
  --strategy lifecycle_based \
  --module-prefix "dr"
```

## Troubleshooting Examples

### Example 10: Handling Conversion Errors

When conversion encounters errors, the tool provides detailed diagnostics.

```bash
cfmigrate convert --input discovery.json --output ./terraform --debug
```

**Common error scenarios and solutions:**

**Unsupported Resource Type:**
```
WARNING: Unsupported CloudFormation resource type: AWS::CustomResource::MyCustomType
Solution: The resource will be documented but not converted. Manual conversion required.
```

**Intrinsic Function Conversion:**
```
WARNING: Complex intrinsic function in stack 'web-app': !Select [0, !Split ['-', !Ref 'AWS::StackName']]
Solution: Converted to Terraform equivalent using local values and string functions.
```

**Missing Dependencies:**
```
ERROR: Resource 'MyInstance' references 'MyVPC' which was not found
Solution: Check stack dependencies and ensure all referenced stacks are included in discovery.
```

### Example 11: Import Validation and Recovery

Validate imports and handle failures gracefully.

```bash
# Run conversion with import validation
cfmigrate convert-all \
  --regions us-east-1 \
  --output ./terraform \
  --validate-imports \
  --create-backup

# If imports fail, use recovery options
cd terraform
terraform init

# Check what failed
./import_resources.sh --dry-run --verbose

# Import with retry logic
./import_resources.sh --retry-failed --max-retries 3

# Validate final state
terraform plan
```

### Example 12: Debugging Discovery Issues

When discovery doesn't find expected resources.

```bash
# Run discovery with debug logging
cfmigrate discover \
  --regions us-east-1 \
  --debug \
  --log-file discovery-debug.log \
  --output discovery.json

# Check specific services
cfmigrate discover \
  --regions us-east-1 \
  --services ec2,s3 \
  --verbose \
  --output partial-discovery.json

# Verify AWS credentials and permissions
aws sts get-caller-identity
aws cloudformation list-stacks --region us-east-1
```

## Integration Examples

### Example 13: CI/CD Pipeline Integration

Integrate CF2TF converter into your CI/CD pipeline.

**GitHub Actions Workflow:**
```yaml
# .github/workflows/cf2tf-conversion.yml
name: CloudFormation to Terraform Conversion

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install CF2TF
        run: pip install cf2tf-converter
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Run CF2TF Conversion
        run: |
          cfmigrate convert-all \
            --config .cf2tf/config.yaml \
            --output ./terraform-output
      
      - name: Validate Terraform
        run: |
          cd terraform-output
          terraform init
          terraform validate
          terraform plan
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'Update Terraform from CloudFormation'
          title: 'Automated CF2TF Conversion'
          body: 'Automated conversion from CloudFormation to Terraform'
          branch: cf2tf-update
```

### Example 14: Terraform Cloud Integration

Integrate with Terraform Cloud for state management.

```bash
# Configure Terraform Cloud backend
cat > backend.tf << EOF
terraform {
  cloud {
    organization = "my-org"
    workspaces {
      name = "cf2tf-converted"
    }
  }
}
EOF

# Run conversion with Terraform Cloud configuration
cfmigrate convert-all \
  --regions us-east-1 \
  --output ./terraform \
  --terraform-version ">=1.5" \
  --backend-config backend.tf

# Initialize with Terraform Cloud
cd terraform
terraform login
terraform init
terraform plan
```

### Example 15: Monitoring and Alerting

Set up monitoring for the conversion process.

```bash
# Run conversion with metrics export
cfmigrate convert-all \
  --regions us-east-1 \
  --output ./terraform \
  --export-metrics metrics.json \
  --webhook-url "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Custom monitoring script
cat > monitor-conversion.sh << 'EOF'
#!/bin/bash
set -e

# Run conversion
cfmigrate convert-all --config config.yaml --output ./terraform

# Check for errors
if [ $? -eq 0 ]; then
    echo "✅ CF2TF conversion completed successfully"
    # Send success notification
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"CF2TF conversion completed successfully"}' \
        $SLACK_WEBHOOK_URL
else
    echo "❌ CF2TF conversion failed"
    # Send failure notification
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"CF2TF conversion failed - check logs"}' \
        $SLACK_WEBHOOK_URL
    exit 1
fi

# Validate Terraform
cd terraform
terraform init
terraform validate

if [ $? -eq 0 ]; then
    echo "✅ Terraform validation passed"
else
    echo "❌ Terraform validation failed"
    exit 1
fi
EOF

chmod +x monitor-conversion.sh
./monitor-conversion.sh
```

These examples demonstrate the flexibility and power of the CF2TF converter across various scenarios, from simple conversions to complex enterprise migrations. Each example can be adapted to your specific requirements and integrated into your existing workflows.

