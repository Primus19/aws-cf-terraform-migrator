# CloudFormation to Terraform Migration Guide

This comprehensive guide provides best practices, strategies, and step-by-step instructions for successfully migrating from AWS CloudFormation to Terraform using the CF2TF converter.

## Table of Contents

- [Migration Overview](#migration-overview)
- [Pre-Migration Planning](#pre-migration-planning)
- [Migration Strategies](#migration-strategies)
- [Step-by-Step Migration Process](#step-by-step-migration-process)
- [Post-Migration Tasks](#post-migration-tasks)
- [Best Practices](#best-practices)
- [Risk Mitigation](#risk-mitigation)
- [Rollback Procedures](#rollback-procedures)
- [Team Training and Adoption](#team-training-and-adoption)

## Migration Overview

### Why Migrate to Terraform?

**Enhanced Multi-Cloud Support**
Terraform provides native support for multiple cloud providers, enabling hybrid and multi-cloud strategies that CloudFormation cannot match.

**Superior State Management**
Terraform's state management capabilities offer better visibility, collaboration features, and conflict resolution compared to CloudFormation's implicit state handling.

**Richer Ecosystem**
The Terraform ecosystem includes thousands of providers, modules, and tools that extend functionality far beyond AWS services.

**Better Developer Experience**
Terraform's HCL syntax is more readable and maintainable than CloudFormation's JSON/YAML templates, with superior IDE support and debugging capabilities.

**Advanced Planning and Validation**
Terraform's plan-and-apply workflow provides better visibility into changes before execution, reducing the risk of unintended modifications.

### Migration Challenges

**Resource State Transition**
Moving existing resources from CloudFormation management to Terraform requires careful import processes to avoid resource recreation.

**Template Complexity**
Complex CloudFormation templates with intrinsic functions, conditions, and nested stacks require sophisticated conversion logic.

**Team Training**
Teams familiar with CloudFormation need training on Terraform concepts, workflows, and best practices.

**Operational Changes**
Migration involves changes to CI/CD pipelines, deployment processes, and operational procedures.

## Pre-Migration Planning

### Assessment Phase

**Inventory Current Infrastructure**
```bash
# Discover all CloudFormation stacks
cfmigrate discover --regions us-east-1,us-west-2,eu-west-1 --output full-inventory.json

# Generate assessment report
cf2tf assess --input full-inventory.json --output assessment-report.md
```

**Analyze Stack Dependencies**
```bash
# Map stack dependencies
cf2tf analyze-dependencies --input full-inventory.json --output dependency-graph.json

# Visualize dependencies
cf2tf visualize-dependencies --input dependency-graph.json --output dependencies.png
```

**Identify Migration Complexity**
- **Simple Stacks**: Basic resources with minimal dependencies
- **Complex Stacks**: Nested stacks, custom resources, complex conditions
- **Critical Stacks**: Production resources requiring zero-downtime migration

### Risk Assessment

**High-Risk Resources**
- Production databases with critical data
- Load balancers handling live traffic
- Security groups with complex rules
- IAM roles with extensive permissions

**Medium-Risk Resources**
- Development and staging environments
- Monitoring and logging infrastructure
- Backup and disaster recovery resources

**Low-Risk Resources**
- Development tools and utilities
- Temporary or experimental resources
- Documentation and metadata resources

### Team Preparation

**Skill Assessment**
- Evaluate team's current Terraform knowledge
- Identify training needs and knowledge gaps
- Plan training sessions and workshops

**Tool Setup**
- Install and configure Terraform
- Set up Terraform Cloud or backend storage
- Configure development environments

**Process Definition**
- Define new deployment workflows
- Update CI/CD pipelines
- Establish code review processes

## Migration Strategies

### Big Bang Migration

**Description**: Migrate all resources simultaneously in a coordinated effort.

**Pros**:
- Fastest overall migration time
- Consistent end state
- Simplified coordination

**Cons**:
- Higher risk of widespread issues
- Requires extensive testing
- Difficult to rollback

**Best For**:
- Small to medium environments
- Non-critical development environments
- Teams with extensive Terraform experience

**Implementation**:
```bash
# Complete migration in single operation
cfmigrate convert-all \
  --regions us-east-1,us-west-2 \
  --output ./terraform-complete \
  --strategy hybrid \
  --import-resources \
  --validate-imports
```

### Phased Migration

**Description**: Migrate resources in logical phases based on dependencies and risk levels.

**Phase 1: Foundation Infrastructure**
- VPCs, subnets, route tables
- IAM roles and policies
- Security groups

**Phase 2: Data Layer**
- RDS databases
- DynamoDB tables
- S3 buckets

**Phase 3: Application Layer**
- EC2 instances
- Load balancers
- Auto Scaling groups

**Phase 4: Supporting Services**
- Lambda functions
- CloudWatch resources
- SNS/SQS queues

**Implementation**:
```bash
# Phase 1: Foundation
cfmigrate convert \
  --input discovery.json \
  --stack-filter "*-network*,*-security*,*-iam*" \
  --output ./terraform-phase1 \
  --strategy service_based

# Phase 2: Data Layer
cfmigrate convert \
  --input discovery.json \
  --stack-filter "*-database*,*-storage*" \
  --output ./terraform-phase2 \
  --strategy service_based

# Continue for remaining phases...
```

### Service-by-Service Migration

**Description**: Migrate one AWS service at a time across all stacks.

**Migration Order**:
1. IAM (roles, policies, users)
2. Networking (VPCs, subnets, security groups)
3. Storage (S3, EBS, EFS)
4. Databases (RDS, DynamoDB)
5. Compute (EC2, Lambda, ECS)
6. Load Balancing (ALB, NLB, CLB)
7. Monitoring (CloudWatch, X-Ray)

**Implementation**:
```bash
# Migrate IAM resources first
cfmigrate convert \
  --input discovery.json \
  --services iam \
  --output ./terraform-iam \
  --strategy service_based

# Then networking
cfmigrate convert \
  --input discovery.json \
  --services ec2 \
  --resource-filter "VPC,Subnet,SecurityGroup,RouteTable" \
  --output ./terraform-networking
```

### Environment-by-Environment Migration

**Description**: Migrate complete environments in order of criticality.

**Migration Order**:
1. Development environments
2. Testing/staging environments
3. Production environments

**Implementation**:
```bash
# Development environment
cfmigrate convert-all \
  --regions us-east-1 \
  --stack-filter "dev-*" \
  --output ./terraform-dev \
  --strategy stack_based

# Staging environment
cfmigrate convert-all \
  --regions us-east-1 \
  --stack-filter "staging-*" \
  --output ./terraform-staging \
  --strategy stack_based

# Production environment (with extra validation)
cfmigrate convert-all \
  --regions us-east-1,us-west-2 \
  --stack-filter "prod-*" \
  --output ./terraform-prod \
  --strategy hybrid \
  --validate-imports \
  --create-backup
```

## Step-by-Step Migration Process

### Step 1: Environment Preparation

**Set Up Terraform Backend**
```bash
# Create S3 bucket for state storage
aws s3 mb s3://my-terraform-state-bucket

# Configure backend
cat > backend.tf << EOF
terraform {
  backend "s3" {
    bucket = "my-terraform-state-bucket"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
    
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
EOF
```

**Configure Terraform Cloud (Alternative)**
```bash
# Login to Terraform Cloud
terraform login

# Configure cloud backend
cat > backend.tf << EOF
terraform {
  cloud {
    organization = "my-organization"
    workspaces {
      name = "infrastructure"
    }
  }
}
EOF
```

### Step 2: Discovery and Analysis

**Comprehensive Discovery**
```bash
# Discover all resources
cfmigrate discover \
  --regions us-east-1,us-west-2,eu-west-1 \
  --include-independent-resources \
  --max-workers 15 \
  --output complete-discovery.json

# Generate analysis report
cf2tf analyze \
  --input complete-discovery.json \
  --output analysis-report.md \
  --include-recommendations
```

**Review Discovery Results**
```bash
# View summary statistics
cf2tf summary --input complete-discovery.json

# List all stacks
cf2tf list-stacks --input complete-discovery.json

# Check for unsupported resources
cf2tf check-support --input complete-discovery.json
```

### Step 3: Conversion Planning

**Create Migration Plan**
```bash
# Generate migration plan
cf2tf plan \
  --input complete-discovery.json \
  --strategy hybrid \
  --output migration-plan.json

# Review plan details
cf2tf review-plan --input migration-plan.json --output plan-review.md
```

**Validate Conversion Approach**
```bash
# Test conversion on subset
cfmigrate convert \
  --input complete-discovery.json \
  --stack-filter "dev-test-*" \
  --output ./test-conversion \
  --dry-run

# Review test results
cat test-conversion/conversion_report.md
```

### Step 4: Pilot Migration

**Select Pilot Environment**
Choose a non-critical environment for initial migration:
- Development environment
- Isolated test environment
- Temporary/experimental resources

**Execute Pilot Migration**
```bash
# Convert pilot environment
cfmigrate convert-all \
  --regions us-east-1 \
  --stack-filter "dev-pilot-*" \
  --output ./terraform-pilot \
  --strategy service_based \
  --generate-docs

# Review generated code
cd terraform-pilot
tree .
cat README.md
```

**Import Resources**
```bash
# Initialize Terraform
terraform init

# Review import plan
cat import_resources.sh

# Execute imports
chmod +x import_resources.sh
./import_resources.sh

# Validate imports
terraform plan
```

**Validate Pilot Results**
```bash
# Check resource state
terraform show

# Verify resource functionality
# Test applications and services
# Monitor for any issues

# Document lessons learned
```

### Step 5: Full Migration Execution

**Pre-Migration Checklist**
- [ ] Backup all CloudFormation templates
- [ ] Document current resource configurations
- [ ] Notify stakeholders of migration timeline
- [ ] Prepare rollback procedures
- [ ] Set up monitoring and alerting

**Execute Migration**
```bash
# Production migration with full validation
cfmigrate convert-all \
  --regions us-east-1,us-west-2 \
  --output ./terraform-production \
  --strategy hybrid \
  --module-prefix "prod" \
  --validate-imports \
  --create-backup \
  --generate-docs

cd terraform-production

# Initialize with backend
terraform init

# Review all generated code
find . -name "*.tf" -exec echo "=== {} ===" \; -exec cat {} \;

# Execute imports with monitoring
./import_resources.sh --verbose --monitor

# Comprehensive validation
terraform plan -detailed-exitcode
terraform validate
```

### Step 6: Post-Migration Validation

**Resource Validation**
```bash
# Verify all resources are managed
terraform state list

# Check for configuration drift
terraform plan

# Validate resource functionality
# Run application tests
# Check monitoring dashboards
```

**Documentation Update**
```bash
# Generate final documentation
terraform-docs markdown table . > TERRAFORM_DOCS.md

# Update team documentation
# Create operational runbooks
# Document new procedures
```

## Post-Migration Tasks

### CloudFormation Cleanup

**Gradual Stack Deletion**
```bash
# List stacks to be deleted
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Delete stacks in reverse dependency order
# Start with leaf stacks (no dependencies)
aws cloudformation delete-stack --stack-name leaf-stack-1

# Monitor deletion progress
aws cloudformation describe-stacks --stack-name leaf-stack-1

# Continue with parent stacks
```

**Resource Verification**
```bash
# Ensure no resources are orphaned
aws cloudformation describe-stack-resources --stack-name deleted-stack

# Check for any remaining CloudFormation-managed resources
cfmigrate discover --regions us-east-1 --output post-migration-check.json
```

### CI/CD Pipeline Updates

**Update Deployment Pipelines**
```yaml
# Example GitHub Actions workflow
name: Terraform Deploy
on:
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0
      
      - name: Terraform Init
        run: terraform init
      
      - name: Terraform Plan
        run: terraform plan -out=tfplan
      
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply tfplan
```

**Update Infrastructure Repositories**
- Move Terraform code to appropriate repositories
- Update README and documentation
- Configure branch protection rules
- Set up code review processes

### Team Training and Adoption

**Terraform Training Program**
1. **Basic Concepts**: Resources, providers, state management
2. **HCL Syntax**: Variables, outputs, locals, functions
3. **Module Development**: Creating and using modules
4. **State Management**: Remote state, locking, collaboration
5. **Best Practices**: Code organization, security, testing

**Operational Procedures**
- Infrastructure change management
- Emergency response procedures
- Monitoring and alerting setup
- Backup and disaster recovery

## Best Practices

### Code Organization

**Directory Structure**
```
terraform/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
├── modules/
│   ├── networking/
│   ├── compute/
│   └── database/
├── shared/
│   ├── variables.tf
│   └── outputs.tf
└── scripts/
    ├── deploy.sh
    └── validate.sh
```

**Module Design**
- Keep modules focused and single-purpose
- Use clear variable names and descriptions
- Provide comprehensive outputs
- Include examples and documentation

**State Management**
- Use remote state storage (S3, Terraform Cloud)
- Enable state locking with DynamoDB
- Implement state backup strategies
- Use workspaces for environment separation

### Security Considerations

**Access Control**
- Use IAM roles instead of access keys
- Implement least-privilege principles
- Enable CloudTrail logging
- Use MFA for sensitive operations

**State Security**
- Encrypt state files at rest and in transit
- Restrict access to state storage
- Avoid storing secrets in state
- Use secret management services

**Code Security**
- Implement code review processes
- Use static analysis tools
- Scan for security vulnerabilities
- Follow security best practices

### Monitoring and Observability

**Infrastructure Monitoring**
```hcl
# CloudWatch alarms for key resources
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "high-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  
  dimensions = {
    InstanceId = aws_instance.web.id
  }
}
```

**Terraform Operations Monitoring**
- Monitor plan and apply operations
- Track state changes and drift
- Alert on failed deployments
- Log all infrastructure changes

## Risk Mitigation

### Pre-Migration Risk Assessment

**Resource Criticality Matrix**
| Resource Type | Business Impact | Migration Risk | Mitigation Strategy |
|---------------|----------------|----------------|-------------------|
| Production DB | High | High | Blue-green migration |
| Load Balancer | High | Medium | Gradual traffic shift |
| Dev Environment | Low | Low | Direct migration |
| Monitoring | Medium | Low | Parallel deployment |

**Dependency Analysis**
```bash
# Map resource dependencies
cf2tf analyze-dependencies \
  --input discovery.json \
  --output dependency-map.json \
  --format graphviz

# Generate dependency graph
dot -Tpng dependency-map.dot -o dependencies.png
```

### Migration Risk Controls

**State Backup Strategy**
```bash
# Automated state backup before changes
#!/bin/bash
BACKUP_DIR="./state-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
terraform state pull > $BACKUP_DIR/terraform.tfstate.$TIMESTAMP

echo "State backed up to $BACKUP_DIR/terraform.tfstate.$TIMESTAMP"
```

**Validation Procedures**
```bash
# Comprehensive validation script
#!/bin/bash
set -e

echo "Running pre-migration validation..."

# Validate Terraform configuration
terraform validate

# Check for syntax errors
terraform fmt -check=true

# Run security scan
tfsec .

# Validate against AWS
terraform plan -detailed-exitcode

echo "Validation completed successfully"
```

### Rollback Procedures

**CloudFormation Rollback**
```bash
# Emergency rollback to CloudFormation
#!/bin/bash
STACK_NAME=$1
TEMPLATE_FILE=$2

echo "Rolling back to CloudFormation stack: $STACK_NAME"

# Remove resources from Terraform state
terraform state rm $(terraform state list)

# Recreate CloudFormation stack
aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-body file://$TEMPLATE_FILE \
  --capabilities CAPABILITY_IAM

echo "Rollback initiated. Monitor stack creation in AWS console."
```

**Terraform State Rollback**
```bash
# Rollback Terraform state
#!/bin/bash
BACKUP_FILE=$1

echo "Rolling back Terraform state from backup: $BACKUP_FILE"

# Backup current state
terraform state pull > terraform.tfstate.pre-rollback

# Restore from backup
terraform state push $BACKUP_FILE

echo "State rollback completed. Run 'terraform plan' to verify."
```

## Team Training and Adoption

### Training Curriculum

**Week 1: Terraform Fundamentals**
- Infrastructure as Code concepts
- Terraform architecture and workflow
- HCL syntax and basic resources
- State management basics

**Week 2: Advanced Terraform**
- Modules and composition
- Variables and outputs
- Functions and expressions
- Provisioners and local-exec

**Week 3: AWS Provider Deep Dive**
- AWS resource types
- Provider configuration
- Authentication and authorization
- Best practices for AWS resources

**Week 4: Operations and Best Practices**
- CI/CD integration
- Testing strategies
- Security considerations
- Troubleshooting and debugging

### Hands-On Exercises

**Exercise 1: Basic Infrastructure**
```hcl
# Create a simple VPC with subnets
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "main-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "public-subnet"
  }
}
```

**Exercise 2: Module Development**
```hcl
# modules/web-server/main.tf
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id
  
  vpc_security_group_ids = [aws_security_group.web.id]
  
  tags = {
    Name = var.server_name
  }
}

resource "aws_security_group" "web" {
  name_prefix = "${var.server_name}-"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### Knowledge Transfer

**Documentation Standards**
- Comprehensive README files
- Inline code comments
- Architecture decision records
- Operational runbooks

**Code Review Process**
- Mandatory peer review for all changes
- Security review for sensitive resources
- Performance review for large changes
- Documentation review for new modules

**Mentorship Program**
- Pair experienced Terraform users with newcomers
- Regular knowledge sharing sessions
- Internal Terraform community of practice
- External training and certification support

This migration guide provides a comprehensive framework for successfully transitioning from CloudFormation to Terraform. The key to success is careful planning, thorough testing, and gradual implementation with proper risk mitigation strategies.

