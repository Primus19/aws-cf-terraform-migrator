# AWS CloudFormation to Terraform Migrator

A production-ready tool for migrating AWS CloudFormation stacks to Terraform with zero downtime. This tool discovers existing CloudFormation stacks and AWS resources, converts them to Terraform configuration, and generates import scripts to maintain existing infrastructure.

## Features

- Discovers CloudFormation stacks across multiple AWS regions
- Finds independent AWS resources not managed by CloudFormation
- Converts CloudFormation templates to Terraform configuration
- Generates modular Terraform code with proper variable management
- Creates import scripts for zero-downtime migration
- Supports 50+ AWS resource types
- Cross-platform compatibility (Windows, Linux, macOS)

## Requirements

- Python 3.8 or higher
- AWS CLI configured with appropriate permissions
- Terraform (for applying the generated configuration)

## Installation

### Quick Start

1. Download and extract the tool
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the tool:
   ```bash
   pip install -e .
   ```

### Alternative: Direct Python Execution

If you prefer not to install the package, you can run it directly:

```bash
python run_cfmigrate.py --help
```

## Usage

### Complete Migration (Recommended)

Convert everything in one command:

```bash
# Linux/macOS
python run_cfmigrate.py convert-all --regions us-east-1 --output ./terraform

# Windows
python run_cfmigrate.py convert-all --regions us-east-1 --output ./terraform
```

### Step-by-Step Process

1. **Discover resources:**
   ```bash
   python run_cfmigrate.py discover --regions us-east-1 --output discovery.json
   ```

2. **Convert to Terraform:**
   ```bash
   python run_cfmigrate.py convert --input discovery.json --output ./terraform
   ```

3. **Generate import scripts:**
   ```bash
   python run_cfmigrate.py generate-imports --terraform-dir ./terraform
   ```

### Apply the Migration

After running the tool:

1. **Initialize Terraform:**
   ```bash
   cd terraform
   terraform init
   ```

2. **Import existing resources:**
   ```bash
   # Linux/macOS
   chmod +x import_resources.sh
   ./import_resources.sh
   
   # Windows
   .\import_resources.ps1
   ```

3. **Verify the plan:**
   ```bash
   terraform plan
   ```
   
   The plan should show no changes if the import was successful.

## Generated Structure

The tool creates a well-organized Terraform project:

```
terraform/
├── main.tf                    # Root module configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars.example  # Example variable values
├── import_resources.sh        # Import script (Linux/macOS)
├── import_resources.ps1       # Import script (Windows)
├── getting_started.md         # Step-by-step guide
└── modules/
    ├── networking/            # VPC, subnets, security groups
    ├── compute/               # EC2, Auto Scaling groups
    ├── storage/               # S3, EBS volumes
    └── database/              # RDS, DynamoDB
```

## Configuration

The tool supports various configuration options:

- **Organization Strategy**: Choose how to organize modules (service-based, stack-based, hybrid)
- **Module Prefix**: Add custom prefixes to module names
- **Resource Naming**: Preserve original AWS resource names
- **Parallel Processing**: Enable parallel resource discovery and conversion

See `docs/configuration.md` for detailed configuration options.

## Supported AWS Resources

The tool supports 50+ AWS resource types including:

- **Compute**: EC2, Auto Scaling, Lambda
- **Networking**: VPC, Subnets, Security Groups, Load Balancers
- **Storage**: S3, EBS, EFS
- **Database**: RDS, DynamoDB
- **Security**: IAM, KMS, Secrets Manager
- **Monitoring**: CloudWatch
- **And many more...**

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure your AWS credentials have sufficient permissions
2. **Import Failures**: Some resources may require manual import adjustments
3. **Module Conflicts**: Check for naming conflicts in generated modules

See `docs/troubleshooting.md` for detailed troubleshooting steps.

## Safety Features

- **Read-Only Operation**: The tool never modifies or deletes existing AWS resources
- **Backup Creation**: Automatically creates backups before any operations
- **Validation**: Built-in validation for generated Terraform code
- **Dry-Run Mode**: Test the migration without making changes

## Support

For issues and questions:

1. Check the troubleshooting guide: `docs/troubleshooting.md`
2. Review the configuration documentation: `docs/configuration.md`
3. See usage examples: `docs/usage_examples.md`

## License

This tool is provided as-is for infrastructure migration purposes.

