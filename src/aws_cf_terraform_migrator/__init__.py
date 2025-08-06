"""
CloudFormation to Terraform Converter Tool

A comprehensive tool for migrating AWS CloudFormation stacks to Terraform modules
with automatic resource discovery and import capabilities.
"""

__version__ = "1.0.0"
__author__ = "Manus AI"
__email__ = "support@manus.ai"

from .discovery import DiscoveryEngine
from .conversion import ConversionEngine
from .modules import ModuleGenerator
from .imports import ImportManager
from .orchestrator import Orchestrator

__all__ = [
    "DiscoveryEngine",
    "ConversionEngine", 
    "ModuleGenerator",
    "ImportManager",
    "Orchestrator"
]

