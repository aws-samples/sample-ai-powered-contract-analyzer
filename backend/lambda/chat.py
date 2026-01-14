import json
import boto3
import os
from strands import Agent
from strands.models import BedrockModel

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']


def handler(event, context):
    """
    Handle chatbot interactions with contract context
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Parse request
        body = json.loads(event['body'])
        contract_id = body['contractId']
        user_message = body['message']
        conversation_history = body.get('history', [])  # Optional conversation history
        
        # Validate message size (max 10KB)
        if len(user_message) > 10000:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Message too long. Maximum 10,000 characters.'})
            }
        
        # Validate conversation history size (max 5 exchanges)
        if len(conversation_history) > 10:  # 5 exchanges = 10 messages
            conversation_history = conversation_history[-10:]
        
        # Get user ID from authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Fetch contract data from DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.query(
            KeyConditionExpression='contractId = :cid',
            ExpressionAttributeValues={':cid': contract_id},
            ScanIndexForward=False,
            Limit=1
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Contract not found'})
            }
        
        item = response['Items'][0]
        
        # Verify user owns this contract
        if item['userId'] != user_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Check if contract has been analyzed
        if item['status'] != 'analyzed' or 'textS3Key' not in item:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Contract not yet analyzed or text not available'})
            }
        
        # Retrieve raw text from S3
        text_s3_key = item['textS3Key']
        print(f"Retrieving text from S3: {text_s3_key}")
        
        try:
            text_response = s3.get_object(Bucket=BUCKET_NAME, Key=text_s3_key)
            raw_text = text_response['Body'].read().decode('utf-8')
            print(f"Retrieved {len(raw_text)} characters from S3")
        except Exception as e:
            print(f"Error retrieving text from S3: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Failed to retrieve contract text'})
            }
        
        analysis = item.get('analysis', {})
        
        # Limit contract text size to prevent excessive costs
        max_context_size = 50000
        if len(raw_text) > max_context_size:
            print(f"Contract text truncated from {len(raw_text)} to {max_context_size} characters")
            raw_text = raw_text[:max_context_size]
        
        # Create system prompt with contract context
        system_prompt = f"""You are an AI assistant helping users understand their contract. 

Contract Title: {analysis.get('title', 'N/A')}
Contract Type: {analysis.get('keyTerms', {}).get('contractType', 'N/A')}

You have access to the full contract text and analysis. Answer questions accurately based on the contract content.
If you're unsure about something, say so. Always cite specific sections or clauses when possible.

Full Contract Text:
{raw_text}

Be concise, professional, and helpful."""
        
        # Create Strands agent for conversation
        region = os.environ.get('AWS_REGION_NAME', 'us-west-2')
        model = BedrockModel(
            temperature=0.3,  # Slightly higher for more natural conversation
            streaming=False,
            region_name=region
        )
        
        agent = Agent(
            model=model,
            system_prompt=system_prompt
        )
        
        # Build conversation context if history exists
        if conversation_history:
            # Add previous messages to context
            for msg in conversation_history[-5:]:  # Keep last 5 exchanges
                if msg['role'] == 'user':
                    agent(msg['content'])
        
        # Get response for current message
        response = agent(user_message)
        bot_response = str(response)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': bot_response,
                'contractId': contract_id
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
                'error': 'An error occurred while processing your request. Please try again later.'
            })
        }
