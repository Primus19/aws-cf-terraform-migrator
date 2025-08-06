# Windows Installation Guide

## 🪟 Windows-Specific Installation Instructions

### Prerequisites

1. **Python 3.8+** installed from [python.org](https://www.python.org/downloads/) or Microsoft Store
2. **AWS CLI** configured with credentials
3. **Git** (optional, for cloning)

### Installation Steps

#### Option 1: Direct Python Execution (Recommended for Windows)

```powershell
# 1. Extract the zip file
# Right-click aws-cf-terraform-migrator-v1.0.0-final.zip -> Extract All

# 2. Open PowerShell and navigate to the directory
cd "C:\path\to\aws-cf-terraform-migrator"

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test the tool
python run_cfmigrate.py --version
```

#### Option 2: Using Batch File (Windows)

```cmd
# After extraction and dependency installation
cfmigrate.bat --version
cfmigrate.bat convert-all --regions us-east-1 --output ./terraform
```

#### Option 3: Traditional pip install (if PATH is configured)

```powershell
# Install the package
pip install -e .

# If scripts are in PATH, you can use:
aws-cf-tf-migrate --version
cfmigrate --version
```

### Usage Examples

#### Basic Usage (Windows PowerShell)

```powershell
# One-command migration
python run_cfmigrate.py convert-all --regions us-east-1,us-west-2 --output ./terraform

# Or using batch file
cfmigrate.bat convert-all --regions us-east-1,us-west-2 --output ./terraform

# Step-by-step process
python run_cfmigrate.py discover --regions us-east-1 --output discovery.json
python run_cfmigrate.py convert --input discovery.json --output ./terraform
```

#### Advanced Usage

```powershell
# Multi-region with specific strategy
python run_cfmigrate.py convert-all `
  --regions us-east-1,us-west-2,eu-west-1 `
  --strategy hybrid `
  --module-prefix mycompany `
  --output ./terraform `
  --verbose

# Using configuration file
python run_cfmigrate.py convert-all --config migration-config.yaml

# Dry run to preview
python run_cfmigrate.py convert-all `
  --regions us-east-1 `
  --output ./terraform `
  --dry-run
```

### Troubleshooting Windows Issues

#### Issue 1: "aws-cf-tf-migrate is not recognized"

**Solution**: Use the direct Python method:
```powershell
python run_cfmigrate.py --version
```

#### Issue 2: "Scripts directory not in PATH"

**Solution**: Either use direct Python execution or add the Scripts directory to PATH:
```powershell
# Find your Python Scripts directory
python -c "import site; print(site.USER_BASE + '\\Scripts')"

# Add to PATH in System Environment Variables
# Or use direct execution: python run_cfmigrate.py
```

#### Issue 3: Permission Denied

**Solution**: Run PowerShell as Administrator or use:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Issue 4: Module Import Errors

**Solution**: Ensure you're in the correct directory:
```powershell
cd "C:\path\to\aws-cf-terraform-migrator"
python run_cfmigrate.py --version
```

### AWS Credentials Setup (Windows)

```powershell
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables (PowerShell)
$env:AWS_ACCESS_KEY_ID="your_access_key"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key"
$env:AWS_DEFAULT_REGION="us-east-1"

# Option 3: Environment Variables (Command Prompt)
set AWS_ACCESS_KEY_ID=your_access_key
set AWS_SECRET_ACCESS_KEY=your_secret_key
set AWS_DEFAULT_REGION=us-east-1
```

### Complete Windows Example

```powershell
# 1. Navigate to extracted directory
cd "C:\Users\YourName\Downloads\aws-cf-terraform-migrator"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure AWS credentials
aws configure

# 4. Run migration
python run_cfmigrate.py convert-all --regions us-east-1 --output ./terraform

# 5. Navigate to output and import resources
cd terraform
terraform init
.\import_resources.ps1  # Windows PowerShell script (will be generated)

# 6. Verify
terraform plan
```

### Generated Files for Windows

The tool will generate Windows-compatible scripts:

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── terraform.tfvars.example
├── import_resources.sh      # Unix script
├── import_resources.ps1     # Windows PowerShell script
└── modules/
    └── ...
```

### Performance Tips for Windows

1. **Use SSD storage** for better I/O performance
2. **Exclude the project directory** from Windows Defender real-time scanning
3. **Use PowerShell** instead of Command Prompt for better Unicode support
4. **Run from local drive** (not network drives) for better performance

### Next Steps

After successful installation and testing:

1. **Bookmark the directory** for easy access
2. **Create a desktop shortcut** to PowerShell in the project directory
3. **Set up your preferred terminal** (Windows Terminal, PowerShell ISE, etc.)
4. **Configure your IDE** (VS Code, PyCharm) to work with the project

---

**Windows Support**: This tool is fully compatible with Windows 10/11 and Windows Server 2019/2022.

