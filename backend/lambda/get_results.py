import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']


def convert_decimal_to_float(obj):
    """Convert Decimal values to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def handler(event, context):
    try:
        contract_id = event['pathParameters']['contractId']
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        table = dynamodb.Table(TABLE_NAME)
        
        # Query all items for this contract
        response = table.query(
            KeyConditionExpression='contractId = :cid',
            ExpressionAttributeValues={':cid': contract_id},
            ScanIndexForward=False
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
        
        # Verify user owns this contract
        if response['Items'][0].get('userId') != user_id:
            return {
                'statusCode': 403,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Unauthorized access to this contract'})
            }
        
        # Get the most recent analyzed version
        analyzed_items = [item for item in response['Items'] if item.get('status') == 'analyzed']
        
        if not analyzed_items:
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'contractId': contract_id,
                    'status': 'pending',
                    'message': 'Analysis not yet complete'
                })
            }
        
        latest_analysis = analyzed_items[0]
        
        # Convert Decimal to float for JSON serialization
        result_data = {
            'contractId': contract_id,
            'fileName': latest_analysis['fileName'],
            'timestamp': latest_analysis['timestamp'],
            'analysis': convert_decimal_to_float(latest_analysis.get('analysis', {}))
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result_data)
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
            'body': json.dumps({'error': 'An error occurred while fetching results. Please try again.'})
        }
