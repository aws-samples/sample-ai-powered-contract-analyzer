import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
from strands import Agent
from strands.models import BedrockModel

s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']


def convert_floats_to_decimal(obj):
    """Convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

ANALYSIS_PROMPT = """Analyze the following contract and extract:

1. Professional Title: Extract a clear, professional title for this contract (e.g., "Master Supply Agreement with ABC Corp", "Software License Agreement - Enterprise Plan")
2. Executive Summary (2-3 sentences)
3. Key Contract Terms:
   - Contract type
   - Parties involved
   - Contract value/amount
   - Duration/term
4. Key Commitments:
   - Payment terms and schedules
   - Packaging requirements and specifications
   - Inventory targets and minimum stock levels
   - Labeling specifications and compliance requirements
   - Portal requirements and system access obligations
5. Points of Contact:
   - Names, roles, and contact information
6. Action Items and Deadlines:
   - Key dates and milestones
7. Risk Factors:
   - Potential compliance issues
   - Notable clauses or obligations

Contract text:
{contract_text}

Provide the analysis in JSON format with the following structure:
{{
  "title": "Professional contract title",
  "executiveSummary": "...",
  "keyTerms": {{
    "contractType": "...",
    "parties": ["..."],
    "value": "...",
    "duration": "..."
  }},
  "keyCommitments": {{
    "paymentTerms": "...",
    "packagingRequirements": "...",
    "inventoryTargets": "...",
    "labelingSpecifications": "...",
    "portalRequirements": "..."
  }},
  "contacts": [
    {{"name": "...", "role": "...", "contact": "..."}}
  ],
  "actionItems": [
    {{"item": "...", "deadline": "...", "priority": "..."}}
  ],
  "riskFactors": ["..."],
  "confidenceScore": 0.0-1.0
}}
"""

def validate_pdf_file(bucket, key):
    """Validate that the file is actually a PDF by checking magic number"""
    try:
        # Read first 4 bytes to check PDF magic number
        response = s3.get_object(Bucket=bucket, Key=key, Range='bytes=0-3')
        magic_bytes = response['Body'].read()
        
        # PDF files start with %PDF (hex: 25 50 44 46)
        if magic_bytes != b'%PDF':
            raise ValueError("File is not a valid PDF")
        
        return True
    except Exception as e:
        print(f"PDF validation failed: {str(e)}")
        raise

def extract_text_with_textract(bucket, key):
    """Extract text from PDF using Amazon Textract"""
    print(f"Starting Textract analysis for {bucket}/{key}")
    
    # Validate file is actually a PDF
    validate_pdf_file(bucket, key)
    
    # Start document text detection
    response = textract.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        }
    )
    
    job_id = response['JobId']
    print(f"Textract job started: {job_id}")
    
    # Wait for job to complete
    import time
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        result = textract.get_document_text_detection(JobId=job_id)
        status = result['JobStatus']
        
        print(f"Textract job status: {status}")
        
        if status == 'SUCCEEDED':
            # Extract text from all pages
            text = ""
            next_token = None
            
            while True:
                if next_token:
                    result = textract.get_document_text_detection(
                        JobId=job_id,
                        NextToken=next_token
                    )
                
                for block in result['Blocks']:
                    if block['BlockType'] == 'LINE':
                        text += block['Text'] + '\n'
                
                next_token = result.get('NextToken')
                if not next_token:
                    break
            
            print(f"Extracted {len(text)} characters from PDF")
            return text
            
        elif status == 'FAILED':
            raise Exception(f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}")
        
        time.sleep(5)
        attempt += 1
    
    raise Exception("Textract job timed out")

def analyze_with_strands(contract_text):
    """Use Strands Agents Framework for cleaner Bedrock interaction"""
    prompt = ANALYSIS_PROMPT.format(contract_text=contract_text[:15000])  # Limit text size
    
    # Create agent with temperature=0 for deterministic, factual analysis
    # Disable streaming since this is async Lambda (no client connection)
    region = os.environ.get('AWS_REGION_NAME', 'us-west-2')
    model = BedrockModel(
        temperature=0,
        streaming=False,  # Use non-streaming for async Lambda
        region_name=region
    )
    
    agent = Agent(
        model=model,
        system_prompt="You are an expert contract analyzer. Always respond with valid JSON. Extract only factual information from the contract text."
    )
    
    # Get analysis
    response = agent(prompt)
    
    # Extract JSON from response
    content = str(response)
    start_idx = content.find('{')
    end_idx = content.rfind('}') + 1
    json_str = content[start_idx:end_idx]
    
    return json.loads(json_str)

def handler(event, context):
    """
    Triggered by S3 upload event - processes contract asynchronously
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Handle S3 event trigger
        if 'Records' in event and event['Records'][0]['eventSource'] == 'aws:s3':
            # S3 event trigger
            s3_event = event['Records'][0]['s3']
            bucket = s3_event['bucket']['name']
            s3_key = s3_event['object']['key']
            
            print(f"S3 Event: {bucket}/{s3_key}")
            
            # Skip if this is an extracted text file (not a PDF)
            if s3_key.endswith('extracted_text.txt'):
                print(f"Skipping extracted text file: {s3_key}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Skipped non-PDF file'})
                }
            
            # Only process PDF files
            if not s3_key.lower().endswith('.pdf'):
                print(f"Skipping non-PDF file: {s3_key}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Skipped non-PDF file'})
                }
            
            # Extract contractId from S3 key (contracts/{contractId}/{filename})
            parts = s3_key.split('/')
            if len(parts) < 3 or parts[0] != 'contracts':
                print(f"Invalid S3 key format: {s3_key}")
                return
            
            contract_id = parts[1]
            print(f"Processing contract: {contract_id}")
        else:
            # Manual API trigger (fallback)
            body = json.loads(event['body'])
            contract_id = body['contractId']
            bucket = BUCKET_NAME
            print(f"Manual trigger for contract: {contract_id}")
        
        table = dynamodb.Table(TABLE_NAME)
        
        # Query to get the latest item for this contractId
        print(f"Querying DynamoDB for contract: {contract_id}")
        response = table.query(
            KeyConditionExpression='contractId = :cid',
            ExpressionAttributeValues={':cid': contract_id},
            ScanIndexForward=False,
            Limit=1
        )
        
        if not response['Items']:
            raise Exception(f'Contract not found: {contract_id}')
        
        item = response['Items'][0]
        print(f"Found contract: {item['fileName']}, status: {item['status']}")
        
        # Update status to processing
        table.update_item(
            Key={
                'contractId': contract_id,
                'timestamp': item['timestamp']
            },
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'processing'}
        )
        
        s3_key = item['s3Key']
        print(f"S3 Key: {s3_key}")
        
        # Extract text using Textract
        print("Extracting text from PDF using Textract...")
        contract_text = extract_text_with_textract(BUCKET_NAME, s3_key)
        print(f"Extracted {len(contract_text)} characters")
        
        # Analyze with Strands Agents Framework
        print("Calling Bedrock via Strands for analysis...")
        analysis_result = analyze_with_strands(contract_text)
        print("Analysis complete")
        
        # Store raw text in S3 (to avoid DynamoDB 400KB limit)
        text_s3_key = f"contracts/{contract_id}/extracted_text.txt"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=text_s3_key,
            Body=contract_text.encode('utf-8'),
            ContentType='text/plain',
            ServerSideEncryption='AES256'  # Encrypt at rest
        )
        print(f"Stored extracted text in S3: {text_s3_key}")
        
        # Update the existing DynamoDB record with analysis results
        # Convert floats to Decimal for DynamoDB compatibility
        analysis_for_dynamodb = convert_floats_to_decimal(analysis_result)
        
        table.update_item(
            Key={
                'contractId': contract_id,
                'timestamp': item['timestamp']  # Use original timestamp
            },
            UpdateExpression='SET #status = :status, analysis = :analysis, textS3Key = :textKey',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'analyzed',
                ':analysis': analysis_for_dynamodb,
                ':textKey': text_s3_key
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'contractId': contract_id,
                'analysis': analysis_result
            })
        }
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error: {str(e)}")
        print(f"Traceback: {error_details}")
        # Don't expose internal errors to client
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'An error occurred while processing the contract. Please try again later.'
            })
        }
