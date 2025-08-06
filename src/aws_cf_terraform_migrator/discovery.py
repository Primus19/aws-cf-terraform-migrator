#!/usr/bin/env python3
"""
CloudFormation Discovery Engine

This module implements comprehensive CloudFormation stack discovery and resource enumeration
capabilities. It provides both CloudFormation-specific discovery and independent AWS resource
discovery to ensure complete infrastructure coverage.
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError, NoCredentialsError
import time
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StackInfo:
    """Information about a CloudFormation stack"""
    stack_id: str
    stack_name: str
    stack_status: str
    creation_time: str
    last_updated_time: Optional[str] = None
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    template_body: Optional[str] = None
    resources: List[Dict[str, Any]] = field(default_factory=list)
    nested_stacks: List[str] = field(default_factory=list)


@dataclass
class ResourceInfo:
    """Information about an AWS resource"""
    resource_id: str
    resource_type: str
    logical_id: Optional[str] = None
    stack_name: Optional[str] = None
    stack_id: Optional[str] = None
    region: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    managed_by_cloudformation: bool = False
    resource_status: Optional[str] = None
    created_time: Optional[str] = None


class DiscoveryEngine:
    """
    CloudFormation and AWS resource discovery engine
    
    This class provides comprehensive discovery capabilities for both CloudFormation-managed
    resources and independent AWS resources across multiple regions and accounts.
    """
    
    def __init__(self, 
                 regions: Optional[List[str]] = None,
                 profile: Optional[str] = None,
                 role_arn: Optional[str] = None,
                 max_workers: int = 10):
        """
        Initialize the discovery engine
        
        Args:
            regions: List of AWS regions to scan (defaults to current region)
            profile: AWS profile to use for authentication
            role_arn: IAM role ARN to assume for cross-account access
            max_workers: Maximum number of concurrent threads for discovery
        """
        self.regions = regions or ['us-east-1']  # Default to us-east-1 if not specified
        self.profile = profile
        self.role_arn = role_arn
        self.max_workers = max_workers
        
        # Initialize AWS session
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        
        # Storage for discovered resources
        self.stacks: Dict[str, StackInfo] = {}
        self.resources: Dict[str, ResourceInfo] = {}
        self.stack_hierarchy: Dict[str, List[str]] = {}  # parent -> children mapping
        
        # CloudFormation resource tags that identify managed resources
        self.cf_tags = {
            'aws:cloudformation:stack-name',
            'aws:cloudformation:stack-id', 
            'aws:cloudformation:logical-id'
        }
        
        logger.info(f"Initialized DiscoveryEngine for regions: {self.regions}")
    
    def discover_all(self, 
                    include_deleted: bool = False,
                    stack_name_filter: Optional[str] = None) -> Tuple[Dict[str, StackInfo], Dict[str, ResourceInfo]]:
        """
        Perform comprehensive discovery of CloudFormation stacks and AWS resources
        
        Args:
            include_deleted: Whether to include deleted stacks in discovery
            stack_name_filter: Optional filter to limit discovery to specific stack names
            
        Returns:
            Tuple of (stacks_dict, resources_dict)
        """
        logger.info("Starting comprehensive AWS resource discovery")
        
        try:
            # Phase 1: Discover CloudFormation stacks
            self._discover_cloudformation_stacks(include_deleted, stack_name_filter)
            
            # Phase 2: Discover independent resources
            self._discover_independent_resources()
            
            # Phase 3: Build resource relationships
            self._build_resource_relationships()
            
            logger.info(f"Discovery complete: {len(self.stacks)} stacks, {len(self.resources)} resources")
            return self.stacks, self.resources
            
        except Exception as e:
            logger.error(f"Discovery failed: {str(e)}")
            raise
    
    def _discover_cloudformation_stacks(self, 
                                      include_deleted: bool = False,
                                      stack_name_filter: Optional[str] = None):
        """Discover all CloudFormation stacks across specified regions"""
        logger.info("Discovering CloudFormation stacks")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for region in self.regions:
                future = executor.submit(
                    self._discover_stacks_in_region, 
                    region, 
                    include_deleted, 
                    stack_name_filter
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    region_stacks = future.result()
                    self.stacks.update(region_stacks)
                except Exception as e:
                    logger.error(f"Failed to discover stacks in region: {str(e)}")
    
    def _discover_stacks_in_region(self, 
                                  region: str, 
                                  include_deleted: bool = False,
                                  stack_name_filter: Optional[str] = None) -> Dict[str, StackInfo]:
        """Discover CloudFormation stacks in a specific region"""
        logger.info(f"Discovering stacks in region: {region}")
        
        try:
            cf_client = self.session.client('cloudformation', region_name=region)
            region_stacks = {}
            
            # List all stacks
            paginator = cf_client.get_paginator('list_stacks')
            
            # Configure stack status filter
            stack_statuses = [
                'CREATE_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE',
                'IMPORT_COMPLETE', 'IMPORT_ROLLBACK_COMPLETE'
            ]
            
            if include_deleted:
                stack_statuses.extend(['DELETE_COMPLETE'])
            
            page_iterator = paginator.paginate(StackStatusFilter=stack_statuses)
            
            for page in page_iterator:
                for stack_summary in page['StackSummaries']:
                    stack_name = stack_summary['StackName']
                    
                    # Apply name filter if specified
                    if stack_name_filter and stack_name_filter not in stack_name:
                        continue
                    
                    try:
                        # Get detailed stack information
                        stack_info = self._get_stack_details(cf_client, stack_name, region)
                        if stack_info:
                            region_stacks[stack_info.stack_id] = stack_info
                            logger.debug(f"Discovered stack: {stack_name}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to get details for stack {stack_name}: {str(e)}")
                        continue
            
            logger.info(f"Discovered {len(region_stacks)} stacks in {region}")
            return region_stacks
            
        except ClientError as e:
            logger.error(f"AWS API error in region {region}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in region {region}: {str(e)}")
            return {}
    
    def _get_stack_details(self, cf_client, stack_name: str, region: str) -> Optional[StackInfo]:
        """Get comprehensive details for a specific stack"""
        try:
            # Get stack information
            stack_response = cf_client.describe_stacks(StackName=stack_name)
            stack_data = stack_response['Stacks'][0]
            
            # Get stack resources
            resources_response = cf_client.describe_stack_resources(StackName=stack_name)
            resources = resources_response['StackResources']
            
            # Get stack template
            template_body = None
            try:
                template_response = cf_client.get_template(StackName=stack_name)
                template_body = json.dumps(template_response['TemplateBody'], indent=2)
            except Exception as e:
                logger.warning(f"Could not retrieve template for stack {stack_name}: {str(e)}")
            
            # Process parameters
            parameters = {}
            for param in stack_data.get('Parameters', []):
                parameters[param['ParameterKey']] = {
                    'value': param.get('ParameterValue'),
                    'resolved_value': param.get('ResolvedValue')
                }
            
            # Process outputs
            outputs = {}
            for output in stack_data.get('Outputs', []):
                outputs[output['OutputKey']] = {
                    'value': output.get('OutputValue'),
                    'description': output.get('Description'),
                    'export_name': output.get('ExportName')
                }
            
            # Process tags
            tags = {}
            for tag in stack_data.get('Tags', []):
                tags[tag['Key']] = tag['Value']
            
            # Create StackInfo object
            stack_info = StackInfo(
                stack_id=stack_data['StackId'],
                stack_name=stack_data['StackName'],
                stack_status=stack_data['StackStatus'],
                creation_time=stack_data['CreationTime'].isoformat(),
                last_updated_time=stack_data.get('LastUpdatedTime', '').isoformat() if stack_data.get('LastUpdatedTime') else None,
                description=stack_data.get('Description'),
                parameters=parameters,
                outputs=outputs,
                tags=tags,
                capabilities=stack_data.get('Capabilities', []),
                parent_id=stack_data.get('ParentId'),
                root_id=stack_data.get('RootId'),
                template_body=template_body,
                resources=resources
            )
            
            # Process stack resources and add to resource registry
            for resource in resources:
                resource_info = ResourceInfo(
                    resource_id=resource['PhysicalResourceId'],
                    resource_type=resource['ResourceType'],
                    logical_id=resource['LogicalResourceId'],
                    stack_name=stack_name,
                    stack_id=stack_data['StackId'],
                    region=region,
                    managed_by_cloudformation=True,
                    resource_status=resource.get('ResourceStatus'),
                    created_time=resource.get('Timestamp', '').isoformat() if resource.get('Timestamp') else None
                )
                
                # Add CloudFormation tags
                resource_info.tags.update({
                    'aws:cloudformation:stack-name': stack_name,
                    'aws:cloudformation:stack-id': stack_data['StackId'],
                    'aws:cloudformation:logical-id': resource['LogicalResourceId']
                })
                
                self.resources[resource_info.resource_id] = resource_info
            
            # Track nested stacks
            nested_stacks = []
            for resource in resources:
                if resource['ResourceType'] == 'AWS::CloudFormation::Stack':
                    nested_stacks.append(resource['PhysicalResourceId'])
            
            stack_info.nested_stacks = nested_stacks
            
            return stack_info
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                logger.warning(f"Stack {stack_name} not found or inaccessible")
            else:
                logger.error(f"AWS API error getting stack details for {stack_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting stack details for {stack_name}: {str(e)}")
            return None
    
    def _discover_independent_resources(self):
        """Discover AWS resources not managed by CloudFormation"""
        logger.info("Discovering independent AWS resources")
        
        # List of AWS services to scan for resources
        services_to_scan = [
            'ec2', 's3', 'rds', 'lambda', 'iam', 'dynamodb', 
            'elasticache', 'elbv2', 'elb', 'autoscaling',
            'route53', 'cloudfront', 'apigateway', 'sns', 'sqs'
        ]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for region in self.regions:
                for service in services_to_scan:
                    future = executor.submit(
                        self._discover_service_resources,
                        service,
                        region
                    )
                    futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    service_resources = future.result()
                    # Only add resources not already managed by CloudFormation
                    for resource_id, resource_info in service_resources.items():
                        if not resource_info.managed_by_cloudformation:
                            if resource_id not in self.resources:
                                self.resources[resource_id] = resource_info
                except Exception as e:
                    logger.error(f"Failed to discover service resources: {str(e)}")
    
    def _discover_service_resources(self, service: str, region: str) -> Dict[str, ResourceInfo]:
        """Discover resources for a specific AWS service in a region"""
        logger.debug(f"Discovering {service} resources in {region}")
        
        try:
            client = self.session.client(service, region_name=region)
            service_resources = {}
            
            if service == 'ec2':
                service_resources.update(self._discover_ec2_resources(client, region))
            elif service == 's3':
                service_resources.update(self._discover_s3_resources(client, region))
            elif service == 'rds':
                service_resources.update(self._discover_rds_resources(client, region))
            elif service == 'lambda':
                service_resources.update(self._discover_lambda_resources(client, region))
            elif service == 'iam':
                service_resources.update(self._discover_iam_resources(client, region))
            # Add more service discovery methods as needed
            
            return service_resources
            
        except ClientError as e:
            logger.warning(f"Could not access {service} in {region}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error discovering {service} resources in {region}: {str(e)}")
            return {}
    
    def _discover_ec2_resources(self, ec2_client, region: str) -> Dict[str, ResourceInfo]:
        """Discover EC2 resources (instances, VPCs, subnets, etc.)"""
        resources = {}
        
        try:
            # Discover EC2 instances
            paginator = ec2_client.get_paginator('describe_instances')
            for page in paginator.paginate():
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        
                        # Check if managed by CloudFormation
                        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                        is_cf_managed = bool(self.cf_tags.intersection(tags.keys()))
                        
                        resource_info = ResourceInfo(
                            resource_id=instance_id,
                            resource_type='AWS::EC2::Instance',
                            region=region,
                            tags=tags,
                            properties=instance,
                            managed_by_cloudformation=is_cf_managed
                        )
                        
                        resources[instance_id] = resource_info
            
            # Discover VPCs
            paginator = ec2_client.get_paginator('describe_vpcs')
            for page in paginator.paginate():
                for vpc in page['Vpcs']:
                    vpc_id = vpc['VpcId']
                    
                    tags = {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
                    is_cf_managed = bool(self.cf_tags.intersection(tags.keys()))
                    
                    resource_info = ResourceInfo(
                        resource_id=vpc_id,
                        resource_type='AWS::EC2::VPC',
                        region=region,
                        tags=tags,
                        properties=vpc,
                        managed_by_cloudformation=is_cf_managed
                    )
                    
                    resources[vpc_id] = resource_info
            
            # Add more EC2 resource types as needed (subnets, security groups, etc.)
            
        except Exception as e:
            logger.error(f"Error discovering EC2 resources: {str(e)}")
        
        return resources
    
    def _discover_s3_resources(self, s3_client, region: str) -> Dict[str, ResourceInfo]:
        """Discover S3 buckets"""
        resources = {}
        
        try:
            response = s3_client.list_buckets()
            
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                
                try:
                    # Get bucket tags
                    tags = {}
                    try:
                        tag_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                        tags = {tag['Key']: tag['Value'] for tag in tag_response['TagSet']}
                    except ClientError:
                        # Bucket has no tags
                        pass
                    
                    is_cf_managed = bool(self.cf_tags.intersection(tags.keys()))
                    
                    resource_info = ResourceInfo(
                        resource_id=bucket_name,
                        resource_type='AWS::S3::Bucket',
                        region=region,
                        tags=tags,
                        properties=bucket,
                        managed_by_cloudformation=is_cf_managed
                    )
                    
                    resources[bucket_name] = resource_info
                    
                except Exception as e:
                    logger.warning(f"Could not get details for bucket {bucket_name}: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error discovering S3 resources: {str(e)}")
        
        return resources
    
    def _discover_rds_resources(self, rds_client, region: str) -> Dict[str, ResourceInfo]:
        """Discover RDS instances and clusters"""
        resources = {}
        
        try:
            # Discover RDS instances
            paginator = rds_client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for instance in page['DBInstances']:
                    instance_id = instance['DBInstanceIdentifier']
                    
                    # Get tags
                    tags = {}
                    try:
                        tag_response = rds_client.list_tags_for_resource(
                            ResourceName=instance['DBInstanceArn']
                        )
                        tags = {tag['Key']: tag['Value'] for tag in tag_response['TagList']}
                    except Exception:
                        pass
                    
                    is_cf_managed = bool(self.cf_tags.intersection(tags.keys()))
                    
                    resource_info = ResourceInfo(
                        resource_id=instance_id,
                        resource_type='AWS::RDS::DBInstance',
                        region=region,
                        tags=tags,
                        properties=instance,
                        managed_by_cloudformation=is_cf_managed
                    )
                    
                    resources[instance_id] = resource_info
        
        except Exception as e:
            logger.error(f"Error discovering RDS resources: {str(e)}")
        
        return resources
    
    def _discover_lambda_resources(self, lambda_client, region: str) -> Dict[str, ResourceInfo]:
        """Discover Lambda functions"""
        resources = {}
        
        try:
            paginator = lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for function in page['Functions']:
                    function_name = function['FunctionName']
                    
                    # Get tags
                    tags = {}
                    try:
                        tag_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                        tags = tag_response.get('Tags', {})
                    except Exception:
                        pass
                    
                    is_cf_managed = bool(self.cf_tags.intersection(tags.keys()))
                    
                    resource_info = ResourceInfo(
                        resource_id=function_name,
                        resource_type='AWS::Lambda::Function',
                        region=region,
                        tags=tags,
                        properties=function,
                        managed_by_cloudformation=is_cf_managed
                    )
                    
                    resources[function_name] = resource_info
        
        except Exception as e:
            logger.error(f"Error discovering Lambda resources: {str(e)}")
        
        return resources
    
    def _discover_iam_resources(self, iam_client, region: str) -> Dict[str, ResourceInfo]:
        """Discover IAM resources (roles, policies, users)"""
        resources = {}
        
        try:
            # Discover IAM roles
            paginator = iam_client.get_paginator('list_roles')
            for page in paginator.paginate():
                for role in page['Roles']:
                    role_name = role['RoleName']
                    
                    # Get tags
                    tags = {}
                    try:
                        tag_response = iam_client.list_role_tags(RoleName=role_name)
                        tags = {tag['Key']: tag['Value'] for tag in tag_response['Tags']}
                    except Exception:
                        pass
                    
                    is_cf_managed = bool(self.cf_tags.intersection(tags.keys()))
                    
                    resource_info = ResourceInfo(
                        resource_id=role_name,
                        resource_type='AWS::IAM::Role',
                        region=region,
                        tags=tags,
                        properties=role,
                        managed_by_cloudformation=is_cf_managed
                    )
                    
                    resources[role_name] = resource_info
        
        except Exception as e:
            logger.error(f"Error discovering IAM resources: {str(e)}")
        
        return resources
    
    def _build_resource_relationships(self):
        """Build resource dependency relationships"""
        logger.info("Building resource relationships")
        
        # Build stack hierarchy
        for stack_id, stack_info in self.stacks.items():
            if stack_info.parent_id:
                if stack_info.parent_id not in self.stack_hierarchy:
                    self.stack_hierarchy[stack_info.parent_id] = []
                self.stack_hierarchy[stack_info.parent_id].append(stack_id)
        
        # Analyze resource dependencies
        for resource_id, resource_info in self.resources.items():
            dependencies = self._analyze_resource_dependencies(resource_info)
            resource_info.dependencies = dependencies
    
    def _analyze_resource_dependencies(self, resource_info: ResourceInfo) -> List[str]:
        """Analyze dependencies for a specific resource"""
        dependencies = []
        
        # Basic dependency analysis based on resource properties
        properties = resource_info.properties
        
        if resource_info.resource_type == 'AWS::EC2::Instance':
            # Instance depends on subnet, security groups, etc.
            if 'SubnetId' in properties:
                dependencies.append(properties['SubnetId'])
            if 'SecurityGroups' in properties:
                dependencies.extend(properties['SecurityGroups'])
        
        elif resource_info.resource_type == 'AWS::EC2::Subnet':
            # Subnet depends on VPC
            if 'VpcId' in properties:
                dependencies.append(properties['VpcId'])
        
        # Add more dependency analysis logic for other resource types
        
        return dependencies
    
    def get_stack_summary(self) -> Dict[str, Any]:
        """Get summary statistics of discovered stacks and resources"""
        stack_statuses = {}
        resource_types = {}
        cf_managed_count = 0
        independent_count = 0
        
        for stack in self.stacks.values():
            status = stack.stack_status
            stack_statuses[status] = stack_statuses.get(status, 0) + 1
        
        for resource in self.resources.values():
            resource_type = resource.resource_type
            resource_types[resource_type] = resource_types.get(resource_type, 0) + 1
            
            if resource.managed_by_cloudformation:
                cf_managed_count += 1
            else:
                independent_count += 1
        
        return {
            'total_stacks': len(self.stacks),
            'total_resources': len(self.resources),
            'cloudformation_managed': cf_managed_count,
            'independent_resources': independent_count,
            'stack_statuses': stack_statuses,
            'resource_types': resource_types,
            'regions_scanned': self.regions
        }
    
    def export_discovery_results(self, output_file: str):
        """Export discovery results to JSON file"""
        logger.info(f"Exporting discovery results to {output_file}")
        
        # Convert dataclasses to dictionaries for JSON serialization
        stacks_dict = {}
        for stack_id, stack_info in self.stacks.items():
            stacks_dict[stack_id] = {
                'stack_id': stack_info.stack_id,
                'stack_name': stack_info.stack_name,
                'stack_status': stack_info.stack_status,
                'creation_time': stack_info.creation_time,
                'last_updated_time': stack_info.last_updated_time,
                'description': stack_info.description,
                'parameters': stack_info.parameters,
                'outputs': stack_info.outputs,
                'tags': stack_info.tags,
                'capabilities': stack_info.capabilities,
                'parent_id': stack_info.parent_id,
                'root_id': stack_info.root_id,
                'nested_stacks': stack_info.nested_stacks,
                'resource_count': len(stack_info.resources)
            }
        
        resources_dict = {}
        for resource_id, resource_info in self.resources.items():
            resources_dict[resource_id] = {
                'resource_id': resource_info.resource_id,
                'resource_type': resource_info.resource_type,
                'logical_id': resource_info.logical_id,
                'stack_name': resource_info.stack_name,
                'stack_id': resource_info.stack_id,
                'region': resource_info.region,
                'tags': resource_info.tags,
                'dependencies': resource_info.dependencies,
                'managed_by_cloudformation': resource_info.managed_by_cloudformation,
                'resource_status': resource_info.resource_status,
                'created_time': resource_info.created_time
            }
        
        export_data = {
            'discovery_metadata': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'regions': self.regions,
                'summary': self.get_stack_summary()
            },
            'stacks': stacks_dict,
            'resources': resources_dict,
            'stack_hierarchy': self.stack_hierarchy
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Discovery results exported to {output_file}")


if __name__ == "__main__":
    # Example usage
    discovery = DiscoveryEngine(regions=['us-east-1', 'us-west-2'])
    stacks, resources = discovery.discover_all()
    
    print(f"Discovered {len(stacks)} stacks and {len(resources)} resources")
    print("\nSummary:")
    summary = discovery.get_stack_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Export results
    discovery.export_discovery_results('discovery_results.json')

