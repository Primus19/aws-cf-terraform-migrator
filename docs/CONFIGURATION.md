# Configuration Guide

The CF2TF converter provides extensive configuration options to customize the conversion process according to your specific requirements. This guide covers all available configuration options, their purposes, and best practices for different scenarios.

## Configuration Methods

### 1. Configuration Files

The CF2TF converter supports both YAML and JSON configuration files. YAML is recommended for better readability and comments support.

#### YAML Configuration Example

```yaml
# cf2tf-config.yaml
discovery:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
  profile: "production"
  role_arn: "arn:aws:iam::123456789012:role/CF2TFRole"
  include_deleted_stacks: false
  stack_name_filter: "prod-*"
  max_workers: 10
  services_to_scan:
    - ec2
    - s3
    - rds
    - lambda
    - iam
    - dynamodb

conversion:
  preserve_original_names: true
  add_import_blocks: true
  generate_variables: true
  generate_outputs: true
  handle_intrinsic_functions: true
  convert_conditions: true
  terraform_version: ">=1.0"
  provider_version: ">=5.0"

modules:
  organization_strategy: "service_based"
  module_prefix: "myorg"
  include_examples: true
  include_readme: true
  include_versions_tf: true
  variable_descriptions: true
  output_descriptions: true
  use_locals: true
  group_similar_resources: true

imports:
  generate_import_scripts: true
  validate_imports: true
  create_backup: true
  parallel_imports: false
  max_import_workers: 5
  import_timeout: 300
  retry_failed_imports: true
  max_retries: 3

output:
  output_directory: "./terraform_output"
  create_subdirectories: true
  overwrite_existing: false
  generate_documentation: true
  export_discovery_data: true
  export_format: "json"
  include_metadata: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "cf2tf.log"
  console: true
  max_file_size: 10485760
  backup_count: 5
```

#### JSON Configuration Example

```json
{
  "discovery": {
    "regions": ["us-east-1", "us-west-2"],
    "profile": null,
    "role_arn": null,
    "include_deleted_stacks": false,
    "stack_name_filter": null,
    "max_workers": 10,
    "services_to_scan": ["ec2", "s3", "rds", "lambda"]
  },
  "conversion": {
    "preserve_original_names": true,
    "handle_intrinsic_functions": true,
    "terraform_version": ">=1.0",
    "provider_version": ">=5.0"
  },
  "modules": {
    "organization_strategy": "service_based",
    "include_readme": true,
    "include_versions_tf": true
  },
  "output": {
    "output_directory": "./terraform_output",
    "generate_documentation": true
  }
}
```

### 2. Command Line Arguments

All configuration options can be overridden via command line arguments:

```bash
cfmigrate convert-all \
  --regions us-east-1,us-west-2 \
  --strategy service_based \
  --output ./terraform \
  --terraform-version ">=1.5" \
  --max-workers 15 \
  --include-examples \
  --generate-docs
```

### 3. Environment Variables

Configuration can also be set via environment variables:

```bash
export CF2TF_REGIONS="us-east-1,us-west-2"
export CF2TF_STRATEGY="service_based"
export CF2TF_OUTPUT_DIR="./terraform"
export CF2TF_MAX_WORKERS="10"

cfmigrate convert-all
```

## Configuration Sections

### Discovery Configuration

Controls how the tool discovers AWS resources and CloudFormation stacks.

```yaml
discovery:
  # AWS regions to scan for resources
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
  
  # AWS profile to use (optional)
  profile: "production"
  
  # IAM role to assume for cross-account access (optional)
  role_arn: "arn:aws:iam::123456789012:role/CF2TFRole"
  
  # Include deleted/failed stacks in discovery
  include_deleted_stacks: false
  
  # Filter stacks by name pattern (supports wildcards)
  stack_name_filter: "prod-*"
  
  # Maximum number of parallel workers for discovery
  max_workers: 10
  
  # AWS services to scan for independent resources
  services_to_scan:
    - ec2
    - s3
    - rds
    - lambda
    - iam
    - dynamodb
    - elasticache
    - elbv2
    - elb
    - autoscaling
    - route53
    - cloudfront
    - apigateway
    - sns
    - sqs
```

**Key Options Explained:**

- `regions`: List of AWS regions to scan. The tool will discover resources in all specified regions.
- `profile`: AWS CLI profile to use. If not specified, uses the default profile.
- `role_arn`: IAM role to assume for cross-account resource discovery.
- `stack_name_filter`: Glob pattern to filter CloudFormation stacks by name.
- `max_workers`: Number of parallel threads for discovery operations.
- `services_to_scan`: List of AWS services to scan for independent resources.

### Conversion Configuration

Controls how CloudFormation templates are converted to Terraform.

```yaml
conversion:
  # Preserve original CloudFormation resource names
  preserve_original_names: true
  
  # Add import blocks to generated Terraform
  add_import_blocks: true
  
  # Generate variables.tf files
  generate_variables: true
  
  # Generate outputs.tf files
  generate_outputs: true
  
  # Handle CloudFormation intrinsic functions
  handle_intrinsic_functions: true
  
  # Convert CloudFormation conditions
  convert_conditions: true
  
  # Minimum Terraform version requirement
  terraform_version: ">=1.0"
  
  # AWS provider version requirement
  provider_version: ">=5.0"
```

**Key Options Explained:**

- `preserve_original_names`: When true, keeps original CloudFormation resource names in Terraform.
- `handle_intrinsic_functions`: Converts CloudFormation functions like `!Ref`, `!GetAtt` to Terraform equivalents.
- `convert_conditions`: Attempts to convert CloudFormation conditions to Terraform conditional expressions.
- `terraform_version`: Sets the minimum Terraform version in generated `versions.tf` files.

### Module Configuration

Controls how Terraform modules are organized and generated.

```yaml
modules:
  # Strategy for organizing resources into modules
  organization_strategy: "service_based"  # service_based, stack_based, lifecycle_based, hybrid
  
  # Prefix for module names
  module_prefix: "myorg"
  
  # Include example usage in module documentation
  include_examples: true
  
  # Generate README.md files for each module
  include_readme: true
  
  # Generate versions.tf files for each module
  include_versions_tf: true
  
  # Include descriptions for all variables
  variable_descriptions: true
  
  # Include descriptions for all outputs
  output_descriptions: true
  
  # Use locals blocks for common values
  use_locals: true
  
  # Group similar resources together
  group_similar_resources: true
```

**Organization Strategies:**

- `service_based`: Groups resources by AWS service (networking, compute, storage, etc.)
- `stack_based`: Creates modules based on original CloudFormation stacks
- `lifecycle_based`: Groups resources by lifecycle (shared infrastructure, application resources, data resources)
- `hybrid`: Combines strategies based on stack size and complexity

### Import Configuration

Controls how Terraform import operations are handled.

```yaml
imports:
  # Generate import scripts for discovered resources
  generate_import_scripts: true
  
  # Validate imports after execution
  validate_imports: true
  
  # Create state backup before imports
  create_backup: true
  
  # Execute imports in parallel
  parallel_imports: false
  
  # Maximum number of parallel import workers
  max_import_workers: 5
  
  # Timeout for individual import operations (seconds)
  import_timeout: 300
  
  # Retry failed imports
  retry_failed_imports: true
  
  # Maximum number of retry attempts
  max_retries: 3
```

**Key Options Explained:**

- `parallel_imports`: When true, executes multiple import operations simultaneously.
- `validate_imports`: Runs `terraform plan` after imports to verify success.
- `create_backup`: Creates a backup of the Terraform state before importing.
- `import_timeout`: Maximum time to wait for a single import operation.

### Output Configuration

Controls where and how output files are generated.

```yaml
output:
  # Base directory for all generated files
  output_directory: "./terraform_output"
  
  # Create subdirectories for organization
  create_subdirectories: true
  
  # Overwrite existing files
  overwrite_existing: false
  
  # Generate comprehensive documentation
  generate_documentation: true
  
  # Export raw discovery data
  export_discovery_data: true
  
  # Format for exported data (json, yaml)
  export_format: "json"
  
  # Include metadata in generated files
  include_metadata: true
```

### Logging Configuration

Controls logging behavior and output.

```yaml
logging:
  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  level: "INFO"
  
  # Log message format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Log file path (optional)
  file: "cf2tf.log"
  
  # Enable console logging
  console: true
  
  # Maximum log file size in bytes
  max_file_size: 10485760  # 10MB
  
  # Number of backup log files to keep
  backup_count: 5
```

## Configuration Validation

The CF2TF converter validates all configuration options against a JSON schema. Invalid configurations will result in clear error messages indicating the specific issues.

### Common Validation Errors

**Invalid Region Names**
```
Error: Invalid region 'us-east-3' in discovery.regions. 
Valid regions: us-east-1, us-east-2, us-west-1, us-west-2, ...
```

**Invalid Organization Strategy**
```
Error: Invalid organization_strategy 'custom'. 
Valid options: service_based, stack_based, lifecycle_based, hybrid
```

**Invalid Worker Count**
```
Error: max_workers must be between 1 and 50, got 100
```

## Environment-Specific Configurations

### Development Environment

```yaml
# dev-config.yaml
discovery:
  regions: [us-east-1]
  max_workers: 5
  
conversion:
  preserve_original_names: true
  
modules:
  organization_strategy: "stack_based"
  include_examples: true
  
output:
  output_directory: "./dev-terraform"
  overwrite_existing: true
  
logging:
  level: "DEBUG"
  console: true
```

### Production Environment

```yaml
# prod-config.yaml
discovery:
  regions: [us-east-1, us-west-2, eu-west-1]
  max_workers: 15
  role_arn: "arn:aws:iam::123456789012:role/CF2TFProdRole"
  
conversion:
  preserve_original_names: true
  terraform_version: ">=1.5"
  
modules:
  organization_strategy: "hybrid"
  module_prefix: "prod"
  include_readme: true
  
imports:
  create_backup: true
  validate_imports: true
  
output:
  output_directory: "./prod-terraform"
  generate_documentation: true
  
logging:
  level: "INFO"
  file: "/var/log/cf2tf/conversion.log"
```

## Best Practices

### Configuration Management

1. **Use Version Control**: Store configuration files in version control alongside your infrastructure code.

2. **Environment Separation**: Maintain separate configuration files for different environments.

3. **Sensitive Data**: Never store sensitive information like access keys in configuration files. Use IAM roles or environment variables instead.

4. **Documentation**: Document any custom configuration choices and their rationale.

### Performance Tuning

1. **Worker Threads**: Adjust `max_workers` based on your system resources and AWS API rate limits.

2. **Region Selection**: Only include regions where you have resources to reduce discovery time.

3. **Service Filtering**: Limit `services_to_scan` to services you actually use.

4. **Parallel Imports**: Use parallel imports for large environments, but be cautious of rate limits.

### Security Considerations

1. **IAM Permissions**: Use least-privilege IAM policies for the discovery and conversion process.

2. **Cross-Account Access**: Use IAM roles for cross-account resource discovery rather than access keys.

3. **State Security**: Ensure Terraform state files are stored securely and encrypted.

4. **Audit Logging**: Enable comprehensive logging for audit and troubleshooting purposes.

