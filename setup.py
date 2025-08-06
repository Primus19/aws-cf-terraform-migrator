#!/usr/bin/env python3
"""
AWS CloudFormation to Terraform Migrator
A comprehensive tool for migrating AWS CloudFormation stacks to Terraform modules
with zero downtime and no hardcoded values.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aws-cf-terraform-migrator",
    version="1.0.0",
    author="AWS CF Terraform Migrator Team",
    author_email="support@aws-cf-terraform-migrator.com",
    description="Convert AWS CloudFormation stacks to Terraform modules with zero downtime, comprehensive resource discovery, and no hardcoded values",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aws-cf-terraform-migrator/aws-cf-terraform-migrator",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aws-cf-tf-migrate=aws_cf_terraform_migrator.enhanced_cli:main",
            "cfmigrate=aws_cf_terraform_migrator.enhanced_cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

