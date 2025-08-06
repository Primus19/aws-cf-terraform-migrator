#!/usr/bin/env python3
"""
Terraform Import Manager

This module handles the generation and execution of Terraform import operations
to bring existing AWS resources under Terraform management without disruption.
"""

import os
import subprocess
import time
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tempfile
import shutil

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of a Terraform import operation"""
    resource_address: str
    resource_id: str
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0


@dataclass
class ImportSummary:
    """Summary of import operations"""
    total_imports: int = 0
    successful_imports: int = 0
    failed_imports: int = 0
    total_time: float = 0.0
    results: List[ImportResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ImportManager:
    """
    Terraform import manager
    
    This class handles the generation and execution of import operations
    to bring existing resources under Terraform management without disruption.
    """
    
    # Import command templates for different resource types
    IMPORT_TEMPLATES = {
        'aws_instance': 'terraform import {address} {id}',
        'aws_vpc': 'terraform import {address} {id}',
        'aws_subnet': 'terraform import {address} {id}',
        'aws_security_group': 'terraform import {address} {id}',
        'aws_security_group_rule': 'terraform import {address} {id}',
        'aws_internet_gateway': 'terraform import {address} {id}',
        'aws_internet_gateway_attachment': 'terraform import {address} {vpc_id}/{igw_id}',
        'aws_route_table': 'terraform import {address} {id}',
        'aws_route': 'terraform import {address} {route_table_id}_{destination}',
        'aws_route_table_association': 'terraform import {address} {subnet_id}/{route_table_id}',
        'aws_nat_gateway': 'terraform import {address} {id}',
        'aws_eip': 'terraform import {address} {id}',
        'aws_eip_association': 'terraform import {address} {id}',
        'aws_network_interface': 'terraform import {address} {id}',
        'aws_network_interface_attachment': 'terraform import {address} {eni_id}:{instance_id}',
        
        # Load Balancing
        'aws_elb': 'terraform import {address} {id}',
        'aws_lb': 'terraform import {address} {arn}',
        'aws_lb_target_group': 'terraform import {address} {arn}',
        'aws_lb_listener': 'terraform import {address} {arn}',
        'aws_lb_listener_rule': 'terraform import {address} {arn}',
        
        # Storage
        'aws_s3_bucket': 'terraform import {address} {id}',
        'aws_s3_bucket_policy': 'terraform import {address} {id}',
        'aws_s3_bucket_notification': 'terraform import {address} {id}',
        'aws_ebs_volume': 'terraform import {address} {id}',
        'aws_volume_attachment': 'terraform import {address} {device_name}:{volume_id}:{instance_id}',
        'aws_efs_file_system': 'terraform import {address} {id}',
        'aws_efs_mount_target': 'terraform import {address} {id}',
        
        # Database
        'aws_db_instance': 'terraform import {address} {id}',
        'aws_rds_cluster': 'terraform import {address} {id}',
        'aws_db_subnet_group': 'terraform import {address} {id}',
        'aws_db_parameter_group': 'terraform import {address} {id}',
        'aws_rds_cluster_parameter_group': 'terraform import {address} {id}',
        'aws_dynamodb_table': 'terraform import {address} {id}',
        'aws_elasticache_cluster': 'terraform import {address} {id}',
        'aws_elasticache_replication_group': 'terraform import {address} {id}',
        'aws_elasticache_subnet_group': 'terraform import {address} {id}',
        
        # IAM
        'aws_iam_role': 'terraform import {address} {id}',
        'aws_iam_policy': 'terraform import {address} {arn}',
        'aws_iam_user': 'terraform import {address} {id}',
        'aws_iam_group': 'terraform import {address} {id}',
        'aws_iam_instance_profile': 'terraform import {address} {id}',
        'aws_iam_role_policy_attachment': 'terraform import {address} {role_name}/{policy_arn}',
        'aws_iam_user_policy_attachment': 'terraform import {address} {user_name}/{policy_arn}',
        'aws_iam_group_policy_attachment': 'terraform import {address} {group_name}/{policy_arn}',
        
        # DNS
        'aws_route53_zone': 'terraform import {address} {id}',
        'aws_route53_record': 'terraform import {address} {zone_id}_{name}_{type}',
        
        # CloudFront
        'aws_cloudfront_distribution': 'terraform import {address} {id}',
        'aws_cloudfront_origin_access_identity': 'terraform import {address} {id}',
        
        # API Gateway
        'aws_api_gateway_rest_api': 'terraform import {address} {id}',
        'aws_api_gateway_resource': 'terraform import {address} {rest_api_id}/{id}',
        'aws_api_gateway_method': 'terraform import {address} {rest_api_id}/{resource_id}/{http_method}',
        'aws_api_gateway_deployment': 'terraform import {address} {rest_api_id}/{id}',
        'aws_api_gateway_stage': 'terraform import {address} {rest_api_id}/{stage_name}',
        
        # Messaging
        'aws_sns_topic': 'terraform import {address} {arn}',
        'aws_sns_topic_subscription': 'terraform import {address} {arn}',
        'aws_sqs_queue': 'terraform import {address} {url}',
        
        # Monitoring
        'aws_cloudwatch_metric_alarm': 'terraform import {address} {id}',
        'aws_cloudwatch_dashboard': 'terraform import {address} {id}',
        'aws_cloudwatch_log_group': 'terraform import {address} {id}',
        'aws_cloudwatch_log_stream': 'terraform import {address} {log_group_name}:{log_stream_name}',
        
        # Security
        'aws_kms_key': 'terraform import {address} {id}',
        'aws_kms_alias': 'terraform import {address} {name}',
        'aws_secretsmanager_secret': 'terraform import {address} {arn}',
        'aws_secretsmanager_secret_version': 'terraform import {address} {arn}|{version_id}',
        
        # Lambda
        'aws_lambda_function': 'terraform import {address} {id}',
        'aws_lambda_permission': 'terraform import {address} {function_name}/{statement_id}',
        'aws_lambda_alias': 'terraform import {address} {function_name}:{name}',
        'aws_lambda_version': 'terraform import {address} {function_name}:{version}',
        
        # Auto Scaling
        'aws_autoscaling_group': 'terraform import {address} {id}',
        'aws_launch_configuration': 'terraform import {address} {id}',
        'aws_launch_template': 'terraform import {address} {id}',
        
        # ECS
        'aws_ecs_cluster': 'terraform import {address} {id}',
        'aws_ecs_service': 'terraform import {address} {cluster}/{service}',
        'aws_ecs_task_definition': 'terraform import {address} {arn}',
    }
    
    def __init__(self, terraform_dir: str, parallel: bool = False, 
                 max_workers: int = 5, timeout: int = 300,
                 retry_failed: bool = True, max_retries: int = 3,
                 create_backup: bool = True):
        """
        Initialize the import manager
        
        Args:
            terraform_dir: Directory containing Terraform configurations
            parallel: Whether to execute imports in parallel
            max_workers: Maximum number of parallel import workers
            timeout: Timeout for individual import operations (seconds)
            retry_failed: Whether to retry failed imports
            max_retries: Maximum number of retries for failed imports
            create_backup: Whether to create backup of state files
        """
        self.terraform_dir = Path(terraform_dir).resolve()
        self.parallel = parallel
        self.max_workers = max_workers
        self.timeout = timeout
        self.retry_failed = retry_failed
        self.max_retries = max_retries
        self.create_backup = create_backup
        
        # Validate Terraform directory
        if not self.terraform_dir.exists():
            raise ValueError(f"Terraform directory does not exist: {terraform_dir}")
        
        logger.info(f"Initialized ImportManager for directory: {self.terraform_dir}")
    
    def generate_import_script(self, resources: Dict[str, Any], 
                              output_file: str = "import_resources.sh") -> str:
        """
        Generate a shell script with import commands for all resources
        
        Args:
            resources: Dictionary of resources to import
            output_file: Output file path for the import script
            
        Returns:
            Path to the generated import script
        """
        logger.info(f"Generating import script for {len(resources)} resources")
        
        script_path = self.terraform_dir / output_file
        import_commands = []
        
        # Add script header
        import_commands.extend([
            "#!/bin/bash",
            "# Terraform Import Script",
            "# Generated by CF2TF Converter",
            f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "set -e  # Exit on any error",
            "",
            "echo 'Starting Terraform import operations...'",
            "echo 'This may take several minutes depending on the number of resources.'",
            "echo ''",
            ""
        ])
        
        # Generate import commands for each resource
        for resource_id, resource_info in resources.items():
            try:
                import_cmd = self._generate_import_command(resource_info)
                if import_cmd:
                    # Handle both StackInfo/ResourceInfo objects and dictionaries
                    if hasattr(resource_info, 'resource_type'):
                        resource_type = resource_info.resource_type
                    elif isinstance(resource_info, dict):
                        resource_type = resource_info.get('resource_type', 'Unknown')
                    else:
                        resource_type = 'Unknown'
                        
                    import_commands.extend([
                        f"# Import {resource_type} - {resource_id}",
                        f"echo 'Importing {resource_id}...'",
                        import_cmd,
                        "echo 'Import completed successfully'",
                        "echo ''",
                        ""
                    ])
                else:
                    import_commands.extend([
                        f"# Skipping {resource_id} - no import template available",
                        f"echo 'Skipping {resource_id} - unsupported resource type'",
                        ""
                    ])
            except Exception as e:
                logger.warning(f"Failed to generate import command for {resource_id}: {str(e)}")
                import_commands.extend([
                    f"# Error generating import command for {resource_id}: {str(e)}",
                    f"echo 'Error: Could not generate import command for {resource_id}'",
                    ""
                ])
        
        # Add script footer
        import_commands.extend([
            "echo 'All import operations completed!'",
            "echo 'Run \"terraform plan\" to verify the imported resources.'",
            ""
        ])
        
        # Write script to file
        with open(script_path, 'w') as f:
            f.write('\n'.join(import_commands))
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        logger.info(f"Import script generated: {script_path}")
        return str(script_path)
    
    def execute_import_script(self, import_script: str) -> ImportSummary:
        """
        Execute a Terraform import script
        
        Args:
            import_script: Path to the import script file
            
        Returns:
            ImportSummary with results of import operations
        """
        logger.info(f"Executing import script: {import_script}")
        
        script_path = Path(import_script)
        if not script_path.exists():
            raise FileNotFoundError(f"Import script not found: {import_script}")
        
        # Create backup if requested
        if self.create_backup:
            self._create_state_backup()
        
        summary = ImportSummary()
        start_time = time.time()
        
        try:
            # Parse import commands from script
            import_commands = self._parse_import_script(script_path)
            summary.total_imports = len(import_commands)
            
            if self.parallel and len(import_commands) > 1:
                # Execute imports in parallel
                summary = self._execute_parallel_imports(import_commands)
            else:
                # Execute imports sequentially
                summary = self._execute_sequential_imports(import_commands)
            
            summary.total_time = time.time() - start_time
            
            logger.info(f"Import execution completed: {summary.successful_imports}/{summary.total_imports} successful")
            
        except Exception as e:
            error_msg = f"Import script execution failed: {str(e)}"
            logger.error(error_msg)
            summary.errors.append(error_msg)
        
        return summary
    
    def import_resource(self, resource_address: str, resource_id: str, 
                       resource_type: str = None) -> ImportResult:
        """
        Import a single resource into Terraform state
        
        Args:
            resource_address: Terraform resource address (e.g., aws_instance.example)
            resource_id: AWS resource ID to import
            resource_type: AWS resource type (optional, for validation)
            
        Returns:
            ImportResult with operation details
        """
        logger.debug(f"Importing resource: {resource_address} -> {resource_id}")
        
        start_time = time.time()
        result = ImportResult(
            resource_address=resource_address,
            resource_id=resource_id,
            success=False
        )
        
        try:
            # Build import command
            import_cmd = f"terraform import {resource_address} {resource_id}"
            
            # Execute import command
            process_result = self._execute_terraform_command(import_cmd)
            
            if process_result['returncode'] == 0:
                result.success = True
                logger.debug(f"Successfully imported {resource_address}")
            else:
                result.error_message = process_result['stderr']
                logger.warning(f"Failed to import {resource_address}: {result.error_message}")
        
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Exception during import of {resource_address}: {str(e)}")
        
        result.execution_time = time.time() - start_time
        return result
    
    def validate_imports(self, resources: List[str] = None) -> Dict[str, Any]:
        """
        Validate imported resources by running terraform plan
        
        Args:
            resources: List of specific resources to validate (optional)
            
        Returns:
            Validation results dictionary
        """
        logger.info("Validating imported resources with terraform plan")
        
        try:
            # Run terraform plan
            plan_cmd = "terraform plan -detailed-exitcode"
            if resources:
                # Add target flags for specific resources
                for resource in resources:
                    plan_cmd += f" -target={resource}"
            
            result = self._execute_terraform_command(plan_cmd)
            
            validation_result = {
                'valid': result['returncode'] == 0,
                'exit_code': result['returncode'],
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'has_changes': result['returncode'] == 2,  # Terraform plan exit code for changes
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if validation_result['valid']:
                logger.info("Terraform plan validation passed - no changes required")
            elif validation_result['has_changes']:
                logger.warning("Terraform plan shows changes - imported resources may need configuration updates")
            else:
                logger.error("Terraform plan validation failed")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                'valid': False,
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _generate_import_command(self, resource_info: Dict[str, Any]) -> Optional[str]:
        """Generate import command for a specific resource"""
        
        # Handle both StackInfo/ResourceInfo objects and dictionaries
        if hasattr(resource_info, 'resource_type'):
            resource_type = resource_info.resource_type
            resource_id = getattr(resource_info, 'resource_id', '')
            logical_id = getattr(resource_info, 'logical_id', '')
        elif isinstance(resource_info, dict):
            resource_type = resource_info.get('resource_type', '')
            resource_id = resource_info.get('resource_id', '')
            logical_id = resource_info.get('logical_id', '')
        else:
            return None
        
        if not resource_type or not resource_id:
            return None
        
        # Map CloudFormation type to Terraform type
        from .conversion import ResourceMapper
        terraform_type = ResourceMapper.get_terraform_type(resource_type)
        
        if not terraform_type:
            logger.warning(f"No Terraform mapping for resource type: {resource_type}")
            return None
        
        # Get import template
        import_template = self.IMPORT_TEMPLATES.get(terraform_type)
        if not import_template:
            logger.warning(f"No import template for Terraform type: {terraform_type}")
            return None
        
        # Generate resource address
        resource_name = logical_id.lower() if logical_id else resource_id.lower()
        resource_address = f"{terraform_type}.{resource_name}"
        
        # Handle special cases that require compound identifiers
        if terraform_type in ['aws_internet_gateway_attachment', 'aws_route_table_association']:
            # These require special handling based on resource properties
            return self._generate_compound_import_command(terraform_type, resource_info)
        
        # Generate standard import command
        try:
            # Handle both object and dictionary access
            if hasattr(resource_info, 'arn'):
                arn = getattr(resource_info, 'arn', resource_id)
                name = getattr(resource_info, 'name', resource_id)
            else:
                arn = resource_info.get('arn', resource_id) if isinstance(resource_info, dict) else resource_id
                name = resource_info.get('name', resource_id) if isinstance(resource_info, dict) else resource_id
                
            import_cmd = import_template.format(
                address=resource_address,
                id=resource_id,
                arn=arn,
                name=name
            )
            return import_cmd
        except KeyError as e:
            logger.warning(f"Missing parameter for import template: {str(e)}")
            return f"terraform import {resource_address} {resource_id}"
    
    def _generate_compound_import_command(self, terraform_type: str, 
                                        resource_info: Dict[str, Any]) -> Optional[str]:
        """Generate import commands for resources requiring compound identifiers"""
        
        # Handle both object and dictionary access
        if hasattr(resource_info, 'resource_id'):
            resource_id = resource_info.resource_id
            properties = getattr(resource_info, 'properties', {})
        else:
            resource_id = resource_info.get('resource_id', '') if isinstance(resource_info, dict) else ''
            properties = resource_info.get('properties', {}) if isinstance(resource_info, dict) else {}
        
        if terraform_type == 'aws_internet_gateway_attachment':
            vpc_id = properties.get('VpcId', '')
            igw_id = properties.get('InternetGatewayId', resource_id)
            if vpc_id and igw_id:
                return f"terraform import aws_internet_gateway_attachment.{resource_id.lower()} {vpc_id}/{igw_id}"
        
        elif terraform_type == 'aws_route_table_association':
            subnet_id = properties.get('SubnetId', '')
            route_table_id = properties.get('RouteTableId', '')
            if subnet_id and route_table_id:
                return f"terraform import aws_route_table_association.{resource_id.lower()} {subnet_id}/{route_table_id}"
        
        return None
    
    def _parse_import_script(self, script_path: Path) -> List[Dict[str, str]]:
        """Parse import commands from a shell script"""
        
        import_commands = []
        
        with open(script_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith('terraform import '):
                # Extract resource address and ID from import command
                parts = line.split(' ', 3)
                if len(parts) >= 3:
                    resource_address = parts[2]
                    resource_id = parts[3] if len(parts) > 3 else ''
                    
                    import_commands.append({
                        'command': line,
                        'address': resource_address,
                        'id': resource_id
                    })
        
        return import_commands
    
    def _execute_sequential_imports(self, import_commands: List[Dict[str, str]]) -> ImportSummary:
        """Execute import commands sequentially"""
        
        summary = ImportSummary()
        summary.total_imports = len(import_commands)
        
        for cmd_info in import_commands:
            try:
                result = self._execute_single_import(cmd_info)
                summary.results.append(result)
                
                if result.success:
                    summary.successful_imports += 1
                else:
                    summary.failed_imports += 1
                    
                    # Retry if configured
                    if self.retry_failed and result.retry_count < self.max_retries:
                        logger.info(f"Retrying import for {result.resource_address}")
                        retry_result = self._execute_single_import(cmd_info, result.retry_count + 1)
                        summary.results.append(retry_result)
                        
                        if retry_result.success:
                            summary.successful_imports += 1
                            summary.failed_imports -= 1
                        else:
                            summary.failed_imports += 1
            
            except Exception as e:
                error_msg = f"Exception during import: {str(e)}"
                logger.error(error_msg)
                summary.errors.append(error_msg)
                summary.failed_imports += 1
        
        return summary
    
    def _execute_parallel_imports(self, import_commands: List[Dict[str, str]]) -> ImportSummary:
        """Execute import commands in parallel"""
        
        summary = ImportSummary()
        summary.total_imports = len(import_commands)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all import tasks
            future_to_cmd = {
                executor.submit(self._execute_single_import, cmd_info): cmd_info
                for cmd_info in import_commands
            }
            
            # Collect results
            for future in as_completed(future_to_cmd):
                try:
                    result = future.result()
                    summary.results.append(result)
                    
                    if result.success:
                        summary.successful_imports += 1
                    else:
                        summary.failed_imports += 1
                
                except Exception as e:
                    error_msg = f"Exception during parallel import: {str(e)}"
                    logger.error(error_msg)
                    summary.errors.append(error_msg)
                    summary.failed_imports += 1
        
        return summary
    
    def _execute_single_import(self, cmd_info: Dict[str, str], retry_count: int = 0) -> ImportResult:
        """Execute a single import command"""
        
        start_time = time.time()
        result = ImportResult(
            resource_address=cmd_info['address'],
            resource_id=cmd_info['id'],
            success=False,
            retry_count=retry_count
        )
        
        try:
            # Execute the import command
            process_result = self._execute_terraform_command(cmd_info['command'])
            
            if process_result['returncode'] == 0:
                result.success = True
                logger.debug(f"Successfully imported {result.resource_address}")
            else:
                result.error_message = process_result['stderr']
                logger.warning(f"Failed to import {result.resource_address}: {result.error_message}")
        
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Exception during import: {str(e)}")
        
        result.execution_time = time.time() - start_time
        return result
    
    def _execute_terraform_command(self, command: str) -> Dict[str, Any]:
        """Execute a Terraform command and return results"""
        
        try:
            # Change to Terraform directory
            original_cwd = os.getcwd()
            os.chdir(self.terraform_dir)
            
            # Execute command
            process = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            return {
                'returncode': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'command': command
            }
        
        except subprocess.TimeoutExpired:
            raise Exception(f"Command timed out after {self.timeout} seconds: {command}")
        
        except Exception as e:
            raise Exception(f"Failed to execute command '{command}': {str(e)}")
        
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    def _create_state_backup(self):
        """Create backup of Terraform state files"""
        
        state_files = [
            'terraform.tfstate',
            'terraform.tfstate.backup'
        ]
        
        backup_dir = self.terraform_dir / 'state_backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        for state_file in state_files:
            state_path = self.terraform_dir / state_file
            if state_path.exists():
                backup_path = backup_dir / f"{state_file}.{timestamp}"
                shutil.copy2(state_path, backup_path)
                logger.info(f"Created state backup: {backup_path}")
    
    def get_import_summary_report(self, summary: ImportSummary) -> str:
        """Generate a formatted report of import operations"""
        
        report_lines = [
            "Terraform Import Summary Report",
            "=" * 40,
            f"Total imports attempted: {summary.total_imports}",
            f"Successful imports: {summary.successful_imports}",
            f"Failed imports: {summary.failed_imports}",
            f"Success rate: {(summary.successful_imports / summary.total_imports * 100):.1f}%" if summary.total_imports > 0 else "N/A",
            f"Total execution time: {summary.total_time:.2f} seconds",
            ""
        ]
        
        if summary.failed_imports > 0:
            report_lines.extend([
                "Failed Imports:",
                "-" * 20
            ])
            
            for result in summary.results:
                if not result.success:
                    report_lines.append(f"  {result.resource_address}: {result.error_message}")
            
            report_lines.append("")
        
        if summary.errors:
            report_lines.extend([
                "Errors:",
                "-" * 10
            ])
            
            for error in summary.errors:
                report_lines.append(f"  {error}")
        
        return '\n'.join(report_lines)


if __name__ == "__main__":
    # Example usage
    import_manager = ImportManager(
        terraform_dir="./terraform",
        parallel=True,
        max_workers=3
    )
    
    # Example resources to import
    resources = {
        'vpc-12345': {
            'resource_type': 'AWS::EC2::VPC',
            'resource_id': 'vpc-12345',
            'logical_id': 'MyVPC'
        },
        'subnet-67890': {
            'resource_type': 'AWS::EC2::Subnet',
            'resource_id': 'subnet-67890',
            'logical_id': 'MySubnet'
        }
    }
    
    # Generate import script
    script_path = import_manager.generate_import_script(resources)
    print(f"Import script generated: {script_path}")
    
    # Execute imports (commented out for example)
    # summary = import_manager.execute_import_script(script_path)
    # print(import_manager.get_import_summary_report(summary))

