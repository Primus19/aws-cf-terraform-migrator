#!/usr/bin/env python3
"""
Terraform Module Generator

This module handles the generation and organization of Terraform modules
from converted CloudFormation resources with intelligent organization
strategies and best practices.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import re
from collections import defaultdict
import yaml
from jinja2 import Template

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """Information about a generated Terraform module"""
    name: str
    path: str
    resources: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    locals: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of module generation process"""
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    root_module: Optional[ModuleInfo] = None
    total_files: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ModuleOrganizer:
    """Organizes resources into logical modules based on different strategies"""
    
    def __init__(self, strategy: str = "service_based"):
        """
        Initialize the module organizer
        
        Args:
            strategy: Organization strategy (service_based, stack_based, lifecycle_based, hybrid)
        """
        self.strategy = strategy
        self.service_groups = self._define_service_groups()
        
    def _define_service_groups(self) -> Dict[str, List[str]]:
        """Define logical service groups for resource organization"""
        return {
            'networking': [
                'AWS::EC2::VPC', 'AWS::EC2::Subnet', 'AWS::EC2::InternetGateway',
                'AWS::EC2::VPCGatewayAttachment', 'AWS::EC2::RouteTable', 'AWS::EC2::Route',
                'AWS::EC2::SubnetRouteTableAssociation', 'AWS::EC2::NatGateway',
                'AWS::EC2::EIP', 'AWS::EC2::EIPAssociation', 'AWS::EC2::NetworkInterface',
                'AWS::EC2::NetworkInterfaceAttachment', 'AWS::EC2::VPCEndpoint'
            ],
            'security': [
                'AWS::EC2::SecurityGroup', 'AWS::EC2::SecurityGroupIngress',
                'AWS::EC2::SecurityGroupEgress', 'AWS::IAM::Role', 'AWS::IAM::Policy',
                'AWS::IAM::User', 'AWS::IAM::Group', 'AWS::IAM::InstanceProfile',
                'AWS::IAM::RolePolicyAttachment', 'AWS::IAM::UserPolicyAttachment',
                'AWS::IAM::GroupPolicyAttachment', 'AWS::KMS::Key', 'AWS::KMS::Alias',
                'AWS::SecretsManager::Secret', 'AWS::SecretsManager::SecretVersion'
            ],
            'compute': [
                'AWS::EC2::Instance', 'AWS::EC2::LaunchTemplate', 'AWS::EC2::LaunchConfiguration',
                'AWS::AutoScaling::AutoScalingGroup', 'AWS::AutoScaling::LaunchConfiguration',
                'AWS::Lambda::Function', 'AWS::Lambda::Permission', 'AWS::Lambda::Alias',
                'AWS::Lambda::Version', 'AWS::ECS::Cluster', 'AWS::ECS::Service',
                'AWS::ECS::TaskDefinition'
            ],
            'storage': [
                'AWS::S3::Bucket', 'AWS::S3::BucketPolicy', 'AWS::S3::BucketNotification',
                'AWS::EBS::Volume', 'AWS::EC2::VolumeAttachment', 'AWS::EFS::FileSystem',
                'AWS::EFS::MountTarget'
            ],
            'database': [
                'AWS::RDS::DBInstance', 'AWS::RDS::DBCluster', 'AWS::RDS::DBSubnetGroup',
                'AWS::RDS::DBParameterGroup', 'AWS::RDS::DBClusterParameterGroup',
                'AWS::DynamoDB::Table', 'AWS::ElastiCache::CacheCluster',
                'AWS::ElastiCache::ReplicationGroup', 'AWS::ElastiCache::SubnetGroup'
            ],
            'load_balancing': [
                'AWS::ElasticLoadBalancing::LoadBalancer', 'AWS::ElasticLoadBalancingV2::LoadBalancer',
                'AWS::ElasticLoadBalancingV2::TargetGroup', 'AWS::ElasticLoadBalancingV2::Listener',
                'AWS::ElasticLoadBalancingV2::ListenerRule'
            ],
            'dns': [
                'AWS::Route53::HostedZone', 'AWS::Route53::RecordSet'
            ],
            'cdn': [
                'AWS::CloudFront::Distribution', 'AWS::CloudFront::OriginAccessIdentity'
            ],
            'api': [
                'AWS::ApiGateway::RestApi', 'AWS::ApiGateway::Resource',
                'AWS::ApiGateway::Method', 'AWS::ApiGateway::Deployment',
                'AWS::ApiGateway::Stage'
            ],
            'messaging': [
                'AWS::SNS::Topic', 'AWS::SNS::Subscription', 'AWS::SQS::Queue'
            ],
            'monitoring': [
                'AWS::CloudWatch::Alarm', 'AWS::CloudWatch::Dashboard',
                'AWS::Logs::LogGroup', 'AWS::Logs::LogStream'
            ]
        }
    
    def organize_resources(self, resources: Dict[str, Any], 
                          stacks: Dict[str, Any] = None) -> Dict[str, List[str]]:
        """
        Organize resources into modules based on the selected strategy
        
        Args:
            resources: Dictionary of resources to organize
            stacks: Dictionary of CloudFormation stacks (for stack-based strategy)
            
        Returns:
            Dictionary mapping module names to lists of resource IDs
        """
        if self.strategy == "service_based":
            return self._organize_by_service(resources)
        elif self.strategy == "stack_based":
            return self._organize_by_stack(resources, stacks)
        elif self.strategy == "lifecycle_based":
            return self._organize_by_lifecycle(resources)
        elif self.strategy == "hybrid":
            return self._organize_hybrid(resources, stacks)
        else:
            raise ValueError(f"Unknown organization strategy: {self.strategy}")
    
    def _organize_by_service(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize resources by AWS service type"""
        modules = defaultdict(list)
        
        for resource_id, resource_info in resources.items():
            resource_type = resource_info.get('resource_type', '')
            
            # Find the service group for this resource type
            service_group = None
            for group_name, resource_types in self.service_groups.items():
                if resource_type in resource_types:
                    service_group = group_name
                    break
            
            # If no specific group found, use generic service name
            if not service_group:
                if resource_type.startswith('AWS::'):
                    service_name = resource_type.split('::')[1].lower()
                    service_group = f"{service_name}_resources"
                else:
                    service_group = "other_resources"
            
            modules[service_group].append(resource_id)
        
        return dict(modules)
    
    def _organize_by_stack(self, resources: Dict[str, Any], 
                          stacks: Dict[str, Any] = None) -> Dict[str, List[str]]:
        """Organize resources by CloudFormation stack"""
        modules = defaultdict(list)
        
        for resource_id, resource_info in resources.items():
            stack_name = resource_info.get('stack_name')
            
            if stack_name:
                # Use stack name as module name
                module_name = self._sanitize_module_name(stack_name)
                modules[module_name].append(resource_id)
            else:
                # Resources not from CloudFormation go to independent module
                modules['independent_resources'].append(resource_id)
        
        return dict(modules)
    
    def _organize_by_lifecycle(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize resources by operational lifecycle"""
        modules = defaultdict(list)
        
        # Define lifecycle categories
        shared_infrastructure = [
            'AWS::EC2::VPC', 'AWS::EC2::Subnet', 'AWS::EC2::InternetGateway',
            'AWS::EC2::RouteTable', 'AWS::EC2::Route', 'AWS::EC2::NatGateway',
            'AWS::IAM::Role', 'AWS::KMS::Key', 'AWS::Route53::HostedZone'
        ]
        
        application_resources = [
            'AWS::EC2::Instance', 'AWS::Lambda::Function', 'AWS::ECS::Service',
            'AWS::AutoScaling::AutoScalingGroup', 'AWS::ElasticLoadBalancingV2::LoadBalancer'
        ]
        
        data_resources = [
            'AWS::RDS::DBInstance', 'AWS::RDS::DBCluster', 'AWS::DynamoDB::Table',
            'AWS::S3::Bucket', 'AWS::ElastiCache::ReplicationGroup'
        ]
        
        for resource_id, resource_info in resources.items():
            resource_type = resource_info.get('resource_type', '')
            
            if resource_type in shared_infrastructure:
                modules['shared_infrastructure'].append(resource_id)
            elif resource_type in application_resources:
                modules['application_resources'].append(resource_id)
            elif resource_type in data_resources:
                modules['data_resources'].append(resource_id)
            else:
                modules['supporting_resources'].append(resource_id)
        
        return dict(modules)
    
    def _organize_hybrid(self, resources: Dict[str, Any], 
                        stacks: Dict[str, Any] = None) -> Dict[str, List[str]]:
        """Organize resources using a hybrid approach"""
        # Start with stack-based organization
        stack_modules = self._organize_by_stack(resources, stacks)
        
        # For large stacks, further subdivide by service
        final_modules = {}
        
        for module_name, resource_ids in stack_modules.items():
            if len(resource_ids) > 20:  # Large module threshold
                # Subdivide by service
                module_resources = {rid: resources[rid] for rid in resource_ids}
                service_modules = self._organize_by_service(module_resources)
                
                for service_name, service_resource_ids in service_modules.items():
                    combined_name = f"{module_name}_{service_name}"
                    final_modules[combined_name] = service_resource_ids
            else:
                final_modules[module_name] = resource_ids
        
        return final_modules
    
    def _sanitize_module_name(self, name: str) -> str:
        """Sanitize a name to be a valid Terraform module name"""
        # Convert to lowercase and replace invalid characters
        sanitized = re.sub(r'[^a-z0-9_-]', '_', name.lower())
        
        # Remove duplicate underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores and hyphens
        sanitized = sanitized.strip('_-')
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = f"module_{sanitized}"
        
        return sanitized or "unnamed_module"


class ModuleGenerator:
    """
    Terraform module generator
    
    This class organizes converted resources into logical Terraform modules
    following best practices and configurable strategies.
    """
    
    # Terraform file templates
    MAIN_TF_TEMPLATE = """# {{ module_description }}
# Generated by CF2TF Converter

{% if terraform_version %}
terraform {
  required_version = "{{ terraform_version }}"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "{{ provider_version }}"
    }
  }
}
{% endif %}

{% if locals %}
locals {
{% for key, value in locals.items() %}
  {{ key }} = {{ value | tojson }}
{% endfor %}
}
{% endif %}

{% for resource_type, resources in terraform_resources.items() %}
{% for resource_name, resource_config in resources.items() %}
resource "{{ resource_type }}" "{{ resource_name }}" {
{% for key, value in resource_config.items() %}
  {{ key }} = {{ value | tojson }}
{% endfor %}
}

{% endfor %}
{% endfor %}
"""

    VARIABLES_TF_TEMPLATE = """# Variables for {{ module_name }} module
# Generated by CF2TF Converter

{% for var_name, var_config in variables.items() %}
variable "{{ var_name }}" {
  description = "{{ var_config.description }}"
  type        = {{ var_config.type }}
{% if var_config.default is defined %}
  default     = {{ var_config.default | tojson }}
{% endif %}
{% if var_config.validation is defined %}
  
  validation {
    condition     = {{ var_config.validation.condition }}
    error_message = "{{ var_config.validation.error_message }}"
  }
{% endif %}
}

{% endfor %}
"""

    OUTPUTS_TF_TEMPLATE = """# Outputs for {{ module_name }} module
# Generated by CF2TF Converter

{% for output_name, output_config in outputs.items() %}
output "{{ output_name }}" {
  description = "{{ output_config.description }}"
  value       = {{ output_config.value }}
{% if output_config.sensitive is defined %}
  sensitive   = {{ output_config.sensitive | lower }}
{% endif %}
}

{% endfor %}
"""

    VERSIONS_TF_TEMPLATE = """# Provider version constraints for {{ module_name }} module
# Generated by CF2TF Converter

terraform {
  required_version = "{{ terraform_version }}"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "{{ provider_version }}"
    }
  }
}
"""

    README_TEMPLATE = """# {{ module_name | title }} Module

{{ module_description }}

## Usage

```hcl
module "{{ module_name }}" {
  source = "./modules/{{ module_name }}"
  
{% for var_name, var_config in variables.items() %}
  {{ var_name }} = {{ var_config.example | default('""') }}
{% endfor %}
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | {{ terraform_version }} |
| aws | {{ provider_version }} |

## Providers

| Name | Version |
|------|---------|
| aws | {{ provider_version }} |

## Resources

{% for resource_type, resources in terraform_resources.items() %}
{% for resource_name in resources.keys() %}
| {{ resource_type }}.{{ resource_name }} | resource |
{% endfor %}
{% endfor %}

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
{% for var_name, var_config in variables.items() %}
| {{ var_name }} | {{ var_config.description }} | `{{ var_config.type }}` | {{ var_config.default | default('n/a') }} | {{ 'no' if var_config.default is defined else 'yes' }} |
{% endfor %}

## Outputs

| Name | Description |
|------|-------------|
{% for output_name, output_config in outputs.items() %}
| {{ output_name }} | {{ output_config.description }} |
{% endfor %}

## Generated Resources

This module was generated from the following CloudFormation resources:

{% for resource_id in original_resources %}
- {{ resource_id }}
{% endfor %}
"""

    def __init__(self, 
                 organization_strategy: str = "service_based",
                 module_prefix: str = "",
                 include_examples: bool = True,
                 include_readme: bool = True,
                 include_versions_tf: bool = True,
                 terraform_version: str = ">=1.0",
                 provider_version: str = ">=5.0"):
        """
        Initialize the module generator
        
        Args:
            organization_strategy: Strategy for organizing resources into modules
            module_prefix: Prefix to add to module names
            include_examples: Whether to include example usage
            include_readme: Whether to generate README files
            include_versions_tf: Whether to generate versions.tf files
            terraform_version: Required Terraform version
            provider_version: Required AWS provider version
        """
        self.organizer = ModuleOrganizer(organization_strategy)
        self.module_prefix = module_prefix
        self.include_examples = include_examples
        self.include_readme = include_readme
        self.include_versions_tf = include_versions_tf
        self.terraform_version = terraform_version
        self.provider_version = provider_version
        
        logger.info(f"Initialized ModuleGenerator with {organization_strategy} strategy")
    
    def generate_modules(self, 
                        converted_resources: Dict[str, Any],
                        discovery_resources: Dict[str, Any],
                        output_dir: str,
                        stacks: Dict[str, Any] = None) -> GenerationResult:
        """
        Generate Terraform modules from converted resources
        
        Args:
            converted_resources: Resources converted from CloudFormation
            discovery_resources: Resources discovered from AWS
            output_dir: Output directory for generated modules
            stacks: CloudFormation stacks information
            
        Returns:
            GenerationResult with module information and statistics
        """
        logger.info(f"Generating Terraform modules in {output_dir}")
        
        result = GenerationResult()
        output_path = Path(output_dir)
        
        try:
            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Combine all resources
            all_resources = {**converted_resources, **discovery_resources}
            
            # Organize resources into modules
            module_organization = self.organizer.organize_resources(all_resources, stacks)
            
            # Generate each module
            for module_name, resource_ids in module_organization.items():
                if not resource_ids:  # Skip empty modules
                    continue
                
                try:
                    module_info = self._generate_single_module(
                        module_name, resource_ids, all_resources, output_path
                    )
                    result.modules[module_name] = module_info
                    
                except Exception as e:
                    error_msg = f"Failed to generate module {module_name}: {str(e)}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
            
            # Generate root module that calls all submodules
            if result.modules:
                root_module = self._generate_root_module(result.modules, output_path)
                result.root_module = root_module
            
            # Count total files generated
            result.total_files = self._count_generated_files(output_path)
            
            logger.info(f"Module generation completed: {len(result.modules)} modules, {result.total_files} files")
            
        except Exception as e:
            error_msg = f"Module generation failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def _generate_single_module(self, 
                               module_name: str, 
                               resource_ids: List[str],
                               all_resources: Dict[str, Any],
                               output_path: Path) -> ModuleInfo:
        """Generate a single Terraform module"""
        
        logger.debug(f"Generating module: {module_name}")
        
        # Create module directory
        module_dir = output_path / "modules" / module_name
        module_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect module resources
        module_resources = {}
        module_variables = {}
        module_outputs = {}
        module_locals = {}
        original_resource_ids = []
        
        for resource_id in resource_ids:
            if resource_id in all_resources:
                resource_info = all_resources[resource_id]
                original_resource_ids.append(resource_id)
                
                # Extract Terraform configuration if available
                if 'terraform_config' in resource_info:
                    tf_config = resource_info['terraform_config']
                    
                    # Merge resources
                    if 'resource' in tf_config:
                        for res_type, resources in tf_config['resource'].items():
                            if res_type not in module_resources:
                                module_resources[res_type] = {}
                            module_resources[res_type].update(resources)
                    
                    # Merge variables
                    if 'variables' in tf_config:
                        module_variables.update(tf_config['variables'])
                    
                    # Merge outputs
                    if 'outputs' in tf_config:
                        module_outputs.update(tf_config['outputs'])
                    
                    # Merge locals
                    if 'locals' in tf_config:
                        module_locals.update(tf_config['locals'])
        
        # Generate additional variables and outputs based on resource analysis
        additional_vars, additional_outputs = self._analyze_module_interfaces(
            module_resources, module_name
        )
        module_variables.update(additional_vars)
        module_outputs.update(additional_outputs)
        
        # Generate module files
        self._write_main_tf(module_dir, module_name, module_resources, module_locals)
        
        if module_variables:
            self._write_variables_tf(module_dir, module_name, module_variables)
        
        if module_outputs:
            self._write_outputs_tf(module_dir, module_name, module_outputs)
        
        if self.include_versions_tf:
            self._write_versions_tf(module_dir, module_name)
        
        if self.include_readme:
            self._write_readme_md(
                module_dir, module_name, module_resources, 
                module_variables, module_outputs, original_resource_ids
            )
        
        # Create module info
        module_info = ModuleInfo(
            name=module_name,
            path=str(module_dir),
            resources=resource_ids,
            variables=module_variables,
            outputs=module_outputs,
            locals=module_locals,
            description=f"Terraform module for {module_name} resources"
        )
        
        return module_info
    
    def _generate_root_module(self, modules: Dict[str, ModuleInfo], 
                             output_path: Path) -> ModuleInfo:
        """Generate root module that orchestrates all submodules"""
        
        logger.debug("Generating root module")
        
        # Create root module files
        root_main_content = self._generate_root_main_tf(modules)
        root_variables_content = self._generate_root_variables_tf(modules)
        root_outputs_content = self._generate_root_outputs_tf(modules)
        
        # Write root module files
        with open(output_path / "main.tf", 'w') as f:
            f.write(root_main_content)
        
        with open(output_path / "variables.tf", 'w') as f:
            f.write(root_variables_content)
        
        with open(output_path / "outputs.tf", 'w') as f:
            f.write(root_outputs_content)
        
        if self.include_versions_tf:
            with open(output_path / "versions.tf", 'w') as f:
                f.write(self._generate_versions_tf_content("root"))
        
        # Generate root README
        if self.include_readme:
            root_readme_content = self._generate_root_readme(modules)
            with open(output_path / "README.md", 'w') as f:
                f.write(root_readme_content)
        
        root_module = ModuleInfo(
            name="root",
            path=str(output_path),
            resources=[],
            description="Root module that orchestrates all infrastructure modules"
        )
        
        return root_module
    
    def _analyze_module_interfaces(self, module_resources: Dict[str, Any], 
                                  module_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Analyze module resources to determine appropriate variables and outputs"""
        
        variables = {}
        outputs = {}
        
        # Common variables based on resource types
        has_ec2 = any('aws_instance' in res_type for res_type in module_resources.keys())
        has_rds = any('aws_db_instance' in res_type for res_type in module_resources.keys())
        has_s3 = any('aws_s3_bucket' in res_type for res_type in module_resources.keys())
        
        # Add common variables
        if has_ec2 or has_rds:
            variables['environment'] = {
                'description': 'Environment name (e.g., dev, staging, prod)',
                'type': 'string',
                'default': 'dev'
            }
        
        if any(res_type in module_resources for res_type in ['aws_instance', 'aws_db_instance', 'aws_s3_bucket']):
            variables['tags'] = {
                'description': 'Common tags to apply to all resources',
                'type': 'map(string)',
                'default': {}
            }
        
        # Add outputs for commonly referenced resources
        for res_type, resources in module_resources.items():
            for res_name in resources.keys():
                if res_type == 'aws_vpc':
                    outputs[f'{res_name}_id'] = {
                        'description': f'ID of the {res_name} VPC',
                        'value': f'aws_vpc.{res_name}.id'
                    }
                elif res_type == 'aws_subnet':
                    outputs[f'{res_name}_id'] = {
                        'description': f'ID of the {res_name} subnet',
                        'value': f'aws_subnet.{res_name}.id'
                    }
                elif res_type == 'aws_security_group':
                    outputs[f'{res_name}_id'] = {
                        'description': f'ID of the {res_name} security group',
                        'value': f'aws_security_group.{res_name}.id'
                    }
                elif res_type == 'aws_s3_bucket':
                    outputs[f'{res_name}_name'] = {
                        'description': f'Name of the {res_name} S3 bucket',
                        'value': f'aws_s3_bucket.{res_name}.id'
                    }
                    outputs[f'{res_name}_arn'] = {
                        'description': f'ARN of the {res_name} S3 bucket',
                        'value': f'aws_s3_bucket.{res_name}.arn'
                    }
        
        return variables, outputs
    
    def _write_main_tf(self, module_dir: Path, module_name: str, 
                      resources: Dict[str, Any], locals_dict: Dict[str, Any]):
        """Write main.tf file for a module"""
        
        template = Template(self.MAIN_TF_TEMPLATE)
        content = template.render(
            module_description=f"Terraform module for {module_name} resources",
            terraform_version=self.terraform_version,
            provider_version=self.provider_version,
            terraform_resources=resources,
            locals=locals_dict
        )
        
        with open(module_dir / "main.tf", 'w') as f:
            f.write(content)
    
    def _write_variables_tf(self, module_dir: Path, module_name: str, 
                           variables: Dict[str, Any]):
        """Write variables.tf file for a module"""
        
        template = Template(self.VARIABLES_TF_TEMPLATE)
        content = template.render(
            module_name=module_name,
            variables=variables
        )
        
        with open(module_dir / "variables.tf", 'w') as f:
            f.write(content)
    
    def _write_outputs_tf(self, module_dir: Path, module_name: str, 
                         outputs: Dict[str, Any]):
        """Write outputs.tf file for a module"""
        
        template = Template(self.OUTPUTS_TF_TEMPLATE)
        content = template.render(
            module_name=module_name,
            outputs=outputs
        )
        
        with open(module_dir / "outputs.tf", 'w') as f:
            f.write(content)
    
    def _write_versions_tf(self, module_dir: Path, module_name: str):
        """Write versions.tf file for a module"""
        
        template = Template(self.VERSIONS_TF_TEMPLATE)
        content = template.render(
            module_name=module_name,
            terraform_version=self.terraform_version,
            provider_version=self.provider_version
        )
        
        with open(module_dir / "versions.tf", 'w') as f:
            f.write(content)
    
    def _write_readme_md(self, module_dir: Path, module_name: str,
                        resources: Dict[str, Any], variables: Dict[str, Any],
                        outputs: Dict[str, Any], original_resources: List[str]):
        """Write README.md file for a module"""
        
        template = Template(self.README_TEMPLATE)
        content = template.render(
            module_name=module_name,
            module_description=f"This module manages {module_name} resources converted from CloudFormation.",
            terraform_version=self.terraform_version,
            provider_version=self.provider_version,
            terraform_resources=resources,
            variables=variables,
            outputs=outputs,
            original_resources=original_resources
        )
        
        with open(module_dir / "README.md", 'w') as f:
            f.write(content)
    
    def _generate_root_main_tf(self, modules: Dict[str, ModuleInfo]) -> str:
        """Generate main.tf content for root module"""
        
        lines = [
            "# Root Terraform configuration",
            "# Generated by CF2TF Converter",
            "",
            "terraform {",
            f'  required_version = "{self.terraform_version}"',
            "",
            "  required_providers {",
            "    aws = {",
            '      source  = "hashicorp/aws"',
            f'      version = "{self.provider_version}"',
            "    }",
            "  }",
            "}",
            "",
            "provider \"aws\" {",
            "  # Configuration options",
            "}",
            ""
        ]
        
        # Add module calls
        for module_name, module_info in modules.items():
            lines.extend([
                f'module "{module_name}" {{',
                f'  source = "./modules/{module_name}"',
                ""
            ])
            
            # Add variable references
            for var_name in module_info.variables.keys():
                lines.append(f'  {var_name} = var.{var_name}')
            
            lines.extend([
                "}",
                ""
            ])
        
        return '\n'.join(lines)
    
    def _generate_root_variables_tf(self, modules: Dict[str, ModuleInfo]) -> str:
        """Generate variables.tf content for root module"""
        
        lines = [
            "# Root module variables",
            "# Generated by CF2TF Converter",
            ""
        ]
        
        # Collect all unique variables from modules
        all_variables = {}
        for module_info in modules.values():
            all_variables.update(module_info.variables)
        
        # Generate variable definitions
        for var_name, var_config in all_variables.items():
            lines.extend([
                f'variable "{var_name}" {{',
                f'  description = "{var_config.get("description", "")}"',
                f'  type        = {var_config.get("type", "string")}'
            ])
            
            if 'default' in var_config:
                lines.append(f'  default     = {json.dumps(var_config["default"])}')
            
            lines.extend([
                "}",
                ""
            ])
        
        return '\n'.join(lines)
    
    def _generate_root_outputs_tf(self, modules: Dict[str, ModuleInfo]) -> str:
        """Generate outputs.tf content for root module"""
        
        lines = [
            "# Root module outputs",
            "# Generated by CF2TF Converter",
            ""
        ]
        
        # Generate outputs that expose module outputs
        for module_name, module_info in modules.items():
            for output_name, output_config in module_info.outputs.items():
                prefixed_name = f"{module_name}_{output_name}"
                lines.extend([
                    f'output "{prefixed_name}" {{',
                    f'  description = "{output_config.get("description", "")}"',
                    f'  value       = module.{module_name}.{output_name}',
                    "}",
                    ""
                ])
        
        return '\n'.join(lines)
    
    def _generate_versions_tf_content(self, module_name: str) -> str:
        """Generate versions.tf content"""
        
        return f"""# Provider version constraints for {module_name} module
# Generated by CF2TF Converter

terraform {{
  required_version = "{self.terraform_version}"
  
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "{self.provider_version}"
    }}
  }}
}}
"""
    
    def _generate_root_readme(self, modules: Dict[str, ModuleInfo]) -> str:
        """Generate README.md content for root module"""
        
        lines = [
            "# Terraform Infrastructure",
            "",
            "This Terraform configuration was generated by CF2TF Converter from CloudFormation templates.",
            "",
            "## Usage",
            "",
            "1. Initialize Terraform:",
            "   ```bash",
            "   terraform init",
            "   ```",
            "",
            "2. Review the plan:",
            "   ```bash",
            "   terraform plan",
            "   ```",
            "",
            "3. Apply the configuration:",
            "   ```bash",
            "   terraform apply",
            "   ```",
            "",
            "## Modules",
            "",
            "This configuration includes the following modules:",
            ""
        ]
        
        for module_name, module_info in modules.items():
            lines.extend([
                f"### {module_name}",
                f"- **Path**: `{module_info.path}`",
                f"- **Resources**: {len(module_info.resources)}",
                f"- **Description**: {module_info.description}",
                ""
            ])
        
        lines.extend([
            "## Requirements",
            "",
            "| Name | Version |",
            "|------|---------|",
            f"| terraform | {self.terraform_version} |",
            f"| aws | {self.provider_version} |",
            "",
            "## Import Instructions",
            "",
            "Before applying this configuration, you need to import existing AWS resources:",
            "",
            "1. Run the import script:",
            "   ```bash",
            "   ./import_resources.sh",
            "   ```",
            "",
            "2. Verify the import was successful:",
            "   ```bash",
            "   terraform plan",
            "   ```",
            "",
            "The plan should show no changes if all resources were imported correctly.",
            ""
        ])
        
        return '\n'.join(lines)
    
    def _count_generated_files(self, output_path: Path) -> int:
        """Count the total number of generated files"""
        
        count = 0
        for file_path in output_path.rglob("*.tf"):
            count += 1
        for file_path in output_path.rglob("*.md"):
            count += 1
        
        return count


if __name__ == "__main__":
    # Example usage
    generator = ModuleGenerator(
        organization_strategy="service_based",
        include_readme=True,
        include_versions_tf=True
    )
    
    # Example converted resources
    converted_resources = {
        'vpc-12345': {
            'resource_type': 'AWS::EC2::VPC',
            'terraform_config': {
                'resource': {
                    'aws_vpc': {
                        'main': {
                            'cidr_block': '10.0.0.0/16',
                            'enable_dns_hostnames': True
                        }
                    }
                }
            }
        }
    }
    
    result = generator.generate_modules(
        converted_resources=converted_resources,
        discovery_resources={},
        output_dir="./terraform_output"
    )
    
    print(f"Generated {len(result.modules)} modules with {result.total_files} files")
    if result.errors:
        print(f"Errors: {result.errors}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")

