#!/usr/bin/env python3
"""
Command Line Interface for CloudFormation to Terraform Converter

This module provides the main CLI interface for the CF2TF converter tool.
"""

import click
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional
import json
import yaml
from tabulate import tabulate

from .config import ConfigManager, DEFAULT_CONFIG_TEMPLATE
from .discovery import DiscoveryEngine
from .orchestrator import Orchestrator


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0")
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, 
              help='Enable quiet mode (warnings and errors only)')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """
    CloudFormation to Terraform Converter Tool
    
    A comprehensive tool for migrating AWS CloudFormation stacks to Terraform modules
    with automatic resource discovery and import capabilities.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options
    ctx.obj['config_file'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.WARNING)


@cli.command()
@click.option('--regions', '-r', multiple=True,
              help='AWS regions to scan (can be specified multiple times)')
@click.option('--profile', '-p', 
              help='AWS profile to use')
@click.option('--role-arn', 
              help='IAM role ARN to assume for cross-account access')
@click.option('--include-deleted', is_flag=True,
              help='Include deleted CloudFormation stacks in discovery')
@click.option('--stack-filter', 
              help='Filter stacks by name pattern')
@click.option('--output-file', '-o', default='discovery_results.json',
              help='Output file for discovery results')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'table']),
              default='json', help='Output format')
@click.pass_context
def discover(ctx, regions, profile, role_arn, include_deleted, stack_filter, 
             output_file, output_format):
    """
    Discover CloudFormation stacks and AWS resources
    
    This command performs comprehensive discovery of CloudFormation stacks and
    independent AWS resources across specified regions.
    """
    try:
        # Load configuration
        config_manager = ConfigManager()
        cli_args = {
            'regions': list(regions) if regions else None,
            'profile': profile,
            'role_arn': role_arn,
            'include_deleted': include_deleted,
            'stack_filter': stack_filter,
            'verbose': ctx.obj.get('verbose', False),
            'quiet': ctx.obj.get('quiet', False)
        }
        
        config = config_manager.load_config(
            config_file=ctx.obj.get('config_file'),
            cli_args=cli_args
        )
        
        click.echo("Discovering Starting AWS resource discovery...")
        
        # Initialize discovery engine
        discovery = DiscoveryEngine(
            regions=config.discovery.regions,
            profile=config.discovery.profile,
            role_arn=config.discovery.role_arn,
            max_workers=config.discovery.max_workers
        )
        
        # Perform discovery
        stacks, resources = discovery.discover_all(
            include_deleted=config.discovery.include_deleted_stacks,
            stack_name_filter=config.discovery.stack_name_filter
        )
        
        # Get summary
        summary = discovery.get_stack_summary()
        
        # Display results
        click.echo(f"\nSuccess Discovery completed successfully!")
        click.echo(f"    Total stacks: {summary['total_stacks']}")
        click.echo(f"    Total resources: {summary['total_resources']}")
        click.echo(f"   --  CloudFormation managed: {summary['cloudformation_managed']}")
        click.echo(f"    Independent resources: {summary['independent_resources']}")
        click.echo(f"   - Regions scanned: {', '.join(summary['regions_scanned'])}")
        
        # Output results
        if output_format == 'table':
            _display_discovery_table(summary, stacks, resources)
        else:
            discovery.export_discovery_results(output_file)
            click.echo(f"\nFiles: Results exported to: {output_file}")
        
    except Exception as e:
        click.echo(f"Error Discovery failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--regions', '-r', multiple=True,
              help='AWS regions to scan')
@click.option('--profile', '-p', 
              help='AWS profile to use')
@click.option('--role-arn', 
              help='IAM role ARN to assume')
@click.option('--stack-filter', 
              help='Filter stacks by name pattern')
@click.option('--output-dir', '-o', default='./terraform_output',
              help='Output directory for generated Terraform modules')
@click.option('--module-strategy', 
              type=click.Choice(['service_based', 'stack_based', 'lifecycle_based', 'hybrid']),
              help='Module organization strategy')
@click.option('--overwrite', is_flag=True,
              help='Overwrite existing output directory')
@click.option('--dry-run', is_flag=True,
              help='Perform a dry run without generating files')
@click.pass_context
def convert(ctx, regions, profile, role_arn, stack_filter, output_dir, 
            module_strategy, overwrite, dry_run):
    """
    Convert CloudFormation stacks to Terraform modules
    
    This command performs the complete conversion process including discovery,
    conversion, module generation, and import script creation.
    """
    try:
        # Load configuration
        config_manager = ConfigManager()
        cli_args = {
            'regions': list(regions) if regions else None,
            'profile': profile,
            'role_arn': role_arn,
            'stack_filter': stack_filter,
            'output_dir': output_dir,
            'module_strategy': module_strategy,
            'overwrite': overwrite,
            'verbose': ctx.obj.get('verbose', False),
            'quiet': ctx.obj.get('quiet', False)
        }
        
        config = config_manager.load_config(
            config_file=ctx.obj.get('config_file'),
            cli_args=cli_args
        )
        
        if dry_run:
            click.echo("- Performing dry run...")
        
        click.echo("Starting Starting CloudFormation to Terraform conversion...")
        
        # Initialize orchestrator
        orchestrator = Orchestrator(config)
        
        # Run conversion process
        result = orchestrator.run_conversion(dry_run=dry_run)
        
        if result['success']:
            click.echo(f"\nSuccess Conversion completed successfully!")
            click.echo(f"   Directory Output directory: {result['output_directory']}")
            click.echo(f"    Modules generated: {result['modules_count']}")
            click.echo(f"   Files: Files created: {result['files_count']}")
            
            if not dry_run:
                click.echo(f"\n Next steps:")
                click.echo(f"   1. Review generated Terraform modules in {result['output_directory']}")
                click.echo(f"   2. Run import scripts to bring resources under Terraform management")
                click.echo(f"   3. Test with 'terraform plan' to verify configurations")
        else:
            click.echo(f"Error Conversion failed: {result['error']}", err=True)
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error Conversion failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--import-file', '-i', required=True, type=click.Path(exists=True),
              help='Import script file to execute')
@click.option('--terraform-dir', '-d', required=True, type=click.Path(exists=True),
              help='Terraform configuration directory')
@click.option('--parallel', is_flag=True,
              help='Execute imports in parallel')
@click.option('--max-workers', type=int, default=5,
              help='Maximum number of parallel import workers')
@click.option('--dry-run', is_flag=True,
              help='Show import commands without executing them')
@click.pass_context
def import_resources(ctx, import_file, terraform_dir, parallel, max_workers, dry_run):
    """
    Execute Terraform import operations
    
    This command executes the generated import scripts to bring existing
    AWS resources under Terraform management.
    """
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config(config_file=ctx.obj.get('config_file'))
        
        if dry_run:
            click.echo("- Dry run - showing import commands...")
            with open(import_file, 'r') as f:
                click.echo(f.read())
            return
        
        click.echo("Importing Starting Terraform import operations...")
        
        # Import resources using ImportManager
        from .imports import ImportManager
        
        import_manager = ImportManager(
            terraform_dir=terraform_dir,
            parallel=parallel,
            max_workers=max_workers,
            timeout=config.imports.import_timeout,
            retry_failed=config.imports.retry_failed_imports,
            max_retries=config.imports.max_retries
        )
        
        result = import_manager.execute_import_script(import_file)
        
        if result['success']:
            click.echo(f"\nSuccess Import operations completed!")
            click.echo(f"   Success Successful imports: {result['successful_imports']}")
            click.echo(f"   Error Failed imports: {result['failed_imports']}")
            click.echo(f"   --  Total time: {result['total_time']:.2f} seconds")
            
            if result['failed_imports'] > 0:
                click.echo(f"\nWarning  Some imports failed. Check the logs for details.")
        else:
            click.echo(f"Error Import operations failed: {result['error']}", err=True)
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error Import operations failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output-file', '-o', default='cf2tf-config.yaml',
              help='Output configuration file')
@click.option('--format', 'config_format', type=click.Choice(['yaml', 'json']),
              default='yaml', help='Configuration file format')
def init_config(output_file, config_format):
    """
    Generate a default configuration file
    
    This command creates a default configuration file that can be customized
    for your specific environment and requirements.
    """
    try:
        if os.path.exists(output_file):
            if not click.confirm(f"Configuration file {output_file} already exists. Overwrite-"):
                click.echo("Configuration file creation cancelled.")
                return
        
        # Write default configuration
        with open(output_file, 'w') as f:
            if config_format == 'yaml':
                f.write(DEFAULT_CONFIG_TEMPLATE)
            else:
                # Convert YAML template to JSON
                config_dict = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
                json.dump(config_dict, f, indent=2)
        
        click.echo(f"Success Default configuration file created: {output_file}")
        click.echo(f" Edit this file to customize settings for your environment.")
        
    except Exception as e:
        click.echo(f"Error Failed to create configuration file: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def validate_config(ctx):
    """
    Validate configuration file
    
    This command validates the configuration file for syntax and semantic errors.
    """
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config(config_file=ctx.obj.get('config_file'))
        
        click.echo("Success Configuration validation passed!")
        
        # Display configuration summary
        summary = config_manager.get_config_summary()
        click.echo("\n Configuration Summary:")
        for key, value in summary.items():
            click.echo(f"   {key}: {value}")
        
    except Exception as e:
        click.echo(f"Error Configuration validation failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--terraform-dir', '-d', required=True, type=click.Path(exists=True),
              help='Terraform configuration directory')
@click.option('--output-file', '-o', default='validation_report.json',
              help='Output file for validation report')
def validate_terraform(terraform_dir, output_file):
    """
    Validate generated Terraform configurations
    
    This command validates the generated Terraform configurations for syntax
    and basic semantic correctness.
    """
    try:
        click.echo("Discovering Validating Terraform configurations...")
        
        # Import validation logic
        from .validation import TerraformValidator
        
        validator = TerraformValidator(terraform_dir)
        result = validator.validate_all()
        
        if result['valid']:
            click.echo("Success Terraform validation passed!")
            click.echo(f"   Directory Modules validated: {result['modules_count']}")
            click.echo(f"   Files: Files validated: {result['files_count']}")
        else:
            click.echo("Error Terraform validation failed!")
            click.echo(f"   Error Errors found: {result['error_count']}")
            click.echo(f"   Warning  Warnings found: {result['warning_count']}")
        
        # Export detailed report
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        click.echo(f"\nFiles: Detailed validation report: {output_file}")
        
    except Exception as e:
        click.echo(f"Error Terraform validation failed: {str(e)}", err=True)
        sys.exit(1)


def _display_discovery_table(summary, stacks, resources):
    """Display discovery results in table format"""
    
    # Stack summary table
    click.echo("\n Stack Summary:")
    stack_data = []
    for status, count in summary['stack_statuses'].items():
        stack_data.append([status, count])
    
    if stack_data:
        click.echo(tabulate(stack_data, headers=['Status', 'Count'], tablefmt='grid'))
    
    # Resource type summary table
    click.echo("\n Resource Type Summary:")
    resource_data = []
    for resource_type, count in sorted(summary['resource_types'].items()):
        resource_data.append([resource_type, count])
    
    if resource_data:
        # Show top 20 resource types
        click.echo(tabulate(resource_data[:20], headers=['Resource Type', 'Count'], tablefmt='grid'))
        if len(resource_data) > 20:
            click.echo(f"... and {len(resource_data) - 20} more resource types")
    
    # Individual stacks table
    if len(stacks) <= 10:  # Only show details for small number of stacks
        click.echo("\n--  Stack Details:")
        stack_details = []
        for stack in stacks.values():
            stack_details.append([
                stack.stack_name,
                stack.stack_status,
                len(stack.resources),
                stack.creation_time[:10]  # Just the date part
            ])
        
        if stack_details:
            click.echo(tabulate(stack_details, 
                              headers=['Stack Name', 'Status', 'Resources', 'Created'], 
                              tablefmt='grid'))


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nWarning  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error Unexpected error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

