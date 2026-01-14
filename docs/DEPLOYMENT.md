# Contract Analyzer - Deployment Guide

Complete guide for deploying the Contract Analyzer using AWS CloudShell and CodeBuild.

## Table of Contents
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Detailed Steps](#detailed-steps)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)
- [Advanced Topics](#advanced-topics)

---

## Quick Start

Deploy in 3 simple steps using AWS CloudShell:

### Step 1: Open AWS CloudShell
1. Log into [AWS Console](https://console.aws.amazon.com)
2. Click the **CloudShell** icon (terminal icon in top navigation)
3. Wait for CloudShell to initialize (~30 seconds)

### Step 2: Deploy
```bash
git clone <your-repo-url>
cd contract-analyzer
./scripts/deployment/setup-and-deploy.sh
```

### Step 3: Access Your App
After 12-15 minutes, you'll see:
```
🎉 Contract Analyzer Deployed Successfully!

🌐 Application URL:
   https://d1234567890abc.cloudfront.net
```

Open that URL and start using your app!

---

## How It Works

### Architecture Overview

```
┌─────────────────┐
│  AWS CloudShell │  ← You run: ./scripts/deployment/setup-and-deploy.sh
└────────┬────────┘
         │
         ├─ Detects AWS Region (from CloudShell environment)
         ├─ Creates S3 bucket for source code
         ├─ Zips and uploads code
         ├─ Deploys CloudFormation stack (CodeBuild project)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              AWS CodeBuild Project                       │
│  (Created via CloudFormation)                           │
└────────┬────────────────────────────────────────────────┘
         │
         ├─ Install Phase (2 min)
         │  ├─ Install AWS CDK
         │  ├─ Install Python dependencies
         │  └─ Install Node.js dependencies
         │
         ├─ Pre-Build Phase (3 min)
         │  └─ Build Lambda layer (Strands framework)
         │
         ├─ Build Phase (5-8 min)
         │  ├─ CDK bootstrap (if needed)
         │  ├─ CDK deploy (all infrastructure)
         │  └─ Capture outputs to JSON
         │
         └─ Post-Build Phase (2-3 min)
            ├─ Generate frontend config (auto!)
            ├─ Build React app
            ├─ Deploy to S3
            └─ Invalidate CloudFront cache
         
         ▼
┌─────────────────────────────────────────────────────────┐
│           Deployed Application                           │
│  - Lambda Functions                                      │
│  - API Gateway                                           │
│  - DynamoDB                                              │
│  - S3 Buckets                                            │
│  - CloudFront                                            │
│  - Cognito                                               │
└──────────────────────────────────────────────────────────┘
```

### Key Features

✅ **Region Detection** - Automatically uses CloudShell's AWS region  
✅ **Automated Config** - No manual copy-paste of CDK outputs  
✅ **Idempotent** - Can run multiple times safely  
✅ **Complete Logs** - Streams to terminal and preserved in CloudWatch  
✅ **Easy Cleanup** - Single command to delete everything  

---

## Detailed Steps

### Prerequisites

- ✅ AWS Account with admin access
- ✅ Access to AWS Console
- ✅ That's it! No local setup required

### Regional Deployment

The deployment automatically uses your **CloudShell region**.

**Supported Regions for Bedrock:**
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- eu-west-1 (Ireland)
- eu-central-1 (Frankfurt)
- ap-southeast-1 (Singapore)
- ap-northeast-1 (Tokyo)

**To deploy to a specific region:**
```bash
export AWS_REGION=us-west-2
./scripts/deployment/setup-and-deploy.sh
```

### What Gets Deployed

#### Backend Infrastructure
- **Lambda Functions** (5)
  - Upload initialization
  - Contract analysis (with Textract + Bedrock)
  - List contracts
  - Get results
  - Chat with contract
- **Lambda Layer** - Strands Agents Framework
- **API Gateway** - REST API with Cognito authorization
- **DynamoDB** - Contract metadata and results
- **S3 Buckets** (2)
  - Contracts storage
  - Frontend hosting
- **CloudFront** - Global CDN with HTTPS
- **Cognito** - User Pool + Identity Pool
- **IAM Roles** - Least privilege permissions

#### Frontend
- **React Application** - Built and deployed to S3
- **Auto-generated Config** - No manual configuration needed
- **CloudFront Distribution** - HTTPS enabled, global CDN

### Deployment Timeline

| Phase | Duration | What Happens |
|-------|----------|--------------|
| **Setup** | 1-2 min | Create S3 bucket, upload code, create CodeBuild project |
| **Install** | 2 min | Install CDK, Python deps, Node deps |
| **Pre-Build** | 3 min | Build Lambda layer with Strands framework |
| **Build** | 5-8 min | Deploy all infrastructure via CDK |
| **Post-Build** | 2-3 min | Build and deploy frontend, invalidate cache |
| **Total** | **12-15 min** | Fully deployed application |

---

## Architecture

### Deployment Flow

```
setup-and-deploy.sh
  ↓
Detect Region (from CloudShell env)
  ↓
Create S3 Bucket (codebuild-source-{account}-{region})
  ↓
Zip Code → Upload to S3
  ↓
Deploy CloudFormation Stack
  ├─ Create IAM Role
  ├─ Create CodeBuild Project
  └─ Create CloudWatch Log Group
  ↓
Start CodeBuild Job
  ↓
CodeBuild: Install → Pre-Build → Build → Post-Build
  ↓
Show CloudFront URL to User
```

### Application Data Flow

```
User Browser
  ↓
CloudFront (React App)
  ↓
Cognito (Authentication)
  ↓
API Gateway (REST API)
  ↓
Lambda Functions
  ├─ Textract (PDF extraction)
  ├─ Bedrock (AI analysis)
  ├─ S3 (Storage)
  └─ DynamoDB (Metadata)
```

### Files Structure

```
contract-analyzer/
├── README.md                          # Main documentation
├── docs/
│   ├── DEPLOYMENT.md                  # This file
│   └── GUIDE.md                       # Feature guide
├── scripts/
│   ├── deployment/
│   │   ├── setup-and-deploy.sh        # Main deployment script
│   │   ├── cleanup.sh                 # Cleanup script
│   │   ├── buildspec.yml              # CodeBuild instructions
│   │   └── codebuild-setup.yaml       # CloudFormation template
│   └── generate-frontend-config.py    # Config generator
├── backend/
│   ├── app.py                         # CDK app
│   ├── stacks/                        # CDK stacks
│   ├── lambda/                        # Lambda functions
│   └── build_layer.sh                 # Lambda layer builder
└── frontend/
    └── src/                           # React app
```

---

## Troubleshooting

### Deployment Issues

#### Build Fails with "Bedrock AccessDeniedException"

**Cause:** Haven't requested access to Claude models in Bedrock console

**Solution:**
1. Go to Bedrock console
2. Click "Model Access" in left sidebar
3. Click "Request Access"
4. Select Claude 3.5 Sonnet
5. Wait for approval (usually instant)
6. Re-run deployment:
   ```bash
   ./scripts/deployment/setup-and-deploy.sh
   ```

#### Build Fails with "Region Not Supported"

**Cause:** Deploying to region where Bedrock is not available

**Solution:**
```bash
export AWS_REGION=us-east-1
./scripts/deployment/setup-and-deploy.sh
```

#### Build Fails in CDK Bootstrap

**Cause:** Usually transient network issues

**Solution:** Just run again:
```bash
./scripts/deployment/setup-and-deploy.sh
```

#### Can't Stream Logs

**Cause:** Log stream not created yet

**Solution:** Check CodeBuild console:
```
https://{region}.console.aws.amazon.com/codesuite/codebuild/projects/ContractAnalyzerBuild/history
```

### Application Issues

#### CloudFront Shows 403 Forbidden

**Cause:** Distribution still propagating

**Solution:** Wait 5-10 minutes and refresh

#### Upload Fails

**Causes:**
- File too large (max 100MB)
- Not a PDF file
- Browser issue

**Solution:**
- Check file size and type
- Try different browser
- Check browser console for errors

#### Analysis Stuck in "Processing"

**Cause:** Lambda error or timeout

**Solution:** Check Lambda logs:
```bash
aws logs tail /aws/lambda/ContractAnalyzerStack-AnalyzeFunction --follow
```

#### Chat Not Working

**Cause:** Contract not analyzed or text not extracted

**Solution:**
- Ensure contract status is "analyzed"
- Check S3 for extracted_text.txt file
- Re-upload contract if needed

### Viewing Logs

**CodeBuild logs:**
```bash
aws logs tail /aws/codebuild/ContractAnalyzerBuild --follow
```

**Lambda logs:**
```bash
# Analyze function
aws logs tail /aws/lambda/ContractAnalyzerStack-AnalyzeFunction --follow

# Chat function
aws logs tail /aws/lambda/ContractAnalyzerStack-ChatFunction --follow
```

**API Gateway logs:**
```bash
aws logs tail /aws/apigateway/ContractAnalyzerApi --follow
```

---

## Cleanup

To delete all resources and avoid charges:

```bash
./scripts/deployment/cleanup.sh
```

This will delete:
- ✅ CDK Stack (Lambda, API Gateway, DynamoDB, S3, CloudFront, Cognito)
- ✅ CodeBuild Project
- ✅ S3 Buckets (including all uploaded contracts)
- ✅ All user data
- ✅ CloudWatch log groups

**Warning:** This is permanent and cannot be undone!

### Manual Cleanup (if script fails)

```bash
# Delete CDK stack
aws cloudformation delete-stack --stack-name ContractAnalyzerStack

# Delete CodeBuild stack
aws cloudformation delete-stack --stack-name ContractAnalyzerCodeBuild

# Empty and delete S3 buckets
aws s3 rm s3://your-bucket-name --recursive
aws s3 rb s3://your-bucket-name
```

---

## Advanced Topics

### Updating the Application

To deploy updates:

```bash
cd contract-analyzer
git pull  # Get latest changes
./scripts/deployment/setup-and-deploy.sh
```

The script will:
- Update the CodeBuild project
- Redeploy with new code
- Preserve existing data (contracts, users)

### Multi-Environment Deployment

Deploy to different environments:

```bash
# Development
export AWS_REGION=us-east-1
./scripts/deployment/setup-and-deploy.sh

# Production (different region)
export AWS_REGION=us-west-2
./scripts/deployment/setup-and-deploy.sh
```

### Cost Monitoring

**Set up billing alerts:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name contract-analyzer-cost \
  --alarm-description "Alert when monthly costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold
```

**View current costs:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### CI/CD Integration

For automatic deployments on git push, integrate with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy Contract Analyzer

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy
        run: ./scripts/deployment/setup-and-deploy.sh
```

### Manual Deployment (Alternative)

If you prefer manual deployment without CodeBuild:

```bash
# 1. Install prerequisites
npm install -g aws-cdk

# 2. Deploy backend
cd backend
pip install -r requirements.txt
./build_layer.sh
cdk deploy --region us-east-1

# 3. Configure frontend
# Manually update frontend/src/aws-config.js with CDK outputs

# 4. Deploy frontend
cd ..
./deploy-frontend.sh
```

---

## Cost Estimate

### Deployment Cost
- **$0.11 per deployment**
  - CodeBuild: $0.10 (15 min × BUILD_GENERAL1_SMALL)
  - S3 API calls: $0.01

### Monthly Running Cost (100 contracts)
- Bedrock (Claude): ~$22
- Textract: ~$1.50
- Lambda: ~$0.50
- S3: ~$0.30
- DynamoDB: ~$0.50
- CloudFront: ~$0.90
- API Gateway: ~$0.04
- Cognito: Free (first 50K users)
- **Total: ~$26/month**

### Free Tier Benefits (First 12 months)
Most services covered by free tier, pay only for Bedrock and Textract (~$24/month).

---

## Support

### Documentation
- **Main README:** [README.md](../README.md)
- **Feature Guide:** [GUIDE.md](GUIDE.md)
- **This Deployment Guide:** You're reading it!

### AWS Resources
- [AWS CloudShell](https://docs.aws.amazon.com/cloudshell/)
- [AWS CodeBuild](https://docs.aws.amazon.com/codebuild/)
- [AWS CDK](https://docs.aws.amazon.com/cdk/)
- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)

### Common Commands

**View build history:**
```bash
aws codebuild list-builds-for-project \
  --project-name ContractAnalyzerBuild
```

**Check stack status:**
```bash
aws cloudformation describe-stacks \
  --stack-name ContractAnalyzerStack
```

**Manual build trigger:**
```bash
aws codebuild start-build \
  --project-name ContractAnalyzerBuild
```

---

**Ready to deploy? Run `./scripts/deployment/setup-and-deploy.sh` to get started!** 🚀
