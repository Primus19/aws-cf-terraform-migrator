#!/usr/bin/env python3
"""
Direct runner for AWS CloudFormation to Terraform Migrator
This script can be run directly with Python on any platform, including Windows
"""

import sys
import os

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

try:
    from aws_cf_terraform_migrator.enhanced_cli import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("\n🔧 Troubleshooting:")
    print("1. Make sure you're in the aws-cf-terraform-migrator directory")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Try running: python run_cfmigrate.py --help")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

