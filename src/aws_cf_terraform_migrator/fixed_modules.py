"""
Fixed Terraform Module Generator

This module generates high-quality Terraform modules with proper resource definitions,
correct syntax, and meaningful resource names.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from jinja2 import Template

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """Information about a generated Terraform module"""
    name: str
    path: str
    resources: List[str]
    variables: Dict[str, Any]
    outputs: Dict[str, Any]
    description: str


@dataclass
class ModuleGenerationResult:
    """Result of module generation"""
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    total_files: int = 0
    total_variables: int = 0
    total_outputs: int = 0
    generation_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class FixedModuleGenerator:
    """Generates high-quality Terraform modules from discovered AWS resources"""
    
    def __init__(self, organization_strategy: str = "hybrid"):
        self.organization_strategy = organization_strategy
        self.terraform_version = ">=1.0"
        self.provider_version = ">=5.0"
    
    def generate_modules(self, 
                        all_resources: Dict[str, Any], 
                        output_dir: str) -> ModuleGenerationResult:
        """Generate Terraform modules from discovered resources"""
        
        start_time = time.time()
        result = ModuleGenerationResult()
        
        try:
            logger.info(f"Generating Terraform modules in {output_dir}")
            
            # Organize resources into modules
            organized_modules = self._organize_resources(all_resources)
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate each module
            for module_name, resource_data in organized_modules.items():
                module_info = self._generate_single_module(
                    module_name, 
                    resource_data, 
                    output_path / "modules" / module_name
                )
                
                result.modules[module_name] = module_info
                result.total_files += len(list((output_path / "modules" / module_name).glob("*.tf")))
                result.total_variables += len(module_info.variables)
                result.total_outputs += len(module_info.outputs)
            
            # Generate root module
            self._generate_root_module(result.modules, output_path)
            result.total_files += len(list(output_path.glob("*.tf")))
            
            # Generate additional files
            self._generate_additional_files(output_path)
            
            result.generation_time = time.time() - start_time
            logger.info(f"Module generation completed: {len(result.modules)} modules, {result.total_files} files")
            
        except Exception as e:
            logger.error(f"Module generation failed: {str(e)}")
            result.errors.append(f"Module generation failed: {str(e)}")
        
        return result
    
    def _organize_resources(self, resources: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Organize resources into logical modules"""
        
        modules = {}
        
        for resource_id, resource_info in resources.items():
            # Determine module based on resource type and properties
            module_name = self._determine_module_name(resource_info)
            
            if module_name not in modules:
                modules[module_name] = {}
            
            modules[module_name][resource_id] = resource_info
        
        return modules
    
    def _determine_module_name(self, resource_info: Any) -> str:
        """Determine the appropriate module name for a resource"""
        
        # Handle StackInfo objects
        if hasattr(resource_info, 'stack_name') and resource_info.stack_name:
            stack_name = resource_info.stack_name.lower()
            # Clean up stack name for module naming
            clean_name = stack_name.replace('-', '_').replace(' ', '_')
            return f"stack_{clean_name}"
        
        # Handle ResourceInfo objects
        if hasattr(resource_info, 'resource_type') and resource_info.resource_type:
            resource_type = resource_info.resource_type
            
            # Group by service
            if resource_type.startswith('AWS::EC2::'):
                return "compute"
            elif resource_type.startswith('AWS::S3::'):
                return "storage"
            elif resource_type.startswith('AWS::RDS::'):
                return "database"
            elif resource_type.startswith('AWS::Lambda::'):
                return "serverless"
            elif resource_type.startswith('AWS::IAM::'):
                return "security"
            elif resource_type.startswith('AWS::VPC::') or resource_type.startswith('AWS::EC2::VPC'):
                return "networking"
            else:
                return "misc"
        
        # Handle dictionary format
        if isinstance(resource_info, dict):
            resource_type = resource_info.get('resource_type', '')
            if resource_type:
                if 'ec2' in resource_type.lower() or 'instance' in resource_type.lower():
                    return "compute"
                elif 's3' in resource_type.lower():
                    return "storage"
                elif 'lambda' in resource_type.lower():
                    return "serverless"
                elif 'iam' in resource_type.lower() or 'role' in resource_type.lower():
                    return "security"
                elif 'vpc' in resource_type.lower():
                    return "networking"
        
        # Default fallback
        return "misc"
    
    def _generate_single_module(self, 
                               module_name: str, 
                               module_resources: Dict[str, Any], 
                               module_path: Path) -> ModuleInfo:
        """Generate a single Terraform module with actual resources"""
        
        logger.info(f"Generating module: {module_name}")
        
        # Create module directory
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Convert resources to Terraform format
        terraform_resources = self._convert_resources_to_terraform(module_resources)
        
        # Generate variables
        variables = self._generate_variables(terraform_resources, module_name)
        
        # Generate outputs
        outputs = self._generate_outputs(terraform_resources, module_name)
        
        # Write module files
        self._write_main_tf(module_path, module_name, terraform_resources)
        self._write_variables_tf(module_path, variables)
        self._write_outputs_tf(module_path, outputs)
        self._write_versions_tf(module_path)
        self._write_module_readme(module_path, module_name, terraform_resources)
        
        return ModuleInfo(
            name=module_name,
            path=str(module_path),
            resources=list(terraform_resources.keys()),
            variables=variables,
            outputs=outputs,
            description=f"Terraform module for {module_name} resources"
        )
    
    def _convert_resources_to_terraform(self, module_resources: Dict[str, Any]) -> Dict[str, Any]:
        """Convert discovered resources to proper Terraform resource blocks"""
        
        terraform_resources = {}
        
        for resource_id, resource_info in module_resources.items():
            try:
                # Handle StackInfo objects (CloudFormation stacks)
                if hasattr(resource_info, 'stack_name') and resource_info.stack_name:
                    # For now, create a placeholder for the stack
                    # In a real implementation, you'd parse the template
                    resource_name = self._sanitize_name(resource_info.stack_name)
                    terraform_resources[f"aws_cloudformation_stack.{resource_name}"] = {
                        'name': f"var.{resource_name}_name",
                        'template_body': f"var.{resource_name}_template",
                        'parameters': f"var.{resource_name}_parameters",
                        'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
                    }
                    continue
                
                # Handle ResourceInfo objects (independent AWS resources)
                if hasattr(resource_info, 'resource_type') and hasattr(resource_info, 'resource_id'):
                    if resource_info.resource_type and resource_info.resource_id:
                        terraform_type = self._map_aws_type_to_terraform(resource_info.resource_type)
                        if terraform_type:
                            resource_name = self._sanitize_name(resource_info.resource_id)
                            terraform_resources[f"{terraform_type}.{resource_name}"] = self._generate_resource_config(
                                terraform_type, resource_info
                            )
                    continue
                
                # Handle dictionary format
                if isinstance(resource_info, dict):
                    resource_type = resource_info.get('resource_type', '')
                    if resource_type:
                        terraform_type = self._map_aws_type_to_terraform(resource_type)
                        if terraform_type:
                            resource_name = self._sanitize_name(resource_id)
                            terraform_resources[f"{terraform_type}.{resource_name}"] = self._generate_resource_config_from_dict(
                                terraform_type, resource_info
                            )
                
            except Exception as e:
                logger.warning(f"Failed to convert resource {resource_id}: {str(e)}")
                continue
        
        return terraform_resources
    
    def _map_aws_type_to_terraform(self, aws_type: str) -> Optional[str]:
        """Map AWS resource types to Terraform resource types"""
        
        mapping = {
            'AWS::EC2::Instance': 'aws_instance',
            'AWS::S3::Bucket': 'aws_s3_bucket',
            'AWS::IAM::Role': 'aws_iam_role',
            'AWS::IAM::Policy': 'aws_iam_policy',
            'AWS::Lambda::Function': 'aws_lambda_function',
            'AWS::VPC::VPC': 'aws_vpc',
            'AWS::EC2::VPC': 'aws_vpc',
            'AWS::EC2::Subnet': 'aws_subnet',
            'AWS::EC2::SecurityGroup': 'aws_security_group',
            'AWS::RDS::DBInstance': 'aws_db_instance',
            'AWS::RDS::DBCluster': 'aws_rds_cluster',
            'AWS::CloudFormation::Stack': 'aws_cloudformation_stack'
        }
        
        # Handle service-based mapping for unknown types
        if aws_type in mapping:
            return mapping[aws_type]
        elif aws_type.startswith('AWS::EC2::'):
            return 'aws_instance'  # Default for EC2 resources
        elif aws_type.startswith('AWS::S3::'):
            return 'aws_s3_bucket'  # Default for S3 resources
        elif aws_type.startswith('AWS::IAM::'):
            return 'aws_iam_role'  # Default for IAM resources
        elif aws_type.startswith('AWS::Lambda::'):
            return 'aws_lambda_function'  # Default for Lambda resources
        
        return None
    
    def _generate_resource_config(self, terraform_type: str, resource_info: Any) -> Dict[str, Any]:
        """Generate Terraform resource configuration"""
        
        config = {}
        resource_name = self._sanitize_name(resource_info.resource_id)
        
        if terraform_type == 'aws_instance':
            config = {
                'ami': f"var.{resource_name}_ami",
                'instance_type': f"var.{resource_name}_instance_type",
                'key_name': f"var.{resource_name}_key_name",
                'vpc_security_group_ids': f"var.{resource_name}_security_groups",
                'subnet_id': f"var.{resource_name}_subnet_id",
                'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
            }
        elif terraform_type == 'aws_s3_bucket':
            config = {
                'bucket': f"var.{resource_name}_bucket_name",
                'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
            }
        elif terraform_type == 'aws_iam_role':
            config = {
                'name': f"var.{resource_name}_role_name",
                'assume_role_policy': f"var.{resource_name}_assume_role_policy",
                'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
            }
        elif terraform_type == 'aws_lambda_function':
            config = {
                'function_name': f"var.{resource_name}_function_name",
                'runtime': f"var.{resource_name}_runtime",
                'handler': f"var.{resource_name}_handler",
                'role': f"var.{resource_name}_role_arn",
                'filename': f"var.{resource_name}_filename",
                'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
            }
        elif terraform_type == 'aws_vpc':
            config = {
                'cidr_block': f"var.{resource_name}_cidr_block",
                'enable_dns_hostnames': f"var.{resource_name}_enable_dns_hostnames",
                'enable_dns_support': f"var.{resource_name}_enable_dns_support",
                'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
            }
        else:
            # Generic configuration
            config = {
                'tags': f"merge(var.tags, {{ Name = \"${{var.name_prefix}}-${{var.environment}}-{resource_name}\" }})"
            }
        
        return config
    
    def _generate_resource_config_from_dict(self, terraform_type: str, resource_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Terraform resource configuration from dictionary"""
        
        resource_id = resource_info.get('resource_id', 'unknown')
        resource_name = self._sanitize_name(resource_id)
        
        return self._generate_resource_config(terraform_type, type('obj', (object,), {
            'resource_id': resource_id,
            'resource_type': resource_info.get('resource_type', '')
        })())
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize resource names for Terraform"""
        
        # Handle None or empty values
        if not name:
            return 'unnamed_resource'
        
        # Convert to string if not already
        name = str(name)
        
        # Remove common prefixes and suffixes
        name = name.replace('arn:aws:', '').replace('AWS-', '').replace('-Stack', '')
        
        # Replace invalid characters
        name = name.replace('-', '_').replace(' ', '_').replace(':', '_').replace('/', '_')
        
        # Remove consecutive underscores
        while '__' in name:
            name = name.replace('__', '_')
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Ensure it starts with a letter
        if name and name[0].isdigit():
            name = f"resource_{name}"
        
        return name.lower() if name else 'unnamed_resource'
    
    def _generate_variables(self, terraform_resources: Dict[str, Any], module_name: str) -> Dict[str, Any]:
        """Generate variables for the module"""
        
        variables = {
            'tags': {
                'description': 'Common tags to be applied to all resources',
                'type': 'map(string)',
                'default': {}
            },
            'environment': {
                'description': 'Environment name (e.g., dev, staging, prod)',
                'type': 'string'
            },
            'region': {
                'description': 'AWS region for resources',
                'type': 'string'
            },
            'name_prefix': {
                'description': 'Prefix for resource names',
                'type': 'string',
                'default': module_name
            }
        }
        
        # Extract variables from resource configurations
        for resource_key, resource_config in terraform_resources.items():
            for config_key, config_value in resource_config.items():
                if isinstance(config_value, str) and config_value.startswith('var.'):
                    var_name = config_value.replace('var.', '')
                    if var_name not in variables:
                        variables[var_name] = {
                            'description': f'Configuration for {config_key}',
                            'type': 'string'
                        }
        
        return variables
    
    def _generate_outputs(self, terraform_resources: Dict[str, Any], module_name: str) -> Dict[str, Any]:
        """Generate outputs for the module"""
        
        outputs = {}
        
        for resource_key in terraform_resources.keys():
            resource_type, resource_name = resource_key.split('.', 1)
            
            # Common outputs
            outputs[f"{resource_name}_id"] = {
                'description': f'ID of {resource_type} {resource_name}',
                'value': f'{resource_type}.{resource_name}.id'
            }
            
            if resource_type != 'aws_cloudformation_stack':
                outputs[f"{resource_name}_arn"] = {
                    'description': f'ARN of {resource_type} {resource_name}',
                    'value': f'{resource_type}.{resource_name}.arn'
                }
        
        return outputs
    
    def _write_main_tf(self, module_path: Path, module_name: str, terraform_resources: Dict[str, Any]):
        """Write main.tf file with actual resources"""
        
        content = f'''# {module_name} Module
# Generated by AWS CloudFormation to Terraform Migrator
# All values are parameterized - no hardcoded values

terraform {{
  required_version = "{self.terraform_version}"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "{self.provider_version}"
    }}
  }}
}}

locals {{
  common_tags = merge(var.tags, {{
    Module      = "{module_name}"
    ManagedBy   = "terraform"
    Environment = var.environment
  }})
  name_prefix = var.name_prefix != "" ? var.name_prefix : var.environment
}}

'''
        
        # Add resources
        for resource_key, resource_config in terraform_resources.items():
            resource_type, resource_name = resource_key.split('.', 1)
            
            content += f'resource "{resource_type}" "{resource_name}" {{\n'
            
            for config_key, config_value in resource_config.items():
                if isinstance(config_value, str):
                    if config_value.startswith('var.') or config_value.startswith('merge(') or config_value.startswith('"${'):
                        content += f'  {config_key} = {config_value}\n'
                    else:
                        content += f'  {config_key} = "{config_value}"\n'
                else:
                    content += f'  {config_key} = {json.dumps(config_value)}\n'
            
            content += '}\n\n'
        
        (module_path / "main.tf").write_text(content)
    
    def _write_variables_tf(self, module_path: Path, variables: Dict[str, Any]):
        """Write variables.tf file"""
        
        content = f'''# Variables for module
# All configurable values are exposed as variables

'''
        
        for var_name, var_config in variables.items():
            content += f'variable "{var_name}" {{\n'
            content += f'  description = "{var_config["description"]}"\n'
            content += f'  type        = {var_config["type"]}\n'
            
            if 'default' in var_config:
                if isinstance(var_config['default'], str):
                    content += f'  default     = "{var_config["default"]}"\n'
                else:
                    content += f'  default     = {json.dumps(var_config["default"])}\n'
            
            content += '}\n\n'
        
        (module_path / "variables.tf").write_text(content)
    
    def _write_outputs_tf(self, module_path: Path, outputs: Dict[str, Any]):
        """Write outputs.tf file"""
        
        content = f'''# Outputs for module
# Expose important resource attributes

'''
        
        for output_name, output_config in outputs.items():
            content += f'output "{output_name}" {{\n'
            content += f'  description = "{output_config["description"]}"\n'
            content += f'  value       = {output_config["value"]}\n'
            content += '}\n\n'
        
        (module_path / "outputs.tf").write_text(content)
    
    def _write_versions_tf(self, module_path: Path):
        """Write versions.tf file"""
        
        content = f'''terraform {{
  required_version = "{self.terraform_version}"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "{self.provider_version}"
    }}
  }}
}}
'''
        
        (module_path / "versions.tf").write_text(content)
    
    def _write_module_readme(self, module_path: Path, module_name: str, terraform_resources: Dict[str, Any]):
        """Write README.md for the module"""
        
        content = f'''# {module_name.title()} Module

This module manages {module_name} resources converted from AWS CloudFormation.

## Resources

This module creates the following resources:

'''
        
        for resource_key in terraform_resources.keys():
            resource_type, resource_name = resource_key.split('.', 1)
            content += f'- `{resource_type}.{resource_name}`\n'
        
        content += f'''
## Usage

```hcl
module "{module_name}" {{
  source = "./modules/{module_name}"
  
  environment = "prod"
  region      = "us-east-1"
  name_prefix = "myapp"
  
  tags = {{
    Project = "MyProject"
    Owner   = "MyTeam"
  }}
}}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | {self.terraform_version} |
| aws | {self.provider_version} |

## Inputs

See `variables.tf` for all available input variables.

## Outputs

See `outputs.tf` for all available outputs.
'''
        
        (module_path / "README.md").write_text(content)
    
    def _generate_root_module(self, modules: Dict[str, ModuleInfo], output_path: Path):
        """Generate root module files"""
        
        # Generate main.tf
        main_content = f'''# Root Module - Generated by AWS CloudFormation to Terraform Migrator
# Orchestrates all infrastructure modules

terraform {{
  required_version = "{self.terraform_version}"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "{self.provider_version}"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
  
  default_tags {{
    tags = var.common_tags
  }}
}}

'''
        
        # Add module calls
        for module_name, module_info in modules.items():
            main_content += f'''module "{module_name}" {{
  source = "./modules/{module_name}"
  
  # Common variables
  environment = var.environment
  region      = var.aws_region
  name_prefix = var.name_prefix
  tags        = var.common_tags
}}

'''
        
        (output_path / "main.tf").write_text(main_content)
        
        # Generate variables.tf
        variables_content = '''# Root module variables

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
}

variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
  default     = {}
}
'''
        
        (output_path / "variables.tf").write_text(variables_content)
        
        # Generate outputs.tf
        outputs_content = '''# Root module outputs

'''
        
        for module_name, module_info in modules.items():
            outputs_content += f'''output "{module_name}_module" {{
  description = "Outputs from {module_name} module"
  value       = module.{module_name}
}}

'''
        
        (output_path / "outputs.tf").write_text(outputs_content)
        
        # Generate versions.tf
        versions_content = f'''terraform {{
  required_version = "{self.terraform_version}"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "{self.provider_version}"
    }}
  }}
}}
'''
        
        (output_path / "versions.tf").write_text(versions_content)
    
    def _generate_additional_files(self, output_path: Path):
        """Generate additional helpful files"""
        
        # Generate terraform.tfvars.example
        tfvars_content = '''# Example Terraform variables file
# Copy this to terraform.tfvars and customize for your environment

aws_region  = "us-east-1"
environment = "dev"
name_prefix = "myapp"

common_tags = {
  Project     = "MyProject"
  Owner       = "MyTeam"
  Environment = "dev"
  ManagedBy   = "terraform"
}
'''
        
        (output_path / "terraform.tfvars.example").write_text(tfvars_content)
        
        # Generate .gitignore
        gitignore_content = '''# Terraform files
*.tfstate
*.tfstate.*
*.tfplan
*.tfplan.*
.terraform/
.terraform.lock.hcl

# Variable files
terraform.tfvars
*.auto.tfvars

# OS files
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo
'''
        
        (output_path / ".gitignore").write_text(gitignore_content)

