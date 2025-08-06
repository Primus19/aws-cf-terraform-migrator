#!/usr/bin/env python3
"""
Orchestration Controller

This module coordinates all components of the CloudFormation to Terraform
conversion process, managing the workflow from discovery through module generation.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from .config import ToolConfig
from .discovery import DiscoveryEngine
from .conversion import ConversionEngine
from .modules import ModuleGenerator
from .imports import ImportManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestration controller
    
    This class coordinates the entire conversion process including discovery,
    conversion, module generation, and import script creation.
    """
    
    def __init__(self, config: ToolConfig):
        """
        Initialize the orchestrator
        
        Args:
            config: Tool configuration object
        """
        self.config = config
        
        # Initialize components
        self.discovery_engine = DiscoveryEngine(
            regions=config.discovery.regions,
            profile=config.discovery.profile,
            role_arn=config.discovery.role_arn,
            max_workers=config.discovery.max_workers
        )
        
        self.conversion_engine = ConversionEngine(
            preserve_names=config.conversion.preserve_original_names,
            handle_functions=config.conversion.handle_intrinsic_functions
        )
        
        self.module_generator = ModuleGenerator(
            organization_strategy=config.modules.organization_strategy,
            module_prefix=config.modules.module_prefix,
            include_examples=config.modules.include_examples,
            include_readme=config.modules.include_readme,
            include_versions_tf=config.modules.include_versions_tf,
            terraform_version=config.conversion.terraform_version,
            provider_version=config.conversion.provider_version
        )
        
        logger.info("Initialized Orchestrator with all components")
    
    def run_conversion(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run the complete conversion process
        
        Args:
            dry_run: If True, perform validation without generating files
            
        Returns:
            Dictionary with conversion results and statistics
        """
        logger.info("Starting complete CloudFormation to Terraform conversion")
        start_time = time.time()
        
        result = {
            'success': False,
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'phases': {},
            'output_directory': self.config.output.output_directory,
            'modules_count': 0,
            'files_count': 0,
            'resources_discovered': 0,
            'resources_converted': 0,
            'import_commands_generated': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Phase 1: Discovery
            logger.info("Phase 1: Discovering AWS resources")
            discovery_result = self._run_discovery_phase()
            result['phases']['discovery'] = discovery_result
            result['resources_discovered'] = discovery_result.get('total_resources', 0)
            
            if not discovery_result['success']:
                result['errors'].extend(discovery_result.get('errors', []))
                return result
            
            # Phase 2: Conversion
            logger.info("Phase 2: Converting CloudFormation to Terraform")
            conversion_result = self._run_conversion_phase(
                discovery_result['stacks'], 
                discovery_result['resources']
            )
            result['phases']['conversion'] = conversion_result
            result['resources_converted'] = conversion_result.get('resources_converted', 0)
            
            if not conversion_result['success']:
                result['errors'].extend(conversion_result.get('errors', []))
                return result
            
            # Phase 3: Module Generation
            if not dry_run:
                logger.info("Phase 3: Generating Terraform modules")
                module_result = self._run_module_generation_phase(
                    conversion_result['converted_resources'],
                    discovery_result['resources'],
                    discovery_result['stacks']
                )
                result['phases']['module_generation'] = module_result
                result['modules_count'] = module_result.get('modules_count', 0)
                result['files_count'] = module_result.get('files_count', 0)
                
                if not module_result['success']:
                    result['errors'].extend(module_result.get('errors', []))
                    return result
            
            # Phase 4: Import Script Generation
            if not dry_run:
                logger.info("Phase 4: Generating import scripts")
                import_result = self._run_import_generation_phase(
                    discovery_result['resources']
                )
                result['phases']['import_generation'] = import_result
                result['import_commands_generated'] = import_result.get('import_commands', 0)
                
                if not import_result['success']:
                    result['errors'].extend(import_result.get('errors', []))
                    return result
            
            # Phase 5: Documentation Generation
            if not dry_run and self.config.output.generate_documentation:
                logger.info("Phase 5: Generating documentation")
                doc_result = self._run_documentation_phase(result)
                result['phases']['documentation'] = doc_result
            
            # Success!
            result['success'] = True
            result['total_time'] = time.time() - start_time
            result['end_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Collect warnings from all phases
            for phase_result in result['phases'].values():
                result['warnings'].extend(phase_result.get('warnings', []))
            
            logger.info(f"Conversion completed successfully in {result['total_time']:.2f} seconds")
            
        except Exception as e:
            error_msg = f"Conversion process failed: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['total_time'] = time.time() - start_time
        
        return result
    
    def _run_discovery_phase(self) -> Dict[str, Any]:
        """Run the resource discovery phase"""
        
        phase_result = {
            'success': False,
            'start_time': time.time(),
            'stacks': {},
            'resources': {},
            'total_stacks': 0,
            'total_resources': 0,
            'cloudformation_managed': 0,
            'independent_resources': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Perform discovery
            stacks, resources = self.discovery_engine.discover_all(
                include_deleted=self.config.discovery.include_deleted_stacks,
                stack_name_filter=self.config.discovery.stack_name_filter
            )
            
            # Get summary statistics
            summary = self.discovery_engine.get_stack_summary()
            
            phase_result.update({
                'success': True,
                'stacks': stacks,
                'resources': resources,
                'total_stacks': summary['total_stacks'],
                'total_resources': summary['total_resources'],
                'cloudformation_managed': summary['cloudformation_managed'],
                'independent_resources': summary['independent_resources']
            })
            
            # Export discovery data if configured
            if self.config.output.export_discovery_data:
                discovery_file = os.path.join(
                    self.config.output.output_directory,
                    f"discovery_results.{self.config.output.export_format}"
                )
                self.discovery_engine.export_discovery_results(discovery_file)
                logger.info(f"Discovery data exported to {discovery_file}")
            
        except Exception as e:
            error_msg = f"Discovery phase failed: {str(e)}"
            logger.error(error_msg)
            phase_result['errors'].append(error_msg)
        
        phase_result['duration'] = time.time() - phase_result['start_time']
        return phase_result
    
    def _run_conversion_phase(self, stacks: Dict[str, Any], 
                             resources: Dict[str, Any]) -> Dict[str, Any]:
        """Run the CloudFormation to Terraform conversion phase"""
        
        phase_result = {
            'success': False,
            'start_time': time.time(),
            'converted_resources': {},
            'resources_converted': 0,
            'conversion_errors': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            converted_resources = {}
            conversion_errors = 0
            
            # Convert CloudFormation stacks
            for stack_id, stack_info in stacks.items():
                try:
                    if stack_info.template_body:
                        # Parse template body
                        template = json.loads(stack_info.template_body)
                        
                        # Convert template
                        conversion_result = self.conversion_engine.convert_template(
                            template, stack_info.stack_name
                        )
                        
                        # Store conversion results
                        for resource_id in stack_info.resources:
                            if resource_id['PhysicalResourceId'] in resources:
                                resource_key = resource_id['PhysicalResourceId']
                                converted_resources[resource_key] = {
                                    **resources[resource_key].__dict__,
                                    'terraform_config': conversion_result.terraform_config,
                                    'import_commands': conversion_result.import_commands,
                                    'conversion_warnings': conversion_result.warnings,
                                    'conversion_errors': conversion_result.errors
                                }
                        
                        # Collect warnings and errors
                        phase_result['warnings'].extend(conversion_result.warnings)
                        if conversion_result.errors:
                            phase_result['errors'].extend(conversion_result.errors)
                            conversion_errors += len(conversion_result.errors)
                
                except Exception as e:
                    error_msg = f"Failed to convert stack {stack_info.stack_name}: {str(e)}"
                    logger.error(error_msg)
                    phase_result['errors'].append(error_msg)
                    conversion_errors += 1
            
            # Convert independent resources
            for resource_id, resource_info in resources.items():
                if not resource_info.managed_by_cloudformation:
                    try:
                        # Create a minimal CloudFormation resource structure for conversion
                        cf_resource = {
                            'Type': resource_info.resource_type,
                            'Properties': resource_info.properties
                        }
                        
                        conversion_result = self.conversion_engine.convert_resource(
                            resource_info.logical_id or resource_id,
                            cf_resource,
                            resource_id
                        )
                        
                        converted_resources[resource_id] = {
                            **resource_info.__dict__,
                            'terraform_config': conversion_result.terraform_config,
                            'import_commands': conversion_result.import_commands,
                            'conversion_warnings': conversion_result.warnings,
                            'conversion_errors': conversion_result.errors
                        }
                        
                        # Collect warnings and errors
                        phase_result['warnings'].extend(conversion_result.warnings)
                        if conversion_result.errors:
                            phase_result['errors'].extend(conversion_result.errors)
                            conversion_errors += len(conversion_result.errors)
                    
                    except Exception as e:
                        error_msg = f"Failed to convert resource {resource_id}: {str(e)}"
                        logger.warning(error_msg)
                        phase_result['warnings'].append(error_msg)
            
            phase_result.update({
                'success': True,
                'converted_resources': converted_resources,
                'resources_converted': len(converted_resources),
                'conversion_errors': conversion_errors
            })
            
        except Exception as e:
            error_msg = f"Conversion phase failed: {str(e)}"
            logger.error(error_msg)
            phase_result['errors'].append(error_msg)
        
        phase_result['duration'] = time.time() - phase_result['start_time']
        return phase_result
    
    def _run_module_generation_phase(self, converted_resources: Dict[str, Any],
                                   discovery_resources: Dict[str, Any],
                                   stacks: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Terraform module generation phase"""
        
        phase_result = {
            'success': False,
            'start_time': time.time(),
            'modules_count': 0,
            'files_count': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Ensure output directory exists
            output_dir = Path(self.config.output.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate modules
            generation_result = self.module_generator.generate_modules(
                converted_resources=converted_resources,
                discovery_resources={k: v.__dict__ for k, v in discovery_resources.items()},
                output_dir=str(output_dir),
                stacks={k: v.__dict__ for k, v in stacks.items()}
            )
            
            phase_result.update({
                'success': True,
                'modules_count': len(generation_result.modules),
                'files_count': generation_result.total_files,
                'warnings': generation_result.warnings,
                'errors': generation_result.errors
            })
            
            # Export module information
            if self.config.output.include_metadata:
                modules_info = {
                    'modules': {name: info.__dict__ for name, info in generation_result.modules.items()},
                    'root_module': generation_result.root_module.__dict__ if generation_result.root_module else None,
                    'generation_metadata': {
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'organization_strategy': self.config.modules.organization_strategy,
                        'terraform_version': self.config.conversion.terraform_version,
                        'provider_version': self.config.conversion.provider_version
                    }
                }
                
                metadata_file = output_dir / "modules_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(modules_info, f, indent=2, default=str)
                
                logger.info(f"Module metadata exported to {metadata_file}")
            
        except Exception as e:
            error_msg = f"Module generation phase failed: {str(e)}"
            logger.error(error_msg)
            phase_result['errors'].append(error_msg)
        
        phase_result['duration'] = time.time() - phase_result['start_time']
        return phase_result
    
    def _run_import_generation_phase(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """Run the import script generation phase"""
        
        phase_result = {
            'success': False,
            'start_time': time.time(),
            'import_commands': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Initialize import manager
            import_manager = ImportManager(
                terraform_dir=self.config.output.output_directory,
                parallel=self.config.imports.parallel_imports,
                max_workers=self.config.imports.max_import_workers,
                timeout=self.config.imports.import_timeout,
                retry_failed=self.config.imports.retry_failed_imports,
                max_retries=self.config.imports.max_retries,
                create_backup=self.config.imports.create_backup
            )
            
            # Convert resources to format expected by import manager
            import_resources = {}
            for resource_id, resource_info in resources.items():
                import_resources[resource_id] = resource_info.__dict__
            
            # Generate import script
            script_path = import_manager.generate_import_script(
                resources=import_resources,
                output_file="import_resources.sh"
            )
            
            # Count import commands
            import_commands = 0
            with open(script_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('terraform import '):
                        import_commands += 1
            
            phase_result.update({
                'success': True,
                'import_commands': import_commands,
                'script_path': script_path
            })
            
            logger.info(f"Import script generated with {import_commands} commands: {script_path}")
            
        except Exception as e:
            error_msg = f"Import generation phase failed: {str(e)}"
            logger.error(error_msg)
            phase_result['errors'].append(error_msg)
        
        phase_result['duration'] = time.time() - phase_result['start_time']
        return phase_result
    
    def _run_documentation_phase(self, conversion_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run the documentation generation phase"""
        
        phase_result = {
            'success': False,
            'start_time': time.time(),
            'documents_generated': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            output_dir = Path(self.config.output.output_directory)
            
            # Generate conversion report
            report_content = self._generate_conversion_report(conversion_result)
            report_file = output_dir / "conversion_report.md"
            
            with open(report_file, 'w') as f:
                f.write(report_content)
            
            # Generate migration guide
            migration_guide = self._generate_migration_guide(conversion_result)
            guide_file = output_dir / "MIGRATION_GUIDE.md"
            
            with open(guide_file, 'w') as f:
                f.write(migration_guide)
            
            phase_result.update({
                'success': True,
                'documents_generated': 2,
                'report_file': str(report_file),
                'guide_file': str(guide_file)
            })
            
            logger.info(f"Documentation generated: {report_file}, {guide_file}")
            
        except Exception as e:
            error_msg = f"Documentation phase failed: {str(e)}"
            logger.error(error_msg)
            phase_result['errors'].append(error_msg)
        
        phase_result['duration'] = time.time() - phase_result['start_time']
        return phase_result
    
    def _generate_conversion_report(self, conversion_result: Dict[str, Any]) -> str:
        """Generate a comprehensive conversion report"""
        
        lines = [
            "# CloudFormation to Terraform Conversion Report",
            "",
            f"**Generated**: {conversion_result['start_time']}",
            f"**Duration**: {conversion_result.get('total_time', 0):.2f} seconds",
            f"**Status**: {'Success' if conversion_result['success'] else 'Failed'}",
            "",
            "## Summary",
            "",
            f"- **Resources Discovered**: {conversion_result['resources_discovered']}",
            f"- **Resources Converted**: {conversion_result['resources_converted']}",
            f"- **Modules Generated**: {conversion_result['modules_count']}",
            f"- **Files Created**: {conversion_result['files_count']}",
            f"- **Import Commands**: {conversion_result['import_commands_generated']}",
            "",
            "## Phase Results",
            ""
        ]
        
        # Add phase details
        for phase_name, phase_result in conversion_result.get('phases', {}).items():
            lines.extend([
                f"### {phase_name.replace('_', ' ').title()}",
                f"- **Status**: {'Success' if phase_result.get('success', False) else 'Failed'}",
                f"- **Duration**: {phase_result.get('duration', 0):.2f} seconds",
            ])
            
            if phase_result.get('warnings'):
                lines.append(f"- **Warnings**: {len(phase_result['warnings'])}")
            
            if phase_result.get('errors'):
                lines.append(f"- **Errors**: {len(phase_result['errors'])}")
            
            lines.append("")
        
        # Add warnings section
        if conversion_result.get('warnings'):
            lines.extend([
                "## Warnings",
                ""
            ])
            for warning in conversion_result['warnings']:
                lines.append(f"- {warning}")
            lines.append("")
        
        # Add errors section
        if conversion_result.get('errors'):
            lines.extend([
                "## Errors",
                ""
            ])
            for error in conversion_result['errors']:
                lines.append(f"- {error}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_migration_guide(self, conversion_result: Dict[str, Any]) -> str:
        """Generate a migration guide for users"""
        
        lines = [
            "# CloudFormation to Terraform Migration Guide",
            "",
            "This guide will help you complete the migration from CloudFormation to Terraform.",
            "",
            "## Prerequisites",
            "",
            "1. **Terraform Installation**: Ensure Terraform is installed (version >= 1.0)",
            "2. **AWS CLI**: Configure AWS CLI with appropriate credentials",
            "3. **Backup**: Create backups of your current CloudFormation stacks",
            "",
            "## Migration Steps",
            "",
            "### Step 1: Review Generated Configuration",
            "",
            "1. Examine the generated Terraform modules in the `modules/` directory",
            "2. Review the root module configuration in `main.tf`",
            "3. Check variable definitions in `variables.tf`",
            "4. Verify outputs in `outputs.tf`",
            "",
            "### Step 2: Initialize Terraform",
            "",
            "```bash",
            "terraform init",
            "```",
            "",
            "### Step 3: Import Existing Resources",
            "",
            "**IMPORTANT**: This step brings your existing AWS resources under Terraform management",
            "without recreating them.",
            "",
            "```bash",
            "# Make the import script executable",
            "chmod +x import_resources.sh",
            "",
            "# Run the import script",
            "./import_resources.sh",
            "```",
            "",
            "### Step 4: Verify Import",
            "",
            "After importing, run a plan to verify no changes are required:",
            "",
            "```bash",
            "terraform plan",
            "```",
            "",
            "**Expected Result**: The plan should show no changes. If changes are shown,",
            "review the Terraform configuration and adjust as needed.",
            "",
            "### Step 5: Test Configuration",
            "",
            "1. Make a small, non-destructive change to test the configuration",
            "2. Run `terraform plan` to preview changes",
            "3. Run `terraform apply` to apply the change",
            "4. Verify the change was applied correctly",
            "",
            "### Step 6: Gradual Migration",
            "",
            "1. **Start Small**: Begin with non-critical resources",
            "2. **Test Thoroughly**: Validate each module before proceeding",
            "3. **Monitor**: Watch for any unexpected behavior",
            "4. **Document**: Keep track of any manual adjustments needed",
            "",
            "## Post-Migration Tasks",
            "",
            "### CloudFormation Stack Cleanup",
            "",
            "Once you've verified Terraform is managing your resources correctly:",
            "",
            "1. **Remove Resources from CloudFormation**: Use stack drift detection",
            "2. **Delete Empty Stacks**: Clean up CloudFormation stacks that no longer manage resources",
            "3. **Update CI/CD**: Modify deployment pipelines to use Terraform",
            "",
            "### Terraform Best Practices",
            "",
            "1. **Remote State**: Configure remote state storage (S3 + DynamoDB)",
            "2. **State Locking**: Enable state locking to prevent conflicts",
            "3. **Workspaces**: Use Terraform workspaces for environment separation",
            "4. **Version Control**: Store Terraform configurations in version control",
            "",
            "## Troubleshooting",
            "",
            "### Import Failures",
            "",
            "If resource imports fail:",
            "",
            "1. Check AWS permissions",
            "2. Verify resource IDs are correct",
            "3. Review Terraform provider documentation",
            "4. Check for resource-specific import requirements",
            "",
            "### Plan Shows Changes After Import",
            "",
            "This usually indicates configuration drift:",
            "",
            "1. Compare Terraform configuration with actual AWS resource settings",
            "2. Update Terraform configuration to match current state",
            "3. Consider if changes should be applied or configuration updated",
            "",
            "### Common Issues",
            "",
            "1. **Resource Dependencies**: Some resources may need to be imported in specific order",
            "2. **Naming Conflicts**: Terraform resource names must be unique within modules",
            "3. **Provider Versions**: Ensure compatible AWS provider version",
            "",
            "## Support",
            "",
            "For additional help:",
            "",
            "1. Review the conversion report for warnings and errors",
            "2. Check Terraform documentation for specific resource types",
            "3. Consult AWS provider documentation",
            "",
            "## Rollback Plan",
            "",
            "If you need to rollback:",
            "",
            "1. **Stop Terraform Management**: Remove resources from Terraform state",
            "2. **Restore CloudFormation**: Re-import resources into CloudFormation if needed",
            "3. **Verify State**: Ensure resources are properly managed by CloudFormation",
            "",
            "**Note**: Always test rollback procedures in a non-production environment first.",
            ""
        ]
        
        return '\n'.join(lines)


if __name__ == "__main__":
    # Example usage
    from .config import ConfigManager
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    orchestrator = Orchestrator(config)
    result = orchestrator.run_conversion(dry_run=True)
    
    print(f"Conversion result: {result['success']}")
    if result['errors']:
        print(f"Errors: {result['errors']}")
    if result['warnings']:
        print(f"Warnings: {result['warnings']}")

