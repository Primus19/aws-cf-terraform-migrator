#!/usr/bin/env python3
"""
CloudFormation to Terraform Conversion Engine

This module implements the core conversion logic for transforming CloudFormation
templates and resources into Terraform configurations with comprehensive
resource mapping and intrinsic function handling.
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of a CloudFormation to Terraform conversion"""
    terraform_config: Dict[str, Any]
    import_commands: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    locals: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ResourceMapper:
    """Maps CloudFormation resource types to Terraform equivalents"""
    
    # Comprehensive mapping of CloudFormation to Terraform resource types
    RESOURCE_TYPE_MAPPING = {
        # Compute
        'AWS::EC2::Instance': 'aws_instance',
        'AWS::EC2::LaunchTemplate': 'aws_launch_template',
        'AWS::EC2::LaunchConfiguration': 'aws_launch_configuration',
        'AWS::AutoScaling::AutoScalingGroup': 'aws_autoscaling_group',
        'AWS::AutoScaling::LaunchConfiguration': 'aws_launch_configuration',
        'AWS::Lambda::Function': 'aws_lambda_function',
        'AWS::Lambda::Permission': 'aws_lambda_permission',
        'AWS::Lambda::Alias': 'aws_lambda_alias',
        'AWS::Lambda::Version': 'aws_lambda_version',
        'AWS::ECS::Cluster': 'aws_ecs_cluster',
        'AWS::ECS::Service': 'aws_ecs_service',
        'AWS::ECS::TaskDefinition': 'aws_ecs_task_definition',
        
        # Networking
        'AWS::EC2::VPC': 'aws_vpc',
        'AWS::EC2::Subnet': 'aws_subnet',
        'AWS::EC2::InternetGateway': 'aws_internet_gateway',
        'AWS::EC2::VPCGatewayAttachment': 'aws_internet_gateway_attachment',
        'AWS::EC2::RouteTable': 'aws_route_table',
        'AWS::EC2::Route': 'aws_route',
        'AWS::EC2::SubnetRouteTableAssociation': 'aws_route_table_association',
        'AWS::EC2::SecurityGroup': 'aws_security_group',
        'AWS::EC2::SecurityGroupIngress': 'aws_security_group_rule',
        'AWS::EC2::SecurityGroupEgress': 'aws_security_group_rule',
        'AWS::EC2::NatGateway': 'aws_nat_gateway',
        'AWS::EC2::EIP': 'aws_eip',
        'AWS::EC2::EIPAssociation': 'aws_eip_association',
        'AWS::EC2::NetworkInterface': 'aws_network_interface',
        'AWS::EC2::NetworkInterfaceAttachment': 'aws_network_interface_attachment',
        
        # Load Balancing
        'AWS::ElasticLoadBalancing::LoadBalancer': 'aws_elb',
        'AWS::ElasticLoadBalancingV2::LoadBalancer': 'aws_lb',
        'AWS::ElasticLoadBalancingV2::TargetGroup': 'aws_lb_target_group',
        'AWS::ElasticLoadBalancingV2::Listener': 'aws_lb_listener',
        'AWS::ElasticLoadBalancingV2::ListenerRule': 'aws_lb_listener_rule',
        
        # Storage
        'AWS::S3::Bucket': 'aws_s3_bucket',
        'AWS::S3::BucketPolicy': 'aws_s3_bucket_policy',
        'AWS::S3::BucketNotification': 'aws_s3_bucket_notification',
        'AWS::EBS::Volume': 'aws_ebs_volume',
        'AWS::EC2::VolumeAttachment': 'aws_volume_attachment',
        'AWS::EFS::FileSystem': 'aws_efs_file_system',
        'AWS::EFS::MountTarget': 'aws_efs_mount_target',
        
        # Database
        'AWS::RDS::DBInstance': 'aws_db_instance',
        'AWS::RDS::DBCluster': 'aws_rds_cluster',
        'AWS::RDS::DBSubnetGroup': 'aws_db_subnet_group',
        'AWS::RDS::DBParameterGroup': 'aws_db_parameter_group',
        'AWS::RDS::DBClusterParameterGroup': 'aws_rds_cluster_parameter_group',
        'AWS::DynamoDB::Table': 'aws_dynamodb_table',
        'AWS::ElastiCache::CacheCluster': 'aws_elasticache_cluster',
        'AWS::ElastiCache::ReplicationGroup': 'aws_elasticache_replication_group',
        'AWS::ElastiCache::SubnetGroup': 'aws_elasticache_subnet_group',
        
        # IAM
        'AWS::IAM::Role': 'aws_iam_role',
        'AWS::IAM::Policy': 'aws_iam_policy',
        'AWS::IAM::User': 'aws_iam_user',
        'AWS::IAM::Group': 'aws_iam_group',
        'AWS::IAM::InstanceProfile': 'aws_iam_instance_profile',
        'AWS::IAM::RolePolicyAttachment': 'aws_iam_role_policy_attachment',
        'AWS::IAM::UserPolicyAttachment': 'aws_iam_user_policy_attachment',
        'AWS::IAM::GroupPolicyAttachment': 'aws_iam_group_policy_attachment',
        
        # DNS
        'AWS::Route53::HostedZone': 'aws_route53_zone',
        'AWS::Route53::RecordSet': 'aws_route53_record',
        
        # CloudFront
        'AWS::CloudFront::Distribution': 'aws_cloudfront_distribution',
        'AWS::CloudFront::OriginAccessIdentity': 'aws_cloudfront_origin_access_identity',
        
        # API Gateway
        'AWS::ApiGateway::RestApi': 'aws_api_gateway_rest_api',
        'AWS::ApiGateway::Resource': 'aws_api_gateway_resource',
        'AWS::ApiGateway::Method': 'aws_api_gateway_method',
        'AWS::ApiGateway::Deployment': 'aws_api_gateway_deployment',
        'AWS::ApiGateway::Stage': 'aws_api_gateway_stage',
        
        # Messaging
        'AWS::SNS::Topic': 'aws_sns_topic',
        'AWS::SNS::Subscription': 'aws_sns_topic_subscription',
        'AWS::SQS::Queue': 'aws_sqs_queue',
        
        # Monitoring
        'AWS::CloudWatch::Alarm': 'aws_cloudwatch_metric_alarm',
        'AWS::CloudWatch::Dashboard': 'aws_cloudwatch_dashboard',
        'AWS::Logs::LogGroup': 'aws_cloudwatch_log_group',
        'AWS::Logs::LogStream': 'aws_cloudwatch_log_stream',
        
        # Security
        'AWS::KMS::Key': 'aws_kms_key',
        'AWS::KMS::Alias': 'aws_kms_alias',
        'AWS::SecretsManager::Secret': 'aws_secretsmanager_secret',
        'AWS::SecretsManager::SecretVersion': 'aws_secretsmanager_secret_version',
        
        # CloudFormation
        'AWS::CloudFormation::Stack': 'terraform_module',  # Special handling needed
    }
    
    # Property mappings for common transformations
    PROPERTY_MAPPINGS = {
        'aws_instance': {
            'ImageId': 'ami',
            'InstanceType': 'instance_type',
            'KeyName': 'key_name',
            'SecurityGroups': 'security_groups',
            'SecurityGroupIds': 'vpc_security_group_ids',
            'SubnetId': 'subnet_id',
            'UserData': 'user_data',
            'IamInstanceProfile': 'iam_instance_profile',
            'Tags': 'tags',
            'BlockDeviceMappings': 'ebs_block_device',
            'Monitoring': 'monitoring',
            'DisableApiTermination': 'disable_api_termination',
            'EbsOptimized': 'ebs_optimized',
            'SourceDestCheck': 'source_dest_check'
        },
        'aws_vpc': {
            'CidrBlock': 'cidr_block',
            'EnableDnsHostnames': 'enable_dns_hostnames',
            'EnableDnsSupport': 'enable_dns_support',
            'InstanceTenancy': 'instance_tenancy',
            'Tags': 'tags'
        },
        'aws_subnet': {
            'VpcId': 'vpc_id',
            'CidrBlock': 'cidr_block',
            'AvailabilityZone': 'availability_zone',
            'MapPublicIpOnLaunch': 'map_public_ip_on_launch',
            'Tags': 'tags'
        },
        'aws_security_group': {
            'GroupDescription': 'description',
            'GroupName': 'name',
            'VpcId': 'vpc_id',
            'SecurityGroupIngress': 'ingress',
            'SecurityGroupEgress': 'egress',
            'Tags': 'tags'
        },
        'aws_s3_bucket': {
            'BucketName': 'bucket',
            'AccessControl': 'acl',
            'BucketEncryption': 'server_side_encryption_configuration',
            'PublicAccessBlockConfiguration': 'public_access_block',
            'VersioningConfiguration': 'versioning',
            'Tags': 'tags'
        },
        'aws_db_instance': {
            'DBInstanceIdentifier': 'identifier',
            'DBInstanceClass': 'instance_class',
            'Engine': 'engine',
            'EngineVersion': 'engine_version',
            'AllocatedStorage': 'allocated_storage',
            'StorageType': 'storage_type',
            'StorageEncrypted': 'storage_encrypted',
            'KmsKeyId': 'kms_key_id',
            'DBName': 'db_name',
            'MasterUsername': 'username',
            'MasterUserPassword': 'password',
            'VPCSecurityGroups': 'vpc_security_group_ids',
            'DBSubnetGroupName': 'db_subnet_group_name',
            'ParameterGroupName': 'parameter_group_name',
            'BackupRetentionPeriod': 'backup_retention_period',
            'PreferredBackupWindow': 'backup_window',
            'PreferredMaintenanceWindow': 'maintenance_window',
            'MultiAZ': 'multi_az',
            'PubliclyAccessible': 'publicly_accessible',
            'Tags': 'tags'
        }
    }
    
    @classmethod
    def get_terraform_type(cls, cf_type: str) -> Optional[str]:
        """Get Terraform resource type for CloudFormation type"""
        return cls.RESOURCE_TYPE_MAPPING.get(cf_type)
    
    @classmethod
    def map_properties(cls, cf_type: str, cf_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Map CloudFormation properties to Terraform properties"""
        terraform_type = cls.get_terraform_type(cf_type)
        if not terraform_type:
            return cf_properties
        
        property_mapping = cls.PROPERTY_MAPPINGS.get(terraform_type, {})
        terraform_properties = {}
        
        for cf_prop, value in cf_properties.items():
            terraform_prop = property_mapping.get(cf_prop, cf_prop.lower())
            terraform_properties[terraform_prop] = value
        
        return terraform_properties


class IntrinsicFunctionHandler:
    """Handles CloudFormation intrinsic functions and converts them to Terraform equivalents"""
    
    def __init__(self, parameters: Dict[str, Any] = None, mappings: Dict[str, Any] = None):
        self.parameters = parameters or {}
        self.mappings = mappings or {}
    
    def process_value(self, value: Any, context: Dict[str, Any] = None) -> Any:
        """Process a value that may contain intrinsic functions"""
        context = context or {}
        
        if isinstance(value, dict):
            if len(value) == 1:
                func_name, func_args = next(iter(value.items()))
                if func_name.startswith('Fn::') or func_name == 'Ref':
                    return self._handle_intrinsic_function(func_name, func_args, context)
            
            # Process nested dictionaries
            return {k: self.process_value(v, context) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self.process_value(item, context) for item in value]
        
        return value
    
    def _handle_intrinsic_function(self, func_name: str, func_args: Any, context: Dict[str, Any]) -> str:
        """Handle specific intrinsic functions"""
        
        if func_name == 'Ref':
            return self._handle_ref(func_args, context)
        
        elif func_name == 'Fn::GetAtt':
            return self._handle_get_att(func_args, context)
        
        elif func_name == 'Fn::Join':
            return self._handle_join(func_args, context)
        
        elif func_name == 'Fn::Sub':
            return self._handle_sub(func_args, context)
        
        elif func_name == 'Fn::Select':
            return self._handle_select(func_args, context)
        
        elif func_name == 'Fn::Split':
            return self._handle_split(func_args, context)
        
        elif func_name == 'Fn::Base64':
            return self._handle_base64(func_args, context)
        
        elif func_name == 'Fn::GetAZs':
            return self._handle_get_azs(func_args, context)
        
        elif func_name == 'Fn::FindInMap':
            return self._handle_find_in_map(func_args, context)
        
        elif func_name == 'Fn::If':
            return self._handle_if(func_args, context)
        
        else:
            logger.warning(f"Unsupported intrinsic function: {func_name}")
            return f"# TODO: Convert {func_name}({func_args})"
    
    def _handle_ref(self, resource_name: str, context: Dict[str, Any]) -> str:
        """Handle Ref function"""
        # Check if it's a parameter
        if resource_name in self.parameters:
            return f"var.{resource_name.lower()}"
        
        # Check if it's a resource in the current template
        if resource_name in context.get('resources', {}):
            # Determine the appropriate reference based on resource type
            resource_info = context['resources'][resource_name]
            resource_type = resource_info.get('Type', '')
            
            if resource_type == 'AWS::EC2::Instance':
                return f"aws_instance.{resource_name.lower()}.id"
            elif resource_type == 'AWS::EC2::VPC':
                return f"aws_vpc.{resource_name.lower()}.id"
            elif resource_type == 'AWS::EC2::Subnet':
                return f"aws_subnet.{resource_name.lower()}.id"
            elif resource_type == 'AWS::EC2::SecurityGroup':
                return f"aws_security_group.{resource_name.lower()}.id"
            elif resource_type == 'AWS::S3::Bucket':
                return f"aws_s3_bucket.{resource_name.lower()}.id"
            else:
                # Generic reference
                terraform_type = ResourceMapper.get_terraform_type(resource_type)
                if terraform_type:
                    return f"{terraform_type}.{resource_name.lower()}.id"
        
        # AWS pseudo parameters
        aws_pseudo_params = {
            'AWS::Region': 'data.aws_region.current.name',
            'AWS::AccountId': 'data.aws_caller_identity.current.account_id',
            'AWS::StackName': 'var.stack_name',
            'AWS::StackId': 'var.stack_id',
            'AWS::Partition': 'data.aws_partition.current.partition'
        }
        
        if resource_name in aws_pseudo_params:
            return aws_pseudo_params[resource_name]
        
        return f"# TODO: Resolve reference to {resource_name}"
    
    def _handle_get_att(self, args: List[str], context: Dict[str, Any]) -> str:
        """Handle Fn::GetAtt function"""
        if len(args) != 2:
            return f"# TODO: Invalid GetAtt arguments: {args}"
        
        resource_name, attribute = args
        
        # Common attribute mappings
        attribute_mappings = {
            'AWS::EC2::Instance': {
                'PrivateIp': 'private_ip',
                'PublicIp': 'public_ip',
                'PrivateDnsName': 'private_dns',
                'PublicDnsName': 'public_dns',
                'AvailabilityZone': 'availability_zone'
            },
            'AWS::EC2::VPC': {
                'CidrBlock': 'cidr_block',
                'DefaultNetworkAcl': 'default_network_acl_id',
                'DefaultSecurityGroup': 'default_security_group_id'
            },
            'AWS::S3::Bucket': {
                'Arn': 'arn',
                'DomainName': 'bucket_domain_name',
                'RegionalDomainName': 'bucket_regional_domain_name'
            },
            'AWS::RDS::DBInstance': {
                'Endpoint.Address': 'endpoint',
                'Endpoint.Port': 'port'
            }
        }
        
        if resource_name in context.get('resources', {}):
            resource_info = context['resources'][resource_name]
            resource_type = resource_info.get('Type', '')
            terraform_type = ResourceMapper.get_terraform_type(resource_type)
            
            if terraform_type and resource_type in attribute_mappings:
                terraform_attr = attribute_mappings[resource_type].get(attribute, attribute.lower())
                return f"{terraform_type}.{resource_name.lower()}.{terraform_attr}"
        
        return f"# TODO: GetAtt {resource_name}.{attribute}"
    
    def _handle_join(self, args: List[Any], context: Dict[str, Any]) -> str:
        """Handle Fn::Join function"""
        if len(args) != 2:
            return f"# TODO: Invalid Join arguments: {args}"
        
        delimiter, values = args
        processed_values = []
        
        for value in values:
            processed_value = self.process_value(value, context)
            if isinstance(processed_value, str):
                processed_values.append(f'"{processed_value}"')
            else:
                processed_values.append(str(processed_value))
        
        return f'join("{delimiter}", [{", ".join(processed_values)}])'
    
    def _handle_sub(self, args: Union[str, List[Any]], context: Dict[str, Any]) -> str:
        """Handle Fn::Sub function"""
        if isinstance(args, str):
            template_string = args
            variables = {}
        elif isinstance(args, list) and len(args) == 2:
            template_string, variables = args
        else:
            return f"# TODO: Invalid Sub arguments: {args}"
        
        # Process variables in the substitution
        processed_vars = {}
        for var_name, var_value in variables.items():
            processed_vars[var_name] = self.process_value(var_value, context)
        
        # Convert CloudFormation substitution syntax to Terraform
        # Replace ${VarName} with ${var.varname} or appropriate Terraform reference
        def replace_var(match):
            var_name = match.group(1)
            
            # Check if it's in the provided variables
            if var_name in processed_vars:
                return f"${{{processed_vars[var_name]}}}"
            
            # Handle AWS pseudo parameters
            if var_name.startswith('AWS::'):
                aws_pseudo_params = {
                    'AWS::Region': 'data.aws_region.current.name',
                    'AWS::AccountId': 'data.aws_caller_identity.current.account_id',
                    'AWS::StackName': 'var.stack_name'
                }
                if var_name in aws_pseudo_params:
                    return f"${{{aws_pseudo_params[var_name]}}}"
            
            # Handle parameter references
            if var_name in self.parameters:
                return f"${{var.{var_name.lower()}}}"
            
            # Handle resource references
            if var_name in context.get('resources', {}):
                return f"${{{self._handle_ref(var_name, context)}}}"
            
            return f"${{{var_name}}}"  # Keep as-is if can't resolve
        
        # Replace ${VarName} patterns
        result = re.sub(r'\$\{([^}]+)\}', replace_var, template_string)
        return f'"{result}"'
    
    def _handle_select(self, args: List[Any], context: Dict[str, Any]) -> str:
        """Handle Fn::Select function"""
        if len(args) != 2:
            return f"# TODO: Invalid Select arguments: {args}"
        
        index, array = args
        processed_array = self.process_value(array, context)
        
        return f"element({processed_array}, {index})"
    
    def _handle_split(self, args: List[Any], context: Dict[str, Any]) -> str:
        """Handle Fn::Split function"""
        if len(args) != 2:
            return f"# TODO: Invalid Split arguments: {args}"
        
        delimiter, string = args
        processed_string = self.process_value(string, context)
        
        return f'split("{delimiter}", {processed_string})'
    
    def _handle_base64(self, value: Any, context: Dict[str, Any]) -> str:
        """Handle Fn::Base64 function"""
        processed_value = self.process_value(value, context)
        return f"base64encode({processed_value})"
    
    def _handle_get_azs(self, region: str, context: Dict[str, Any]) -> str:
        """Handle Fn::GetAZs function"""
        if region == "":
            return "data.aws_availability_zones.available.names"
        else:
            processed_region = self.process_value(region, context)
            return f"# TODO: GetAZs for specific region {processed_region}"
    
    def _handle_find_in_map(self, args: List[Any], context: Dict[str, Any]) -> str:
        """Handle Fn::FindInMap function"""
        if len(args) != 3:
            return f"# TODO: Invalid FindInMap arguments: {args}"
        
        map_name, top_level_key, second_level_key = args
        
        # Try to resolve from mappings
        if map_name in self.mappings:
            try:
                processed_top_key = self.process_value(top_level_key, context)
                processed_second_key = self.process_value(second_level_key, context)
                
                # If keys are static strings, we can resolve the value
                if isinstance(processed_top_key, str) and isinstance(processed_second_key, str):
                    value = self.mappings[map_name][processed_top_key][processed_second_key]
                    return f'"{value}"'
            except (KeyError, TypeError):
                pass
        
        # Convert to Terraform local value lookup
        return f"local.{map_name.lower()}[{self.process_value(top_level_key, context)}][{self.process_value(second_level_key, context)}]"
    
    def _handle_if(self, args: List[Any], context: Dict[str, Any]) -> str:
        """Handle Fn::If function"""
        if len(args) != 3:
            return f"# TODO: Invalid If arguments: {args}"
        
        condition_name, true_value, false_value = args
        
        processed_true = self.process_value(true_value, context)
        processed_false = self.process_value(false_value, context)
        
        return f"var.{condition_name.lower()} - {processed_true} : {processed_false}"


class ConversionEngine:
    """
    CloudFormation to Terraform conversion engine
    
    This class handles the conversion of CloudFormation templates and resources
    into equivalent Terraform configurations with comprehensive resource mapping
    and intrinsic function handling.
    """
    
    def __init__(self, preserve_names: bool = True, handle_functions: bool = True):
        """
        Initialize the conversion engine
        
        Args:
            preserve_names: Whether to preserve original CloudFormation resource names
            handle_functions: Whether to convert CloudFormation intrinsic functions
        """
        self.preserve_names = preserve_names
        self.handle_functions = handle_functions
        self.resource_mapper = ResourceMapper()
        
        logger.info("Initialized ConversionEngine")
    
    def convert_template(self, template: Dict[str, Any], stack_name: str = None) -> ConversionResult:
        """
        Convert a complete CloudFormation template to Terraform configuration
        
        Args:
            template: CloudFormation template as dictionary
            stack_name: Name of the CloudFormation stack
            
        Returns:
            ConversionResult with Terraform configuration and metadata
        """
        logger.info(f"Converting CloudFormation template to Terraform")
        
        result = ConversionResult(terraform_config={})
        
        try:
            # Extract template sections
            parameters = template.get('Parameters', {})
            mappings = template.get('Mappings', {})
            conditions = template.get('Conditions', {})
            resources = template.get('Resources', {})
            outputs = template.get('Outputs', {})
            
            # Initialize intrinsic function handler
            func_handler = IntrinsicFunctionHandler(parameters, mappings)
            
            # Convert parameters to variables
            if parameters:
                result.variables = self._convert_parameters(parameters)
            
            # Convert mappings to locals
            if mappings:
                result.locals.update(self._convert_mappings(mappings))
            
            # Convert conditions to locals (simplified)
            if conditions:
                result.locals.update(self._convert_conditions(conditions, func_handler))
            
            # Convert resources
            terraform_resources = {}
            context = {'resources': resources, 'parameters': parameters}
            
            for logical_id, resource_config in resources.items():
                try:
                    converted_resource = self._convert_resource(
                        logical_id, resource_config, func_handler, context
                    )
                    
                    if converted_resource:
                        terraform_resources.update(converted_resource['resources'])
                        result.import_commands.extend(converted_resource.get('import_commands', []))
                        result.warnings.extend(converted_resource.get('warnings', []))
                
                except Exception as e:
                    error_msg = f"Failed to convert resource {logical_id}: {str(e)}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
            
            result.terraform_config['resource'] = terraform_resources
            
            # Convert outputs
            if outputs:
                result.outputs = self._convert_outputs(outputs, func_handler, context)
            
            # Add required data sources
            data_sources = self._generate_data_sources()
            if data_sources:
                result.terraform_config['data'] = data_sources
            
            # Add locals if any
            if result.locals:
                result.terraform_config['locals'] = result.locals
            
            logger.info(f"Template conversion completed: {len(terraform_resources)} resources converted")
            
        except Exception as e:
            error_msg = f"Template conversion failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def convert_resource(self, logical_id: str, resource_config: Dict[str, Any], 
                        physical_id: str = None) -> ConversionResult:
        """
        Convert a single CloudFormation resource to Terraform
        
        Args:
            logical_id: CloudFormation logical resource ID
            resource_config: CloudFormation resource configuration
            physical_id: AWS physical resource ID for import
            
        Returns:
            ConversionResult with converted resource
        """
        logger.info(f"Converting resource: {logical_id} ({resource_config.get('Type', 'Unknown')})")
        
        result = ConversionResult(terraform_config={})
        func_handler = IntrinsicFunctionHandler()
        
        try:
            converted = self._convert_resource(logical_id, resource_config, func_handler, {})
            
            if converted:
                result.terraform_config['resource'] = converted['resources']
                result.import_commands = converted.get('import_commands', [])
                result.warnings = converted.get('warnings', [])
                
                # Add physical ID to import command if provided
                if physical_id and result.import_commands:
                    for i, cmd in enumerate(result.import_commands):
                        if 'PHYSICAL_ID' in cmd:
                            result.import_commands[i] = cmd.replace('PHYSICAL_ID', physical_id)
        
        except Exception as e:
            error_msg = f"Resource conversion failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def _convert_resource(self, logical_id: str, resource_config: Dict[str, Any],
                         func_handler: IntrinsicFunctionHandler, 
                         context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single CloudFormation resource"""
        
        cf_type = resource_config.get('Type')
        if not cf_type:
            return None
        
        terraform_type = self.resource_mapper.get_terraform_type(cf_type)
        if not terraform_type:
            logger.warning(f"No Terraform mapping for CloudFormation type: {cf_type}")
            return {
                'resources': {},
                'warnings': [f"Unsupported resource type: {cf_type}"],
                'import_commands': []
            }
        
        # Handle special cases
        if cf_type == 'AWS::CloudFormation::Stack':
            return self._convert_nested_stack(logical_id, resource_config, func_handler, context)
        
        # Get resource properties
        cf_properties = resource_config.get('Properties', {})
        
        # Process properties through intrinsic function handler
        if self.handle_functions:
            processed_properties = func_handler.process_value(cf_properties, context)
        else:
            processed_properties = cf_properties
        
        # Map properties to Terraform equivalents
        terraform_properties = self.resource_mapper.map_properties(cf_type, processed_properties)
        
        # Apply resource-specific transformations
        terraform_properties = self._apply_resource_transformations(
            cf_type, terraform_properties, logical_id
        )
        
        # Generate resource name
        resource_name = logical_id.lower() if self.preserve_names else self._generate_resource_name(logical_id)
        
        # Build Terraform resource
        terraform_resource = {
            terraform_type: {
                resource_name: terraform_properties
            }
        }
        
        # Generate import command
        import_command = self._generate_import_command(terraform_type, resource_name, cf_type)
        
        return {
            'resources': terraform_resource,
            'import_commands': [import_command] if import_command else [],
            'warnings': []
        }
    
    def _convert_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CloudFormation parameters to Terraform variables"""
        variables = {}
        
        for param_name, param_config in parameters.items():
            variable_name = param_name.lower()
            
            variable_def = {
                'description': param_config.get('Description', f'CloudFormation parameter {param_name}'),
                'type': self._map_parameter_type(param_config.get('Type', 'String'))
            }
            
            # Add default value if present
            if 'Default' in param_config:
                variable_def['default'] = param_config['Default']
            
            # Add validation if present
            if 'AllowedValues' in param_config:
                variable_def['validation'] = {
                    'condition': f'contains({param_config["AllowedValues"]}, var.{variable_name})',
                    'error_message': f'Value must be one of: {", ".join(param_config["AllowedValues"])}'
                }
            
            variables[variable_name] = variable_def
        
        return variables
    
    def _convert_mappings(self, mappings: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CloudFormation mappings to Terraform locals"""
        locals_dict = {}
        
        for mapping_name, mapping_data in mappings.items():
            local_name = mapping_name.lower()
            locals_dict[local_name] = mapping_data
        
        return locals_dict
    
    def _convert_conditions(self, conditions: Dict[str, Any], 
                           func_handler: IntrinsicFunctionHandler) -> Dict[str, Any]:
        """Convert CloudFormation conditions to Terraform locals (simplified)"""
        locals_dict = {}
        
        for condition_name, condition_expr in conditions.items():
            local_name = condition_name.lower()
            # Simplified conversion - in practice, this would need more sophisticated logic
            locals_dict[local_name] = f"# TODO: Convert condition {condition_name}"
        
        return locals_dict
    
    def _convert_outputs(self, outputs: Dict[str, Any], 
                        func_handler: IntrinsicFunctionHandler,
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CloudFormation outputs to Terraform outputs"""
        terraform_outputs = {}
        
        for output_name, output_config in outputs.items():
            output_def = {
                'description': output_config.get('Description', f'CloudFormation output {output_name}'),
                'value': func_handler.process_value(output_config.get('Value'), context)
            }
            
            # Add export name as a tag if present
            if 'Export' in output_config:
                export_name = output_config['Export'].get('Name')
                if export_name:
                    output_def['description'] += f' (exported as {export_name})'
            
            terraform_outputs[output_name.lower()] = output_def
        
        return terraform_outputs
    
    def _convert_nested_stack(self, logical_id: str, resource_config: Dict[str, Any],
                             func_handler: IntrinsicFunctionHandler, 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert AWS::CloudFormation::Stack to Terraform module"""
        
        properties = resource_config.get('Properties', {})
        
        # Process template URL and parameters
        template_url = properties.get('TemplateURL', '')
        parameters = properties.get('Parameters', {})
        
        # Convert to module call
        module_name = logical_id.lower()
        module_config = {
            'source': f'# TODO: Convert nested stack template from {template_url}',
        }
        
        # Add parameters as module inputs
        for param_name, param_value in parameters.items():
            processed_value = func_handler.process_value(param_value, context)
            module_config[param_name.lower()] = processed_value
        
        terraform_resource = {
            'module': {
                module_name: module_config
            }
        }
        
        return {
            'resources': terraform_resource,
            'import_commands': [],
            'warnings': [f'Nested stack {logical_id} requires manual template conversion']
        }
    
    def _apply_resource_transformations(self, cf_type: str, properties: Dict[str, Any], 
                                      logical_id: str) -> Dict[str, Any]:
        """Apply resource-specific transformations"""
        
        # Security group rule transformations
        if cf_type in ['AWS::EC2::SecurityGroupIngress', 'AWS::EC2::SecurityGroupEgress']:
            return self._transform_security_group_rule(properties, cf_type)
        
        # S3 bucket transformations
        elif cf_type == 'AWS::S3::Bucket':
            return self._transform_s3_bucket(properties)
        
        # IAM role transformations
        elif cf_type == 'AWS::IAM::Role':
            return self._transform_iam_role(properties)
        
        # Lambda function transformations
        elif cf_type == 'AWS::Lambda::Function':
            return self._transform_lambda_function(properties)
        
        return properties
    
    def _transform_security_group_rule(self, properties: Dict[str, Any], cf_type: str) -> Dict[str, Any]:
        """Transform security group rule properties"""
        transformed = properties.copy()
        
        # Set rule type
        transformed['type'] = 'ingress' if 'Ingress' in cf_type else 'egress'
        
        # Map protocol
        if 'IpProtocol' in transformed:
            protocol = transformed.pop('IpProtocol')
            transformed['protocol'] = protocol
        
        # Map port ranges
        if 'FromPort' in transformed:
            transformed['from_port'] = transformed.pop('FromPort')
        if 'ToPort' in transformed:
            transformed['to_port'] = transformed.pop('ToPort')
        
        # Map CIDR blocks
        if 'CidrIp' in transformed:
            transformed['cidr_blocks'] = [transformed.pop('CidrIp')]
        
        return transformed
    
    def _transform_s3_bucket(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Transform S3 bucket properties"""
        transformed = properties.copy()
        
        # Handle bucket encryption
        if 'BucketEncryption' in transformed:
            encryption_config = transformed.pop('BucketEncryption')
            if 'ServerSideEncryptionConfiguration' in encryption_config:
                transformed['server_side_encryption_configuration'] = encryption_config['ServerSideEncryptionConfiguration']
        
        # Handle versioning
        if 'VersioningConfiguration' in transformed:
            versioning = transformed.pop('VersioningConfiguration')
            transformed['versioning'] = {
                'enabled': versioning.get('Status') == 'Enabled'
            }
        
        return transformed
    
    def _transform_iam_role(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IAM role properties"""
        transformed = properties.copy()
        
        # Convert assume role policy document
        if 'AssumeRolePolicyDocument' in transformed:
            policy_doc = transformed.pop('AssumeRolePolicyDocument')
            if isinstance(policy_doc, dict):
                transformed['assume_role_policy'] = json.dumps(policy_doc)
            else:
                transformed['assume_role_policy'] = policy_doc
        
        # Handle managed policy ARNs
        if 'ManagedPolicyArns' in transformed:
            transformed['managed_policy_arns'] = transformed.pop('ManagedPolicyArns')
        
        return transformed
    
    def _transform_lambda_function(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Lambda function properties"""
        transformed = properties.copy()
        
        # Map function name
        if 'FunctionName' in transformed:
            transformed['function_name'] = transformed.pop('FunctionName')
        
        # Map runtime
        if 'Runtime' in transformed:
            transformed['runtime'] = transformed.pop('Runtime')
        
        # Map handler
        if 'Handler' in transformed:
            transformed['handler'] = transformed.pop('Handler')
        
        # Map code
        if 'Code' in transformed:
            code_config = transformed.pop('Code')
            if 'S3Bucket' in code_config and 'S3Key' in code_config:
                transformed['s3_bucket'] = code_config['S3Bucket']
                transformed['s3_key'] = code_config['S3Key']
                if 'S3ObjectVersion' in code_config:
                    transformed['s3_object_version'] = code_config['S3ObjectVersion']
            elif 'ZipFile' in code_config:
                transformed['filename'] = 'lambda_function.zip'
                # Note: ZipFile content would need to be written to a file
        
        return transformed
    
    def _generate_data_sources(self) -> Dict[str, Any]:
        """Generate commonly needed data sources"""
        return {
            'aws_region': {
                'current': {}
            },
            'aws_caller_identity': {
                'current': {}
            },
            'aws_partition': {
                'current': {}
            },
            'aws_availability_zones': {
                'available': {
                    'state': 'available'
                }
            }
        }
    
    def _generate_import_command(self, terraform_type: str, resource_name: str, cf_type: str) -> Optional[str]:
        """Generate Terraform import command for a resource"""
        
        # Import command templates for different resource types
        import_templates = {
            'aws_instance': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_vpc': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_subnet': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_security_group': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_s3_bucket': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_db_instance': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_iam_role': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
            'aws_lambda_function': f'terraform import {terraform_type}.{resource_name} PHYSICAL_ID',
        }
        
        return import_templates.get(terraform_type)
    
    def _map_parameter_type(self, cf_type: str) -> str:
        """Map CloudFormation parameter type to Terraform variable type"""
        type_mapping = {
            'String': 'string',
            'Number': 'number',
            'CommaDelimitedList': 'list(string)',
            'AWS::EC2::AvailabilityZone::Name': 'string',
            'AWS::EC2::Image::Id': 'string',
            'AWS::EC2::Instance::Id': 'string',
            'AWS::EC2::KeyPair::KeyName': 'string',
            'AWS::EC2::SecurityGroup::Id': 'string',
            'AWS::EC2::Subnet::Id': 'string',
            'AWS::EC2::VPC::Id': 'string',
            'AWS::Route53::HostedZone::Id': 'string',
            'AWS::SSM::Parameter::Value<String>': 'string'
        }
        
        return type_mapping.get(cf_type, 'string')
    
    def _generate_resource_name(self, logical_id: str) -> str:
        """Generate a Terraform-friendly resource name from CloudFormation logical ID"""
        # Convert CamelCase to snake_case
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', logical_id).lower()
        
        # Replace any remaining non-alphanumeric characters with underscores
        name = re.sub(r'[^a-z0-9_]', '_', name)
        
        # Remove duplicate underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        return name or 'resource'


if __name__ == "__main__":
    # Example usage
    converter = ConversionEngine()
    
    # Example CloudFormation template
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Parameters": {
            "InstanceType": {
                "Type": "String",
                "Default": "t3.micro",
                "Description": "EC2 instance type"
            }
        },
        "Resources": {
            "MyVPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                    "EnableDnsHostnames": True,
                    "Tags": [{"Key": "Name", "Value": "MyVPC"}]
                }
            },
            "MyInstance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": "ami-0abcdef1234567890",
                    "InstanceType": {"Ref": "InstanceType"},
                    "Tags": [{"Key": "Name", "Value": "MyInstance"}]
                }
            }
        },
        "Outputs": {
            "VPCId": {
                "Description": "VPC ID",
                "Value": {"Ref": "MyVPC"}
            }
        }
    }
    
    result = converter.convert_template(cf_template)
    
    print("Conversion Result:")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Resources: {len(result.terraform_config.get('resource', {}))}")
    print(f"Variables: {len(result.variables)}")
    print(f"Outputs: {len(result.outputs)}")
    print(f"Import commands: {len(result.import_commands)}")
    
    if result.terraform_config:
        print("\nTerraform Configuration:")
        print(json.dumps(result.terraform_config, indent=2))

