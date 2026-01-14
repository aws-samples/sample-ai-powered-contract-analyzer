#!/bin/bash
set -e

# Contract Analyzer - Cleanup Script
# Removes all AWS resources created by the deployment

echo "🧹 Contract Analyzer - Cleanup"
echo "=============================="
echo ""
echo "⚠️  WARNING: This will delete ALL resources including:"
echo "   - CDK Stack (Lambda, API Gateway, DynamoDB, S3, CloudFront, Cognito)"
echo "   - CodeBuild Project"
echo "   - S3 Buckets (including all uploaded contracts)"
echo "   - All user data"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " -r
echo

if [ "$REPLY" != "yes" ]; then
  echo "Cleanup cancelled"
  exit 0
fi

# Get AWS region from CloudShell environment
AWS_REGION=${AWS_REGION:-$(aws configure get region)}
if [ -z "$AWS_REGION" ]; then
  echo "❌ Error: Could not determine AWS region"
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo ""

# Step 1: Empty and delete S3 buckets
echo "📦 Cleaning up S3 buckets..."

# Get bucket names from CDK stack
CONTRACTS_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name ContractAnalyzerStack \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text 2>/dev/null || echo "")

FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name ContractAnalyzerStack \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$CONTRACTS_BUCKET" ]; then
  echo "   Emptying contracts bucket: $CONTRACTS_BUCKET"
  aws s3 rm "s3://$CONTRACTS_BUCKET" --recursive --region $AWS_REGION 2>/dev/null || true
fi

if [ -n "$FRONTEND_BUCKET" ]; then
  echo "   Emptying frontend bucket: $FRONTEND_BUCKET"
  aws s3 rm "s3://$FRONTEND_BUCKET" --recursive --region $AWS_REGION 2>/dev/null || true
fi

# Step 2: Delete CDK stack
echo ""
echo "🗑️  Deleting CDK stack..."
aws cloudformation delete-stack \
  --stack-name ContractAnalyzerStack \
  --region $AWS_REGION 2>/dev/null || echo "   Stack not found or already deleted"

echo "   Waiting for stack deletion (this may take 5-10 minutes)..."
aws cloudformation wait stack-delete-complete \
  --stack-name ContractAnalyzerStack \
  --region $AWS_REGION 2>/dev/null || echo "   Stack deletion complete or not found"

# Step 3: Delete CodeBuild stack
echo ""
echo "🗑️  Deleting CodeBuild stack..."
aws cloudformation delete-stack \
  --stack-name ContractAnalyzerCodeBuild \
  --region $AWS_REGION 2>/dev/null || echo "   Stack not found or already deleted"

echo "   Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name ContractAnalyzerCodeBuild \
  --region $AWS_REGION 2>/dev/null || echo "   Stack deletion complete or not found"

# Step 4: Delete source code bucket
echo ""
echo "📦 Cleaning up source code bucket..."
SOURCE_BUCKET="codebuild-source-$AWS_ACCOUNT_ID-$AWS_REGION"
if aws s3 ls "s3://$SOURCE_BUCKET" 2>/dev/null; then
  echo "   Emptying and deleting: $SOURCE_BUCKET"
  aws s3 rm "s3://$SOURCE_BUCKET" --recursive --region $AWS_REGION
  aws s3 rb "s3://$SOURCE_BUCKET" --region $AWS_REGION
else
  echo "   Bucket not found: $SOURCE_BUCKET"
fi

# Step 5: Delete CloudWatch log groups
echo ""
echo "📊 Cleaning up CloudWatch logs..."
aws logs delete-log-group \
  --log-group-name /aws/codebuild/ContractAnalyzerBuild \
  --region $AWS_REGION 2>/dev/null || echo "   Log group not found or already deleted"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "All resources have been deleted."
