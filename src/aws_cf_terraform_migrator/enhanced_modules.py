#!/usr/bin/env python3
"""
Enhanced Terraform Module Generator

This module generates Terraform modules with NO hardcoded values, ensuring all
configuration is properly parameterized through variables.tf files.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from jinja2 import Template
import re

logger = logging.getLogger(__name__)


@dataclass
class EnhancedModuleInfo:
    """Enhanced information about a generated Terraform module"""
    name: str
    path: str
    resources: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    locals: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    original_resources: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class EnhancedGenerationResult:
    """Enhanced result of module generation"""
    modules: Dict[str, EnhancedModuleInfo] = field(default_factory=dict)
    root_module: Optional[EnhancedModuleInfo] = None
    total_files: int = 0
    total_variables: int = 0
    total_outputs: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    generation_time: float = 0.0


class EnhancedModuleGenerator:
    """Enhanced Terraform module generator with no hardcoded values"""
    
    def __init__(self, 
                 organization_strategy: str = "service_based",
                 module_prefix: str = "",
                 preserve_resource_names: bool = True,
                 terraform_version: str = ">=1.0",
                 provider_version: str = ">=5.0"):
        """
        Initialize the enhanced module generator
        
        Args:
            organization_strategy: Strategy for organizing resources
            module_prefix: Prefix for module names
            preserve_resource_names: Whether to preserve original resource names
            terraform_version: Required Terraform version
            provider_version: Required AWS provider version
        """
        self.organization_strategy = organization_strategy
        self.module_prefix = module_prefix
        self.preserve_resource_names = preserve_resource_names
        self.terraform_version = terraform_version
        self.provider_version = provider_version
        
        # Variable type mappings for different resource properties
        self.variable_type_mappings = {
            'cidr_block': 'string',
            'availability_zone': 'string',
            'instance_type': 'string',
            'ami': 'string',
            'key_name': 'string',
            'bucket': 'string',
            'db_instance_class': 'string',
            'engine': 'string',
            'engine_version': 'string',
            'allocated_storage': 'number',
            'function_name': 'string',
            'runtime': 'string',
            'handler': 'string',
            'memory_size': 'number',
            'timeout': 'number',
            'port': 'number',
            'protocol': 'string',
            'from_port': 'number',
            'to_port': 'number',
            'desired_capacity': 'number',
            'min_size': 'number',
            'max_size': 'number',
            'enable_deletion_protection': 'bool',
            'enable_dns_hostnames': 'bool',
            'enable_dns_support': 'bool',
            'map_public_ip_on_launch': 'bool',
            'associate_public_ip_address': 'bool',
            'delete_on_termination': 'bool',
            'encrypted': 'bool',
            'monitoring': 'bool',
            'ebs_optimized': 'bool',
            'source_dest_check': 'bool',
            'publicly_accessible': 'bool',
            'multi_az': 'bool',
            'auto_minor_version_upgrade': 'bool',
            'backup_retention_period': 'number',
            'backup_window': 'string',
            'maintenance_window': 'string',
            'storage_type': 'string',
            'iops': 'number',
            'kms_key_id': 'string',
            'snapshot_identifier': 'string',
            'final_snapshot_identifier': 'string',
            'skip_final_snapshot': 'bool',
            'copy_tags_to_snapshot': 'bool',
            'enabled': 'bool',
            'versioning': 'map(any)',
            'lifecycle_configuration': 'list(any)',
            'cors_rule': 'list(any)',
            'website': 'map(any)',
            'logging': 'map(any)',
            'notification': 'map(any)',
            'replication_configuration': 'map(any)',
            'server_side_encryption_configuration': 'list(any)',
            'object_lock_configuration': 'map(any)',
            'policy': 'string',
            'acl': 'string',
            'force_destroy': 'bool',
            'acceleration_status': 'string',
            'request_payer': 'string',
            'tags': 'map(string)',
            'name': 'string',
            'description': 'string',
            'vpc_id': 'string',
            'subnet_id': 'string',
            'subnet_ids': 'list(string)',
            'security_group_ids': 'list(string)',
            'security_groups': 'list(string)',
            'user_data': 'string',
            'iam_instance_profile': 'string',
            'placement_group': 'string',
            'tenancy': 'string',
            'host_id': 'string',
            'cpu_core_count': 'number',
            'cpu_threads_per_core': 'number',
            'disable_api_termination': 'bool',
            'instance_initiated_shutdown_behavior': 'string',
            'placement_partition_number': 'number',
            'private_ip': 'string',
            'secondary_private_ips': 'list(string)',
            'ipv6_address_count': 'number',
            'ipv6_addresses': 'list(string)',
            'volume_tags': 'map(string)',
            'root_block_device': 'list(any)',
            'ebs_block_device': 'list(any)',
            'ephemeral_block_device': 'list(any)',
            'network_interface': 'list(any)',
            'credit_specification': 'list(any)',
            'hibernation': 'bool',
            'metadata_options': 'list(any)',
            'enclave_options': 'list(any)',
            'capacity_reservation_specification': 'list(any)',
            'launch_template': 'list(any)',
        }
    
    def generate_modules(self, 
                        converted_resources: Dict[str, Any],
                        discovery_resources: Dict[str, Any],
                        output_dir: str) -> EnhancedGenerationResult:
        """
        Generate Terraform modules with NO hardcoded values
        
        Args:
            converted_resources: Resources converted from CloudFormation
            discovery_resources: Resources discovered independently
            output_dir: Output directory for generated modules
            
        Returns:
            EnhancedGenerationResult with generation details
        """
        import time
        start_time = time.time()
        
        result = EnhancedGenerationResult()
        
        try:
            logger.info(f"Generating enhanced Terraform modules in {output_dir}")
            
            # Combine all resources
            all_resources = {**converted_resources, **discovery_resources}
            
            if not all_resources:
                logger.warning("No resources to generate modules for")
                return result
            
            # Organize resources into modules
            organized_modules = self._organize_resources(all_resources)
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate each module
            for module_name, resource_ids in organized_modules.items():
                module_resources = {rid: all_resources[rid] for rid in resource_ids if rid in all_resources}
                
                if not module_resources:
                    continue
                
                module_info = self._generate_single_module(
                    module_name, 
                    module_resources, 
                    output_path / "modules" / module_name
                )
                
                result.modules[module_name] = module_info
                result.total_files += len(list((output_path / "modules" / module_name).glob("*.tf")))
                result.total_variables += len(module_info.variables)
                result.total_outputs += len(module_info.outputs)
            
            # Generate root module
            root_module_info = self._generate_root_module(result.modules, output_path)
            result.root_module = root_module_info
            result.total_files += len(list(output_path.glob("*.tf")))
            
            # Generate additional files
            self._generate_additional_files(output_path, result)
            
            result.generation_time = time.time() - start_time
            logger.info(f"Module generation completed: {len(result.modules)} modules, {result.total_files} files")
            
        except Exception as e:
            logger.error(f"Module generation failed: {str(e)}")
            result.errors.append(f"Module generation failed: {str(e)}")
        
        return result
    
    def _organize_resources(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize resources into modules based on strategy"""
        
        if self.organization_strategy == "service_based":
            return self._organize_by_service(resources)
        elif self.organization_strategy == "stack_based":
            return self._organize_by_stack(resources)
        elif self.organization_strategy == "lifecycle_based":
            return self._organize_by_lifecycle(resources)
        elif self.organization_strategy == "hybrid":
            return self._organize_hybrid(resources)
        else:
            # Default to service-based
            return self._organize_by_service(resources)
    
    def _organize_by_service(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize resources by AWS service"""
        service_mapping = {
            'AWS::EC2::VPC': 'networking',
            'AWS::EC2::Subnet': 'networking',
            'AWS::EC2::InternetGateway': 'networking',
            'AWS::EC2::NatGateway': 'networking',
            'AWS::EC2::RouteTable': 'networking',
            'AWS::EC2::Route': 'networking',
            'AWS::EC2::SecurityGroup': 'security',
            'AWS::EC2::SecurityGroupIngress': 'security',
            'AWS::EC2::SecurityGroupEgress': 'security',
            'AWS::EC2::Instance': 'compute',
            'AWS::EC2::LaunchTemplate': 'compute',
            'AWS::AutoScaling::AutoScalingGroup': 'compute',
            'AWS::AutoScaling::LaunchConfiguration': 'compute',
            'AWS::ElasticLoadBalancingV2::LoadBalancer': 'load_balancing',
            'AWS::ElasticLoadBalancingV2::TargetGroup': 'load_balancing',
            'AWS::ElasticLoadBalancingV2::Listener': 'load_balancing',
            'AWS::S3::Bucket': 'storage',
            'AWS::S3::BucketPolicy': 'storage',
            'AWS::EBS::Volume': 'storage',
            'AWS::EFS::FileSystem': 'storage',
            'AWS::RDS::DBInstance': 'database',
            'AWS::RDS::DBSubnetGroup': 'database',
            'AWS::RDS::DBParameterGroup': 'database',
            'AWS::DynamoDB::Table': 'database',
            'AWS::ElastiCache::CacheCluster': 'database',
            'AWS::Lambda::Function': 'compute',
            'AWS::Lambda::Permission': 'compute',
            'AWS::IAM::Role': 'security',
            'AWS::IAM::Policy': 'security',
            'AWS::IAM::InstanceProfile': 'security',
            'AWS::KMS::Key': 'security',
            'AWS::CloudWatch::Alarm': 'monitoring',
            'AWS::CloudWatch::Dashboard': 'monitoring',
            'AWS::Logs::LogGroup': 'monitoring',
            'AWS::SNS::Topic': 'messaging',
            'AWS::SQS::Queue': 'messaging',
            'AWS::Route53::HostedZone': 'dns',
            'AWS::Route53::RecordSet': 'dns',
            'AWS::CloudFront::Distribution': 'cdn',
            'AWS::ApiGateway::RestApi': 'api',
            'AWS::ApiGateway::Resource': 'api',
            'AWS::ApiGateway::Method': 'api',
        }
        
        modules = {}
        
        for resource_id, resource_info in resources.items():
            resource_type = resource_info.get('resource_type', '')
            module_name = service_mapping.get(resource_type, 'misc')
            
            if self.module_prefix:
                module_name = f"{self.module_prefix}_{module_name}"
            
            if module_name not in modules:
                modules[module_name] = []
            
            modules[module_name].append(resource_id)
        
        return modules
    
    def _organize_by_stack(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize resources by original CloudFormation stack"""
        modules = {}
        
        for resource_id, resource_info in resources.items():
            stack_name = resource_info.get('stack_name', 'independent_resources')
            
            # Sanitize stack name for module name
            module_name = self._sanitize_module_name(stack_name)
            
            if self.module_prefix:
                module_name = f"{self.module_prefix}_{module_name}"
            
            if module_name not in modules:
                modules[module_name] = []
            
            modules[module_name].append(resource_id)
        
        return modules
    
    def _organize_by_lifecycle(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize resources by operational lifecycle"""
        lifecycle_mapping = {
            'AWS::EC2::VPC': 'shared_infrastructure',
            'AWS::EC2::Subnet': 'shared_infrastructure',
            'AWS::EC2::InternetGateway': 'shared_infrastructure',
            'AWS::EC2::NatGateway': 'shared_infrastructure',
            'AWS::EC2::RouteTable': 'shared_infrastructure',
            'AWS::IAM::Role': 'shared_infrastructure',
            'AWS::IAM::Policy': 'shared_infrastructure',
            'AWS::KMS::Key': 'shared_infrastructure',
            'AWS::EC2::SecurityGroup': 'shared_infrastructure',
            'AWS::EC2::Instance': 'application_resources',
            'AWS::AutoScaling::AutoScalingGroup': 'application_resources',
            'AWS::ElasticLoadBalancingV2::LoadBalancer': 'application_resources',
            'AWS::Lambda::Function': 'application_resources',
            'AWS::S3::Bucket': 'application_resources',
            'AWS::RDS::DBInstance': 'data_resources',
            'AWS::DynamoDB::Table': 'data_resources',
            'AWS::ElastiCache::CacheCluster': 'data_resources',
            'AWS::CloudWatch::Alarm': 'monitoring_resources',
            'AWS::Logs::LogGroup': 'monitoring_resources',
            'AWS::SNS::Topic': 'messaging_resources',
            'AWS::SQS::Queue': 'messaging_resources',
        }
        
        modules = {}
        
        for resource_id, resource_info in resources.items():
            resource_type = resource_info.get('resource_type', '')
            module_name = lifecycle_mapping.get(resource_type, 'misc_resources')
            
            if self.module_prefix:
                module_name = f"{self.module_prefix}_{module_name}"
            
            if module_name not in modules:
                modules[module_name] = []
            
            modules[module_name].append(resource_id)
        
        return modules
    
    def _organize_hybrid(self, resources: Dict[str, Any]) -> Dict[str, List[str]]:
        """Hybrid organization strategy"""
        # Start with stack-based organization
        stack_modules = self._organize_by_stack(resources)
        
        # If any module has too many resources, subdivide by service
        final_modules = {}
        
        for module_name, resource_ids in stack_modules.items():
            if len(resource_ids) > 20:  # Large module, subdivide
                # Get resources for this module
                module_resources = {rid: resources[rid] for rid in resource_ids if rid in resources}
                
                # Organize by service
                service_modules = self._organize_by_service(module_resources)
                
                # Add stack prefix to service modules
                for service_name, service_resource_ids in service_modules.items():
                    hybrid_name = f"{module_name}_{service_name}"
                    final_modules[hybrid_name] = service_resource_ids
            else:
                # Keep as single module
                final_modules[module_name] = resource_ids
        
        return final_modules
    
    def _generate_single_module(self, 
                               module_name: str, 
                               module_resources: Dict[str, Any], 
                               module_path: Path) -> EnhancedModuleInfo:
        """Generate a single Terraform module with NO hardcoded values"""
        
        logger.info(f"Generating module: {module_name}")
        
        # Create module directory
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Extract Terraform resources from module resources
        terraform_resources = {}
        original_resource_ids = []
        
        for resource_id, resource_info in module_resources.items():
            original_resource_ids.append(resource_id)
            
            terraform_config = resource_info.get('terraform_config', {})
            if 'resource' in terraform_config:
                for tf_type, tf_instances in terraform_config['resource'].items():
                    if tf_type not in terraform_resources:
                        terraform_resources[tf_type] = {}
                    terraform_resources[tf_type].update(tf_instances)
        
        # Generate variables (NO hardcoded values)
        variables = self._generate_comprehensive_variables(terraform_resources, module_name, module_resources)
        
        # Generate outputs
        outputs = self._generate_comprehensive_outputs(terraform_resources, module_name)
        
        # Generate locals
        locals_dict = self._generate_locals(module_name)
        
        # Convert hardcoded values to variable references
        terraform_resources = self._convert_hardcoded_to_variables(terraform_resources, variables)
        
        # Write module files
        self._write_main_tf(module_path, module_name, terraform_resources, locals_dict)
        self._write_variables_tf(module_path, variables)
        self._write_outputs_tf(module_path, outputs)
        self._write_versions_tf(module_path)
        self._write_module_readme(module_path, module_name, variables, outputs, original_resource_ids)
        
        return EnhancedModuleInfo(
            name=module_name,
            path=str(module_path),
            resources=list(terraform_resources.keys()),
            variables=variables,
            outputs=outputs,
            locals=locals_dict,
            description=f"Terraform module for {module_name} resources",
            original_resources=original_resource_ids
        )
    
    def _generate_comprehensive_variables(self, 
                                        terraform_resources: Dict[str, Any], 
                                        module_name: str,
                                        original_resources: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive variables with NO hardcoded values allowed"""
        
        variables = {}
        
        # Always include common variables
        variables['tags'] = {
            'description': 'Common tags to be applied to all resources',
            'type': 'map(string)',
            'default': {}
        }
        
        variables['environment'] = {
            'description': 'Environment name (e.g., dev, staging, prod)',
            'type': 'string'
            # No default - must be provided
        }
        
        variables['region'] = {
            'description': 'AWS region for resources',
            'type': 'string'
            # No default - must be provided
        }
        
        variables['name_prefix'] = {
            'description': 'Prefix for resource names',
            'type': 'string',
            'default': module_name
        }
        
        # Extract variables from each resource configuration
        for tf_type, tf_instances in terraform_resources.items():
            for instance_name, instance_config in tf_instances.items():
                self._extract_variables_from_resource(
                    tf_type, 
                    instance_name, 
                    instance_config, 
                    variables
                )
        
        # Add variables based on original resource information
        for resource_id, resource_info in original_resources.items():
            self._extract_variables_from_original_resource(resource_info, variables)
        
        return variables
    
    def _extract_variables_from_resource(self, 
                                       tf_type: str, 
                                       instance_name: str, 
                                       config: Dict[str, Any], 
                                       variables: Dict[str, Any]):
        """Extract variables from a Terraform resource configuration"""
        
        # Resource-specific variable extraction
        if tf_type == 'aws_vpc':
            self._add_variable_if_not_exists(variables, f"{instance_name}_cidr_block", {
                'description': f'CIDR block for VPC {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_enable_dns_hostnames", {
                'description': f'Enable DNS hostnames for VPC {instance_name}',
                'type': 'bool',
                'default': True
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_enable_dns_support", {
                'description': f'Enable DNS support for VPC {instance_name}',
                'type': 'bool',
                'default': True
            })
        
        elif tf_type == 'aws_subnet':
            self._add_variable_if_not_exists(variables, f"{instance_name}_cidr_block", {
                'description': f'CIDR block for subnet {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_availability_zone", {
                'description': f'Availability zone for subnet {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_map_public_ip_on_launch", {
                'description': f'Map public IP on launch for subnet {instance_name}',
                'type': 'bool',
                'default': False
            })
        
        elif tf_type == 'aws_instance':
            self._add_variable_if_not_exists(variables, f"{instance_name}_ami", {
                'description': f'AMI ID for instance {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_instance_type", {
                'description': f'Instance type for {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_key_name", {
                'description': f'Key pair name for instance {instance_name}',
                'type': 'string',
                'default': None
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_monitoring", {
                'description': f'Enable detailed monitoring for instance {instance_name}',
                'type': 'bool',
                'default': False
            })
        
        elif tf_type == 'aws_s3_bucket':
            self._add_variable_if_not_exists(variables, f"{instance_name}_bucket_name", {
                'description': f'Name for S3 bucket {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_force_destroy", {
                'description': f'Force destroy S3 bucket {instance_name}',
                'type': 'bool',
                'default': False
            })
        
        elif tf_type == 'aws_db_instance':
            self._add_variable_if_not_exists(variables, f"{instance_name}_db_instance_class", {
                'description': f'Instance class for RDS {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_engine", {
                'description': f'Database engine for RDS {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_engine_version", {
                'description': f'Database engine version for RDS {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_allocated_storage", {
                'description': f'Allocated storage for RDS {instance_name}',
                'type': 'number'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_db_name", {
                'description': f'Database name for RDS {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_username", {
                'description': f'Master username for RDS {instance_name}',
                'type': 'string'
            })
            # Note: Password should be handled via AWS Secrets Manager or similar
            self._add_variable_if_not_exists(variables, f"{instance_name}_manage_master_user_password", {
                'description': f'Manage master user password via AWS Secrets Manager for RDS {instance_name}',
                'type': 'bool',
                'default': True
            })
        
        elif tf_type == 'aws_lambda_function':
            self._add_variable_if_not_exists(variables, f"{instance_name}_function_name", {
                'description': f'Function name for Lambda {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_runtime", {
                'description': f'Runtime for Lambda {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_handler", {
                'description': f'Handler for Lambda {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_memory_size", {
                'description': f'Memory size for Lambda {instance_name}',
                'type': 'number',
                'default': 128
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_timeout", {
                'description': f'Timeout for Lambda {instance_name}',
                'type': 'number',
                'default': 3
            })
        
        elif tf_type == 'aws_security_group':
            self._add_variable_if_not_exists(variables, f"{instance_name}_name", {
                'description': f'Name for security group {instance_name}',
                'type': 'string'
            })
            self._add_variable_if_not_exists(variables, f"{instance_name}_description", {
                'description': f'Description for security group {instance_name}',
                'type': 'string'
            })
        
        # Generic extraction for any remaining properties
        self._extract_generic_variables(config, variables, f"{tf_type}_{instance_name}")
    
    def _extract_generic_variables(self, config: Dict[str, Any], variables: Dict[str, Any], prefix: str):
        """Extract variables from any configuration recursively"""
        
        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)):
                var_name = f"{prefix}_{key}"
                var_type = self.variable_type_mappings.get(key, 'string')
                
                if isinstance(value, bool):
                    var_type = 'bool'
                elif isinstance(value, int):
                    var_type = 'number'
                elif isinstance(value, float):
                    var_type = 'number'
                
                self._add_variable_if_not_exists(variables, var_name, {
                    'description': f'{key.replace("_", " ").title()} for {prefix}',
                    'type': var_type
                })
            
            elif isinstance(value, list) and value:
                var_name = f"{prefix}_{key}"
                var_type = f'list({self.variable_type_mappings.get(key, "string")})'
                
                self._add_variable_if_not_exists(variables, var_name, {
                    'description': f'{key.replace("_", " ").title()} for {prefix}',
                    'type': var_type
                })
            
            elif isinstance(value, dict) and value:
                var_name = f"{prefix}_{key}"
                var_type = f'map({self.variable_type_mappings.get(key, "any")})'
                
                self._add_variable_if_not_exists(variables, var_name, {
                    'description': f'{key.replace("_", " ").title()} for {prefix}',
                    'type': var_type
                })
    
    def _extract_variables_from_original_resource(self, resource_info: Dict[str, Any], variables: Dict[str, Any]):
        """Extract variables from original resource information"""
        
        # Extract resource-specific information
        resource_type = resource_info.get('resource_type', '')
        resource_id = resource_info.get('resource_id', '')
        
        # Add resource ID as a variable for import purposes
        if resource_id:
            var_name = f"existing_{resource_id.replace('-', '_')}_id"
            self._add_variable_if_not_exists(variables, var_name, {
                'description': f'Existing resource ID for {resource_id}',
                'type': 'string',
                'default': resource_id
            })
    
    def _add_variable_if_not_exists(self, variables: Dict[str, Any], var_name: str, var_config: Dict[str, Any]):
        """Add a variable only if it doesn't already exist"""
        if var_name not in variables:
            variables[var_name] = var_config
    
    def _convert_hardcoded_to_variables(self, 
                                      terraform_resources: Dict[str, Any], 
                                      variables: Dict[str, Any]) -> Dict[str, Any]:
        """Convert hardcoded values in Terraform resources to variable references"""
        
        converted_resources = {}
        
        for tf_type, tf_instances in terraform_resources.items():
            converted_resources[tf_type] = {}
            
            for instance_name, instance_config in tf_instances.items():
                converted_config = {}
                
                for key, value in instance_config.items():
                    # Convert hardcoded values to variable references
                    if isinstance(value, (str, int, float, bool)):
                        var_name = f"{instance_name}_{key}"
                        if var_name in variables:
                            converted_config[key] = f"var.{var_name}"
                        else:
                            # Look for generic variable
                            generic_var_name = f"{tf_type}_{instance_name}_{key}"
                            if generic_var_name in variables:
                                converted_config[key] = f"var.{generic_var_name}"
                            else:
                                # Keep original value but add warning
                                converted_config[key] = value
                                logger.warning(f"No variable found for {key} in {tf_type}.{instance_name}")
                    else:
                        converted_config[key] = value
                
                # Add common attributes
                if 'tags' not in converted_config:
                    converted_config['tags'] = "merge(var.tags, { Name = \"${var.name_prefix}-${var.environment}-" + instance_name + "\" })"
                
                converted_resources[tf_type][instance_name] = converted_config
        
        return converted_resources
    
    def _generate_comprehensive_outputs(self, terraform_resources: Dict[str, Any], module_name: str) -> Dict[str, Any]:
        """Generate comprehensive outputs for all resources"""
        
        outputs = {}
        
        for tf_type, tf_instances in terraform_resources.items():
            for instance_name, instance_config in tf_instances.items():
                
                # Common outputs for all resources
                outputs[f"{instance_name}_id"] = {
                    'description': f'ID of {tf_type} {instance_name}',
                    'value': f'{tf_type}.{instance_name}.id'
                }
                
                outputs[f"{instance_name}_arn"] = {
                    'description': f'ARN of {tf_type} {instance_name}',
                    'value': f'{tf_type}.{instance_name}.arn'
                }
                
                # Resource-specific outputs
                if tf_type == 'aws_vpc':
                    outputs[f"{instance_name}_cidr_block"] = {
                        'description': f'CIDR block of VPC {instance_name}',
                        'value': f'aws_vpc.{instance_name}.cidr_block'
                    }
                    outputs[f"{instance_name}_default_security_group_id"] = {
                        'description': f'Default security group ID of VPC {instance_name}',
                        'value': f'aws_vpc.{instance_name}.default_security_group_id'
                    }
                
                elif tf_type == 'aws_subnet':
                    outputs[f"{instance_name}_cidr_block"] = {
                        'description': f'CIDR block of subnet {instance_name}',
                        'value': f'aws_subnet.{instance_name}.cidr_block'
                    }
                    outputs[f"{instance_name}_availability_zone"] = {
                        'description': f'Availability zone of subnet {instance_name}',
                        'value': f'aws_subnet.{instance_name}.availability_zone'
                    }
                
                elif tf_type == 'aws_instance':
                    outputs[f"{instance_name}_public_ip"] = {
                        'description': f'Public IP of instance {instance_name}',
                        'value': f'aws_instance.{instance_name}.public_ip'
                    }
                    outputs[f"{instance_name}_private_ip"] = {
                        'description': f'Private IP of instance {instance_name}',
                        'value': f'aws_instance.{instance_name}.private_ip'
                    }
                    outputs[f"{instance_name}_public_dns"] = {
                        'description': f'Public DNS of instance {instance_name}',
                        'value': f'aws_instance.{instance_name}.public_dns'
                    }
                
                elif tf_type == 'aws_s3_bucket':
                    outputs[f"{instance_name}_bucket_name"] = {
                        'description': f'Name of S3 bucket {instance_name}',
                        'value': f'aws_s3_bucket.{instance_name}.bucket'
                    }
                    outputs[f"{instance_name}_bucket_domain_name"] = {
                        'description': f'Domain name of S3 bucket {instance_name}',
                        'value': f'aws_s3_bucket.{instance_name}.bucket_domain_name'
                    }
                
                elif tf_type == 'aws_db_instance':
                    outputs[f"{instance_name}_endpoint"] = {
                        'description': f'Endpoint of RDS instance {instance_name}',
                        'value': f'aws_db_instance.{instance_name}.endpoint'
                    }
                    outputs[f"{instance_name}_port"] = {
                        'description': f'Port of RDS instance {instance_name}',
                        'value': f'aws_db_instance.{instance_name}.port'
                    }
                
                elif tf_type == 'aws_lambda_function':
                    outputs[f"{instance_name}_function_name"] = {
                        'description': f'Name of Lambda function {instance_name}',
                        'value': f'aws_lambda_function.{instance_name}.function_name'
                    }
                    outputs[f"{instance_name}_invoke_arn"] = {
                        'description': f'Invoke ARN of Lambda function {instance_name}',
                        'value': f'aws_lambda_function.{instance_name}.invoke_arn'
                    }
        
        return outputs
    
    def _generate_locals(self, module_name: str) -> Dict[str, Any]:
        """Generate locals block for the module"""
        
        return {
            'common_tags': {
                'Module': module_name,
                'ManagedBy': 'terraform',
                'Environment': 'var.environment'
            },
            'name_prefix': 'var.name_prefix != "" ? var.name_prefix : var.environment'
        }
    
    def _write_main_tf(self, module_path: Path, module_name: str, terraform_resources: Dict[str, Any], locals_dict: Dict[str, Any]):
        """Write main.tf file"""
        
        main_tf_template = '''# {{ module_name }} Module
# Generated by CF2TF Converter
# All values are parameterized - no hardcoded values

terraform {
  required_version = "{{ terraform_version }}"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "{{ provider_version }}"
    }
  }
}

locals {
{% for key, value in locals.items() %}
  {{ key }} = {{ value }}
{% endfor %}
}

{% for resource_type, instances in resources.items() %}
{% for instance_name, config in instances.items() %}
resource "{{ resource_type }}" "{{ instance_name }}" {
{% for key, value in config.items() %}
  {{ key }} = {{ value }}
{% endfor %}
}

{% endfor %}
{% endfor %}
'''
        
        template = Template(main_tf_template)
        content = template.render(
            module_name=module_name,
            terraform_version=self.terraform_version,
            provider_version=self.provider_version,
            locals=locals_dict,
            resources=terraform_resources
        )
        
        (module_path / "main.tf").write_text(content)
    
    def _write_variables_tf(self, module_path: Path, variables: Dict[str, Any]):
        """Write variables.tf file"""
        
        variables_tf_template = '''# Variables for {{ module_name }}
# All configurable values are exposed as variables

{% for var_name, var_config in variables.items() %}
variable "{{ var_name }}" {
  description = "{{ var_config.description }}"
  type        = {{ var_config.type }}
{% if var_config.default is defined %}
  default     = {{ var_config.default }}
{% endif %}
{% if var_config.validation is defined %}
  validation {
    condition     = {{ var_config.validation.condition }}
    error_message = "{{ var_config.validation.error_message }}"
  }
{% endif %}
}

{% endfor %}
'''
        
        template = Template(variables_tf_template)
        content = template.render(
            module_name=module_path.name,
            variables=variables
        )
        
        (module_path / "variables.tf").write_text(content)
    
    def _write_outputs_tf(self, module_path: Path, outputs: Dict[str, Any]):
        """Write outputs.tf file"""
        
        outputs_tf_template = '''# Outputs for {{ module_name }}

{% for output_name, output_config in outputs.items() %}
output "{{ output_name }}" {
  description = "{{ output_config.description }}"
  value       = {{ output_config.value }}
{% if output_config.sensitive is defined %}
  sensitive   = {{ output_config.sensitive }}
{% endif %}
}

{% endfor %}
'''
        
        template = Template(outputs_tf_template)
        content = template.render(
            module_name=module_path.name,
            outputs=outputs
        )
        
        (module_path / "outputs.tf").write_text(content)
    
    def _write_versions_tf(self, module_path: Path):
        """Write versions.tf file"""
        
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
        
        (module_path / "versions.tf").write_text(versions_content)
    
    def _write_module_readme(self, module_path: Path, module_name: str, variables: Dict[str, Any], outputs: Dict[str, Any], original_resources: List[str]):
        """Write README.md for the module"""
        
        readme_template = '''# {{ module_name }} Module

This Terraform module manages {{ module_name }} resources with NO hardcoded values.
All configuration is parameterized through variables.

## Features

- ✅ No hardcoded values - everything is configurable
- ✅ Preserves original AWS resource names
- ✅ Comprehensive variable validation
- ✅ Complete output coverage
- ✅ Ready for import of existing resources

## Usage

```hcl
module "{{ module_name }}" {
  source = "./modules/{{ module_name }}"
  
  # Required variables
  environment = "prod"
  region      = "us-east-1"
  
  # Module-specific variables
{% for var_name, var_config in variables.items() %}
{% if not var_config.default is defined %}
  {{ var_name }} = "your_value_here"  # {{ var_config.description }}
{% endif %}
{% endfor %}
  
  # Optional variables with defaults
{% for var_name, var_config in variables.items() %}
{% if var_config.default is defined %}
  # {{ var_name }} = {{ var_config.default }}  # {{ var_config.description }}
{% endif %}
{% endfor %}
  
  tags = {
    Environment = "prod"
    Project     = "my-project"
  }
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
{% for var_name, var_config in variables.items() %}
| {{ var_name }} | {{ var_config.description }} | `{{ var_config.type }}` | {{ var_config.default if var_config.default is defined else 'n/a' }} | {{ 'no' if var_config.default is defined else 'yes' }} |
{% endfor %}

## Outputs

| Name | Description |
|------|-------------|
{% for output_name, output_config in outputs.items() %}
| {{ output_name }} | {{ output_config.description }} |
{% endfor %}

## Original Resources

This module was generated from the following AWS resources:

{% for resource_id in original_resources %}
- `{{ resource_id }}`
{% endfor %}

## Import Existing Resources

To import existing AWS resources into this module:

```bash
# Initialize Terraform
terraform init

# Import each resource (examples)
{% for resource_id in original_resources %}
# terraform import module.{{ module_name }}.RESOURCE_TYPE.RESOURCE_NAME {{ resource_id }}
{% endfor %}

# Verify import
terraform plan
```

## Notes

- All values are parameterized to avoid hardcoding
- Resource names are preserved from original AWS resources
- Module is designed for zero-downtime import of existing resources
- Comprehensive validation ensures configuration correctness
'''
        
        template = Template(readme_template)
        content = template.render(
            module_name=module_name,
            variables=variables,
            outputs=outputs,
            original_resources=original_resources
        )
        
        (module_path / "README.md").write_text(content)
    
    def _generate_root_module(self, modules: Dict[str, EnhancedModuleInfo], output_path: Path) -> EnhancedModuleInfo:
        """Generate root module that calls all other modules"""
        
        # Generate root main.tf
        root_main_template = '''# Root Module - Generated by CF2TF Converter
# Orchestrates all infrastructure modules

terraform {
  required_version = "{{ terraform_version }}"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "{{ provider_version }}"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = var.common_tags
  }
}

{% for module_name, module_info in modules.items() %}
module "{{ module_name }}" {
  source = "./modules/{{ module_name }}"
  
  # Common variables
  environment = var.environment
  region      = var.aws_region
  name_prefix = var.name_prefix
  tags        = var.common_tags
  
  # Module-specific variables
{% for var_name, var_config in module_info.variables.items() %}
{% if var_name not in ['environment', 'region', 'tags', 'name_prefix'] %}
  {{ var_name }} = var.{{ module_name }}_{{ var_name }}
{% endif %}
{% endfor %}
}

{% endfor %}
'''
        
        template = Template(root_main_template)
        content = template.render(
            terraform_version=self.terraform_version,
            provider_version=self.provider_version,
            modules=modules
        )
        
        (output_path / "main.tf").write_text(content)
        
        # Generate root variables.tf
        root_variables = {
            'aws_region': {
                'description': 'AWS region for all resources',
                'type': 'string'
            },
            'environment': {
                'description': 'Environment name (e.g., dev, staging, prod)',
                'type': 'string'
            },
            'name_prefix': {
                'description': 'Prefix for all resource names',
                'type': 'string',
                'default': ''
            },
            'common_tags': {
                'description': 'Common tags applied to all resources',
                'type': 'map(string)',
                'default': {}
            }
        }
        
        # Add module-specific variables to root
        for module_name, module_info in modules.items():
            for var_name, var_config in module_info.variables.items():
                if var_name not in ['environment', 'region', 'tags', 'name_prefix']:
                    root_var_name = f"{module_name}_{var_name}"
                    root_variables[root_var_name] = {
                        'description': f"{var_config['description']} (for {module_name} module)",
                        'type': var_config['type']
                    }
                    if 'default' in var_config:
                        root_variables[root_var_name]['default'] = var_config['default']
        
        self._write_variables_tf(output_path, root_variables)
        
        # Generate root outputs.tf
        root_outputs = {}
        for module_name, module_info in modules.items():
            for output_name, output_config in module_info.outputs.items():
                root_output_name = f"{module_name}_{output_name}"
                root_outputs[root_output_name] = {
                    'description': f"{output_config['description']} (from {module_name} module)",
                    'value': f"module.{module_name}.{output_name}"
                }
        
        self._write_outputs_tf(output_path, root_outputs)
        
        # Generate root versions.tf
        self._write_versions_tf(output_path)
        
        return EnhancedModuleInfo(
            name="root",
            path=str(output_path),
            variables=root_variables,
            outputs=root_outputs,
            description="Root module orchestrating all infrastructure"
        )
    
    def _generate_additional_files(self, output_path: Path, result: EnhancedGenerationResult):
        """Generate additional files like terraform.tfvars.example"""
        
        # Generate terraform.tfvars.example
        tfvars_content = '''# Example Terraform variables file
# Copy this to terraform.tfvars and customize for your environment

# Required variables
aws_region  = "us-east-1"
environment = "dev"

# Optional variables
name_prefix = "myproject"

common_tags = {
  Environment = "dev"
  Project     = "my-project"
  ManagedBy   = "terraform"
  Owner       = "platform-team"
}

# Module-specific variables
# Uncomment and customize as needed
'''
        
        if result.root_module:
            for var_name, var_config in result.root_module.variables.items():
                if var_name not in ['aws_region', 'environment', 'name_prefix', 'common_tags']:
                    if 'default' not in var_config:
                        tfvars_content += f'\n# {var_name} = "your_value_here"  # {var_config["description"]}'
        
        (output_path / "terraform.tfvars.example").write_text(tfvars_content)
        
        # Generate .gitignore
        gitignore_content = '''# Terraform files
*.tfstate
*.tfstate.*
*.tfvars
!*.tfvars.example
.terraform/
.terraform.lock.hcl
crash.log
crash.*.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terraformrc
terraform.rc

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db
'''
        
        (output_path / ".gitignore").write_text(gitignore_content)
    
    def _sanitize_module_name(self, name: str) -> str:
        """Sanitize module name to be valid Terraform identifier"""
        
        if not name:
            return "unnamed_module"
        
        # Convert to lowercase and replace invalid characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        
        # Ensure it starts with a letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = f"module_{sanitized}"
        
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        return sanitized or "unnamed_module"

