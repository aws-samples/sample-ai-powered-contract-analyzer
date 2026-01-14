#!/bin/bash

# Frontend Deployment Script for S3 + CloudFront
# Builds React app and deploys to S3, then invalidates CloudFront cache

set -e

echo "🚀 Contract Analyzer - Frontend Deployment"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    echo "Install it with: brew install awscli (Mac) or pip install awscli"
    exit 1
fi

# Get stack outputs
echo "📋 Getting deployment configuration from CDK stack..."
STACK_NAME="ContractAnalyzerStack"

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
    --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" \
    --output text)

FRONTEND_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" \
    --output text)

if [ -z "$BUCKET_NAME" ] || [ -z "$DISTRIBUTION_ID" ]; then
    echo "❌ Error: Could not get stack outputs"
    echo "Make sure you've deployed the CDK stack first: cd backend && cdk deploy"
    exit 1
fi

echo "   S3 Bucket: $BUCKET_NAME"
echo "   CloudFront Distribution: $DISTRIBUTION_ID"
echo "   Frontend URL: $FRONTEND_URL"
echo ""

# Navigate to frontend
cd frontend

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the app
echo ""
echo "🔨 Building production bundle..."
npm run build

if [ ! -d "build" ]; then
    echo "❌ Error: Build directory not found"
    exit 1
fi

# Get build size
BUILD_SIZE=$(du -sh build | cut -f1)
echo "   Build size: $BUILD_SIZE"

# Upload to S3
echo ""
echo "📤 Uploading to S3..."
aws s3 sync build/ "s3://$BUCKET_NAME" \
    --delete \
    --cache-control "public,max-age=31536000,immutable" \
    --exclude "index.html" \
    --exclude "asset-manifest.json" \
    --exclude "service-worker.js"

# Upload index.html with no-cache (for React Router)
echo "   Uploading index.html with no-cache..."
aws s3 cp build/index.html "s3://$BUCKET_NAME/index.html" \
    --cache-control "no-cache,no-store,must-revalidate" \
    --content-type "text/html"

# Upload other non-cacheable files
if [ -f "build/asset-manifest.json" ]; then
    aws s3 cp build/asset-manifest.json "s3://$BUCKET_NAME/asset-manifest.json" \
        --cache-control "no-cache"
fi

if [ -f "build/service-worker.js" ]; then
    aws s3 cp build/service-worker.js "s3://$BUCKET_NAME/service-worker.js" \
        --cache-control "no-cache"
fi

echo "✅ Upload complete!"

# Invalidate CloudFront cache
echo ""
echo "🔄 Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text)

echo "   Invalidation ID: $INVALIDATION_ID"
echo "   This may take 1-2 minutes to complete"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your app is live at:"
echo "   $FRONTEND_URL"
echo ""
echo "📊 Monitor invalidation status:"
echo "   aws cloudfront get-invalidation --distribution-id $DISTRIBUTION_ID --id $INVALIDATION_ID"
echo ""
echo "💡 Note: It may take a few minutes for changes to propagate globally"
