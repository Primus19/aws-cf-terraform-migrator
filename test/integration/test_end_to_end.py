#!/usr/bin/env python3
"""
End-to-end integration tests for the CF2TF converter
"""

import unittest
import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from aws_cf_terraform_migrator.orchestrator import Orchestrator
from aws_cf_terraform_migrator.config import ToolConfig, DiscoveryConfig, ConversionConfig, ModulesConfig, OutputConfig, ImportsConfig
from test.fixtures.sample_cloudformation_templates import SIMPLE_VPC_TEMPLATE, COMPLEX_WEB_APP_TEMPLATE


class TestEndToEndConversion(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.config = ToolConfig(
            discovery=DiscoveryConfig(
                regions=['us-east-1'],
                profile=None,
                role_arn=None,
                max_workers=2,
                include_deleted_stacks=False,
                stack_name_filter=None
            ),
            conversion=ConversionConfig(
                preserve_original_names=True,
                handle_intrinsic_functions=True,
                terraform_version='>=1.0',
                provider_version='>=5.0'
            ),
            modules=ModulesConfig(
                organization_strategy='service_based',
                module_prefix='',
                include_examples=True,
                include_readme=True,
                include_versions_tf=True
            ),
            output=OutputConfig(
                output_directory=self.temp_dir,
                export_discovery_data=True,
                export_format='json',
                generate_documentation=True,
                include_metadata=True
            ),
            imports=ImportsConfig(
                parallel_imports=False,
                max_import_workers=3,
                import_timeout=300,
                retry_failed_imports=True,
                max_retries=2,
                create_backup=True
            )
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('boto3.Session')
    def test_simple_vpc_conversion(self, mock_session):
        """Test end-to-end conversion of simple VPC template"""
        # Mock AWS session and clients
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
        
        # Mock CloudFormation stack discovery
        mock_cf_client.list_stacks.return_value = {
            'StackSummaries': [{
                'StackName': 'simple-vpc-stack',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/simple-vpc-stack/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z'
            }]
        }
        
        mock_cf_client.describe_stacks.return_value = {
            'Stacks': [{
                'StackName': 'simple-vpc-stack',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/simple-vpc-stack/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z',
                'Parameters': [
                    {'ParameterKey': 'VpcCidr', 'ParameterValue': '10.0.0.0/16'},
                    {'ParameterKey': 'SubnetCidr', 'ParameterValue': '10.0.1.0/24'}
                ],
                'Outputs': [
                    {'OutputKey': 'VpcId', 'OutputValue': 'vpc-12345'},
                    {'OutputKey': 'SubnetId', 'OutputValue': 'subnet-67890'}
                ]
            }]
        }
        
        mock_cf_client.describe_stack_resources.return_value = {
            'StackResources': [
                {
                    'LogicalResourceId': 'MyVPC',
                    'PhysicalResourceId': 'vpc-12345',
                    'ResourceType': 'AWS::EC2::VPC',
                    'ResourceStatus': 'CREATE_COMPLETE'
                },
                {
                    'LogicalResourceId': 'MySubnet',
                    'PhysicalResourceId': 'subnet-67890',
                    'ResourceType': 'AWS::EC2::Subnet',
                    'ResourceStatus': 'CREATE_COMPLETE'
                },
                {
                    'LogicalResourceId': 'MyInternetGateway',
                    'PhysicalResourceId': 'igw-abcdef',
                    'ResourceType': 'AWS::EC2::InternetGateway',
                    'ResourceStatus': 'CREATE_COMPLETE'
                }
            ]
        }
        
        mock_cf_client.get_template.return_value = {
            'TemplateBody': json.dumps(SIMPLE_VPC_TEMPLATE)
        }
        
        # Mock EC2 resource discovery (no independent resources)
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}
        mock_ec2_client.describe_instances.return_value = {'Reservations': []}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        
        # Run conversion
        orchestrator = Orchestrator(self.config)
        result = orchestrator.run_conversion(dry_run=False)
        
        # Verify conversion success
        self.assertTrue(result['success'], f"Conversion failed: {result.get('errors', [])}")
        self.assertGreater(result['resources_discovered'], 0)
        self.assertGreater(result['resources_converted'], 0)
        self.assertGreater(result['modules_count'], 0)
        self.assertGreater(result['files_count'], 0)
        
        # Verify output directory structure
        output_path = Path(self.temp_dir)
        
        # Check root module files
        self.assertTrue((output_path / "main.tf").exists())
        self.assertTrue((output_path / "variables.tf").exists())
        self.assertTrue((output_path / "outputs.tf").exists())
        self.assertTrue((output_path / "README.md").exists())
        
        # Check modules directory
        modules_dir = output_path / "modules"
        self.assertTrue(modules_dir.exists())
        
        # Should have networking module (VPC, Subnet, IGW)
        networking_module = modules_dir / "networking"
        self.assertTrue(networking_module.exists())
        self.assertTrue((networking_module / "main.tf").exists())
        self.assertTrue((networking_module / "variables.tf").exists())
        self.assertTrue((networking_module / "outputs.tf").exists())
        
        # Check import script
        import_script = output_path / "import_resources.sh"
        self.assertTrue(import_script.exists())
        
        # Verify import script content
        import_content = import_script.read_text()
        self.assertIn("terraform import", import_content)
        self.assertIn("vpc-12345", import_content)
        self.assertIn("subnet-67890", import_content)
        
        # Check documentation
        self.assertTrue((output_path / "conversion_report.md").exists())
        self.assertTrue((output_path / "MIGRATION_GUIDE.md").exists())
    
    @patch('boto3.Session')
    def test_complex_web_app_conversion(self, mock_session):
        """Test conversion of complex web application template"""
        # Mock AWS session and clients
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        mock_cf_client = Mock()
        mock_ec2_client = Mock()
        mock_elbv2_client = Mock()
        mock_rds_client = Mock()
        mock_autoscaling_client = Mock()
        
        def mock_client_factory(service, region_name):
            if service == 'cloudformation':
                return mock_cf_client
            elif service == 'ec2':
                return mock_ec2_client
            elif service == 'elbv2':
                return mock_elbv2_client
            elif service == 'rds':
                return mock_rds_client
            elif service == 'autoscaling':
                return mock_autoscaling_client
            return Mock()
        
        mock_session_instance.client.side_effect = mock_client_factory
        
        # Mock CloudFormation stack discovery
        mock_cf_client.list_stacks.return_value = {
            'StackSummaries': [{
                'StackName': 'web-app-stack',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/web-app-stack/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z'
            }]
        }
        
        mock_cf_client.describe_stacks.return_value = {
            'Stacks': [{
                'StackName': 'web-app-stack',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/web-app-stack/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z',
                'Parameters': [
                    {'ParameterKey': 'InstanceType', 'ParameterValue': 't3.micro'},
                    {'ParameterKey': 'KeyName', 'ParameterValue': 'my-key'},
                    {'ParameterKey': 'DBPassword', 'ParameterValue': 'password123'}
                ],
                'Outputs': [
                    {'OutputKey': 'LoadBalancerDNS', 'OutputValue': 'alb-123.us-east-1.elb.amazonaws.com'},
                    {'OutputKey': 'DatabaseEndpoint', 'OutputValue': 'db-123.cluster-xyz.us-east-1.rds.amazonaws.com'}
                ]
            }]
        }
        
        # Mock stack resources (simplified)
        mock_cf_client.describe_stack_resources.return_value = {
            'StackResources': [
                {
                    'LogicalResourceId': 'VPC',
                    'PhysicalResourceId': 'vpc-webapp',
                    'ResourceType': 'AWS::EC2::VPC',
                    'ResourceStatus': 'CREATE_COMPLETE'
                },
                {
                    'LogicalResourceId': 'ApplicationLoadBalancer',
                    'PhysicalResourceId': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/webapp-alb/1234567890123456',
                    'ResourceType': 'AWS::ElasticLoadBalancingV2::LoadBalancer',
                    'ResourceStatus': 'CREATE_COMPLETE'
                },
                {
                    'LogicalResourceId': 'Database',
                    'PhysicalResourceId': 'webapp-database',
                    'ResourceType': 'AWS::RDS::DBInstance',
                    'ResourceStatus': 'CREATE_COMPLETE'
                }
            ]
        }
        
        mock_cf_client.get_template.return_value = {
            'TemplateBody': json.dumps(COMPLEX_WEB_APP_TEMPLATE)
        }
        
        # Mock EC2 resource discovery (no independent resources)
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}
        mock_ec2_client.describe_instances.return_value = {'Reservations': []}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        
        # Run conversion
        orchestrator = Orchestrator(self.config)
        result = orchestrator.run_conversion(dry_run=False)
        
        # Verify conversion success
        self.assertTrue(result['success'], f"Conversion failed: {result.get('errors', [])}")
        
        # Should have multiple modules for complex app
        self.assertGreaterEqual(result['modules_count'], 3)  # networking, load_balancing, database at minimum
        
        # Verify module structure
        output_path = Path(self.temp_dir)
        modules_dir = output_path / "modules"
        
        # Should have networking module
        self.assertTrue((modules_dir / "networking").exists())
        
        # Should have load balancing module
        self.assertTrue((modules_dir / "load_balancing").exists())
        
        # Should have database module
        self.assertTrue((modules_dir / "database").exists())
    
    @patch('boto3.Session')
    def test_mixed_resources_conversion(self, mock_session):
        """Test conversion with both CloudFormation and independent resources"""
        # Mock AWS session and clients
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
        
        # Mock CloudFormation stack with one VPC
        mock_cf_client.list_stacks.return_value = {
            'StackSummaries': [{
                'StackName': 'managed-vpc-stack',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/managed-vpc-stack/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z'
            }]
        }
        
        mock_cf_client.describe_stacks.return_value = {
            'Stacks': [{
                'StackName': 'managed-vpc-stack',
                'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/managed-vpc-stack/12345',
                'StackStatus': 'CREATE_COMPLETE',
                'CreationTime': '2023-01-01T00:00:00Z',
                'Parameters': [],
                'Outputs': []
            }]
        }
        
        mock_cf_client.describe_stack_resources.return_value = {
            'StackResources': [{
                'LogicalResourceId': 'ManagedVPC',
                'PhysicalResourceId': 'vpc-managed-12345',
                'ResourceType': 'AWS::EC2::VPC',
                'ResourceStatus': 'CREATE_COMPLETE'
            }]
        }
        
        mock_cf_client.get_template.return_value = {
            'TemplateBody': json.dumps({
                'Resources': {
                    'ManagedVPC': {
                        'Type': 'AWS::EC2::VPC',
                        'Properties': {
                            'CidrBlock': '10.0.0.0/16'
                        }
                    }
                }
            })
        }
        
        # Mock independent VPC discovery
        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [{
                'VpcId': 'vpc-independent-67890',
                'CidrBlock': '10.1.0.0/16',
                'State': 'available',
                'Tags': [
                    {'Key': 'Name', 'Value': 'Independent VPC'}
                ]
            }]
        }
        
        # Mock other resources as empty
        mock_ec2_client.describe_instances.return_value = {'Reservations': []}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        
        # Run conversion
        orchestrator = Orchestrator(self.config)
        result = orchestrator.run_conversion(dry_run=False)
        
        # Verify conversion success
        self.assertTrue(result['success'], f"Conversion failed: {result.get('errors', [])}")
        
        # Should discover both managed and independent resources
        self.assertGreaterEqual(result['resources_discovered'], 2)
        
        # Check that import script includes both resources
        import_script = Path(self.temp_dir) / "import_resources.sh"
        import_content = import_script.read_text()
        
        self.assertIn("vpc-managed-12345", import_content)
        self.assertIn("vpc-independent-67890", import_content)
    
    def test_dry_run_mode(self):
        """Test dry run mode (no file generation)"""
        with patch('boto3.Session') as mock_session:
            # Mock empty AWS environment
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
            
            # Mock empty responses
            mock_cf_client.list_stacks.return_value = {'StackSummaries': []}
            mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}
            mock_ec2_client.describe_instances.return_value = {'Reservations': []}
            mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
            mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
            
            # Run dry run
            orchestrator = Orchestrator(self.config)
            result = orchestrator.run_conversion(dry_run=True)
            
            # Should complete successfully
            self.assertTrue(result['success'])
            
            # Should not generate files in dry run mode
            self.assertEqual(result['files_count'], 0)
            self.assertEqual(result['modules_count'], 0)
            
            # Output directory should be empty or not exist
            output_path = Path(self.temp_dir)
            if output_path.exists():
                files = list(output_path.rglob("*.tf"))
                self.assertEqual(len(files), 0)
    
    def test_error_handling(self):
        """Test error handling in end-to-end conversion"""
        with patch('boto3.Session') as mock_session:
            # Mock AWS API error
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            mock_cf_client = Mock()
            mock_session_instance.client.return_value = mock_cf_client
            
            # Mock API error
            from botocore.exceptions import ClientError
            mock_cf_client.list_stacks.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'ListStacks'
            )
            
            # Run conversion
            orchestrator = Orchestrator(self.config)
            result = orchestrator.run_conversion(dry_run=False)
            
            # Should handle error gracefully
            self.assertFalse(result['success'])
            self.assertTrue(len(result['errors']) > 0)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Test with invalid output directory
        invalid_config = ToolConfig(
            discovery=DiscoveryConfig(regions=['us-east-1']),
            conversion=ConversionConfig(),
            modules=ModulesConfig(),
            output=OutputConfig(output_directory="/invalid/path/that/does/not/exist"),
            imports=ImportsConfig()
        )
        
        # Should handle invalid configuration gracefully
        orchestrator = Orchestrator(invalid_config)
        result = orchestrator.run_conversion(dry_run=True)
        
        # May succeed in dry run mode, but should handle errors in real mode
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)


class TestModuleIntegration(unittest.TestCase):
    """Test integration between different modules"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_discovery_to_conversion_integration(self):
        """Test integration between discovery and conversion modules"""
        from aws_cf_terraform_migrator.discovery import DiscoveryEngine, StackInfo, ResourceInfo
        from aws_cf_terraform_migrator.conversion import ConversionEngine
        from datetime import datetime
        
        # Create mock discovery results
        stack_info = StackInfo(
            stack_name="test-stack",
            stack_id="arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/12345",
            stack_status="CREATE_COMPLETE",
            creation_time=datetime.now(),
            region="us-east-1",
            template_body=json.dumps(SIMPLE_VPC_TEMPLATE)
        )
        
        resource_info = ResourceInfo(
            resource_id="vpc-12345",
            resource_type="AWS::EC2::VPC",
            region="us-east-1",
            managed_by_cloudformation=True,
            stack_name="test-stack",
            logical_id="MyVPC"
        )
        
        # Test conversion of discovered resources
        conversion_engine = ConversionEngine()
        
        # Convert the template from discovery
        template = json.loads(stack_info.template_body)
        conversion_result = conversion_engine.convert_template(template, stack_info.stack_name)
        
        # Verify conversion worked
        self.assertIn('resource', conversion_result.terraform_config)
        self.assertIn('aws_vpc', conversion_result.terraform_config['resource'])
    
    def test_conversion_to_modules_integration(self):
        """Test integration between conversion and module generation"""
        from aws_cf_terraform_migrator.conversion import ConversionEngine
        from aws_cf_terraform_migrator.modules import ModuleGenerator
        
        # Convert a template
        conversion_engine = ConversionEngine()
        conversion_result = conversion_engine.convert_template(SIMPLE_VPC_TEMPLATE)
        
        # Create converted resources structure
        converted_resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345',
                'terraform_config': conversion_result.terraform_config,
                'import_commands': conversion_result.import_commands
            }
        }
        
        # Generate modules
        module_generator = ModuleGenerator(organization_strategy="service_based")
        generation_result = module_generator.generate_modules(
            converted_resources=converted_resources,
            discovery_resources={},
            output_dir=self.temp_dir
        )
        
        # Verify module generation worked
        self.assertTrue(generation_result.modules)
        self.assertGreater(generation_result.total_files, 0)
        
        # Check that files were actually created
        output_path = Path(self.temp_dir)
        tf_files = list(output_path.rglob("*.tf"))
        self.assertGreater(len(tf_files), 0)


if __name__ == '__main__':
    unittest.main()

