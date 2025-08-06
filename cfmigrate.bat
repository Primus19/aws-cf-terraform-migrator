@echo off
REM AWS CloudFormation to Terraform Migrator - Windows Batch Runner
REM This batch file makes it easy to run the tool on Windows

cd /d "%~dp0"
python run_cfmigrate.py %*

