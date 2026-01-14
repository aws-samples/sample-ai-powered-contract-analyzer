import json
import boto3
import os
from datetime import datetime
import uuid

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event, context):
    """Initialize contract upload and return S3 details"""
    try:
        body = json.loads(event['body'])
        file_name = body['fileName']
        file_size = body.get('fileSize', 0)
        
        # Validate and sanitize filename
        import re
        import os
        
        # Remove any path components
        file_name = os.path.basename(file_name)
        
        # Check for path traversal attempts
        if '..' in file_name or '/' in file_name or '\\' in file_name:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Invalid filename: path traversal detected'})
            }
        
        # Sanitize filename - allow only alphanumeric, dots, hyphens, underscores
        sanitized_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file_name)
        
        # Ensure filename is not empty and has reasonable length
        if not sanitized_name or len(sanitized_name) > 255:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Invalid filename: must be 1-255 characters'})
            }
        
        # Ensure it's a PDF file
        if not sanitized_name.lower().endswith('.pdf'):
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Only PDF files are allowed'})
            }
        
        # Use sanitized filename
        file_name = sanitized_name
        
        # Validate file size (max 100MB)
        if file_size > 100 * 1024 * 1024:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'File size exceeds 100MB limit'})
            }
        
        # Get user ID from Cognito authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        contract_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        s3_key = f"contracts/{contract_id}/{file_name}"
        
        # Store initial metadata in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'contractId': contract_id,
                'timestamp': timestamp,
                'fileName': file_name,
                's3Key': s3_key,
                'status': 'uploaded',
                'userId': user_id
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
                'bucketName': BUCKET_NAME,
                's3Key': s3_key,
                'message': 'Upload details generated successfully'
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        # Don't expose internal errors to client
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'An error occurred while initializing upload. Please try again.'})
        }
