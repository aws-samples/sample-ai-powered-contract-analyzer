#!/bin/bash
set -e

# Contract Analyzer - Automated Deployment via CodeBuild
# This script sets up and triggers a CodeBuild job that deploys everything

echo "🚀 Contract Analyzer - Automated Deployment"
echo "============================================"
echo ""

# Get AWS region from CloudShell environment
AWS_REGION=${AWS_REGION:-$(aws configure get region)}
if [ -z "$AWS_REGION" ]; then
  echo "❌ Error: Could not determine AWS region"
  echo "Please set AWS_REGION environment variable or configure AWS CLI"
  exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

# Configuration
STACK_NAME="ContractAnalyzerCodeBuild"
PROJECT_NAME="ContractAnalyzerBuild"
BUCKET_NAME="codebuild-source-$AWS_ACCOUNT_ID-$AWS_REGION"

echo "📋 Configuration:"
echo "   Region: $AWS_REGION"
echo "   Account: $AWS_ACCOUNT_ID"
echo "   CodeBuild Project: $PROJECT_NAME"
echo ""

# Validate Bedrock availability in region
echo "🔍 Validating Bedrock availability in $AWS_REGION..."
BEDROCK_REGIONS=("us-east-1" "us-west-2" "eu-west-1" "eu-central-1" "ap-southeast-1" "ap-northeast-1")
if [[ ! " ${BEDROCK_REGIONS[@]} " =~ " ${AWS_REGION} " ]]; then
  echo "⚠️  Warning: Bedrock may not be available in $AWS_REGION"
  echo "   Recommended regions: ${BEDROCK_REGIONS[@]}"
  echo ""
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Step 1: Create S3 bucket for source code (if needed)
echo "📦 Setting up S3 bucket for source code..."
if ! aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
  echo "   Creating bucket: $BUCKET_NAME"
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3 mb "s3://$BUCKET_NAME"
  else
    aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
  fi
else
  echo "   Bucket already exists: $BUCKET_NAME"
fi

# Step 2: Zip and upload code
echo ""
echo "📤 Packaging and uploading source code..."
ZIP_FILE="/tmp/contract-analyzer-$(date +%s).zip"

zip -r "$ZIP_FILE" . \
  -x "*.git*" \
  -x "*/node_modules/*" \
  -x "*/.venv/*" \
  -x "*/cdk.out/*" \
  -x "*/build/*" \
  -x "*/__pycache__/*" \
  -x "*.DS_Store" \
  -x "*/lambda_layer/*" \
  > /dev/null

ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "   Package size: $ZIP_SIZE"

aws s3 cp "$ZIP_FILE" "s3://$BUCKET_NAME/contract-analyzer.zip" --region "$AWS_REGION"
rm "$ZIP_FILE"
echo "   ✓ Uploaded to S3"

# Step 3: Deploy CloudFormation stack (creates/updates CodeBuild project)
echo ""
echo "🏗️  Setting up CodeBuild project..."
aws cloudformation deploy \
  --template-file scripts/deployment/codebuild-setup.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
      SourceBucket="$BUCKET_NAME" \
      SourceKey="contract-analyzer.zip" \
      DeploymentRegion="$AWS_REGION" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$AWS_REGION" \
  --no-cli-pager

echo "   ✓ CodeBuild project ready"

# Step 4: Start build
echo ""
echo "🔨 Starting CodeBuild deployment..."
BUILD_ID=$(aws codebuild start-build \
  --project-name "$PROJECT_NAME" \
  --region "$AWS_REGION" \
  --environment-variables-override \
      name=AWS_REGION,value="$AWS_REGION" \
      name=AWS_ACCOUNT_ID,value="$AWS_ACCOUNT_ID" \
  --query 'build.id' \
  --output text)

echo "   Build ID: $BUILD_ID"
echo ""
echo "📊 Streaming build logs (this will take 12-15 minutes)..."
echo "   You can safely close this and check progress in the CodeBuild console"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 5: Wait for log stream to be created and stream logs
LOG_GROUP="/aws/codebuild/$PROJECT_NAME"
sleep 5

# Get log stream name
LOG_STREAM=$(aws codebuild batch-get-builds \
  --ids "$BUILD_ID" \
  --region "$AWS_REGION" \
  --query 'builds[0].logs.streamName' \
  --output text 2>/dev/null || echo "")

if [ -n "$LOG_STREAM" ] && [ "$LOG_STREAM" != "None" ]; then
  # Wait a bit more for logs to start
  sleep 5
  
  # Stream logs in background and poll for completion
  aws logs tail "$LOG_GROUP" \
    --log-stream-names "$LOG_STREAM" \
    --follow \
    --format short \
    --region "$AWS_REGION" 2>/dev/null &
  
  LOG_PID=$!
  
  # Poll for build completion
  while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds \
      --ids "$BUILD_ID" \
      --region "$AWS_REGION" \
      --query 'builds[0].buildStatus' \
      --output text 2>/dev/null || echo "IN_PROGRESS")
    
    if [ "$BUILD_STATUS" != "IN_PROGRESS" ]; then
      sleep 2
      kill $LOG_PID 2>/dev/null || true
      break
    fi
    
    sleep 10
  done
else
  echo "⚠️  Could not stream logs. Waiting for build to complete..."
  
  # Poll for build completion
  while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds \
      --ids "$BUILD_ID" \
      --region "$AWS_REGION" \
      --query 'builds[0].buildStatus' \
      --output text)
    
    if [ "$BUILD_STATUS" != "IN_PROGRESS" ]; then
      break
    fi
    
    echo -n "."
    sleep 10
  done
  echo ""
fi

# Step 6: Check build status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

BUILD_STATUS=$(aws codebuild batch-get-builds \
  --ids "$BUILD_ID" \
  --region "$AWS_REGION" \
  --query 'builds[0].buildStatus' \
  --output text)

if [ "$BUILD_STATUS" = "SUCCEEDED" ]; then
  echo "✅ Deployment successful!"
  echo ""
  echo "📋 Retrieving deployment information..."
  
  # Get outputs from CDK stack
  API_URL=$(aws cloudformation describe-stacks \
    --stack-name ContractAnalyzerStack \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "N/A")
  
  CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name ContractAnalyzerStack \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' \
    --output text 2>/dev/null || echo "N/A")
  
  USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name ContractAnalyzerStack \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
    --output text 2>/dev/null || echo "N/A")
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🎉 Contract Analyzer Deployed Successfully!"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "🌐 Application URL:"
  echo "   $CLOUDFRONT_URL"
  echo ""
  echo "📡 API Endpoint:"
  echo "   $API_URL"
  echo ""
  echo "🔐 Cognito User Pool:"
  echo "   $USER_POOL_ID"
  echo ""
  echo "📍 Region:"
  echo "   $AWS_REGION"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "📝 Next Steps:"
  echo "   1. Open the Application URL in your browser"
  echo "   2. Click 'Sign Up' to create an account"
  echo "   3. Verify your email address"
  echo "   4. Login and start uploading contracts!"
  echo ""
  echo "💡 Note: CloudFront distribution may take a few minutes to fully propagate"
  echo ""
  
else
  echo "❌ Deployment failed with status: $BUILD_STATUS"
  echo ""
  echo "🔍 To view detailed logs:"
  echo "   aws logs tail /aws/codebuild/$PROJECT_NAME --follow --region $AWS_REGION"
  echo ""
  echo "🌐 Or check the CodeBuild console:"
  echo "   https://$AWS_REGION.console.aws.amazon.com/codesuite/codebuild/projects/$PROJECT_NAME/history"
  echo ""
  exit 1
fi
