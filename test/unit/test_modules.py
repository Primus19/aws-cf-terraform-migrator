#!/usr/bin/env python3
"""
Unit tests for the module generator
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from aws_cf_terraform_migrator.modules import ModuleGenerator, ModuleOrganizer, ModuleInfo, GenerationResult


class TestModuleOrganizer(unittest.TestCase):
    """Test the ModuleOrganizer class"""
    
    def setUp(self):
        self.organizer = ModuleOrganizer(strategy="service_based")
    
    def test_service_based_organization(self):
        """Test service-based resource organization"""
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345'
            },
            'subnet-67890': {
                'resource_type': 'AWS::EC2::Subnet',
                'resource_id': 'subnet-67890'
            },
            'bucket-abc123': {
                'resource_type': 'AWS::S3::Bucket',
                'resource_id': 'bucket-abc123'
            },
            'function-def456': {
                'resource_type': 'AWS::Lambda::Function',
                'resource_id': 'function-def456'
            }
        }
        
        modules = self.organizer.organize_resources(resources)
        
        # Should group networking resources together
        self.assertIn('networking', modules)
        self.assertIn('vpc-12345', modules['networking'])
        self.assertIn('subnet-67890', modules['networking'])
        
        # Should group storage resources
        self.assertIn('storage', modules)
        self.assertIn('bucket-abc123', modules['storage'])
        
        # Should group compute resources
        self.assertIn('compute', modules)
        self.assertIn('function-def456', modules['compute'])
    
    def test_stack_based_organization(self):
        """Test stack-based resource organization"""
        organizer = ModuleOrganizer(strategy="stack_based")
        
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345',
                'stack_name': 'networking-stack'
            },
            'bucket-abc123': {
                'resource_type': 'AWS::S3::Bucket',
                'resource_id': 'bucket-abc123',
                'stack_name': 'storage-stack'
            },
            'independent-vpc': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-independent',
                'stack_name': None
            }
        }
        
        modules = organizer.organize_resources(resources)
        
        # Should group by stack name
        self.assertIn('networking_stack', modules)
        self.assertIn('vpc-12345', modules['networking_stack'])
        
        self.assertIn('storage_stack', modules)
        self.assertIn('bucket-abc123', modules['storage_stack'])
        
        # Independent resources should go to separate module
        self.assertIn('independent_resources', modules)
        self.assertIn('independent-vpc', modules['independent_resources'])
    
    def test_lifecycle_based_organization(self):
        """Test lifecycle-based resource organization"""
        organizer = ModuleOrganizer(strategy="lifecycle_based")
        
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345'
            },
            'instance-67890': {
                'resource_type': 'AWS::EC2::Instance',
                'resource_id': 'instance-67890'
            },
            'database-abc123': {
                'resource_type': 'AWS::RDS::DBInstance',
                'resource_id': 'database-abc123'
            }
        }
        
        modules = organizer.organize_resources(resources)
        
        # Should group by lifecycle
        self.assertIn('shared_infrastructure', modules)
        self.assertIn('vpc-12345', modules['shared_infrastructure'])
        
        self.assertIn('application_resources', modules)
        self.assertIn('instance-67890', modules['application_resources'])
        
        self.assertIn('data_resources', modules)
        self.assertIn('database-abc123', modules['data_resources'])
    
    def test_hybrid_organization(self):
        """Test hybrid organization strategy"""
        organizer = ModuleOrganizer(strategy="hybrid")
        
        # Create a large stack that should be subdivided
        resources = {}
        for i in range(25):  # More than 20 resources
            resources[f'vpc-{i}'] = {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': f'vpc-{i}',
                'stack_name': 'large-stack'
            }
        
        modules = organizer.organize_resources(resources)
        
        # Should subdivide large stack by service
        self.assertIn('large_stack_networking', modules)
        self.assertEqual(len(modules['large_stack_networking']), 25)
    
    def test_sanitize_module_name(self):
        """Test module name sanitization"""
        test_cases = [
            ('My-Stack-Name', 'my_stack_name'),
            ('Stack With Spaces', 'stack_with_spaces'),
            ('123-numeric-start', 'module_123_numeric_start'),
            ('special!@#chars', 'special___chars'),
            ('multiple___underscores', 'multiple_underscores'),
            ('', 'unnamed_module')
        ]
        
        for input_name, expected in test_cases:
            result = self.organizer._sanitize_module_name(input_name)
            self.assertEqual(result, expected, f"Failed for input: {input_name}")


class TestModuleGenerator(unittest.TestCase):
    """Test the ModuleGenerator class"""
    
    def setUp(self):
        self.generator = ModuleGenerator(
            organization_strategy="service_based",
            include_readme=True,
            include_versions_tf=True
        )
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_single_module(self):
        """Test generation of a single module"""
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345',
                'terraform_config': {
                    'resource': {
                        'aws_vpc': {
                            'main_vpc': {
                                'cidr_block': '10.0.0.0/16',
                                'enable_dns_hostnames': True
                            }
                        }
                    },
                    'variables': {
                        'vpc_cidr': {
                            'description': 'VPC CIDR block',
                            'type': 'string',
                            'default': '10.0.0.0/16'
                        }
                    },
                    'outputs': {
                        'vpc_id': {
                            'description': 'VPC ID',
                            'value': 'aws_vpc.main_vpc.id'
                        }
                    }
                }
            }
        }
        
        result = self.generator.generate_modules(
            converted_resources=resources,
            discovery_resources={},
            output_dir=self.temp_dir
        )
        
        self.assertIsInstance(result, GenerationResult)
        self.assertTrue(result.modules)
        self.assertGreater(result.total_files, 0)
        
        # Check that module directory was created
        modules_dir = Path(self.temp_dir) / "modules"
        self.assertTrue(modules_dir.exists())
        
        # Check that networking module was created (VPC goes to networking)
        networking_module = modules_dir / "networking"
        self.assertTrue(networking_module.exists())
        
        # Check that required files were created
        self.assertTrue((networking_module / "main.tf").exists())
        self.assertTrue((networking_module / "variables.tf").exists())
        self.assertTrue((networking_module / "outputs.tf").exists())
        self.assertTrue((networking_module / "versions.tf").exists())
        self.assertTrue((networking_module / "README.md").exists())
    
    def test_generate_multiple_modules(self):
        """Test generation of multiple modules"""
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345',
                'terraform_config': {
                    'resource': {
                        'aws_vpc': {
                            'main_vpc': {
                                'cidr_block': '10.0.0.0/16'
                            }
                        }
                    }
                }
            },
            'bucket-67890': {
                'resource_type': 'AWS::S3::Bucket',
                'resource_id': 'bucket-67890',
                'terraform_config': {
                    'resource': {
                        'aws_s3_bucket': {
                            'main_bucket': {
                                'bucket': 'my-test-bucket'
                            }
                        }
                    }
                }
            }
        }
        
        result = self.generator.generate_modules(
            converted_resources=resources,
            discovery_resources={},
            output_dir=self.temp_dir
        )
        
        # Should create multiple modules
        self.assertGreaterEqual(len(result.modules), 2)
        
        # Check that both networking and storage modules exist
        modules_dir = Path(self.temp_dir) / "modules"
        self.assertTrue((modules_dir / "networking").exists())
        self.assertTrue((modules_dir / "storage").exists())
    
    def test_generate_root_module(self):
        """Test generation of root module"""
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345',
                'terraform_config': {
                    'resource': {
                        'aws_vpc': {
                            'main_vpc': {
                                'cidr_block': '10.0.0.0/16'
                            }
                        }
                    }
                }
            }
        }
        
        result = self.generator.generate_modules(
            converted_resources=resources,
            discovery_resources={},
            output_dir=self.temp_dir
        )
        
        # Should create root module
        self.assertIsNotNone(result.root_module)
        
        # Check root module files
        output_path = Path(self.temp_dir)
        self.assertTrue((output_path / "main.tf").exists())
        self.assertTrue((output_path / "variables.tf").exists())
        self.assertTrue((output_path / "outputs.tf").exists())
        self.assertTrue((output_path / "versions.tf").exists())
        self.assertTrue((output_path / "README.md").exists())
    
    def test_module_file_content(self):
        """Test content of generated module files"""
        resources = {
            'vpc-12345': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-12345',
                'terraform_config': {
                    'resource': {
                        'aws_vpc': {
                            'main_vpc': {
                                'cidr_block': '10.0.0.0/16',
                                'enable_dns_hostnames': True
                            }
                        }
                    },
                    'variables': {
                        'vpc_cidr': {
                            'description': 'VPC CIDR block',
                            'type': 'string',
                            'default': '10.0.0.0/16'
                        }
                    },
                    'outputs': {
                        'vpc_id': {
                            'description': 'VPC ID',
                            'value': 'aws_vpc.main_vpc.id'
                        }
                    }
                }
            }
        }
        
        result = self.generator.generate_modules(
            converted_resources=resources,
            discovery_resources={},
            output_dir=self.temp_dir
        )
        
        # Check main.tf content
        networking_module = Path(self.temp_dir) / "modules" / "networking"
        main_tf_content = (networking_module / "main.tf").read_text()
        
        self.assertIn('resource "aws_vpc" "main_vpc"', main_tf_content)
        self.assertIn('cidr_block', main_tf_content)
        self.assertIn('enable_dns_hostnames', main_tf_content)
        
        # Check variables.tf content
        variables_tf_content = (networking_module / "variables.tf").read_text()
        self.assertIn('variable "vpc_cidr"', variables_tf_content)
        self.assertIn('VPC CIDR block', variables_tf_content)
        
        # Check outputs.tf content
        outputs_tf_content = (networking_module / "outputs.tf").read_text()
        self.assertIn('output "vpc_id"', outputs_tf_content)
        self.assertIn('aws_vpc.main_vpc.id', outputs_tf_content)
    
    def test_analyze_module_interfaces(self):
        """Test analysis of module interfaces for variables and outputs"""
        module_resources = {
            'aws_vpc': {
                'main_vpc': {
                    'cidr_block': '10.0.0.0/16'
                }
            },
            'aws_s3_bucket': {
                'main_bucket': {
                    'bucket': 'my-bucket'
                }
            }
        }
        
        variables, outputs = self.generator._analyze_module_interfaces(
            module_resources, 'test_module'
        )
        
        # Should generate common variables
        self.assertIn('tags', variables)
        self.assertEqual(variables['tags']['type'], 'map(string)')
        
        # Should generate outputs for VPC and S3 bucket
        self.assertIn('main_vpc_id', outputs)
        self.assertIn('main_bucket_name', outputs)
        self.assertIn('main_bucket_arn', outputs)
    
    def test_template_rendering(self):
        """Test Terraform template rendering"""
        # Test main.tf template
        module_resources = {
            'aws_vpc': {
                'test_vpc': {
                    'cidr_block': '10.0.0.0/16',
                    'enable_dns_hostnames': True
                }
            }
        }
        
        locals_dict = {
            'common_tags': {
                'Environment': 'test',
                'ManagedBy': 'terraform'
            }
        }
        
        # Create temporary module directory
        module_dir = Path(self.temp_dir) / "test_module"
        module_dir.mkdir(parents=True)
        
        # Test main.tf generation
        self.generator._write_main_tf(module_dir, "test_module", module_resources, locals_dict)
        
        main_tf_content = (module_dir / "main.tf").read_text()
        
        # Should contain resource definition
        self.assertIn('resource "aws_vpc" "test_vpc"', main_tf_content)
        self.assertIn('cidr_block = "10.0.0.0/16"', main_tf_content)
        self.assertIn('enable_dns_hostnames = true', main_tf_content)
        
        # Should contain locals
        self.assertIn('locals {', main_tf_content)
        self.assertIn('common_tags', main_tf_content)
    
    def test_error_handling(self):
        """Test error handling in module generation"""
        # Test with invalid output directory
        invalid_dir = "/invalid/path/that/does/not/exist"
        
        result = self.generator.generate_modules(
            converted_resources={},
            discovery_resources={},
            output_dir=invalid_dir
        )
        
        # Should handle error gracefully
        self.assertFalse(result.modules)
        self.assertTrue(len(result.errors) > 0)
    
    def test_module_organization_strategies(self):
        """Test different module organization strategies"""
        resources = {
            'vpc-1': {
                'resource_type': 'AWS::EC2::VPC',
                'resource_id': 'vpc-1',
                'stack_name': 'network-stack',
                'terraform_config': {'resource': {'aws_vpc': {'vpc1': {}}}}
            },
            'bucket-1': {
                'resource_type': 'AWS::S3::Bucket',
                'resource_id': 'bucket-1',
                'stack_name': 'storage-stack',
                'terraform_config': {'resource': {'aws_s3_bucket': {'bucket1': {}}}}
            }
        }
        
        # Test service-based strategy
        service_generator = ModuleGenerator(organization_strategy="service_based")
        service_result = service_generator.generate_modules(
            converted_resources=resources,
            discovery_resources={},
            output_dir=os.path.join(self.temp_dir, "service")
        )
        
        # Should organize by service
        self.assertIn('networking', service_result.modules)
        self.assertIn('storage', service_result.modules)
        
        # Test stack-based strategy
        stack_generator = ModuleGenerator(organization_strategy="stack_based")
        stack_result = stack_generator.generate_modules(
            converted_resources=resources,
            discovery_resources={},
            output_dir=os.path.join(self.temp_dir, "stack")
        )
        
        # Should organize by stack
        self.assertIn('network_stack', stack_result.modules)
        self.assertIn('storage_stack', stack_result.modules)


class TestModuleInfo(unittest.TestCase):
    """Test the ModuleInfo dataclass"""
    
    def test_module_info_creation(self):
        """Test ModuleInfo creation"""
        module_info = ModuleInfo(
            name="test_module",
            path="/path/to/module",
            resources=["vpc-1", "subnet-1"],
            variables={"vpc_cidr": {"type": "string"}},
            outputs={"vpc_id": {"value": "aws_vpc.main.id"}},
            description="Test module"
        )
        
        self.assertEqual(module_info.name, "test_module")
        self.assertEqual(module_info.path, "/path/to/module")
        self.assertEqual(len(module_info.resources), 2)
        self.assertIn("vpc_cidr", module_info.variables)
        self.assertIn("vpc_id", module_info.outputs)


class TestGenerationResult(unittest.TestCase):
    """Test the GenerationResult dataclass"""
    
    def test_generation_result_creation(self):
        """Test GenerationResult creation"""
        modules = {
            "networking": ModuleInfo(name="networking", path="/path/to/networking"),
            "storage": ModuleInfo(name="storage", path="/path/to/storage")
        }
        
        result = GenerationResult(
            modules=modules,
            total_files=10,
            warnings=["Warning 1"],
            errors=[]
        )
        
        self.assertEqual(len(result.modules), 2)
        self.assertEqual(result.total_files, 10)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.errors), 0)


if __name__ == '__main__':
    unittest.main()

