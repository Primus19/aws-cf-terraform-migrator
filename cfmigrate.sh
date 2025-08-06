#!/bin/bash
# AWS CloudFormation to Terraform Migrator - Unix Shell Runner
# This script makes it easy to run the tool on Linux/Mac

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run the Python script with all arguments
python3 run_cfmigrate.py "$@"

