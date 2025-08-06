#!/usr/bin/env python3
"""
Comprehensive test runner for CF2TF converter scenarios
"""

import sys
import os
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from aws_cf_terraform_migrator.orchestrator import Orchestrator
from aws_cf_terraform_migrator.config import ToolConfig, DiscoveryConfig, ConversionConfig, ModuleConfig, OutputConfig, ImportConfig
from aws_cf_terraform_migrator.conversion import ConversionEngine
from aws_cf_terraform_migrator.modules import ModuleGenerator
from test.fixtures.sample_cloudformation_templates import ALL_TEMPLATES


class TestScenario:
    """Represents a test scenario"""
    
    def __init__(self, name, description, template, expected_modules=None, expected_resources=None):
        self.name = name
        self.description = description
        self.template = template
        self.expected_modules = expected_modules or []
        self.expected_resources = expected_resources or []
        self.results = {}
        self.success = False
        self.errors = []
        self.warnings = []


class TestRunner:
    """Comprehensive test runner for various scenarios"""
    
    def __init__(self):
        self.scenarios = []
        self.results = {}
        self.temp_dirs = []
    
    def add_scenario(self, scenario):
        """Add a test scenario"""
        self.scenarios.append(scenario)
    
    def setup_test_scenarios(self):
        """Set up all test scenarios"""
        
        # Scenario 1: Simple VPC
        self.add_scenario(TestScenario(
            name="simple_vpc",
            description="Simple VPC with subnet and internet gateway",
            template=ALL_TEMPLATES["simple_vpc"],
            expected_modules=["networking"],
            expected_resources=["aws_vpc", "aws_subnet", "aws_internet_gateway"]
        ))
        
        # Scenario 2: Complex Web Application
        self.add_scenario(TestScenario(
            name="complex_web_app",
            description="Complex web application with ALB, ASG, and RDS",
            template=ALL_TEMPLATES["complex_web_app"],
            expected_modules=["networking", "security", "compute", "load_balancing", "database"],
            expected_resources=["aws_vpc", "aws_subnet", "aws_security_group", "aws_launch_template", 
                              "aws_autoscaling_group", "aws_lb", "aws_rds_db_instance"]
        ))
        
        # Scenario 3: S3 and Lambda
        self.add_scenario(TestScenario(
            name="s3_lambda",
            description="S3 bucket with Lambda function processing",
            template=ALL_TEMPLATES["s3_lambda"],
            expected_modules=["storage", "compute", "security"],
            expected_resources=["aws_s3_bucket", "aws_lambda_function", "aws_iam_role"]
        ))
        
        # Scenario 4: Conditional Template
        self.add_scenario(TestScenario(
            name="conditional",
            description="Template with conditions and optional resources",
            template=ALL_TEMPLATES["conditional"],
            expected_modules=["networking", "database", "storage"],
            expected_resources=["aws_vpc", "aws_rds_db_instance", "aws_s3_bucket"]
        ))
    
    def run_conversion_test(self, scenario):
        """Run conversion test for a scenario"""
        print(f"\n{'='*60}")
        print(f"Testing Scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"{'='*60}")
        
        try:
            # Create temporary directory for this test
            temp_dir = tempfile.mkdtemp(prefix=f"cf2tf_test_{scenario.name}_")
            self.temp_dirs.append(temp_dir)
            
            # Test 1: Direct conversion engine test
            print("\n1. Testing Conversion Engine...")
            conversion_result = self._test_conversion_engine(scenario)
            scenario.results['conversion'] = conversion_result
            
            # Test 2: Module generation test
            print("2. Testing Module Generation...")
            module_result = self._test_module_generation(scenario, temp_dir)
            scenario.results['modules'] = module_result
            
            # Test 3: End-to-end orchestration test
            print("3. Testing End-to-End Orchestration...")
            orchestration_result = self._test_orchestration(scenario, temp_dir)
            scenario.results['orchestration'] = orchestration_result
            
            # Test 4: Validate generated Terraform
            print("4. Validating Generated Terraform...")
            validation_result = self._test_terraform_validation(scenario, temp_dir)
            scenario.results['validation'] = validation_result
            
            # Determine overall success
            scenario.success = all([
                conversion_result.get('success', False),
                module_result.get('success', False),
                orchestration_result.get('success', False),
                validation_result.get('success', False)
            ])
            
            # Collect errors and warnings
            for result in scenario.results.values():
                scenario.errors.extend(result.get('errors', []))
                scenario.warnings.extend(result.get('warnings', []))
            
            print(f"\nScenario {scenario.name}: {'✓ PASSED' if scenario.success else '✗ FAILED'}")
            if scenario.errors:
                print(f"Errors: {len(scenario.errors)}")
                for error in scenario.errors[:3]:  # Show first 3 errors
                    print(f"  - {error}")
            if scenario.warnings:
                print(f"Warnings: {len(scenario.warnings)}")
        
        except Exception as e:
            scenario.success = False
            scenario.errors.append(f"Test execution failed: {str(e)}")
            print(f"\nScenario {scenario.name}: ✗ FAILED - {str(e)}")
    
    def _test_conversion_engine(self, scenario):
        """Test the conversion engine directly"""
        result = {'success': False, 'errors': [], 'warnings': []}
        
        try:
            engine = ConversionEngine()
            conversion_result = engine.convert_template(scenario.template)
            
            # Check basic conversion success
            if not conversion_result.terraform_config:
                result['errors'].append("No Terraform configuration generated")
                return result
            
            # Check for expected resource types
            resources = conversion_result.terraform_config.get('resource', {})
            found_resources = list(resources.keys())
            
            missing_resources = []
            for expected_resource in scenario.expected_resources:
                if expected_resource not in found_resources:
                    missing_resources.append(expected_resource)
            
            if missing_resources:
                result['warnings'].append(f"Missing expected resources: {missing_resources}")
            
            # Check for import commands
            if not conversion_result.import_commands:
                result['warnings'].append("No import commands generated")
            
            result['success'] = True
            result['resources_converted'] = len(found_resources)
            result['import_commands'] = len(conversion_result.import_commands)
            result['conversion_warnings'] = len(conversion_result.warnings)
            result['conversion_errors'] = len(conversion_result.errors)
            
            print(f"   ✓ Converted {result['resources_converted']} resource types")
            print(f"   ✓ Generated {result['import_commands']} import commands")
            
        except Exception as e:
            result['errors'].append(f"Conversion engine failed: {str(e)}")
        
        return result
    
    def _test_module_generation(self, scenario, temp_dir):
        """Test module generation"""
        result = {'success': False, 'errors': [], 'warnings': []}
        
        try:
            # First convert the template
            engine = ConversionEngine()
            conversion_result = engine.convert_template(scenario.template)
            
            # Create mock converted resources
            converted_resources = {}
            resources = conversion_result.terraform_config.get('resource', {})
            
            for resource_type, resource_instances in resources.items():
                for resource_name in resource_instances.keys():
                    resource_id = f"{resource_type}-{resource_name}-123"
                    converted_resources[resource_id] = {
                        'resource_type': f"AWS::{resource_type.replace('aws_', '').replace('_', '::').title()}",
                        'resource_id': resource_id,
                        'terraform_config': {
                            'resource': {resource_type: {resource_name: resource_instances[resource_name]}}
                        }
                    }
            
            # Generate modules
            generator = ModuleGenerator(organization_strategy="service_based")
            generation_result = generator.generate_modules(
                converted_resources=converted_resources,
                discovery_resources={},
                output_dir=os.path.join(temp_dir, "modules_test")
            )
            
            # Check module generation success
            if not generation_result.modules:
                result['errors'].append("No modules generated")
                return result
            
            # Check for expected modules
            generated_modules = list(generation_result.modules.keys())
            missing_modules = []
            for expected_module in scenario.expected_modules:
                if expected_module not in generated_modules:
                    missing_modules.append(expected_module)
            
            if missing_modules:
                result['warnings'].append(f"Missing expected modules: {missing_modules}")
            
            # Check file generation
            if generation_result.total_files == 0:
                result['errors'].append("No files generated")
                return result
            
            result['success'] = True
            result['modules_generated'] = len(generation_result.modules)
            result['files_generated'] = generation_result.total_files
            result['module_errors'] = len(generation_result.errors)
            result['module_warnings'] = len(generation_result.warnings)
            
            print(f"   ✓ Generated {result['modules_generated']} modules")
            print(f"   ✓ Created {result['files_generated']} files")
            
        except Exception as e:
            result['errors'].append(f"Module generation failed: {str(e)}")
        
        return result
    
    def _test_orchestration(self, scenario, temp_dir):
        """Test end-to-end orchestration"""
        result = {'success': False, 'errors': [], 'warnings': []}
        
        try:
            # Create test configuration
            config = ToolConfig(
                discovery=DiscoveryConfig(regions=['us-east-1']),
                conversion=ConversionConfig(),
                modules=ModuleConfig(organization_strategy="service_based"),
                output=OutputConfig(
                    output_directory=os.path.join(temp_dir, "orchestration_test"),
                    export_discovery_data=True,
                    generate_documentation=True
                ),
                imports=ImportConfig()
            )
            
            # Mock AWS services
            with patch('boto3.Session') as mock_session:
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
                mock_cf_client.list_stacks.return_value = {
                    'StackSummaries': [{
                        'StackName': f'{scenario.name}-stack',
                        'StackId': f'arn:aws:cloudformation:us-east-1:123456789012:stack/{scenario.name}-stack/12345',
                        'StackStatus': 'CREATE_COMPLETE',
                        'CreationTime': datetime.now()
                    }]
                }
                
                mock_cf_client.describe_stacks.return_value = {
                    'Stacks': [{
                        'StackName': f'{scenario.name}-stack',
                        'StackId': f'arn:aws:cloudformation:us-east-1:123456789012:stack/{scenario.name}-stack/12345',
                        'StackStatus': 'CREATE_COMPLETE',
                        'CreationTime': datetime.now(),
                        'Parameters': [],
                        'Outputs': []
                    }]
                }
                
                # Mock stack resources
                mock_resources = []
                for i, resource_type in enumerate(scenario.expected_resources):
                    cf_type = f"AWS::{resource_type.replace('aws_', '').replace('_', '::').title()}"
                    mock_resources.append({
                        'LogicalResourceId': f'Resource{i}',
                        'PhysicalResourceId': f'{resource_type}-{i}-123',
                        'ResourceType': cf_type,
                        'ResourceStatus': 'CREATE_COMPLETE'
                    })
                
                mock_cf_client.describe_stack_resources.return_value = {
                    'StackResources': mock_resources
                }
                
                mock_cf_client.get_template.return_value = {
                    'TemplateBody': json.dumps(scenario.template)
                }
                
                # Mock EC2 responses (no independent resources)
                mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}
                mock_ec2_client.describe_instances.return_value = {'Reservations': []}
                mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
                mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
                
                # Run orchestration
                orchestrator = Orchestrator(config)
                orchestration_result = orchestrator.run_conversion(dry_run=False)
                
                # Check orchestration success
                if not orchestration_result['success']:
                    result['errors'].extend(orchestration_result.get('errors', []))
                    return result
                
                result['success'] = True
                result['resources_discovered'] = orchestration_result.get('resources_discovered', 0)
                result['resources_converted'] = orchestration_result.get('resources_converted', 0)
                result['modules_count'] = orchestration_result.get('modules_count', 0)
                result['files_count'] = orchestration_result.get('files_count', 0)
                
                print(f"   ✓ Discovered {result['resources_discovered']} resources")
                print(f"   ✓ Converted {result['resources_converted']} resources")
                print(f"   ✓ Generated {result['modules_count']} modules")
        
        except Exception as e:
            result['errors'].append(f"Orchestration failed: {str(e)}")
        
        return result
    
    def _test_terraform_validation(self, scenario, temp_dir):
        """Test validation of generated Terraform code"""
        result = {'success': False, 'errors': [], 'warnings': []}
        
        try:
            # Look for generated Terraform files
            terraform_dir = Path(temp_dir) / "orchestration_test"
            
            if not terraform_dir.exists():
                result['errors'].append("Terraform output directory not found")
                return result
            
            # Check for required files
            required_files = ['main.tf', 'variables.tf', 'outputs.tf']
            missing_files = []
            
            for required_file in required_files:
                if not (terraform_dir / required_file).exists():
                    missing_files.append(required_file)
            
            if missing_files:
                result['warnings'].append(f"Missing files: {missing_files}")
            
            # Check main.tf content
            main_tf = terraform_dir / "main.tf"
            if main_tf.exists():
                content = main_tf.read_text()
                
                # Basic syntax checks
                if 'terraform {' not in content:
                    result['warnings'].append("No terraform block found in main.tf")
                
                if 'provider "aws"' not in content:
                    result['warnings'].append("No AWS provider configuration found")
                
                # Check for module calls
                module_count = content.count('module "')
                if module_count == 0:
                    result['warnings'].append("No module calls found in main.tf")
            
            # Check modules directory
            modules_dir = terraform_dir / "modules"
            if modules_dir.exists():
                module_dirs = [d for d in modules_dir.iterdir() if d.is_dir()]
                result['modules_found'] = len(module_dirs)
                
                # Check each module
                for module_dir in module_dirs:
                    module_files = ['main.tf', 'variables.tf', 'outputs.tf']
                    for module_file in module_files:
                        if not (module_dir / module_file).exists():
                            result['warnings'].append(f"Missing {module_file} in {module_dir.name} module")
            
            # Check import script
            import_script = terraform_dir / "import_resources.sh"
            if import_script.exists():
                import_content = import_script.read_text()
                import_count = import_content.count('terraform import')
                result['import_commands_found'] = import_count
                
                if import_count == 0:
                    result['warnings'].append("No import commands found in import script")
            else:
                result['warnings'].append("Import script not found")
            
            result['success'] = True
            result['terraform_files'] = len(list(terraform_dir.rglob("*.tf")))
            
            print(f"   ✓ Found {result['terraform_files']} Terraform files")
            print(f"   ✓ Found {result.get('modules_found', 0)} modules")
            print(f"   ✓ Found {result.get('import_commands_found', 0)} import commands")
        
        except Exception as e:
            result['errors'].append(f"Terraform validation failed: {str(e)}")
        
        return result
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("CF2TF Converter - Comprehensive Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Set up scenarios
        self.setup_test_scenarios()
        
        # Run each scenario
        for scenario in self.scenarios:
            self.run_conversion_test(scenario)
            self.results[scenario.name] = scenario
        
        # Generate summary report
        self.generate_summary_report()
        
        # Cleanup
        self.cleanup()
        
        total_time = time.time() - start_time
        print(f"\nTotal test execution time: {total_time:.2f} seconds")
    
    def generate_summary_report(self):
        """Generate a summary report of all test results"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY REPORT")
        print(f"{'='*60}")
        
        total_scenarios = len(self.scenarios)
        passed_scenarios = sum(1 for s in self.scenarios if s.success)
        failed_scenarios = total_scenarios - passed_scenarios
        
        print(f"Total Scenarios: {total_scenarios}")
        print(f"Passed: {passed_scenarios}")
        print(f"Failed: {failed_scenarios}")
        print(f"Success Rate: {(passed_scenarios/total_scenarios*100):.1f}%")
        
        print(f"\n{'Scenario':<20} {'Status':<10} {'Errors':<8} {'Warnings':<10}")
        print("-" * 60)
        
        for scenario in self.scenarios:
            status = "✓ PASS" if scenario.success else "✗ FAIL"
            print(f"{scenario.name:<20} {status:<10} {len(scenario.errors):<8} {len(scenario.warnings):<10}")
        
        # Detailed failure analysis
        if failed_scenarios > 0:
            print(f"\n{'='*60}")
            print("FAILURE ANALYSIS")
            print(f"{'='*60}")
            
            for scenario in self.scenarios:
                if not scenario.success:
                    print(f"\nScenario: {scenario.name}")
                    print(f"Description: {scenario.description}")
                    
                    if scenario.errors:
                        print("Errors:")
                        for error in scenario.errors:
                            print(f"  - {error}")
                    
                    if scenario.warnings:
                        print("Warnings:")
                        for warning in scenario.warnings[:5]:  # Show first 5 warnings
                            print(f"  - {warning}")
        
        # Performance metrics
        print(f"\n{'='*60}")
        print("PERFORMANCE METRICS")
        print(f"{'='*60}")
        
        for scenario in self.scenarios:
            if scenario.success:
                conversion = scenario.results.get('conversion', {})
                modules = scenario.results.get('modules', {})
                orchestration = scenario.results.get('orchestration', {})
                
                print(f"\n{scenario.name}:")
                print(f"  Resources Converted: {conversion.get('resources_converted', 0)}")
                print(f"  Modules Generated: {modules.get('modules_generated', 0)}")
                print(f"  Files Created: {modules.get('files_generated', 0)}")
                print(f"  Import Commands: {conversion.get('import_commands', 0)}")
    
    def cleanup(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_tests()

