#!/usr/bin/env python3
"""
Unit tests for the discovery engine
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from aws_cf_terraform_migrator.discovery import DiscoveryEngine, StackInfo, ResourceInfo


class TestStackInfo(unittest.TestCase):
    """Test the StackInfo dataclass"""
    
    def test_stack_info_creation(self):
        """Test StackInfo creation with basic data"""
        stack_info = StackInfo(
            stack_name="test-stack",
            stack_id="arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/12345",
            stack_status="CREATE_COMPLETE",
            creation_time=datetime.now(),
            region="us-east-1"
        )
        
        self.assertEqual(stack_info.stack_name, "test-stack")
        self.assertEqual(stack_info.stack_status, "CREATE_COMPLETE")
        self.assertEqual(stack_info.region, "us-east-1")
        self.assertIsInstance(stack_info.resources, list)
        self.assertIsInstance(stack_info.parameters, dict)
        self.assertIsInstance(stack_info.outputs, dict)
    
    def test_stack_info_with_resources(self):
        """Test StackInfo with resources"""
        resources = [
            {'LogicalResourceId': 'MyVPC', 'PhysicalResourceId': 'vpc-12345'},
            {'LogicalResourceId': 'MySubnet', 'PhysicalResourceId': 'subnet-67890'}
        ]
        
        stack_info = StackInfo(
            stack_name="test-stack",
            stack_id="arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/12345",
            stack_status="CREATE_COMPLETE",
            creation_time=datetime.now(),
            region="us-east-1",
            resources=resources
        )
        
        self.assertEqual(len(stack_info.resources), 2)
        self.assertEqual(stack_info.resources[0]['PhysicalResourceId'], 'vpc-12345')


class TestResourceInfo(unittest.TestCase):
    """Test the ResourceInfo dataclass"""
    
    def test_resource_info_creation(self):
        """Test ResourceInfo creation"""
        resource_info = ResourceInfo(
            resource_id="vpc-12345",
            resource_type="AWS::EC2::VPC",
            region="us-east-1",
            managed_by_cloudformation=True,
            stack_name="test-stack"
        )
        
        self.assertEqual(resource_info.resource_id, "vpc-12345")
        self.assertEqual(resource_info.resource_type, "AWS::EC2::VPC")
        self.assertTrue(resource_info.managed_by_cloudformation)
        self.assertEqual(resource_info.stack_name, "test-stack")
    
    def test_resource_info_independent(self):
        """Test ResourceInfo for independent resource"""
        resource_info = ResourceInfo(
            resource_id="vpc-98765",
            resource_type="AWS::EC2::VPC",
            region="us-west-2",
            managed_by_cloudformation=False
        )
        
        self.assertFalse(resource_info.managed_by_cloudformation)
        self.assertIsNone(resource_info.stack_name)


class TestDiscoveryEngine(unittest.TestCase):
    """Test the DiscoveryEngine class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = DiscoveryEngine(regions=['us-east-1'])
    
    @patch('boto3.Session')
    def test_initialization(self, mock_session):
        """Test DiscoveryEngine initialization"""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        engine = DiscoveryEngine(
            regions=['us-east-1', 'us-west-2'],
            profile='test-profile',
            role_arn='arn:aws:iam::123456789012:role/test-role'
        )
        
        self.assertEqual(engine.regions, ['us-east-1', 'us-west-2'])
        self.assertEqual(engine.profile, 'test-profile')
        self.assertEqual(engine.role_arn, 'arn:aws:iam::123456789012:role/test-role')
    
    @patch('boto3.Session')
    def test_get_cloudformation_client(self, mock_session):
        """Test CloudFormation client creation"""
        mock_session_instance = Mock()
        mock_client = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_client
        
        engine = DiscoveryEngine(regions=['us-east-1'])
        client = engine._get_cloudformation_client('us-east-1')
        
        mock_session_instance.client.assert_called_with('cloudformation', region_name='us-east-1')
        self.assertEqual(client, mock_client)
    
    @patch('boto3.Session')
    def test_discover_stacks(self, mock_session):
        """Test stack discovery"""
        # Mock CloudFormation client
        mock_client = Mock()
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_client
        
        # Mock stack data
        mock_stacks_response = {
            'StackSummaries': [
                {
                    'StackName': 'test-stack-1',
                    'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack-1/12345',
                    'StackStatus': 'CREATE_COMPLETE',
                    'CreationTime': datetime.now()
                },
                {
                    'StackName': 'test-stack-2',
                    'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack-2/67890',
                    'StackStatus': 'UPDATE_COMPLETE',
                    'CreationTime': datetime.now()
                }
            ]
        }
        
        mock_client.list_stacks.return_value = mock_stacks_response
        
        # Mock individual stack details
        mock_stack_detail = {
            'Stacks': [{
                'StackName': 'test-stack-1',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack-1/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': datetime.now(),
                'Parameters': [],
                'Outputs': []
            }]
        }
        
        mock_client.describe_stacks.return_value = mock_stack_detail
        
        # Mock stack resources
        mock_resources_response = {
            'StackResources': [
                {
                    'LogicalResourceId': 'MyVPC',
                    'PhysicalResourceId': 'vpc-12345',
                    'ResourceType': 'AWS::EC2::VPC',
                    'ResourceStatus': 'CREATE_COMPLETE'
                }
            ]
        }
        
        mock_client.describe_stack_resources.return_value = mock_resources_response
        
        # Mock template body
        mock_template_response = {
            'TemplateBody': '{"Resources": {"MyVPC": {"Type": "AWS::EC2::VPC"}}}'
        }
        
        mock_client.get_template.return_value = mock_template_response
        
        # Test discovery
        stacks = self.engine.discover_stacks('us-east-1')
        
        self.assertEqual(len(stacks), 2)
        self.assertIn('test-stack-1', [stack.stack_name for stack in stacks.values()])
        self.assertIn('test-stack-2', [stack.stack_name for stack in stacks.values()])
    
    @patch('boto3.Session')
    def test_discover_independent_resources(self, mock_session):
        """Test discovery of independent resources"""
        # Mock EC2 client
        mock_ec2_client = Mock()
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        def mock_client_factory(service, region_name):
            if service == 'ec2':
                return mock_ec2_client
            return Mock()
        
        mock_session_instance.client.side_effect = mock_client_factory
        
        # Mock VPC data
        mock_vpcs_response = {
            'Vpcs': [
                {
                    'VpcId': 'vpc-independent-1',
                    'CidrBlock': '10.0.0.0/16',
                    'State': 'available',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'Independent VPC'}
                    ]
                }
            ]
        }
        
        mock_ec2_client.describe_vpcs.return_value = mock_vpcs_response
        
        # Mock other resource types to return empty
        mock_ec2_client.describe_instances.return_value = {'Reservations': []}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        
        # Test discovery
        resources = self.engine.discover_independent_resources('us-east-1', set())
        
        # Should find the independent VPC
        vpc_resources = [r for r in resources.values() if r.resource_type == 'AWS::EC2::VPC']
        self.assertEqual(len(vpc_resources), 1)
        self.assertEqual(vpc_resources[0].resource_id, 'vpc-independent-1')
        self.assertFalse(vpc_resources[0].managed_by_cloudformation)
    
    @patch('boto3.Session')
    def test_discover_all(self, mock_session):
        """Test complete discovery process"""
        # Mock session and clients
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        mock_cf_client = Mock()
        mock_ec2_client = Mock()
        
        def mock_client_factory(service, region_name):
            if service == 'cloudformation':
                return mock_cf_client
            elif service == 'ec2':
                return mock_ec2_client
            return Mock()
        
        mock_session_instance.client.side_effect = mock_client_factory
        
        # Mock CloudFormation responses
        mock_cf_client.list_stacks.return_value = {'StackSummaries': []}
        
        # Mock EC2 responses
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}
        mock_ec2_client.describe_instances.return_value = {'Reservations': []}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        
        # Test discovery
        stacks, resources = self.engine.discover_all()
        
        self.assertIsInstance(stacks, dict)
        self.assertIsInstance(resources, dict)
    
    def test_get_stack_summary(self):
        """Test stack summary generation"""
        # Create mock data
        self.engine.discovered_stacks = {
            'stack1': StackInfo(
                stack_name='stack1',
                stack_id='id1',
                stack_status='CREATE_COMPLETE',
                creation_time=datetime.now(),
                region='us-east-1'
            )
        }
        
        self.engine.discovered_resources = {
            'vpc-1': ResourceInfo(
                resource_id='vpc-1',
                resource_type='AWS::EC2::VPC',
                region='us-east-1',
                managed_by_cloudformation=True,
                stack_name='stack1'
            ),
            'vpc-2': ResourceInfo(
                resource_id='vpc-2',
                resource_type='AWS::EC2::VPC',
                region='us-east-1',
                managed_by_cloudformation=False
            )
        }
        
        summary = self.engine.get_stack_summary()
        
        self.assertEqual(summary['total_stacks'], 1)
        self.assertEqual(summary['total_resources'], 2)
        self.assertEqual(summary['cloudformation_managed'], 1)
        self.assertEqual(summary['independent_resources'], 1)
    
    def test_export_discovery_results_json(self):
        """Test exporting discovery results to JSON"""
        # Create mock data
        self.engine.discovered_stacks = {
            'stack1': StackInfo(
                stack_name='stack1',
                stack_id='id1',
                stack_status='CREATE_COMPLETE',
                creation_time=datetime.now(),
                region='us-east-1'
            )
        }
        
        self.engine.discovered_resources = {
            'vpc-1': ResourceInfo(
                resource_id='vpc-1',
                resource_type='AWS::EC2::VPC',
                region='us-east-1',
                managed_by_cloudformation=True,
                stack_name='stack1'
            )
        }
        
        # Test export to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.engine.export_discovery_results(temp_file)
            
            # Verify file was created and contains data
            self.assertTrue(os.path.exists(temp_file))
            
            with open(temp_file, 'r') as f:
                import json
                data = json.load(f)
                
                self.assertIn('stacks', data)
                self.assertIn('resources', data)
                self.assertIn('summary', data)
        
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_filter_stacks_by_name(self):
        """Test stack filtering by name pattern"""
        # This would test the stack name filtering functionality
        # Implementation depends on the actual filtering logic in the engine
        pass
    
    def test_handle_pagination(self):
        """Test handling of paginated AWS API responses"""
        # This would test pagination handling for large numbers of resources
        # Implementation depends on the actual pagination logic
        pass
    
    def test_error_handling(self):
        """Test error handling for AWS API failures"""
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.client.return_value = mock_client
            
            # Mock API error
            from botocore.exceptions import ClientError
            mock_client.list_stacks.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'ListStacks'
            )
            
            # Should handle error gracefully
            stacks = self.engine.discover_stacks('us-east-1')
            self.assertEqual(len(stacks), 0)


class TestResourceFiltering(unittest.TestCase):
    """Test resource filtering and identification"""
    
    def setUp(self):
        self.engine = DiscoveryEngine(regions=['us-east-1'])
    
    def test_identify_cloudformation_managed_resources(self):
        """Test identification of CloudFormation-managed resources"""
        cf_managed_resources = {'vpc-12345', 'subnet-67890'}
        
        resource_info = ResourceInfo(
            resource_id='vpc-12345',
            resource_type='AWS::EC2::VPC',
            region='us-east-1',
            managed_by_cloudformation=False  # Initially set to False
        )
        
        # Test the logic that would identify this as CF-managed
        is_cf_managed = resource_info.resource_id in cf_managed_resources
        self.assertTrue(is_cf_managed)
    
    def test_resource_tagging_analysis(self):
        """Test analysis of resource tags for organization"""
        tags = [
            {'Key': 'aws:cloudformation:stack-name', 'Value': 'my-stack'},
            {'Key': 'Environment', 'Value': 'production'},
            {'Key': 'Team', 'Value': 'platform'}
        ]
        
        # Test tag analysis logic
        has_cf_tag = any(tag['Key'] == 'aws:cloudformation:stack-name' for tag in tags)
        self.assertTrue(has_cf_tag)
        
        environment = next((tag['Value'] for tag in tags if tag['Key'] == 'Environment'), None)
        self.assertEqual(environment, 'production')


if __name__ == '__main__':
    unittest.main()

