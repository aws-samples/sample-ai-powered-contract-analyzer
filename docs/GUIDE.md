# Contract Analyzer - Complete Guide

Comprehensive documentation for the AI-Powered Contract Analyzer system.

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Details](#architecture-details)
3. [Setup & Deployment](#setup--deployment)
4. [Features & Usage](#features--usage)
5. [API Reference](#api-reference)
6. [Security](#security)
7. [Troubleshooting](#troubleshooting)
8. [Cost Optimization](#cost-optimization)

---

## System Overview

### What It Does

The Contract Analyzer is an intelligent system that:
- Extracts text from PDF contracts using Amazon Textract
- Analyzes contracts using Claude Sonnect 4.5 (Amazon Bedrock)
- Identifies key terms, commitments, risks, and action items
- Enables interactive Q&A with contracts via AI chatbot
- Provides real-time dashboard for tracking analysis

### Key Features

**Contract Analysis (Powered by Claude Sonnet 4.5)**
- Professional title extraction
- Executive summary generation
- Key terms identification (type, parties, value, duration)
- Commitments tracking (payment, packaging, inventory, labeling, portal)
- Contact information extraction
- Action items with deadlines
- Risk factor identification

**Interactive Chat (Powered by Claude Sonnet 4.5)**
- Ask questions about contract content
- Get AI-powered answers with context
- Conversation history maintained
- Markdown-formatted responses

**User Experience**
- Secure authentication (Cognito)
- Real-time status updates
- Responsive design (mobile-friendly)
- Floating chat widget
- Contract list with search

---

## Architecture Details

### Frontend Architecture

**Technology Stack:**
- React 18.2
- AWS Amplify (Auth & Storage)
- React Markdown (Chat formatting)

**Components:**
- `ContractUpload` - File upload with progress
- `ContractList` - Dashboard with status
- `ContractResults` - Analysis display
- `ContractChat` - AI chatbot widget

**State Management:**
- React hooks (useState, useEffect)
- Amplify Auth session management
- Local state for UI interactions

### Backend Architecture

**Infrastructure (AWS CDK):**
- API Gateway - REST API with Cognito authorizer
- Lambda Functions - Python 3.12 serverless compute
- DynamoDB - NoSQL database with GSI
- S3 - Object storage with versioning
- CloudFront - Global CDN
- Cognito - User authentication

**Lambda Functions:**

1. **upload.py** - Initialize upload
   - Validates filename and size
   - Creates DynamoDB record
   - Returns S3 upload details

2. **analyze.py** - Process contract (S3 triggered)
   - Validates PDF file type
   - Extracts text with Textract
   - Analyzes with Bedrock (Claude Sonnet 4.5)
   - Stores results in DynamoDB
   - Saves extracted text to S3

3. **list_contracts.py** - List user's contracts
   - Queries DynamoDB GSI by userId
   - Returns sorted list with status

4. **get_results.py** - Get analysis results
   - Verifies user ownership
   - Returns analysis data

5. **chat.py** - Chatbot interactions
   - Retrieves contract text from S3
   - Uses Strands framework with Claude Sonnet 4.5
   - Maintains conversation history

**Data Flow:**

```
User Upload → S3 → Event Trigger → Analyze Lambda
                                        ↓
                                   Textract → Extract Text
                                        ↓
                            Bedrock (Claude Sonnet 4.5) → Analyze
                                        ↓
                                   DynamoDB ← Store Results
```

### Database Schema

**DynamoDB Table: ContractsTable**

Primary Key:
- `contractId` (Partition Key) - UUID
- `timestamp` (Sort Key) - ISO 8601 timestamp

Attributes:
- `userId` - Cognito user ID
- `fileName` - Original filename
- `s3Key` - S3 object key
- `textS3Key` - Extracted text S3 key
- `status` - uploaded | processing | analyzed | failed
- `analysis` - JSON object with results

Global Secondary Index:
- `UserIdIndex` - Partition: userId, Sort: timestamp

---

## Setup & Deployment

### Prerequisites

**Required:**
- AWS Account with admin access
- AWS CLI configured (`aws configure`)
- Node.js 18+ and npm
- Python 3.12+
- AWS CDK: `npm install -g aws-cdk`

**Optional:**
- Docker (for Lambda layer building)
- Git (for version control)

### Step 1: Clone & Install

```bash
# Clone repository
git clone <your-repo-url>
cd contract-analyzer

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

### Step 2: Build Lambda Layer

The Lambda layer contains the Strands Agents Framework and dependencies.

```bash
cd backend
./build_layer.sh
```

This creates `lambda_layer/python/` with all required packages.

### Step 3: Deploy Backend

**Choose Your Region:**

The stack is fully region-agnostic. Deploy to any AWS region where Bedrock is available.

```bash
cd backend

# First time only - bootstrap CDK in your chosen region
cdk bootstrap

# Option 1: Deploy to default region (from AWS CLI config)
cdk deploy

# Option 2: Deploy to specific region
cdk deploy --region us-east-1

# Option 3: Set region via environment variable
export AWS_REGION=eu-west-1
cdk deploy
```

**Regional Considerations:**
- **Bedrock Availability**: Ensure Claude Sonnet 4.5 is available in your region
- **Textract**: Available in most regions
- **Latency**: Choose a region close to your users
- **Compliance**: Consider data residency requirements

**Supported Regions for Bedrock:**
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- eu-west-1 (Ireland)
- eu-central-1 (Frankfurt)
- ap-southeast-1 (Singapore)
- ap-northeast-1 (Tokyo)

**Save these CDK outputs:**
```
ContractAnalyzerStack.ApiUrl = https://xxx.execute-api.REGION.amazonaws.com/prod/
ContractAnalyzerStack.UserPoolId = REGION_xxxxxxxxx
ContractAnalyzerStack.UserPoolClientId = xxxxxxxxxxxxxxxxxxxxxxxxxx
ContractAnalyzerStack.IdentityPoolId = REGION:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ContractAnalyzerStack.BucketName = contractanalyzerstack-contractsbucket...
ContractAnalyzerStack.FrontendURL = https://dxxxxxxxxxxxxx.cloudfront.net
```

**Note the region** - you'll need it for frontend configuration.

### Step 4: Configure Frontend

Edit `frontend/src/aws-config.js` with values from CDK outputs:

```javascript
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'YOUR_USER_POOL_ID',        // From CDK output
      userPoolClientId: 'YOUR_CLIENT_ID',      // From CDK output
      identityPoolId: 'YOUR_IDENTITY_POOL_ID', // From CDK output
      region: 'YOUR_DEPLOYMENT_REGION'         // Match backend region!
    }
  },
  API: {
    REST: {
      ContractAnalyzer: {
        endpoint: 'YOUR_API_URL',              // From CDK output
        region: 'YOUR_DEPLOYMENT_REGION'       // Match backend region!
      }
    }
  },
  Storage: {
    S3: {
      bucket: 'YOUR_BUCKET_NAME',              // From CDK output
      region: 'us-west-2'
    }
  }
};
```

### Step 5: Deploy Frontend

```bash
# From project root
./deploy-frontend.sh
```

This script:
1. Builds React app
2. Uploads to S3
3. Invalidates CloudFront cache
4. Shows your live URL

### Step 6: Create First User

1. Open CloudFront URL in browser
2. Click "Sign Up"
3. Enter email and password
4. Verify email (check inbox)
5. Login and start using!

---

## Features & Usage

### User Authentication

**Sign Up:**
- Email address (verified)
- Password requirements:
  - Minimum 8 characters
  - Uppercase and lowercase
  - Numbers and symbols

**Login:**
- Email and password
- Session persists in browser
- Auto-logout after inactivity

### Contract Upload

**Supported Files:**
- PDF format only
- Maximum size: 100MB
- Filename automatically sanitized

**Upload Process:**
1. Click "Upload Contract"
2. Select PDF file
3. File uploads directly to S3
4. Analysis starts automatically
5. Status updates in real-time

### Contract Analysis

**Processing Time:**
- Small contracts (1-10 pages): 30-60 seconds
- Medium contracts (10-50 pages): 1-3 minutes
- Large contracts (50+ pages): 3-5 minutes

**Extracted Information:**
- **Title** - Professional contract title
- **Executive Summary** - 2-3 sentence overview
- **Key Terms** - Type, parties, value, duration
- **Commitments** - Payment, packaging, inventory, labeling, portal
- **Contacts** - Names, roles, contact info
- **Action Items** - Tasks with deadlines and priority
- **Risk Factors** - Compliance issues, notable clauses

### Interactive Chat

**Features:**
- Ask questions about contract
- Get contextual answers
- Conversation history maintained
- Markdown formatting support

**Example Questions:**
- "What are the payment terms?"
- "Who are the key contacts?"
- "Summarize the termination clause"
- "What are the penalties for late delivery?"

**Chat Interface:**
- Floating button (bottom-right)
- Modal overlay
- Suggested starter questions
- Clear chat option

---

## API Reference

### Base URL
```
https://xxx.execute-api.us-west-2.amazonaws.com/prod/
```

### Authentication
All endpoints require Cognito ID token in Authorization header:
```
Authorization: <cognito-id-token>
```

### Endpoints

#### POST /contracts
Initialize contract upload

**Request:**
```json
{
  "fileName": "contract.pdf",
  "fileSize": 1048576
}
```

**Response:**
```json
{
  "contractId": "uuid",
  "bucketName": "bucket-name",
  "s3Key": "contracts/uuid/contract.pdf"
}
```

#### GET /contracts
List user's contracts

**Response:**
```json
{
  "contracts": [
    {
      "contractId": "uuid",
      "fileName": "contract.pdf",
      "timestamp": "2025-11-26T12:00:00Z",
      "status": "analyzed",
      "analysis": {
        "title": "Contract Title"
      }
    }
  ]
}
```

#### GET /contracts/{contractId}/results
Get analysis results

**Response:**
```json
{
  "contractId": "uuid",
  "fileName": "contract.pdf",
  "timestamp": "2025-11-26T12:00:00Z",
  "analysis": {
    "title": "...",
    "executiveSummary": "...",
    "keyTerms": {...},
    "keyCommitments": {...},
    "contacts": [...],
    "actionItems": [...],
    "riskFactors": [...],
    "confidenceScore": 0.95
  }
}
```

#### POST /contracts/{contractId}/chat
Chat with contract

**Request:**
```json
{
  "contractId": "uuid",
  "message": "What are the payment terms?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Response:**
```json
{
  "message": "The payment terms are...",
  "contractId": "uuid"
}
```

---

## Security

### Authentication & Authorization
- **Cognito User Pool** - User authentication
- **Cognito Identity Pool** - AWS credentials for S3 access
- **API Gateway Authorizer** - Validates JWT tokens
- **IAM Policies** - Least privilege access

### Data Protection
- **Encryption at Rest** - S3 (AES256), DynamoDB (AWS managed)
- **Encryption in Transit** - HTTPS/TLS everywhere
- **Data Isolation** - Users can only access their own contracts
- **S3 Versioning** - Recover from accidental deletions

### Input Validation
- **Filename Sanitization** - Prevents path traversal
- **File Type Validation** - PDF magic number check
- **Size Limits** - 100MB files, 10KB messages
- **Rate Limiting** - 100 requests/second per user

### Security Best Practices
- Strong password policy enforced
- Email verification required
- Private S3 buckets (no public access)
- CloudFront OAI for secure access
- No sensitive data in logs
- Generic error messages to users

### Monitoring
- CloudWatch Logs for all Lambda functions
- API Gateway access logs
- Failed authentication attempts logged
- Unusual activity patterns detectable

---

## Troubleshooting

### Upload Issues

**Problem:** Upload fails immediately
- **Check:** File size under 100MB
- **Check:** File is actually a PDF
- **Check:** Browser console for errors
- **Solution:** Try smaller file or different browser

**Problem:** Upload succeeds but analysis never starts
- **Check:** S3 event notification configured
- **Check:** Lambda has permissions
- **Solution:** Redeploy backend: `cd backend && cdk deploy`

### Analysis Issues

**Problem:** Analysis stuck in "processing"
- **Check:** Lambda logs: `aws logs tail /aws/lambda/ContractAnalyzerStack-AnalyzeFunction --follow`
- **Common causes:**
  - Textract timeout (large PDFs)
  - Bedrock model access denied
  - Invalid PDF format
- **Solution:** Check logs for specific error

**Problem:** Analysis fails with error
- **Check:** PDF is valid and not corrupted
- **Check:** Bedrock model access in IAM
- **Solution:** Re-upload contract

### Regional Deployment Issues

**Problem:** Bedrock AccessDeniedException
- **Error:** "User is not authorized to perform: bedrock:InvokeModel"
- **Causes:**
  1. Model not available in your region
  2. Haven't requested model access in Bedrock console
  3. Region mismatch between frontend and backend
- **Solutions:**
  1. Check [Bedrock model availability](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)
  2. Request access: Bedrock Console → Model Access → Request Access
  3. Verify all `region` fields in `aws-config.js` match your deployment region
  4. Redeploy: `cd backend && cdk deploy`

**Problem:** Frontend can't connect to API
- **Check:** API endpoint region matches frontend config
- **Check:** All region fields in `aws-config.js` are consistent
- **Solution:** Update `aws-config.js` with correct region from CDK outputs

**Problem:** S3 upload fails with region error
- **Check:** S3 bucket region matches frontend config
- **Check:** Identity Pool region matches User Pool region
- **Solution:** Ensure all AWS resources are in the same region

### Chat Issues

**Problem:** Chat button doesn't appear
- **Check:** Contract status is "analyzed"
- **Check:** Browser console for errors
- **Solution:** Refresh page

**Problem:** Chat responses are slow
- **Normal:** First response takes 5-10 seconds
- **Check:** Contract text size (large = slower)
- **Solution:** This is expected behavior

**Problem:** Chat returns error
- **Check:** Contract has extracted text in S3
- **Check:** Bedrock permissions
- **Solution:** Re-analyze contract

### Frontend Issues

**Problem:** CloudFront shows 403 Forbidden
- **Cause:** No files in S3 bucket
- **Solution:** Run `./deploy-frontend.sh`

**Problem:** Login doesn't work
- **Check:** Cognito configuration in aws-config.js
- **Check:** User Pool and Client IDs are correct
- **Solution:** Verify configuration matches CDK outputs

**Problem:** API calls fail with CORS error
- **Check:** API Gateway CORS configuration
- **Solution:** Should work by default (wildcard CORS)

### Performance Issues

**Problem:** Slow page loads
- **Check:** CloudFront cache hit ratio
- **Solution:** Wait for cache to warm up (first load is slow)

**Problem:** High costs
- **Check:** CloudWatch metrics for Bedrock/Textract usage
- **Check:** Number of contracts processed
- **Solution:** Implement usage limits or alerts

---

## Cost Optimization

### Detailed Cost Breakdown

**Per Contract Processing:**
- Textract: $0.015 (10 pages × $1.50/1000 pages)
- Bedrock Analysis: $0.135 (20K input + 5K output tokens)
- Lambda: $0.005 (30 seconds × 512MB)
- S3 Storage: $0.002 (100MB × $0.023/GB)
- DynamoDB: $0.001 (10 writes + 100 reads)
- **Total per contract: ~$0.16**

**Per Chat Interaction:**
- Bedrock: $0.06 (10K input + 2K output tokens)
- Lambda: $0.001 (5 seconds × 512MB)
- DynamoDB: $0.0001 (1 read)
- **Total per chat: ~$0.06**

### Optimization Strategies

#### 1. Reduce Bedrock Costs (70% of total cost)

**Current Usage:**
- Contract analysis: 20K input tokens
- Chat context: 50K characters (~10K tokens)

**Optimizations:**
```python
# In analyze.py - reduce input tokens
contract_text[:10000]  # Instead of [:15000]
# Savings: 25% reduction = $0.03 per analysis

# In chat.py - reduce context size
raw_text[:30000]  # Instead of [:50000]
# Savings: 40% reduction = $0.024 per chat
```

**Potential Savings: $8-10/month for 100 contracts**

#### 2. Reduce Textract Costs

**Current:** Process all pages
**Optimization:** Limit to first 20 pages for large contracts

```python
# Add to analyze.py
MAX_PAGES = 20
# Savings: 30-50% for large contracts
```

**Potential Savings: $0.50-1.00/month for 100 contracts**

#### 3. Optimize Lambda Memory

**Current:** 512MB-1024MB
**Test:** Try 256MB for upload/list/results functions

```python
# In CDK stack
memory_size=256  # Instead of 512
# Savings: 50% on Lambda costs
```

**Potential Savings: $0.25/month**

#### 4. Implement Caching

**Response Caching:**
```python
# Cache common questions
cache = {
    "payment terms": cached_response,
    "key dates": cached_response
}
# Savings: 20-30% on chat costs
```

**Potential Savings: $1-2/month**

#### 5. S3 Lifecycle Policies

**Delete old extracted text after 90 days:**
```python
# In CDK stack
contracts_bucket.add_lifecycle_rule(
    expiration=Duration.days(90),
    prefix="contracts/*/extracted_text.txt"
)
```

**Potential Savings: $0.10-0.20/month**

### Cost Monitoring & Alerts

#### Set Up Budget Alerts

```bash
# Create monthly budget
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json

# budget.json
{
  "BudgetName": "ContractAnalyzerBudget",
  "BudgetLimit": {
    "Amount": "50",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

#### CloudWatch Cost Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name contract-analyzer-cost-alert \
  --alarm-description "Alert when costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:billing-alerts
```

#### Track Costs by Service

```bash
# Get cost breakdown
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Cost Comparison by Scale

| Contracts/Month | Without Optimization | With Optimization | Savings |
|-----------------|---------------------|-------------------|---------|
| 10 | $5 | $3.50 | 30% |
| 50 | $16 | $11 | 31% |
| 100 | $26 | $18 | 31% |
| 500 | $132 | $90 | 32% |
| 1000 | $259 | $180 | 31% |

### Reserved Capacity (Enterprise)

For 500+ contracts/month, consider:

**Bedrock Provisioned Throughput:**
- Fixed monthly cost for guaranteed capacity
- 30-50% savings vs on-demand
- Requires commitment

**DynamoDB Reserved Capacity:**
- 1-year or 3-year commitment
- 50-75% savings
- Good for predictable workloads

### Free Tier Maximization

**First 12 Months:**
- Lambda: 1M requests/month (covers ~10K contracts)
- DynamoDB: 25GB + 25 WCU + 25 RCU (covers ~50K contracts)
- S3: 5GB storage (covers ~50 contracts)
- CloudFront: 1TB transfer (covers ~100K page views)

**Always Free:**
- Cognito: First 50K MAU
- API Gateway: First 1M requests (12 months)

**Effective Cost with Free Tier (100 contracts/month):**
- Textract: $1.50
- Bedrock: $22.40
- Other services: $0 (covered by free tier)
- **Total: ~$24/month**

### Cost Optimization Checklist

- [ ] Set up billing alerts ($50 threshold)
- [ ] Enable Cost Explorer
- [ ] Tag all resources for cost tracking
- [ ] Implement Bedrock token limits
- [ ] Add response caching for common questions
- [ ] Set S3 lifecycle policies
- [ ] Optimize Lambda memory allocation
- [ ] Monitor daily costs in CloudWatch
- [ ] Review monthly cost reports
- [ ] Consider reserved capacity at scale

---

## Maintenance

### Regular Tasks

**Weekly:**
- Review CloudWatch logs for errors
- Check cost dashboard
- Monitor user activity

**Monthly:**
- Update dependencies (npm, pip)
- Review and optimize Lambda memory
- Clean up old test data

**Quarterly:**
- Security audit
- Performance review
- Cost optimization review

### Backup & Recovery

**Automated Backups:**
- DynamoDB: Point-in-time recovery enabled
- S3: Versioning enabled

**Manual Backup:**
```bash
# Export DynamoDB table
aws dynamodb export-table-to-point-in-time \
  --table-arn <table-arn> \
  --s3-bucket <backup-bucket>

# Sync S3 bucket
aws s3 sync s3://source-bucket s3://backup-bucket
```

### Disaster Recovery

**RTO (Recovery Time Objective):** 1 hour
**RPO (Recovery Point Objective):** 5 minutes

**Recovery Steps:**
1. Restore DynamoDB from point-in-time
2. Restore S3 from versioning
3. Redeploy CDK stack if needed
4. Verify functionality

---

## Advanced Topics

### Multi-Region Deployment

To deploy in multiple regions:
1. Update CDK stack with region parameter
2. Deploy to each region separately
3. Use Route53 for failover

### Custom Domain

1. Register domain in Route53
2. Request ACM certificate (us-east-1)
3. Add domain to CloudFront distribution
4. Update DNS records

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node
        uses: actions/setup-node@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Deploy Backend
        run: |
          cd backend
          pip install -r requirements.txt
          ./build_layer.sh
          cdk deploy --require-approval never
      - name: Deploy Frontend
        run: ./deploy-frontend.sh
```

### Monitoring Dashboard

Create CloudWatch dashboard:
```bash
aws cloudwatch put-dashboard \
  --dashboard-name ContractAnalyzer \
  --dashboard-body file://dashboard.json
```

---

## Support & Resources

### Documentation
- This guide
- AWS CDK: https://docs.aws.amazon.com/cdk/
- Amazon Bedrock: https://docs.aws.amazon.com/bedrock/
- Strands Framework: https://github.com/strands-ai/strands

### Getting Help
- Check troubleshooting section above
- Review CloudWatch logs
- Open GitHub issue
- Contact AWS Support

### Contributing
1. Fork repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

---

**Last Updated:** November 2025  
**Version:** 1.0.0
