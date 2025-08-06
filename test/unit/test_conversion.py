#!/usr/bin/env python3
"""
Unit tests for the conversion engine
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from aws_cf_terraform_migrator.conversion import ConversionEngine, ResourceMapper, ConversionResult
from test.fixtures.sample_cloudformation_templates import SIMPLE_VPC_TEMPLATE, S3_LAMBDA_TEMPLATE


class TestResourceMapper(unittest.TestCase):
    """Test the ResourceMapper class"""
    
    def setUp(self):
        self.mapper = ResourceMapper()
    
    def test_get_terraform_type_vpc(self):
        """Test VPC resource type mapping"""
        tf_type = self.mapper.get_terraform_type('AWS::EC2::VPC')
        self.assertEqual(tf_type, 'aws_vpc')
    
    def test_get_terraform_type_s3(self):
        """Test S3 bucket resource type mapping"""
        tf_type = self.mapper.get_terraform_type('AWS::S3::Bucket')
        self.assertEqual(tf_type, 'aws_s3_bucket')
    
    def test_get_terraform_type_lambda(self):
        """Test Lambda function resource type mapping"""
        tf_type = self.mapper.get_terraform_type('AWS::Lambda::Function')
        self.assertEqual(tf_type, 'aws_lambda_function')
    
    def test_get_terraform_type_unknown(self):
        """Test unknown resource type"""
        tf_type = self.mapper.get_terraform_type('AWS::Unknown::Resource')
        self.assertIsNone(tf_type)
    
    def test_convert_vpc_properties(self):
        """Test VPC properties conversion"""
        cf_properties = {
            'CidrBlock': '10.0.0.0/16',
            'EnableDnsHostnames': True,
            'EnableDnsSupport': True,
            'Tags': [
                {'Key': 'Name', 'Value': 'MyVPC'},
                {'Key': 'Environment', 'Value': 'test'}
            ]
        }
        
        tf_properties = self.mapper.convert_properties('AWS::EC2::VPC', cf_properties)
        
        expected = {
            'cidr_block': '10.0.0.0/16',
            'enable_dns_hostnames': True,
            'enable_dns_support': True,
            'tags': {
                'Name': 'MyVPC',
                'Environment': 'test'
            }
        }
        
        self.assertEqual(tf_properties, expected)
    
    def test_convert_s3_properties(self):
        """Test S3 bucket properties conversion"""
        cf_properties = {
            'BucketName': 'my-test-bucket',
            'VersioningConfiguration': {
                'Status': 'Enabled'
            },
            'BucketEncryption': {
                'ServerSideEncryptionConfiguration': [
                    {
                        'ServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }
                ]
            }
        }
        
        tf_properties = self.mapper.convert_properties('AWS::S3::Bucket', cf_properties)
        
        self.assertIn('bucket', tf_properties)
        self.assertIn('versioning', tf_properties)
        self.assertIn('server_side_encryption_configuration', tf_properties)
    
    def test_convert_tags_list_to_map(self):
        """Test conversion of CloudFormation tags list to Terraform tags map"""
        cf_tags = [
            {'Key': 'Name', 'Value': 'MyResource'},
            {'Key': 'Environment', 'Value': 'test'},
            {'Key': 'Owner', 'Value': 'team@company.com'}
        ]
        
        tf_tags = self.mapper._convert_tags(cf_tags)
        
        expected = {
            'Name': 'MyResource',
            'Environment': 'test',
            'Owner': 'team@company.com'
        }
        
        self.assertEqual(tf_tags, expected)
    
    def test_convert_tags_empty_list(self):
        """Test conversion of empty tags list"""
        tf_tags = self.mapper._convert_tags([])
        self.assertEqual(tf_tags, {})
    
    def test_convert_tags_none(self):
        """Test conversion of None tags"""
        tf_tags = self.mapper._convert_tags(None)
        self.assertEqual(tf_tags, {})


class TestConversionEngine(unittest.TestCase):
    """Test the ConversionEngine class"""
    
    def setUp(self):
        self.engine = ConversionEngine()
    
    def test_convert_simple_vpc_template(self):
        """Test conversion of simple VPC template"""
        result = self.engine.convert_template(SIMPLE_VPC_TEMPLATE)
        
        self.assertIsInstance(result, ConversionResult)
        self.assertIn('resource', result.terraform_config)
        self.assertIn('variable', result.terraform_config)
        self.assertIn('output', result.terraform_config)
        
        # Check VPC resource
        resources = result.terraform_config['resource']
        self.assertIn('aws_vpc', resources)
        self.assertIn('MyVPC', resources['aws_vpc'])
        
        vpc_config = resources['aws_vpc']['MyVPC']
        self.assertIn('cidr_block', vpc_config)
        self.assertIn('enable_dns_hostnames', vpc_config)
    
    def test_convert_template_with_parameters(self):
        """Test conversion of template with parameters"""
        result = self.engine.convert_template(SIMPLE_VPC_TEMPLATE)
        
        variables = result.terraform_config.get('variable', {})
        self.assertIn('VpcCidr', variables)
        self.assertIn('SubnetCidr', variables)
        
        vpc_cidr_var = variables['VpcCidr']
        self.assertEqual(vpc_cidr_var['type'], 'string')
        self.assertEqual(vpc_cidr_var['default'], '10.0.0.0/16')
    
    def test_convert_template_with_outputs(self):
        """Test conversion of template with outputs"""
        result = self.engine.convert_template(SIMPLE_VPC_TEMPLATE)
        
        outputs = result.terraform_config.get('output', {})
        self.assertIn('VpcId', outputs)
        self.assertIn('SubnetId', outputs)
        
        vpc_id_output = outputs['VpcId']
        self.assertIn('description', vpc_id_output)
        self.assertIn('value', vpc_id_output)
    
    def test_convert_template_with_intrinsic_functions(self):
        """Test conversion of template with CloudFormation intrinsic functions"""
        result = self.engine.convert_template(SIMPLE_VPC_TEMPLATE)
        
        # Check that Ref functions are converted
        resources = result.terraform_config['resource']
        subnet_config = resources['aws_subnet']['MySubnet']
        
        # VPC ID should reference the VPC resource
        self.assertIn('vpc_id', subnet_config)
        # Should be a Terraform reference
        self.assertTrue(str(subnet_config['vpc_id']).startswith('aws_vpc.'))
    
    def test_convert_s3_lambda_template(self):
        """Test conversion of S3 and Lambda template"""
        result = self.engine.convert_template(S3_LAMBDA_TEMPLATE)
        
        resources = result.terraform_config['resource']
        
        # Check S3 bucket
        self.assertIn('aws_s3_bucket', resources)
        self.assertIn('S3Bucket', resources['aws_s3_bucket'])
        
        # Check Lambda function
        self.assertIn('aws_lambda_function', resources)
        self.assertIn('ProcessorFunction', resources['aws_lambda_function'])
        
        # Check IAM role
        self.assertIn('aws_iam_role', resources)
        self.assertIn('LambdaExecutionRole', resources['aws_iam_role'])
    
    def test_convert_single_resource(self):
        """Test conversion of a single resource"""
        cf_resource = {
            'Type': 'AWS::EC2::VPC',
            'Properties': {
                'CidrBlock': '10.0.0.0/16',
                'EnableDnsHostnames': True
            }
        }
        
        result = self.engine.convert_resource('TestVPC', cf_resource, 'vpc-12345')
        
        self.assertIsInstance(result, ConversionResult)
        self.assertIn('resource', result.terraform_config)
        
        resources = result.terraform_config['resource']
        self.assertIn('aws_vpc', resources)
        self.assertIn('TestVPC', resources['aws_vpc'])
    
    def test_handle_unsupported_resource(self):
        """Test handling of unsupported resource types"""
        cf_resource = {
            'Type': 'AWS::Unknown::Resource',
            'Properties': {
                'SomeProperty': 'value'
            }
        }
        
        result = self.engine.convert_resource('UnknownResource', cf_resource, 'unknown-123')
        
        # Should have warnings about unsupported resource
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any('unsupported' in warning.lower() for warning in result.warnings))
    
    def test_preserve_original_names(self):
        """Test preservation of original resource names"""
        engine = ConversionEngine(preserve_names=True)
        
        cf_resource = {
            'Type': 'AWS::EC2::VPC',
            'Properties': {
                'CidrBlock': '10.0.0.0/16'
            }
        }
        
        result = engine.convert_resource('MyOriginalVPC', cf_resource, 'vpc-12345')
        
        resources = result.terraform_config['resource']
        vpc_resources = resources['aws_vpc']
        
        # Should preserve the original name
        self.assertIn('MyOriginalVPC', vpc_resources)
    
    def test_generate_import_commands(self):
        """Test generation of import commands"""
        result = self.engine.convert_template(SIMPLE_VPC_TEMPLATE)
        
        self.assertTrue(len(result.import_commands) > 0)
        
        # Check that import commands are properly formatted
        for cmd in result.import_commands:
            self.assertTrue(cmd.startswith('terraform import '))
            self.assertIn(' ', cmd)  # Should have resource address and ID
    
    def test_error_handling(self):
        """Test error handling for malformed templates"""
        malformed_template = {
            'Resources': {
                'BadResource': {
                    'Type': 'AWS::EC2::VPC'
                    # Missing Properties
                }
            }
        }
        
        result = self.engine.convert_template(malformed_template)
        
        # Should handle errors gracefully
        self.assertIsInstance(result, ConversionResult)
        # May have warnings or errors
        self.assertTrue(len(result.warnings) > 0 or len(result.errors) > 0)


class TestIntrinsicFunctions(unittest.TestCase):
    """Test CloudFormation intrinsic function handling"""
    
    def setUp(self):
        self.engine = ConversionEngine(handle_functions=True)
    
    def test_ref_function(self):
        """Test Ref function conversion"""
        cf_value = {'Ref': 'MyVPC'}
        tf_value = self.engine._convert_intrinsic_function(cf_value, 'TestResource')
        
        # Should convert to Terraform reference
        self.assertIn('aws_vpc.MyVPC', str(tf_value))
    
    def test_getatt_function(self):
        """Test Fn::GetAtt function conversion"""
        cf_value = {'Fn::GetAtt': ['MyVPC', 'CidrBlock']}
        tf_value = self.engine._convert_intrinsic_function(cf_value, 'TestResource')
        
        # Should convert to Terraform attribute reference
        self.assertIn('aws_vpc.MyVPC.cidr_block', str(tf_value))
    
    def test_sub_function(self):
        """Test Fn::Sub function conversion"""
        cf_value = {'Fn::Sub': '${AWS::StackName}-vpc'}
        tf_value = self.engine._convert_intrinsic_function(cf_value, 'TestResource')
        
        # Should convert to Terraform interpolation
        self.assertIsInstance(tf_value, str)
        self.assertIn('${', tf_value)
    
    def test_join_function(self):
        """Test Fn::Join function conversion"""
        cf_value = {'Fn::Join': ['-', ['prefix', {'Ref': 'Environment'}, 'suffix']]}
        tf_value = self.engine._convert_intrinsic_function(cf_value, 'TestResource')
        
        # Should convert to Terraform join function
        self.assertIsInstance(tf_value, str)
    
    def test_select_function(self):
        """Test Fn::Select function conversion"""
        cf_value = {'Fn::Select': [0, {'Fn::GetAZs': ''}]}
        tf_value = self.engine._convert_intrinsic_function(cf_value, 'TestResource')
        
        # Should convert to Terraform data source reference
        self.assertIsInstance(tf_value, str)
    
    def test_nested_functions(self):
        """Test nested intrinsic functions"""
        cf_value = {
            'Fn::Sub': [
                '${VpcId}-${SubnetId}',
                {
                    'VpcId': {'Ref': 'MyVPC'},
                    'SubnetId': {'Ref': 'MySubnet'}
                }
            ]
        }
        
        tf_value = self.engine._convert_intrinsic_function(cf_value, 'TestResource')
        
        # Should handle nested functions
        self.assertIsInstance(tf_value, str)


if __name__ == '__main__':
    unittest.main()

