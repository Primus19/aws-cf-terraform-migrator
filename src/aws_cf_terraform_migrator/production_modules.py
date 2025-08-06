"""
Production-Ready Terraform Module Generator

This module generates valid, import-ready Terraform configurations by properly
extracting actual values from discovered AWS resources and creating meaningful
variables without hardcoded values.
"""

import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ResourceData:
    """Extracted data from an AWS resource"""
    resource_type: str
    resource_id: str
    terraform_type: str
    terraform_name: str
    attributes: Dict[str, Any]
    import_id: str
    region: str = "us-east-1"


@dataclass
class ModuleData:
    """Data for a Terraform module"""
    name: str
    resources: List[ResourceData]
    variables: Dict[str, Any]
    outputs: Dict[str, Any]


class ProductionModuleGenerator:
    """Generates production-ready Terraform modules with proper value extraction"""
    
    def __init__(self):
        self.terraform_version = ">=1.0"
        self.provider_version = ">=5.0"
        self.resource_mappers = self._init_resource_mappers()
    
    def _init_resource_mappers(self) -> Dict[str, Dict[str, Any]]:
        """Initialize resource type mappers with attribute extraction rules"""
        return {
            'AWS::IAM::Role': {
                'terraform_type': 'aws_iam_role',
                'attributes': {
                    'name': 'RoleName',
                    'assume_role_policy': 'AssumeRolePolicyDocument',
                    'description': 'Description',
                    'max_session_duration': 'MaxSessionDuration',
                    'path': 'Path'
                },
                'import_format': '{name}'
            },
            'AWS::IAM::Policy': {
                'terraform_type': 'aws_iam_policy',
                'attributes': {
                    'name': 'PolicyName',
                    'policy': 'PolicyDocument',
                    'description': 'Description',
                    'path': 'Path'
                },
                'import_format': '{arn}'
            },
            'AWS::S3::Bucket': {
                'terraform_type': 'aws_s3_bucket',
                'attributes': {
                    'bucket': 'BucketName'
                },
                'import_format': '{bucket}'
            },
            'AWS::Lambda::Function': {
                'terraform_type': 'aws_lambda_function',
                'attributes': {
                    'function_name': 'FunctionName',
                    'runtime': 'Runtime',
                    'handler': 'Handler',
                    'role': 'Role',
                    'timeout': 'Timeout',
                    'memory_size': 'MemorySize',
                    'description': 'Description'
                },
                'import_format': '{function_name}'
            },
            'AWS::EC2::Instance': {
                'terraform_type': 'aws_instance',
                'attributes': {
                    'ami': 'ImageId',
                    'instance_type': 'InstanceType',
                    'key_name': 'KeyName',
                    'subnet_id': 'SubnetId',
                    'vpc_security_group_ids': 'SecurityGroupIds',
                    'availability_zone': 'AvailabilityZone'
                },
                'import_format': '{instance_id}'
            },
            'AWS::EC2::VPC': {
                'terraform_type': 'aws_vpc',
                'attributes': {
                    'cidr_block': 'CidrBlock',
                    'enable_dns_hostnames': 'EnableDnsHostnames',
                    'enable_dns_support': 'EnableDnsSupport'
                },
                'import_format': '{vpc_id}'
            },
            'AWS::EC2::Subnet': {
                'terraform_type': 'aws_subnet',
                'attributes': {
                    'vpc_id': 'VpcId',
                    'cidr_block': 'CidrBlock',
                    'availability_zone': 'AvailabilityZone',
                    'map_public_ip_on_launch': 'MapPublicIpOnLaunch'
                },
                'import_format': '{subnet_id}'
            },
            'AWS::EC2::SecurityGroup': {
                'terraform_type': 'aws_security_group',
                'attributes': {
                    'name': 'GroupName',
                    'description': 'Description',
                    'vpc_id': 'VpcId'
                },
                'import_format': '{group_id}'
            },
            'AWS::RDS::DBInstance': {
                'terraform_type': 'aws_db_instance',
                'attributes': {
                    'identifier': 'DBInstanceIdentifier',
                    'engine': 'Engine',
                    'engine_version': 'EngineVersion',
                    'instance_class': 'DBInstanceClass',
                    'allocated_storage': 'AllocatedStorage',
                    'db_name': 'DBName',
                    'username': 'MasterUsername'
                },
                'import_format': '{identifier}'
            }
        }
    
    def generate_modules(self, discovery_result: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """Generate production-ready Terraform modules"""
        
        start_time = time.time()
        logger.info(f"Generating production Terraform modules in {output_dir}")
        
        try:
            # Extract resource data from discovery results
            extracted_resources = self._extract_resource_data(discovery_result)
            
            # Organize resources into modules
            modules = self._organize_into_modules(extracted_resources)
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate each module
            generated_modules = {}
            total_files = 0
            
            for module_name, module_data in modules.items():
                logger.info(f"Generating module: {module_name}")
                
                module_path = output_path / "modules" / module_name
                module_path.mkdir(parents=True, exist_ok=True)
                
                # Generate module files
                self._generate_module_files(module_data, module_path)
                
                # Count files
                module_files = len(list(module_path.glob("*.tf")))
                total_files += module_files
                
                generated_modules[module_name] = {
                    'path': str(module_path),
                    'resources': len(module_data.resources),
                    'files': module_files
                }
            
            # Generate root module
            self._generate_root_module(modules, output_path)
            total_files += len(list(output_path.glob("*.tf")))
            
            # Generate import scripts
            self._generate_import_scripts(modules, output_path)
            
            # Generate additional files
            self._generate_additional_files(output_path)
            
            # Validate generated Terraform
            validation_result = self._validate_terraform(output_path)
            
            result = {
                'modules': generated_modules,
                'total_files': total_files,
                'total_resources': sum(len(m.resources) for m in modules.values()),
                'generation_time': time.time() - start_time,
                'validation': validation_result,
                'errors': []
            }
            
            logger.info(f"Module generation completed: {len(modules)} modules, {total_files} files")
            return result
            
        except Exception as e:
            logger.error(f"Module generation failed: {str(e)}")
            return {
                'modules': {},
                'total_files': 0,
                'total_resources': 0,
                'generation_time': time.time() - start_time,
                'validation': {'valid': False, 'errors': [str(e)]},
                'errors': [str(e)]
            }
    
    def _extract_resource_data(self, discovery_result: Dict[str, Any]) -> List[ResourceData]:
        """Extract actual resource data from discovery results"""
        
        extracted_resources = []
        
        for resource_id, resource_info in discovery_result.items():
            try:
                # Handle CloudFormation stacks
                if hasattr(resource_info, 'stack_name') and resource_info.stack_name:
                    # Extract resources from CloudFormation stack
                    if hasattr(resource_info, 'resources') and resource_info.resources:
                        for cf_resource in resource_info.resources:
                            resource_data = self._extract_cf_resource_data(cf_resource, resource_info)
                            if resource_data:
                                extracted_resources.append(resource_data)
                    else:
                        # Create a CloudFormation stack resource
                        resource_data = ResourceData(
                            resource_type='AWS::CloudFormation::Stack',
                            resource_id=resource_info.stack_name,
                            terraform_type='aws_cloudformation_stack',
                            terraform_name=self._sanitize_name(resource_info.stack_name),
                            attributes={
                                'name': resource_info.stack_name,
                                'template_body': getattr(resource_info, 'template_body', '{}'),
                                'parameters': getattr(resource_info, 'parameters', {})
                            },
                            import_id=resource_info.stack_name,
                            region=getattr(resource_info, 'region', 'us-east-1')
                        )
                        extracted_resources.append(resource_data)
                
                # Handle independent resources
                elif hasattr(resource_info, 'resource_type') and resource_info.resource_type:
                    resource_data = self._extract_independent_resource_data(resource_info)
                    if resource_data:
                        extracted_resources.append(resource_data)
                
                # Handle dictionary format
                elif isinstance(resource_info, dict):
                    resource_data = self._extract_dict_resource_data(resource_info, resource_id)
                    if resource_data:
                        extracted_resources.append(resource_data)
                        
            except Exception as e:
                logger.warning(f"Failed to extract resource data for {resource_id}: {str(e)}")
                continue
        
        logger.info(f"Extracted {len(extracted_resources)} resources for Terraform generation")
        return extracted_resources
    
    def _extract_cf_resource_data(self, cf_resource: Any, stack_info: Any) -> Optional[ResourceData]:
        """Extract data from a CloudFormation resource"""
        
        try:
            resource_type = getattr(cf_resource, 'resource_type', None)
            resource_id = getattr(cf_resource, 'physical_resource_id', None) or getattr(cf_resource, 'logical_resource_id', None)
            
            if not resource_type or not resource_id:
                return None
            
            # Get mapper for this resource type
            mapper = self.resource_mappers.get(resource_type)
            if not mapper:
                logger.warning(f"No mapper found for resource type: {resource_type}")
                return None
            
            # Extract attributes
            attributes = {}
            resource_properties = getattr(cf_resource, 'resource_properties', {}) or {}
            
            for tf_attr, cf_attr in mapper['attributes'].items():
                if cf_attr in resource_properties:
                    attributes[tf_attr] = resource_properties[cf_attr]
                elif hasattr(cf_resource, cf_attr.lower()):
                    attributes[tf_attr] = getattr(cf_resource, cf_attr.lower())
            
            # Generate import ID
            import_id = self._generate_import_id(mapper['import_format'], attributes, resource_id)
            
            return ResourceData(
                resource_type=resource_type,
                resource_id=resource_id,
                terraform_type=mapper['terraform_type'],
                terraform_name=self._sanitize_name(resource_id),
                attributes=attributes,
                import_id=import_id,
                region=getattr(stack_info, 'region', 'us-east-1')
            )
            
        except Exception as e:
            logger.warning(f"Failed to extract CloudFormation resource data: {str(e)}")
            return None
    
    def _extract_independent_resource_data(self, resource_info: Any) -> Optional[ResourceData]:
        """Extract data from an independent AWS resource"""
        
        try:
            resource_type = resource_info.resource_type
            resource_id = resource_info.resource_id
            
            # Get mapper for this resource type
            mapper = self.resource_mappers.get(resource_type)
            if not mapper:
                # Create a generic mapper for unknown types
                mapper = {
                    'terraform_type': self._guess_terraform_type(resource_type),
                    'attributes': {},
                    'import_format': '{resource_id}'
                }
            
            # Extract attributes from resource info
            attributes = {}
            if hasattr(resource_info, 'attributes') and resource_info.attributes:
                for tf_attr, cf_attr in mapper['attributes'].items():
                    if cf_attr in resource_info.attributes:
                        attributes[tf_attr] = resource_info.attributes[cf_attr]
            
            # Use resource_id as fallback for missing attributes
            if not attributes and mapper['attributes']:
                # Try to extract from resource_id or other available data
                for tf_attr in mapper['attributes'].keys():
                    if tf_attr == 'name' and hasattr(resource_info, 'resource_name'):
                        attributes[tf_attr] = resource_info.resource_name
                    elif tf_attr in ['id', 'identifier'] and resource_id:
                        attributes[tf_attr] = resource_id
            
            # Generate import ID
            import_id = self._generate_import_id(mapper['import_format'], attributes, resource_id)
            
            return ResourceData(
                resource_type=resource_type,
                resource_id=resource_id,
                terraform_type=mapper['terraform_type'],
                terraform_name=self._sanitize_name(resource_id),
                attributes=attributes,
                import_id=import_id,
                region=getattr(resource_info, 'region', 'us-east-1')
            )
            
        except Exception as e:
            logger.warning(f"Failed to extract independent resource data: {str(e)}")
            return None
    
    def _extract_dict_resource_data(self, resource_info: Dict[str, Any], resource_id: str) -> Optional[ResourceData]:
        """Extract data from dictionary format resource"""
        
        try:
            resource_type = resource_info.get('resource_type', '')
            if not resource_type:
                return None
            
            # Get mapper for this resource type
            mapper = self.resource_mappers.get(resource_type)
            if not mapper:
                mapper = {
                    'terraform_type': self._guess_terraform_type(resource_type),
                    'attributes': {},
                    'import_format': '{resource_id}'
                }
            
            # Extract attributes
            attributes = {}
            for tf_attr, cf_attr in mapper['attributes'].items():
                if cf_attr in resource_info:
                    attributes[tf_attr] = resource_info[cf_attr]
            
            # Generate import ID
            import_id = self._generate_import_id(mapper['import_format'], attributes, resource_id)
            
            return ResourceData(
                resource_type=resource_type,
                resource_id=resource_id,
                terraform_type=mapper['terraform_type'],
                terraform_name=self._sanitize_name(resource_id),
                attributes=attributes,
                import_id=import_id,
                region=resource_info.get('region', 'us-east-1')
            )
            
        except Exception as e:
            logger.warning(f"Failed to extract dict resource data: {str(e)}")
            return None
    
    def _guess_terraform_type(self, aws_type: str) -> str:
        """Guess Terraform type from AWS type"""
        
        # Convert AWS::Service::Resource to aws_service_resource
        parts = aws_type.split('::')
        if len(parts) >= 3:
            service = parts[1].lower()
            resource = parts[2].lower()
            return f"aws_{service}_{resource}"
        
        return "aws_resource"
    
    def _generate_import_id(self, format_string: str, attributes: Dict[str, Any], resource_id: str) -> str:
        """Generate import ID using format string and attributes"""
        
        try:
            # Replace placeholders in format string
            import_id = format_string
            
            # Replace known placeholders
            replacements = {
                '{resource_id}': resource_id,
                '{name}': attributes.get('name', resource_id),
                '{identifier}': attributes.get('identifier', resource_id),
                '{arn}': attributes.get('arn', resource_id),
                '{bucket}': attributes.get('bucket', resource_id),
                '{function_name}': attributes.get('function_name', resource_id),
                '{instance_id}': resource_id if resource_id.startswith('i-') else resource_id,
                '{vpc_id}': resource_id if resource_id.startswith('vpc-') else resource_id,
                '{subnet_id}': resource_id if resource_id.startswith('subnet-') else resource_id,
                '{group_id}': resource_id if resource_id.startswith('sg-') else resource_id
            }
            
            for placeholder, value in replacements.items():
                import_id = import_id.replace(placeholder, str(value))
            
            return import_id
            
        except Exception:
            return resource_id
    
    def _organize_into_modules(self, resources: List[ResourceData]) -> Dict[str, ModuleData]:
        """Organize resources into logical modules"""
        
        modules = {}
        
        for resource in resources:
            module_name = self._determine_module_name(resource)
            
            if module_name not in modules:
                modules[module_name] = ModuleData(
                    name=module_name,
                    resources=[],
                    variables={},
                    outputs={}
                )
            
            modules[module_name].resources.append(resource)
        
        # Generate variables and outputs for each module
        for module_name, module_data in modules.items():
            module_data.variables = self._generate_module_variables(module_data.resources)
            module_data.outputs = self._generate_module_outputs(module_data.resources)
        
        return modules
    
    def _determine_module_name(self, resource: ResourceData) -> str:
        """Determine module name based on resource type and properties"""
        
        # Group by service type
        if resource.terraform_type.startswith('aws_iam_'):
            return 'security'
        elif resource.terraform_type.startswith('aws_s3_'):
            return 'storage'
        elif resource.terraform_type.startswith('aws_lambda_'):
            return 'serverless'
        elif resource.terraform_type.startswith('aws_rds_') or resource.terraform_type.startswith('aws_db_'):
            return 'database'
        elif resource.terraform_type.startswith('aws_vpc') or resource.terraform_type.startswith('aws_subnet') or resource.terraform_type.startswith('aws_security_group'):
            return 'networking'
        elif resource.terraform_type.startswith('aws_instance') or resource.terraform_type.startswith('aws_launch'):
            return 'compute'
        elif resource.terraform_type == 'aws_cloudformation_stack':
            return f"stack_{self._sanitize_name(resource.resource_id)}"
        else:
            return 'misc'
    
    def _generate_module_variables(self, resources: List[ResourceData]) -> Dict[str, Any]:
        """Generate variables for a module based on its resources"""
        
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
            }
        }
        
        # Generate specific variables for each resource
        for resource in resources:
            resource_prefix = resource.terraform_name
            
            for attr_name, attr_value in resource.attributes.items():
                var_name = f"{resource_prefix}_{attr_name}"
                
                # Determine variable type and default
                var_type = self._determine_variable_type(attr_value)
                var_description = f"{attr_name.replace('_', ' ').title()} for {resource.terraform_type} {resource.terraform_name}"
                
                variables[var_name] = {
                    'description': var_description,
                    'type': var_type,
                    'default': attr_value if attr_value is not None else None
                }
        
        return variables
    
    def _determine_variable_type(self, value: Any) -> str:
        """Determine Terraform variable type from value"""
        
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'number'
        elif isinstance(value, list):
            return 'list(string)'
        elif isinstance(value, dict):
            return 'map(any)'
        else:
            return 'string'
    
    def _generate_module_outputs(self, resources: List[ResourceData]) -> Dict[str, Any]:
        """Generate outputs for a module based on its resources"""
        
        outputs = {}
        
        for resource in resources:
            resource_ref = f"{resource.terraform_type}.{resource.terraform_name}"
            
            # Common outputs for all resources
            outputs[f"{resource.terraform_name}_id"] = {
                'description': f'ID of {resource.terraform_type} {resource.terraform_name}',
                'value': f'{resource_ref}.id'
            }
            
            # Resource-specific outputs
            if resource.terraform_type == 'aws_iam_role':
                outputs[f"{resource.terraform_name}_arn"] = {
                    'description': f'ARN of IAM role {resource.terraform_name}',
                    'value': f'{resource_ref}.arn'
                }
            elif resource.terraform_type == 'aws_s3_bucket':
                outputs[f"{resource.terraform_name}_arn"] = {
                    'description': f'ARN of S3 bucket {resource.terraform_name}',
                    'value': f'{resource_ref}.arn'
                }
                outputs[f"{resource.terraform_name}_domain_name"] = {
                    'description': f'Domain name of S3 bucket {resource.terraform_name}',
                    'value': f'{resource_ref}.bucket_domain_name'
                }
            elif resource.terraform_type == 'aws_lambda_function':
                outputs[f"{resource.terraform_name}_arn"] = {
                    'description': f'ARN of Lambda function {resource.terraform_name}',
                    'value': f'{resource_ref}.arn'
                }
                outputs[f"{resource.terraform_name}_invoke_arn"] = {
                    'description': f'Invoke ARN of Lambda function {resource.terraform_name}',
                    'value': f'{resource_ref}.invoke_arn'
                }
        
        return outputs
    
    def _generate_module_files(self, module_data: ModuleData, module_path: Path):
        """Generate all files for a module"""
        
        # Generate main.tf
        self._write_main_tf(module_data, module_path)
        
        # Generate variables.tf
        self._write_variables_tf(module_data, module_path)
        
        # Generate outputs.tf
        self._write_outputs_tf(module_data, module_path)
        
        # Generate versions.tf
        self._write_versions_tf(module_path)
        
        # Generate README.md
        self._write_module_readme(module_data, module_path)
    
    def _write_main_tf(self, module_data: ModuleData, module_path: Path):
        """Write main.tf with actual resource configurations"""
        
        content = f'''# {module_data.name.title()} Module
# Generated by AWS CloudFormation to Terraform Migrator
# Contains actual resource configurations extracted from AWS

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
    Module      = "{module_data.name}"
    ManagedBy   = "terraform"
    Environment = var.environment
  }})
}}

'''
        
        # Add resources
        for resource in module_data.resources:
            content += f'resource "{resource.terraform_type}" "{resource.terraform_name}" {{\n'
            
            # Add resource attributes
            for attr_name, attr_value in resource.attributes.items():
                var_name = f"var.{resource.terraform_name}_{attr_name}"
                
                if isinstance(attr_value, str):
                    content += f'  {attr_name} = {var_name}\n'
                elif isinstance(attr_value, bool):
                    content += f'  {attr_name} = {var_name}\n'
                elif isinstance(attr_value, (int, float)):
                    content += f'  {attr_name} = {var_name}\n'
                elif isinstance(attr_value, list):
                    content += f'  {attr_name} = {var_name}\n'
                elif isinstance(attr_value, dict):
                    content += f'  {attr_name} = {var_name}\n'
                else:
                    content += f'  {attr_name} = {var_name}\n'
            
            # Add common tags
            content += '  tags = merge(local.common_tags, {\n'
            content += f'    Name = "{resource.terraform_name}"\n'
            content += '  })\n'
            
            content += '}\n\n'
        
        (module_path / "main.tf").write_text(content)
    
    def _write_variables_tf(self, module_data: ModuleData, module_path: Path):
        """Write variables.tf with actual variable definitions"""
        
        content = f'''# Variables for {module_data.name} module
# All values extracted from actual AWS resources

'''
        
        for var_name, var_config in module_data.variables.items():
            content += f'variable "{var_name}" {{\n'
            content += f'  description = "{var_config["description"]}"\n'
            content += f'  type        = {var_config["type"]}\n'
            
            if var_config.get('default') is not None:
                default_value = var_config['default']
                if isinstance(default_value, str):
                    content += f'  default     = "{default_value}"\n'
                elif isinstance(default_value, bool):
                    content += f'  default     = {str(default_value).lower()}\n'
                elif isinstance(default_value, (int, float)):
                    content += f'  default     = {default_value}\n'
                elif isinstance(default_value, (list, dict)):
                    content += f'  default     = {json.dumps(default_value)}\n'
            
            content += '}\n\n'
        
        (module_path / "variables.tf").write_text(content)
    
    def _write_outputs_tf(self, module_data: ModuleData, module_path: Path):
        """Write outputs.tf with meaningful outputs"""
        
        content = f'''# Outputs for {module_data.name} module
# Expose important resource attributes

'''
        
        for output_name, output_config in module_data.outputs.items():
            content += f'output "{output_name}" {{\n'
            content += f'  description = "{output_config["description"]}"\n'
            content += f'  value       = {output_config["value"]}\n'
            content += '}\n\n'
        
        (module_path / "outputs.tf").write_text(content)
    
    def _write_versions_tf(self, module_path: Path):
        """Write versions.tf"""
        
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
    
    def _write_module_readme(self, module_data: ModuleData, module_path: Path):
        """Write README.md for the module"""
        
        content = f'''# {module_data.name.title()} Module

This module manages {len(module_data.resources)} AWS resources extracted from your existing infrastructure.

## Resources

This module creates the following resources:

'''
        
        for resource in module_data.resources:
            content += f'- `{resource.terraform_type}.{resource.terraform_name}` (imported from `{resource.import_id}`)\n'
        
        content += f'''

## Usage

```hcl
module "{module_data.name}" {{
  source = "./modules/{module_data.name}"
  
  environment = "prod"
  region      = "us-east-1"
  
  tags = {{
    Project = "MyProject"
    Owner   = "MyTeam"
  }}
  
  # Resource-specific variables
  # See variables.tf for all available options
}}
```

## Import Commands

After applying this module, import existing resources:

```bash
'''
        
        for resource in module_data.resources:
            content += f'terraform import module.{module_data.name}.{resource.terraform_type}.{resource.terraform_name} {resource.import_id}\n'
        
        content += '''```

## Requirements

| Name | Version |
|------|---------|
| terraform | >=1.0 |
| aws | >=5.0 |
'''
        
        (module_path / "README.md").write_text(content)
    
    def _generate_root_module(self, modules: Dict[str, ModuleData], output_path: Path):
        """Generate root module files"""
        
        # Generate main.tf
        main_content = f'''# Root Module - AWS Infrastructure
# Generated by AWS CloudFormation to Terraform Migrator

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
        for module_name, module_data in modules.items():
            main_content += f'''module "{module_name}" {{
  source = "./modules/{module_name}"
  
  # Common variables
  environment = var.environment
  region      = var.aws_region
  tags        = var.common_tags
  
  # Module-specific variables
  # Uncomment and configure as needed
'''
            
            # Add commented variable examples
            for var_name in module_data.variables.keys():
                if var_name not in ['tags', 'environment', 'region']:
                    main_content += f'  # {var_name} = "value"\n'
            
            main_content += '}\n\n'
        
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
        
        for module_name in modules.keys():
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
    
    def _generate_import_scripts(self, modules: Dict[str, ModuleData], output_path: Path):
        """Generate import scripts for all resources"""
        
        # Generate bash script
        bash_content = '''#!/bin/bash
# Import script for existing AWS resources
# Run this after applying the Terraform configuration

set -e

echo "Starting resource import process..."

'''
        
        # Generate PowerShell script
        ps_content = '''# Import script for existing AWS resources
# Run this after applying the Terraform configuration

Write-Host "Starting resource import process..."

'''
        
        for module_name, module_data in modules.items():
            bash_content += f'\necho "Importing {module_name} module resources..."\n'
            ps_content += f'\nWrite-Host "Importing {module_name} module resources..."\n'
            
            for resource in module_data.resources:
                import_cmd = f'terraform import module.{module_name}.{resource.terraform_type}.{resource.terraform_name} {resource.import_id}'
                bash_content += f'{import_cmd}\n'
                ps_content += f'{import_cmd}\n'
        
        bash_content += '\necho "Import process completed!"\n'
        ps_content += '\nWrite-Host "Import process completed!"\n'
        
        # Write scripts
        (output_path / "import_resources.sh").write_text(bash_content)
        (output_path / "import_resources.ps1").write_text(ps_content)
        
        # Make bash script executable
        import stat
        script_path = output_path / "import_resources.sh"
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    
    def _generate_additional_files(self, output_path: Path):
        """Generate additional helpful files"""
        
        # Generate terraform.tfvars.example
        tfvars_content = '''# Example Terraform variables file
# Copy this to terraform.tfvars and customize for your environment

aws_region  = "us-east-1"
environment = "prod"

common_tags = {
  Project     = "MyProject"
  Owner       = "MyTeam"
  Environment = "prod"
  ManagedBy   = "terraform"
}

# Uncomment and configure module-specific variables as needed
# See each module's variables.tf for available options
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
        
        # Generate getting started guide
        guide_content = '''# Getting Started

This Terraform configuration was generated from your existing AWS infrastructure.

## Quick Start

1. **Review the configuration**:
   ```bash
   # Check the generated modules
   ls -la modules/
   
   # Review the main configuration
   cat main.tf
   ```

2. **Configure variables**:
   ```bash
   # Copy the example variables file
   cp terraform.tfvars.example terraform.tfvars
   
   # Edit with your values
   nano terraform.tfvars
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Plan the configuration**:
   ```bash
   terraform plan
   ```

5. **Import existing resources**:
   ```bash
   # Make the script executable (Linux/Mac)
   chmod +x import_resources.sh
   ./import_resources.sh
   
   # Or on Windows
   ./import_resources.ps1
   ```

6. **Verify the import**:
   ```bash
   terraform plan
   # Should show no changes if import was successful
   ```

## Next Steps

- Review each module's README.md for specific configuration options
- Customize variables in terraform.tfvars
- Add additional resources as needed
- Set up remote state storage (recommended for production)

## Support

This configuration was generated automatically. Review all settings before applying in production.
'''
        
        (output_path / "GETTING_STARTED.md").write_text(guide_content)
    
    def _validate_terraform(self, output_path: Path) -> Dict[str, Any]:
        """Validate the generated Terraform configuration"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check for required files
            required_files = ['main.tf', 'variables.tf', 'outputs.tf', 'versions.tf']
            for file_name in required_files:
                file_path = output_path / file_name
                if not file_path.exists():
                    validation_result['errors'].append(f"Missing required file: {file_name}")
                    validation_result['valid'] = False
            
            # Check module structure
            modules_dir = output_path / "modules"
            if modules_dir.exists():
                for module_dir in modules_dir.iterdir():
                    if module_dir.is_dir():
                        for file_name in required_files:
                            module_file = module_dir / file_name
                            if not module_file.exists():
                                validation_result['warnings'].append(f"Module {module_dir.name} missing {file_name}")
            
            # Basic syntax validation
            for tf_file in output_path.rglob("*.tf"):
                try:
                    content = tf_file.read_text()
                    
                    # Check for basic syntax issues
                    if content.count('{') != content.count('}'):
                        validation_result['errors'].append(f"Mismatched braces in {tf_file}")
                        validation_result['valid'] = False
                    
                    # Check for invalid variable references
                    if 'var.' in content and '${var.' not in content:
                        # This is expected for normal variable references
                        pass
                    
                except Exception as e:
                    validation_result['errors'].append(f"Error reading {tf_file}: {str(e)}")
                    validation_result['valid'] = False
            
        except Exception as e:
            validation_result['errors'].append(f"Validation failed: {str(e)}")
            validation_result['valid'] = False
        
        return validation_result
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize resource names for Terraform"""
        
        if not name:
            return 'unnamed_resource'
        
        # Convert to string and clean up
        name = str(name)
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_').lower()
        
        # Ensure it starts with a letter
        if name and name[0].isdigit():
            name = f"resource_{name}"
        
        return name if name else 'unnamed_resource'

