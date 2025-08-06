#!/usr/bin/env python3
"""
Sample CloudFormation templates for testing
"""

# Simple VPC template
SIMPLE_VPC_TEMPLATE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Simple VPC with public subnet",
    "Parameters": {
        "VpcCidr": {
            "Type": "String",
            "Default": "10.0.0.0/16",
            "Description": "CIDR block for VPC"
        },
        "SubnetCidr": {
            "Type": "String",
            "Default": "10.0.1.0/24",
            "Description": "CIDR block for subnet"
        }
    },
    "Resources": {
        "MyVPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": {"Ref": "VpcCidr"},
                "EnableDnsHostnames": True,
                "EnableDnsSupport": True,
                "Tags": [
                    {"Key": "Name", "Value": "MyVPC"}
                ]
            }
        },
        "MySubnet": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "MyVPC"},
                "CidrBlock": {"Ref": "SubnetCidr"},
                "AvailabilityZone": {"Fn::Select": [0, {"Fn::GetAZs": ""}]},
                "MapPublicIpOnLaunch": True,
                "Tags": [
                    {"Key": "Name", "Value": "MySubnet"}
                ]
            }
        },
        "MyInternetGateway": {
            "Type": "AWS::EC2::InternetGateway",
            "Properties": {
                "Tags": [
                    {"Key": "Name", "Value": "MyInternetGateway"}
                ]
            }
        },
        "AttachGateway": {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {"Ref": "MyVPC"},
                "InternetGatewayId": {"Ref": "MyInternetGateway"}
            }
        }
    },
    "Outputs": {
        "VpcId": {
            "Description": "VPC ID",
            "Value": {"Ref": "MyVPC"},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-VpcId"}}
        },
        "SubnetId": {
            "Description": "Subnet ID",
            "Value": {"Ref": "MySubnet"},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-SubnetId"}}
        }
    }
}

# Complex web application template
COMPLEX_WEB_APP_TEMPLATE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Complex web application with ALB, ASG, and RDS",
    "Parameters": {
        "InstanceType": {
            "Type": "String",
            "Default": "t3.micro",
            "AllowedValues": ["t3.micro", "t3.small", "t3.medium"],
            "Description": "EC2 instance type"
        },
        "KeyName": {
            "Type": "AWS::EC2::KeyPair::KeyName",
            "Description": "EC2 Key Pair for SSH access"
        },
        "DBPassword": {
            "Type": "String",
            "NoEcho": True,
            "MinLength": 8,
            "Description": "Database password"
        }
    },
    "Mappings": {
        "AmiMap": {
            "us-east-1": {"AMI": "ami-0abcdef1234567890"},
            "us-west-2": {"AMI": "ami-0fedcba0987654321"}
        }
    },
    "Resources": {
        # VPC Resources
        "VPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16",
                "EnableDnsHostnames": True,
                "EnableDnsSupport": True,
                "Tags": [{"Key": "Name", "Value": "WebApp-VPC"}]
            }
        },
        "PublicSubnet1": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.1.0/24",
                "AvailabilityZone": {"Fn::Select": [0, {"Fn::GetAZs": ""}]},
                "MapPublicIpOnLaunch": True,
                "Tags": [{"Key": "Name", "Value": "Public-Subnet-1"}]
            }
        },
        "PublicSubnet2": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.2.0/24",
                "AvailabilityZone": {"Fn::Select": [1, {"Fn::GetAZs": ""}]},
                "MapPublicIpOnLaunch": True,
                "Tags": [{"Key": "Name", "Value": "Public-Subnet-2"}]
            }
        },
        "PrivateSubnet1": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.3.0/24",
                "AvailabilityZone": {"Fn::Select": [0, {"Fn::GetAZs": ""}]},
                "Tags": [{"Key": "Name", "Value": "Private-Subnet-1"}]
            }
        },
        "PrivateSubnet2": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "CidrBlock": "10.0.4.0/24",
                "AvailabilityZone": {"Fn::Select": [1, {"Fn::GetAZs": ""}]},
                "Tags": [{"Key": "Name", "Value": "Private-Subnet-2"}]
            }
        },
        
        # Internet Gateway
        "InternetGateway": {
            "Type": "AWS::EC2::InternetGateway",
            "Properties": {
                "Tags": [{"Key": "Name", "Value": "WebApp-IGW"}]
            }
        },
        "AttachGateway": {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "InternetGatewayId": {"Ref": "InternetGateway"}
            }
        },
        
        # Security Groups
        "WebServerSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Security group for web servers",
                "VpcId": {"Ref": "VPC"},
                "SecurityGroupIngress": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                        "SourceSecurityGroupId": {"Ref": "ALBSecurityGroup"}
                    },
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "CidrIp": "0.0.0.0/0"
                    }
                ],
                "Tags": [{"Key": "Name", "Value": "WebServer-SG"}]
            }
        },
        "ALBSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Security group for Application Load Balancer",
                "VpcId": {"Ref": "VPC"},
                "SecurityGroupIngress": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                        "CidrIp": "0.0.0.0/0"
                    },
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "CidrIp": "0.0.0.0/0"
                    }
                ],
                "Tags": [{"Key": "Name", "Value": "ALB-SG"}]
            }
        },
        "DatabaseSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Security group for RDS database",
                "VpcId": {"Ref": "VPC"},
                "SecurityGroupIngress": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 3306,
                        "ToPort": 3306,
                        "SourceSecurityGroupId": {"Ref": "WebServerSecurityGroup"}
                    }
                ],
                "Tags": [{"Key": "Name", "Value": "Database-SG"}]
            }
        },
        
        # Launch Template
        "LaunchTemplate": {
            "Type": "AWS::EC2::LaunchTemplate",
            "Properties": {
                "LaunchTemplateName": "WebApp-LaunchTemplate",
                "LaunchTemplateData": {
                    "ImageId": {"Fn::FindInMap": ["AmiMap", {"Ref": "AWS::Region"}, "AMI"]},
                    "InstanceType": {"Ref": "InstanceType"},
                    "KeyName": {"Ref": "KeyName"},
                    "SecurityGroupIds": [{"Ref": "WebServerSecurityGroup"}],
                    "UserData": {
                        "Fn::Base64": {
                            "Fn::Sub": [
                                "#!/bin/bash\nyum update -y\nyum install -y httpd\nsystemctl start httpd\nsystemctl enable httpd\necho '<h1>Hello from ${AWS::Region}</h1>' > /var/www/html/index.html",
                                {}
                            ]
                        }
                    },
                    "TagSpecifications": [
                        {
                            "ResourceType": "instance",
                            "Tags": [
                                {"Key": "Name", "Value": "WebApp-Instance"}
                            ]
                        }
                    ]
                }
            }
        },
        
        # Auto Scaling Group
        "AutoScalingGroup": {
            "Type": "AWS::AutoScaling::AutoScalingGroup",
            "Properties": {
                "VPCZoneIdentifier": [{"Ref": "PublicSubnet1"}, {"Ref": "PublicSubnet2"}],
                "LaunchTemplate": {
                    "LaunchTemplateId": {"Ref": "LaunchTemplate"},
                    "Version": {"Fn::GetAtt": ["LaunchTemplate", "LatestVersionNumber"]}
                },
                "MinSize": 2,
                "MaxSize": 6,
                "DesiredCapacity": 2,
                "TargetGroupARNs": [{"Ref": "TargetGroup"}],
                "HealthCheckType": "ELB",
                "HealthCheckGracePeriod": 300,
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "WebApp-ASG",
                        "PropagateAtLaunch": True
                    }
                ]
            }
        },
        
        # Application Load Balancer
        "ApplicationLoadBalancer": {
            "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
            "Properties": {
                "Name": "WebApp-ALB",
                "Scheme": "internet-facing",
                "Type": "application",
                "Subnets": [{"Ref": "PublicSubnet1"}, {"Ref": "PublicSubnet2"}],
                "SecurityGroups": [{"Ref": "ALBSecurityGroup"}],
                "Tags": [{"Key": "Name", "Value": "WebApp-ALB"}]
            }
        },
        "TargetGroup": {
            "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
            "Properties": {
                "Name": "WebApp-TG",
                "Port": 80,
                "Protocol": "HTTP",
                "VpcId": {"Ref": "VPC"},
                "HealthCheckPath": "/",
                "HealthCheckProtocol": "HTTP",
                "HealthCheckIntervalSeconds": 30,
                "HealthCheckTimeoutSeconds": 5,
                "HealthyThresholdCount": 2,
                "UnhealthyThresholdCount": 3,
                "Tags": [{"Key": "Name", "Value": "WebApp-TG"}]
            }
        },
        "Listener": {
            "Type": "AWS::ElasticLoadBalancingV2::Listener",
            "Properties": {
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": {"Ref": "TargetGroup"}
                    }
                ],
                "LoadBalancerArn": {"Ref": "ApplicationLoadBalancer"},
                "Port": 80,
                "Protocol": "HTTP"
            }
        },
        
        # RDS Database
        "DBSubnetGroup": {
            "Type": "AWS::RDS::DBSubnetGroup",
            "Properties": {
                "DBSubnetGroupDescription": "Subnet group for RDS database",
                "SubnetIds": [{"Ref": "PrivateSubnet1"}, {"Ref": "PrivateSubnet2"}],
                "Tags": [{"Key": "Name", "Value": "WebApp-DB-SubnetGroup"}]
            }
        },
        "Database": {
            "Type": "AWS::RDS::DBInstance",
            "Properties": {
                "DBInstanceIdentifier": "webapp-database",
                "DBInstanceClass": "db.t3.micro",
                "Engine": "mysql",
                "EngineVersion": "8.0",
                "AllocatedStorage": 20,
                "StorageType": "gp2",
                "DBName": "webapp",
                "MasterUsername": "admin",
                "MasterUserPassword": {"Ref": "DBPassword"},
                "VPCSecurityGroups": [{"Ref": "DatabaseSecurityGroup"}],
                "DBSubnetGroupName": {"Ref": "DBSubnetGroup"},
                "BackupRetentionPeriod": 7,
                "MultiAZ": False,
                "PubliclyAccessible": False,
                "StorageEncrypted": True,
                "Tags": [{"Key": "Name", "Value": "WebApp-Database"}]
            },
            "DeletionPolicy": "Snapshot"
        }
    },
    "Outputs": {
        "LoadBalancerDNS": {
            "Description": "DNS name of the load balancer",
            "Value": {"Fn::GetAtt": ["ApplicationLoadBalancer", "DNSName"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-LoadBalancerDNS"}}
        },
        "DatabaseEndpoint": {
            "Description": "RDS database endpoint",
            "Value": {"Fn::GetAtt": ["Database", "Endpoint.Address"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-DatabaseEndpoint"}}
        }
    }
}

# S3 and Lambda template
S3_LAMBDA_TEMPLATE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "S3 bucket with Lambda function for processing",
    "Parameters": {
        "BucketName": {
            "Type": "String",
            "Description": "Name for the S3 bucket"
        }
    },
    "Resources": {
        "S3Bucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": {"Ref": "BucketName"},
                "VersioningConfiguration": {
                    "Status": "Enabled"
                },
                "BucketEncryption": {
                    "ServerSideEncryptionConfiguration": [
                        {
                            "ServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                },
                "NotificationConfiguration": {
                    "LambdaConfigurations": [
                        {
                            "Event": "s3:ObjectCreated:*",
                            "Function": {"Fn::GetAtt": ["ProcessorFunction", "Arn"]}
                        }
                    ]
                }
            }
        },
        "LambdaExecutionRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                ],
                "Policies": [
                    {
                        "PolicyName": "S3Access",
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "s3:GetObject",
                                        "s3:PutObject"
                                    ],
                                    "Resource": {"Fn::Sub": "${S3Bucket}/*"}
                                }
                            ]
                        }
                    }
                ]
            }
        },
        "ProcessorFunction": {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "FunctionName": "S3ObjectProcessor",
                "Runtime": "python3.9",
                "Handler": "index.handler",
                "Role": {"Fn::GetAtt": ["LambdaExecutionRole", "Arn"]},
                "Code": {
                    "ZipFile": "import json\ndef handler(event, context):\n    print('Processing S3 event:', json.dumps(event))\n    return {'statusCode': 200}"
                },
                "Description": "Process S3 object events",
                "Timeout": 60,
                "MemorySize": 128
            }
        },
        "LambdaInvokePermission": {
            "Type": "AWS::Lambda::Permission",
            "Properties": {
                "FunctionName": {"Ref": "ProcessorFunction"},
                "Action": "lambda:InvokeFunction",
                "Principal": "s3.amazonaws.com",
                "SourceArn": {"Fn::GetAtt": ["S3Bucket", "Arn"]}
            }
        }
    },
    "Outputs": {
        "BucketName": {
            "Description": "Name of the created S3 bucket",
            "Value": {"Ref": "S3Bucket"}
        },
        "LambdaFunctionArn": {
            "Description": "ARN of the Lambda function",
            "Value": {"Fn::GetAtt": ["ProcessorFunction", "Arn"]}
        }
    }
}

# Template with conditions and nested stacks
CONDITIONAL_TEMPLATE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Template with conditions and optional resources",
    "Parameters": {
        "Environment": {
            "Type": "String",
            "Default": "dev",
            "AllowedValues": ["dev", "staging", "prod"],
            "Description": "Environment name"
        },
        "CreateDatabase": {
            "Type": "String",
            "Default": "false",
            "AllowedValues": ["true", "false"],
            "Description": "Whether to create a database"
        }
    },
    "Conditions": {
        "IsProduction": {"Fn::Equals": [{"Ref": "Environment"}, "prod"]},
        "ShouldCreateDatabase": {"Fn::Equals": [{"Ref": "CreateDatabase"}, "true"]},
        "CreateProdDatabase": {"Fn::And": [{"Condition": "IsProduction"}, {"Condition": "ShouldCreateDatabase"}]}
    },
    "Resources": {
        "VPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": {"Fn::If": ["IsProduction", "10.0.0.0/16", "10.1.0.0/16"]},
                "EnableDnsHostnames": True,
                "Tags": [
                    {"Key": "Name", "Value": {"Fn::Sub": "${Environment}-VPC"}},
                    {"Key": "Environment", "Value": {"Ref": "Environment"}}
                ]
            }
        },
        "Database": {
            "Type": "AWS::RDS::DBInstance",
            "Condition": "ShouldCreateDatabase",
            "Properties": {
                "DBInstanceClass": {"Fn::If": ["IsProduction", "db.t3.small", "db.t3.micro"]},
                "Engine": "mysql",
                "AllocatedStorage": {"Fn::If": ["IsProduction", 100, 20]},
                "MasterUsername": "admin",
                "MasterUserPassword": "password123",
                "MultiAZ": {"Condition": "IsProduction"},
                "BackupRetentionPeriod": {"Fn::If": ["IsProduction", 30, 7]}
            }
        },
        "ProdOnlyResource": {
            "Type": "AWS::S3::Bucket",
            "Condition": "IsProduction",
            "Properties": {
                "BucketName": {"Fn::Sub": "${Environment}-prod-only-bucket"},
                "VersioningConfiguration": {
                    "Status": "Enabled"
                }
            }
        }
    },
    "Outputs": {
        "VpcId": {
            "Description": "VPC ID",
            "Value": {"Ref": "VPC"}
        },
        "DatabaseEndpoint": {
            "Condition": "ShouldCreateDatabase",
            "Description": "Database endpoint",
            "Value": {"Fn::GetAtt": ["Database", "Endpoint.Address"]}
        }
    }
}

# All templates for easy access
ALL_TEMPLATES = {
    "simple_vpc": SIMPLE_VPC_TEMPLATE,
    "complex_web_app": COMPLEX_WEB_APP_TEMPLATE,
    "s3_lambda": S3_LAMBDA_TEMPLATE,
    "conditional": CONDITIONAL_TEMPLATE
}

