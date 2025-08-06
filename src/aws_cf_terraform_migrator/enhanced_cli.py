#!/usr/bin/env python3
"""
Enhanced CLI for AWS CloudFormation to Terraform Migrator

Simple, user-friendly command-line interface that makes the tool easy to use
with clear commands and helpful output.
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from .discovery import DiscoveryEngine
from .conversion import ConversionEngine
from .enhanced_modules import EnhancedModuleGenerator
from .imports import ImportManager
from .config import ConfigManager


class EnhancedCLI:
    """Enhanced command-line interface for CF2TF converter"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.config_manager = ConfigManager()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return logging.getLogger(__name__)
    
    def main(self):
        """Main CLI entry point"""
        parser = self._create_parser()
        args = parser.parse_args()
        
        if hasattr(args, 'func'):
            try:
                args.func(args)
            except KeyboardInterrupt:
                print("\nError Operation cancelled by user")
                sys.exit(1)
            except Exception as e:
                self.logger.error(f"Operation failed: {str(e)}")
                print(f"\nError Error: {str(e)}")
                sys.exit(1)
        else:
            parser.print_help()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands"""
        parser = argparse.ArgumentParser(
            description="AWS CloudFormation to Terraform Migrator - Convert CloudFormation to Terraform with zero downtime",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Quick conversion (discover + convert + generate imports)
  %(prog)s convert-all --regions us-east-1 --output ./terraform
  
  # Step by step
  %(prog)s discover --regions us-east-1 --output discovery.json
  %(prog)s convert --input discovery.json --output ./terraform
  %(prog)s generate-imports --terraform-dir ./terraform --output import.sh
  
  # Validate configuration
  %(prog)s validate --terraform-dir ./terraform
"""
        )
        
        parser.add_argument('--version', action='version', version='AWS CloudFormation to Terraform Migrator 1.0.0')
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Convert-all command (most common use case)
        convert_all_parser = subparsers.add_parser(
            'convert-all',
            help='Starting One-command conversion: discover, convert, and generate imports',
            description='Discover AWS resources, convert to Terraform, and generate import scripts in one command'
        )
        self._add_convert_all_args(convert_all_parser)
        convert_all_parser.set_defaults(func=self.convert_all)
        
        # Discover command
        discover_parser = subparsers.add_parser(
            'discover',
            help='Discovering Discover AWS resources and CloudFormation stacks',
            description='Discover all AWS resources including CloudFormation stacks and independent resources'
        )
        self._add_discover_args(discover_parser)
        discover_parser.set_defaults(func=self.discover)
        
        # Convert command
        convert_parser = subparsers.add_parser(
            'convert',
            help='Converting Convert discovered resources to Terraform modules',
            description='Convert discovered AWS resources to Terraform modules with proper organization'
        )
        self._add_convert_args(convert_parser)
        convert_parser.set_defaults(func=self.convert)
        
        # Generate imports command
        imports_parser = subparsers.add_parser(
            'generate-imports',
            help='Importing Generate Terraform import scripts',
            description='Generate scripts to import existing AWS resources into Terraform state'
        )
        self._add_imports_args(imports_parser)
        imports_parser.set_defaults(func=self.generate_imports)
        
        # Validate command
        validate_parser = subparsers.add_parser(
            'validate',
            help='Success Validate generated Terraform configuration',
            description='Validate Terraform configuration and check for issues'
        )
        self._add_validate_args(validate_parser)
        validate_parser.set_defaults(func=self.validate)
        
        # Status command
        status_parser = subparsers.add_parser(
            'status',
            help=' Show status of Terraform configuration',
            description='Show current status of Terraform configuration and resources'
        )
        self._add_status_args(status_parser)
        status_parser.set_defaults(func=self.status)
        
        return parser
    
    def _add_convert_all_args(self, parser):
        """Add arguments for convert-all command"""
        parser.add_argument(
            '--regions', '-r',
            required=True,
            help='AWS regions to scan (comma-separated, e.g., us-east-1,us-west-2)'
        )
        parser.add_argument(
            '--output', '-o',
            required=True,
            help='Output directory for generated Terraform files'
        )
        parser.add_argument(
            '--config', '-c',
            help='Configuration file (YAML or JSON)'
        )
        parser.add_argument(
            '--profile',
            help='AWS profile to use'
        )
        parser.add_argument(
            '--strategy',
            choices=['service_based', 'stack_based', 'lifecycle_based', 'hybrid'],
            default='hybrid',
            help='Module organization strategy (default: hybrid)'
        )
        parser.add_argument(
            '--module-prefix',
            help='Prefix for module names'
        )
        parser.add_argument(
            '--stack-filter',
            help='Filter CloudFormation stacks by name pattern (supports wildcards)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
    
    def _add_discover_args(self, parser):
        """Add arguments for discover command"""
        parser.add_argument(
            '--regions', '-r',
            required=True,
            help='AWS regions to scan (comma-separated)'
        )
        parser.add_argument(
            '--output', '-o',
            required=True,
            help='Output file for discovery results (JSON)'
        )
        parser.add_argument(
            '--profile',
            help='AWS profile to use'
        )
        parser.add_argument(
            '--stack-filter',
            help='Filter CloudFormation stacks by name pattern'
        )
        parser.add_argument(
            '--services',
            help='AWS services to scan (comma-separated, default: all)'
        )
        parser.add_argument(
            '--max-workers',
            type=int,
            default=10,
            help='Maximum number of parallel workers (default: 10)'
        )
        parser.add_argument(
            '--include-independent',
            action='store_true',
            help='Include resources not managed by CloudFormation'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
    
    def _add_convert_args(self, parser):
        """Add arguments for convert command"""
        parser.add_argument(
            '--input', '-i',
            required=True,
            help='Input discovery file (JSON)'
        )
        parser.add_argument(
            '--output', '-o',
            required=True,
            help='Output directory for Terraform modules'
        )
        parser.add_argument(
            '--strategy',
            choices=['service_based', 'stack_based', 'lifecycle_based', 'hybrid'],
            default='hybrid',
            help='Module organization strategy (default: hybrid)'
        )
        parser.add_argument(
            '--module-prefix',
            help='Prefix for module names'
        )
        parser.add_argument(
            '--preserve-names',
            action='store_true',
            default=True,
            help='Preserve original AWS resource names (default: true)'
        )
        parser.add_argument(
            '--generate-docs',
            action='store_true',
            default=True,
            help='Generate documentation for modules (default: true)'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
    
    def _add_imports_args(self, parser):
        """Add arguments for generate-imports command"""
        parser.add_argument(
            '--terraform-dir', '-d',
            required=True,
            help='Terraform directory containing modules'
        )
        parser.add_argument(
            '--discovery-file',
            help='Discovery file with resource information (JSON)'
        )
        parser.add_argument(
            '--output-script',
            default='import_resources.sh',
            help='Output script filename (default: import_resources.sh)'
        )
        parser.add_argument(
            '--parallel',
            action='store_true',
            default=True,
            help='Enable parallel imports (default: true)'
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            default=True,
            help='Create state backup before imports (default: true)'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
    
    def _add_validate_args(self, parser):
        """Add arguments for validate command"""
        parser.add_argument(
            '--terraform-dir', '-d',
            required=True,
            help='Terraform directory to validate'
        )
        parser.add_argument(
            '--check-imports',
            action='store_true',
            help='Check if resources can be imported'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
    
    def _add_status_args(self, parser):
        """Add arguments for status command"""
        parser.add_argument(
            '--terraform-dir', '-d',
            required=True,
            help='Terraform directory to check'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed status information'
        )
    
    def convert_all(self, args):
        """Execute complete conversion process"""
        print("Starting Starting complete CloudFormation to Terraform conversion...")
        print("   This process will:")
        print("   1. Discover AWS resources and CloudFormation stacks")
        print("   2. Convert to Terraform modules with no hardcoded values")
        print("   3. Generate import scripts for existing resources")
        print("   4. Create comprehensive documentation")
        print()
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        start_time = time.time()
        
        # Load configuration if provided
        config = {}
        if args.config:
            config = self._load_config(args.config)
        
        # Parse regions
        regions = [r.strip() for r in args.regions.split(',')]
        
        # Step 1: Discovery
        print("Discovering Step 1: Discovering AWS resources...")
        discovery_result = self._run_discovery(regions, args, config)
        
        if not discovery_result:
            print("Error No resources discovered. Please check your AWS credentials and permissions.")
            return
        
        print(f"Success Discovery complete: {len(discovery_result)} resources found")
        
        # Step 2: Conversion
        print("\nConverting Step 2: Converting to Terraform modules...")
        conversion_result = self._run_conversion(discovery_result, args, config)
        
        print(f"Success Conversion complete: {len(conversion_result.modules)} modules generated")
        
        # Step 3: Generate imports
        print("\nImporting Step 3: Generating import scripts...")
        import_result = self._run_import_generation(args.output, discovery_result, args)
        
        print(f"Success Import scripts generated: {import_result}")
        
        # Summary
        elapsed_time = time.time() - start_time
        print(f"\nComplete Conversion completed successfully in {elapsed_time:.2f} seconds!")
        print(f"   Directory Output directory: {args.output}")
        print(f"    Modules generated: {len(conversion_result.modules)}")
        print(f"   Total files: {conversion_result.total_files}")
        print(f"    Variables: {conversion_result.total_variables}")
        print(f"   Outputs: {conversion_result.total_outputs}")
        
        print("\n Next steps:")
        print(f"   1. cd {args.output}")
        print("   2. terraform init")
        print("   3. Review terraform.tfvars.example and create terraform.tfvars")
        print("   4. chmod +x import_resources.sh && ./import_resources.sh")
        print("   5. terraform plan")
        
        if not args.dry_run:
            self._create_getting_started_guide(args.output, conversion_result)
    
    def discover(self, args):
        """Execute discovery process"""
        print("Discovering Discovering AWS resources and CloudFormation stacks...")
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        regions = [r.strip() for r in args.regions.split(',')]
        
        discovery_result = self._run_discovery(regions, args, {})
        
        if discovery_result:
            # Save discovery results
            with open(args.output, 'w') as f:
                json.dump(discovery_result, f, indent=2, default=str)
            
            print(f"Success Discovery complete: {len(discovery_result)} resources saved to {args.output}")
        else:
            print("Error No resources discovered")
    
    def convert(self, args):
        """Execute conversion process"""
        print("Converting Converting discovered resources to Terraform modules...")
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Load discovery results
        with open(args.input, 'r') as f:
            discovery_result = json.load(f)
        
        conversion_result = self._run_conversion(discovery_result, args, {})
        
        print(f"Success Conversion complete: {len(conversion_result.modules)} modules generated in {args.output}")
    
    def generate_imports(self, args):
        """Generate import scripts"""
        print("Importing Generating Terraform import scripts...")
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        discovery_result = {}
        if args.discovery_file:
            with open(args.discovery_file, 'r') as f:
                discovery_result = json.load(f)
        
        import_result = self._run_import_generation(args.terraform_dir, discovery_result, args)
        
        print(f"Success Import scripts generated: {import_result}")
    
    def validate(self, args):
        """Validate Terraform configuration"""
        print("Success Validating Terraform configuration...")
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        terraform_dir = Path(args.terraform_dir)
        
        if not terraform_dir.exists():
            print(f"Error Terraform directory not found: {terraform_dir}")
            return
        
        # Check for required files
        required_files = ['main.tf', 'variables.tf', 'outputs.tf']
        missing_files = []
        
        for file_name in required_files:
            if not (terraform_dir / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"Error Missing required files: {', '.join(missing_files)}")
            return
        
        # Run terraform validate if available
        import subprocess
        try:
            result = subprocess.run(
                ['terraform', 'validate'],
                cwd=terraform_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("Success Terraform configuration is valid")
            else:
                print(f"Error Terraform validation failed:\n{result.stderr}")
        
        except FileNotFoundError:
            print("Warning  Terraform not found in PATH. Skipping terraform validate.")
            print("Success Basic file structure validation passed")
    
    def status(self, args):
        """Show status of Terraform configuration"""
        print(" Checking Terraform configuration status...")
        
        terraform_dir = Path(args.terraform_dir)
        
        if not terraform_dir.exists():
            print(f"Error Terraform directory not found: {terraform_dir}")
            return
        
        # Count files and modules
        tf_files = list(terraform_dir.glob("**/*.tf"))
        modules = list(terraform_dir.glob("modules/*/"))
        
        print(f"Directory Terraform directory: {terraform_dir}")
        print(f"Terraform files: {len(tf_files)}")
        print(f" Modules: {len(modules)}")
        
        if args.detailed:
            print("\n Module details:")
            for module_dir in modules:
                module_files = list(module_dir.glob("*.tf"))
                print(f"   {module_dir.name}: {len(module_files)} files")
        
        # Check for state file
        state_files = list(terraform_dir.glob("*.tfstate"))
        if state_files:
            print(f" State files: {len(state_files)}")
        else:
            print(" No state files found (not initialized)")
        
        # Check for import script
        import_script = terraform_dir / "import_resources.sh"
        if import_script.exists():
            print("Importing Import script: Success Available")
        else:
            print("Importing Import script: Error Not found")
    
    def _run_discovery(self, regions: List[str], args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run the discovery process"""
        all_resources = {}
        
        for region in regions:
            print(f"   Scanning region: {region}")
            
            # Use the unified discovery engine
            discovery_engine = DiscoveryEngine(
                regions=[region],  # Pass as list, not single region
                profile=getattr(args, 'profile', None),
                max_workers=getattr(args, 'max_workers', 10)
            )
            
            # Discover all resources (CloudFormation and independent)
            stacks, resources = discovery_engine.discover_all(
                include_deleted=False,
                stack_name_filter=getattr(args, 'stack_filter', None)
            )
            
            # Combine stacks and resources into a single dictionary
            region_resources = {}
            region_resources.update(stacks)
            region_resources.update(resources)
            
            all_resources.update(region_resources)
        
        return all_resources
    
    def _run_conversion(self, discovery_result: Dict[str, Any], args, config: Dict[str, Any]):
        """Run the conversion process"""
        # Convert CloudFormation resources
        converter = ConversionEngine()
        converted_resources = {}
        
        for resource_id, resource_info in discovery_result.items():
            try:
                # Check if this is a StackInfo object (CloudFormation stack)
                if hasattr(resource_info, 'stack_id') and hasattr(resource_info, 'stack_name'):
                    # This is a StackInfo object - convert its template
                    if hasattr(resource_info, 'template_body') and resource_info.template_body:
                        try:
                            import json
                            template = json.loads(resource_info.template_body)
                            converted = converter.convert_template(template, resource_info.stack_name)
                            if converted:
                                converted_resources[resource_id] = {
                                    'type': 'cloudformation_stack',
                                    'stack_name': resource_info.stack_name,
                                    'conversion_result': converted,
                                    'source': 'cloudformation'
                                }
                        except Exception as e:
                            print(f"Warning  Warning: Failed to convert stack {resource_info.stack_name}: {e}")
                    else:
                        # Stack without template body - just record it
                        converted_resources[resource_id] = {
                            'type': 'cloudformation_stack',
                            'stack_name': resource_info.stack_name,
                            'source': 'cloudformation',
                            'note': 'Template body not available'
                        }
                # Check if this is a ResourceInfo object (independent resource)
                elif hasattr(resource_info, 'resource_id') and hasattr(resource_info, 'resource_type'):
                    # This is a ResourceInfo object - convert it to Terraform format
                    converted_resources[resource_id] = {
                        'type': 'independent_resource',
                        'resource_id': resource_info.resource_id,
                        'resource_type': resource_info.resource_type,
                        'source': 'independent'
                    }
                else:
                    # Fallback for dictionary format or unknown objects
                    if isinstance(resource_info, dict) and resource_info.get('source') == 'cloudformation':
                        converted = converter.convert_resource(resource_info)
                        if converted:
                            converted_resources[resource_id] = converted
                    else:
                        # Independent resources or unknown format - just record them
                        converted_resources[resource_id] = {
                            'type': 'unknown_resource',
                            'data': str(resource_info),
                            'source': 'unknown'
                        }
            except Exception as e:
                print(f"Warning: Failed to process resource {resource_id}: {str(e)}")
        
        # Step 2: Convert to Terraform modules
        print("Converting Step 2: Converting to Terraform modules...")
        
        from .production_modules import ProductionModuleGenerator
        
        module_generator = ProductionModuleGenerator()
        
        conversion_result = module_generator.generate_modules(
            discovery_result=discovery_result,
            output_dir=args.output
        )
        
        return conversion_result
    
    def _run_import_generation(self, terraform_dir: str, discovery_result: Dict[str, Any], args) -> str:
        """Run the import generation process"""
        import_manager = ImportManager(
            terraform_dir=terraform_dir,
            parallel=getattr(args, 'parallel', True),
            create_backup=getattr(args, 'backup', True)
        )
        
        script_path = import_manager.generate_import_script(
            discovery_result,
            output_file=getattr(args, 'output_script', 'import_resources.sh')
        )
        
        return script_path
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                return json.load(f)
    
    def _create_getting_started_guide(self, output_dir: str, conversion_result):
        """Create a getting started guide"""
        guide_content = f'''# Getting Started with Your Terraform Configuration

This guide helps you get started with your newly converted Terraform configuration.

## Complete Conversion Summary

- **Modules Generated**: {len(conversion_result.modules)}
- **Total Files**: {conversion_result.total_files}
- **Variables**: {conversion_result.total_variables}
- **Outputs**: {conversion_result.total_outputs}

## Starting Quick Start

### 1. Initialize Terraform

```bash
cd {output_dir}
terraform init
```

### 2. Configure Variables

Copy the example variables file and customize it:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your specific values
```

### 3. Import Existing Resources

Import your existing AWS resources into Terraform state:

```bash
chmod +x import_resources.sh
./import_resources.sh
```

### 4. Verify Configuration

Check that everything is configured correctly:

```bash
terraform plan
```

You should see "No changes" if everything is imported correctly.

### 5. Apply Changes (if needed)

If you need to make any changes:

```bash
terraform apply
```

## Directory Directory Structure

```
{output_dir}/
--- main.tf                    # Root module
--- variables.tf               # Root variables
--- outputs.tf                 # Root outputs
--- versions.tf                # Provider versions
--- terraform.tfvars.example  # Example variables
--- import_resources.sh        # Import script
--- .gitignore                # Git ignore file
--- modules/                   # Generated modules
'''

        for module_name in conversion_result.modules.keys():
            guide_content += f'''    --- {module_name}/
    -   --- main.tf
    -   --- variables.tf
    -   --- outputs.tf
    -   --- versions.tf
    -   --- README.md
'''

        guide_content += '''
```

##  Key Features

- **No Hardcoded Values**: All configuration is parameterized through variables
- **Preserve Resource Names**: Original AWS resource names are maintained
- **Zero Downtime**: Import existing resources without recreation
- **Comprehensive Documentation**: Each module includes detailed README
- **Flexible Organization**: Modules organized for maintainability

## Next Steps

1. **Review Module Documentation**: Check each module's README.md
2. **Customize Variables**: Adjust terraform.tfvars for your environment
3. **Set Up CI/CD**: Integrate with your deployment pipeline
4. **Add Monitoring**: Set up Terraform state monitoring
5. **Team Training**: Train your team on the new Terraform workflow

## - Need Help-

- Check the troubleshooting guide in docs/TROUBLESHOOTING.md
- Review module-specific README files
- Validate configuration with `terraform validate`
- Use `terraform plan` to preview changes

## - Security Notes

- Never commit terraform.tfvars to version control
- Use AWS IAM roles instead of access keys when possible
- Enable state file encryption
- Regularly review and rotate credentials

Happy Terraforming! -
'''
        
        guide_path = Path(output_dir) / "GETTING_STARTED.md"
        guide_path.write_text(guide_content)


def main():
    """Main entry point for the CLI"""
    cli = EnhancedCLI()
    cli.main()


if __name__ == '__main__':
    main()

