#!/usr/bin/env python3
"""
Configuration Management Module

This module handles configuration loading, validation, and management for the
CloudFormation to Terraform converter tool.
"""

import os
import yaml
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryConfig:
    """Configuration for resource discovery"""
    regions: List[str] = field(default_factory=lambda: ['us-east-1'])
    profile: Optional[str] = None
    role_arn: Optional[str] = None
    include_deleted_stacks: bool = False
    stack_name_filter: Optional[str] = None
    max_workers: int = 10
    services_to_scan: List[str] = field(default_factory=lambda: [
        'ec2', 's3', 'rds', 'lambda', 'iam', 'dynamodb',
        'elasticache', 'elbv2', 'elb', 'autoscaling',
        'route53', 'cloudfront', 'apigateway', 'sns', 'sqs'
    ])


@dataclass
class ConversionConfig:
    """Configuration for CloudFormation to Terraform conversion"""
    preserve_original_names: bool = True
    add_import_blocks: bool = True
    generate_variables: bool = True
    generate_outputs: bool = True
    handle_intrinsic_functions: bool = True
    convert_conditions: bool = True
    terraform_version: str = ">=1.0"
    provider_version: str = ">=5.0"


@dataclass
class ModuleConfig:
    """Configuration for Terraform module generation"""
    organization_strategy: str = "service_based"  # service_based, stack_based, lifecycle_based, hybrid
    module_prefix: str = ""
    include_examples: bool = True
    include_readme: bool = True
    include_versions_tf: bool = True
    variable_descriptions: bool = True
    output_descriptions: bool = True
    use_locals: bool = True
    group_similar_resources: bool = True


@dataclass
class ImportConfig:
    """Configuration for Terraform import operations"""
    generate_import_scripts: bool = True
    validate_imports: bool = True
    create_backup: bool = True
    parallel_imports: bool = False
    max_import_workers: int = 5
    import_timeout: int = 300  # seconds
    retry_failed_imports: bool = True
    max_retries: int = 3


@dataclass
class OutputConfig:
    """Configuration for output generation"""
    output_directory: str = "./terraform_output"
    create_subdirectories: bool = True
    overwrite_existing: bool = False
    generate_documentation: bool = True
    export_discovery_data: bool = True
    export_format: str = "json"  # json, yaml
    include_metadata: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    console: bool = True
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class ToolConfig:
    """Main configuration class for the CF2TF converter tool"""
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    conversion: ConversionConfig = field(default_factory=ConversionConfig)
    modules: ModuleConfig = field(default_factory=ModuleConfig)
    imports: ImportConfig = field(default_factory=ImportConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigManager:
    """Configuration manager for the CF2TF converter tool"""
    
    # JSON Schema for configuration validation
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "discovery": {
                "type": "object",
                "properties": {
                    "regions": {"type": "array", "items": {"type": "string"}},
                    "profile": {"type": ["string", "null"]},
                    "role_arn": {"type": ["string", "null"]},
                    "include_deleted_stacks": {"type": "boolean"},
                    "stack_name_filter": {"type": ["string", "null"]},
                    "max_workers": {"type": "integer", "minimum": 1, "maximum": 50},
                    "services_to_scan": {"type": "array", "items": {"type": "string"}}
                }
            },
            "conversion": {
                "type": "object",
                "properties": {
                    "preserve_original_names": {"type": "boolean"},
                    "add_import_blocks": {"type": "boolean"},
                    "generate_variables": {"type": "boolean"},
                    "generate_outputs": {"type": "boolean"},
                    "handle_intrinsic_functions": {"type": "boolean"},
                    "convert_conditions": {"type": "boolean"},
                    "terraform_version": {"type": "string"},
                    "provider_version": {"type": "string"}
                }
            },
            "modules": {
                "type": "object",
                "properties": {
                    "organization_strategy": {
                        "type": "string",
                        "enum": ["service_based", "stack_based", "lifecycle_based", "hybrid"]
                    },
                    "module_prefix": {"type": "string"},
                    "include_examples": {"type": "boolean"},
                    "include_readme": {"type": "boolean"},
                    "include_versions_tf": {"type": "boolean"},
                    "variable_descriptions": {"type": "boolean"},
                    "output_descriptions": {"type": "boolean"},
                    "use_locals": {"type": "boolean"},
                    "group_similar_resources": {"type": "boolean"}
                }
            },
            "imports": {
                "type": "object",
                "properties": {
                    "generate_import_scripts": {"type": "boolean"},
                    "validate_imports": {"type": "boolean"},
                    "create_backup": {"type": "boolean"},
                    "parallel_imports": {"type": "boolean"},
                    "max_import_workers": {"type": "integer", "minimum": 1, "maximum": 20},
                    "import_timeout": {"type": "integer", "minimum": 30},
                    "retry_failed_imports": {"type": "boolean"},
                    "max_retries": {"type": "integer", "minimum": 1, "maximum": 10}
                }
            },
            "output": {
                "type": "object",
                "properties": {
                    "output_directory": {"type": "string"},
                    "create_subdirectories": {"type": "boolean"},
                    "overwrite_existing": {"type": "boolean"},
                    "generate_documentation": {"type": "boolean"},
                    "export_discovery_data": {"type": "boolean"},
                    "export_format": {"type": "string", "enum": ["json", "yaml"]},
                    "include_metadata": {"type": "boolean"}
                }
            },
            "logging": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                    },
                    "format": {"type": "string"},
                    "file": {"type": ["string", "null"]},
                    "console": {"type": "boolean"},
                    "max_file_size": {"type": "integer", "minimum": 1024},
                    "backup_count": {"type": "integer", "minimum": 1}
                }
            }
        }
    }
    
    def __init__(self):
        self.config = ToolConfig()
        self._config_sources = []
    
    def load_config(self, 
                   config_file: Optional[str] = None,
                   cli_args: Optional[Dict[str, Any]] = None,
                   env_vars: bool = True) -> ToolConfig:
        """
        Load configuration from multiple sources with precedence:
        1. CLI arguments (highest priority)
        2. Environment variables
        3. Configuration file
        4. Default values (lowest priority)
        """
        logger.info("Loading configuration")
        
        # Start with default configuration
        self.config = ToolConfig()
        self._config_sources.append("defaults")
        
        # Load from configuration file
        if config_file:
            self._load_from_file(config_file)
        else:
            # Try to find default config files
            default_locations = [
                './cf2tf-config.yaml',
                './cf2tf-config.yml',
                './config/cf2tf-config.yaml',
                '~/.cf2tf/config.yaml',
                '/etc/cf2tf/config.yaml'
            ]
            
            for location in default_locations:
                expanded_path = os.path.expanduser(location)
                if os.path.exists(expanded_path):
                    self._load_from_file(expanded_path)
                    break
        
        # Load from environment variables
        if env_vars:
            self._load_from_env()
        
        # Apply CLI arguments
        if cli_args:
            self._apply_cli_args(cli_args)
        
        # Validate final configuration
        self._validate_config()
        
        logger.info(f"Configuration loaded from sources: {', '.join(self._config_sources)}")
        return self.config
    
    def _load_from_file(self, config_file: str):
        """Load configuration from YAML or JSON file"""
        try:
            config_path = Path(config_file).expanduser()
            if not config_path.exists():
                logger.warning(f"Configuration file not found: {config_file}")
                return
            
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    logger.warning(f"Unsupported configuration file format: {config_path.suffix}")
                    return
            
            if file_config:
                self._merge_config(file_config)
                self._config_sources.append(f"file:{config_file}")
                logger.info(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {str(e)}")
            raise
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        env_config = {}
        env_loaded = False
        
        # Discovery configuration
        if os.getenv('CF2TF_REGIONS'):
            env_config.setdefault('discovery', {})['regions'] = os.getenv('CF2TF_REGIONS').split(',')
            env_loaded = True
        
        if os.getenv('CF2TF_PROFILE'):
            env_config.setdefault('discovery', {})['profile'] = os.getenv('CF2TF_PROFILE')
            env_loaded = True
        
        if os.getenv('CF2TF_ROLE_ARN'):
            env_config.setdefault('discovery', {})['role_arn'] = os.getenv('CF2TF_ROLE_ARN')
            env_loaded = True
        
        if os.getenv('CF2TF_MAX_WORKERS'):
            env_config.setdefault('discovery', {})['max_workers'] = int(os.getenv('CF2TF_MAX_WORKERS'))
            env_loaded = True
        
        # Output configuration
        if os.getenv('CF2TF_OUTPUT_DIR'):
            env_config.setdefault('output', {})['output_directory'] = os.getenv('CF2TF_OUTPUT_DIR')
            env_loaded = True
        
        if os.getenv('CF2TF_OVERWRITE'):
            env_config.setdefault('output', {})['overwrite_existing'] = os.getenv('CF2TF_OVERWRITE').lower() == 'true'
            env_loaded = True
        
        # Module configuration
        if os.getenv('CF2TF_MODULE_STRATEGY'):
            env_config.setdefault('modules', {})['organization_strategy'] = os.getenv('CF2TF_MODULE_STRATEGY')
            env_loaded = True
        
        # Logging configuration
        if os.getenv('CF2TF_LOG_LEVEL'):
            env_config.setdefault('logging', {})['level'] = os.getenv('CF2TF_LOG_LEVEL')
            env_loaded = True
        
        if os.getenv('CF2TF_LOG_FILE'):
            env_config.setdefault('logging', {})['file'] = os.getenv('CF2TF_LOG_FILE')
            env_loaded = True
        
        if env_config:
            self._merge_config(env_config)
            self._config_sources.append("environment")
            logger.debug("Loaded configuration from environment variables")
    
    def _apply_cli_args(self, cli_args: Dict[str, Any]):
        """Apply CLI arguments to configuration"""
        if not cli_args:
            return
        
        # Map CLI arguments to configuration structure
        cli_config = {}
        
        # Discovery arguments
        if 'regions' in cli_args and cli_args['regions']:
            cli_config.setdefault('discovery', {})['regions'] = cli_args['regions']
        
        if 'profile' in cli_args and cli_args['profile']:
            cli_config.setdefault('discovery', {})['profile'] = cli_args['profile']
        
        if 'role_arn' in cli_args and cli_args['role_arn']:
            cli_config.setdefault('discovery', {})['role_arn'] = cli_args['role_arn']
        
        if 'include_deleted' in cli_args:
            cli_config.setdefault('discovery', {})['include_deleted_stacks'] = cli_args['include_deleted']
        
        if 'stack_filter' in cli_args and cli_args['stack_filter']:
            cli_config.setdefault('discovery', {})['stack_name_filter'] = cli_args['stack_filter']
        
        # Output arguments
        if 'output_dir' in cli_args and cli_args['output_dir']:
            cli_config.setdefault('output', {})['output_directory'] = cli_args['output_dir']
        
        if 'overwrite' in cli_args:
            cli_config.setdefault('output', {})['overwrite_existing'] = cli_args['overwrite']
        
        # Module arguments
        if 'module_strategy' in cli_args and cli_args['module_strategy']:
            cli_config.setdefault('modules', {})['organization_strategy'] = cli_args['module_strategy']
        
        # Logging arguments
        if 'verbose' in cli_args and cli_args['verbose']:
            cli_config.setdefault('logging', {})['level'] = 'DEBUG'
        elif 'quiet' in cli_args and cli_args['quiet']:
            cli_config.setdefault('logging', {})['level'] = 'WARNING'
        
        if cli_config:
            self._merge_config(cli_config)
            self._config_sources.append("cli_args")
            logger.debug("Applied CLI arguments to configuration")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration into existing configuration"""
        def merge_dict(base: Dict, update: Dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        # Convert current config to dict for merging
        config_dict = self._config_to_dict()
        
        # Merge new configuration
        merge_dict(config_dict, new_config)
        
        # Convert back to dataclass
        self.config = self._dict_to_config(config_dict)
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert configuration dataclass to dictionary"""
        return {
            'discovery': {
                'regions': self.config.discovery.regions,
                'profile': self.config.discovery.profile,
                'role_arn': self.config.discovery.role_arn,
                'include_deleted_stacks': self.config.discovery.include_deleted_stacks,
                'stack_name_filter': self.config.discovery.stack_name_filter,
                'max_workers': self.config.discovery.max_workers,
                'services_to_scan': self.config.discovery.services_to_scan
            },
            'conversion': {
                'preserve_original_names': self.config.conversion.preserve_original_names,
                'add_import_blocks': self.config.conversion.add_import_blocks,
                'generate_variables': self.config.conversion.generate_variables,
                'generate_outputs': self.config.conversion.generate_outputs,
                'handle_intrinsic_functions': self.config.conversion.handle_intrinsic_functions,
                'convert_conditions': self.config.conversion.convert_conditions,
                'terraform_version': self.config.conversion.terraform_version,
                'provider_version': self.config.conversion.provider_version
            },
            'modules': {
                'organization_strategy': self.config.modules.organization_strategy,
                'module_prefix': self.config.modules.module_prefix,
                'include_examples': self.config.modules.include_examples,
                'include_readme': self.config.modules.include_readme,
                'include_versions_tf': self.config.modules.include_versions_tf,
                'variable_descriptions': self.config.modules.variable_descriptions,
                'output_descriptions': self.config.modules.output_descriptions,
                'use_locals': self.config.modules.use_locals,
                'group_similar_resources': self.config.modules.group_similar_resources
            },
            'imports': {
                'generate_import_scripts': self.config.imports.generate_import_scripts,
                'validate_imports': self.config.imports.validate_imports,
                'create_backup': self.config.imports.create_backup,
                'parallel_imports': self.config.imports.parallel_imports,
                'max_import_workers': self.config.imports.max_import_workers,
                'import_timeout': self.config.imports.import_timeout,
                'retry_failed_imports': self.config.imports.retry_failed_imports,
                'max_retries': self.config.imports.max_retries
            },
            'output': {
                'output_directory': self.config.output.output_directory,
                'create_subdirectories': self.config.output.create_subdirectories,
                'overwrite_existing': self.config.output.overwrite_existing,
                'generate_documentation': self.config.output.generate_documentation,
                'export_discovery_data': self.config.output.export_discovery_data,
                'export_format': self.config.output.export_format,
                'include_metadata': self.config.output.include_metadata
            },
            'logging': {
                'level': self.config.logging.level,
                'format': self.config.logging.format,
                'file': self.config.logging.file,
                'console': self.config.logging.console,
                'max_file_size': self.config.logging.max_file_size,
                'backup_count': self.config.logging.backup_count
            }
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> ToolConfig:
        """Convert dictionary to configuration dataclass"""
        return ToolConfig(
            discovery=DiscoveryConfig(**config_dict.get('discovery', {})),
            conversion=ConversionConfig(**config_dict.get('conversion', {})),
            modules=ModuleConfig(**config_dict.get('modules', {})),
            imports=ImportConfig(**config_dict.get('imports', {})),
            output=OutputConfig(**config_dict.get('output', {})),
            logging=LoggingConfig(**config_dict.get('logging', {}))
        )
    
    def _validate_config(self):
        """Validate configuration against schema"""
        try:
            config_dict = self._config_to_dict()
            validate(instance=config_dict, schema=self.CONFIG_SCHEMA)
            logger.debug("Configuration validation passed")
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e.message}")
            raise ValueError(f"Invalid configuration: {e.message}")
    
    def save_config(self, output_file: str, format: str = 'yaml'):
        """Save current configuration to file"""
        config_dict = self._config_to_dict()
        
        try:
            with open(output_file, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(config_dict, f, indent=2)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Configuration saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            'sources': self._config_sources,
            'discovery_regions': self.config.discovery.regions,
            'output_directory': self.config.output.output_directory,
            'module_strategy': self.config.modules.organization_strategy,
            'logging_level': self.config.logging.level,
            'max_workers': self.config.discovery.max_workers
        }


# Default configuration template
DEFAULT_CONFIG_TEMPLATE = """
# CloudFormation to Terraform Converter Configuration

discovery:
  regions:
    - us-east-1
    - us-west-2
  profile: null  # AWS profile to use
  role_arn: null  # IAM role to assume
  include_deleted_stacks: false
  stack_name_filter: null  # Filter stacks by name pattern
  max_workers: 10
  services_to_scan:
    - ec2
    - s3
    - rds
    - lambda
    - iam
    - dynamodb
    - elasticache
    - elbv2
    - elb
    - autoscaling
    - route53
    - cloudfront
    - apigateway
    - sns
    - sqs

conversion:
  preserve_original_names: true
  add_import_blocks: true
  generate_variables: true
  generate_outputs: true
  handle_intrinsic_functions: true
  convert_conditions: true
  terraform_version: ">=1.0"
  provider_version: ">=5.0"

modules:
  organization_strategy: service_based  # service_based, stack_based, lifecycle_based, hybrid
  module_prefix: ""
  include_examples: true
  include_readme: true
  include_versions_tf: true
  variable_descriptions: true
  output_descriptions: true
  use_locals: true
  group_similar_resources: true

imports:
  generate_import_scripts: true
  validate_imports: true
  create_backup: true
  parallel_imports: false
  max_import_workers: 5
  import_timeout: 300
  retry_failed_imports: true
  max_retries: 3

output:
  output_directory: "./terraform_output"
  create_subdirectories: true
  overwrite_existing: false
  generate_documentation: true
  export_discovery_data: true
  export_format: json  # json, yaml
  include_metadata: true

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null  # Log file path (null for no file logging)
  console: true
  max_file_size: 10485760  # 10MB
  backup_count: 5
"""


if __name__ == "__main__":
    # Example usage
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    print("Configuration Summary:")
    summary = config_manager.get_config_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

