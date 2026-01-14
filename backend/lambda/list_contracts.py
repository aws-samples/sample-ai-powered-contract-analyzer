import json
import boto3
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key

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
    """List all contracts for the authenticated user"""
    try:
        user_id = event['requestContext']['authorizer']['claims']['sub']
        table = dynamodb.Table(TABLE_NAME)
        
        # Query all contracts for this user
        # Note: This requires a GSI on userId
        response = table.scan(
            FilterExpression=Key('userId').eq(user_id)
        )
        
        # Group by contractId and get latest status for each
        contracts_map = {}
        for item in response['Items']:
            contract_id = item['contractId']
            if contract_id not in contracts_map or item['timestamp'] > contracts_map[contract_id]['timestamp']:
                contract_data = {
                    'contractId': contract_id,
                    'fileName': item['fileName'],
                    'timestamp': item['timestamp'],
                    'status': item['status'],
                    's3Key': item['s3Key']
                }
                # Include analysis data if available (for displaying title in list)
                if 'analysis' in item and item['analysis']:
                    contract_data['analysis'] = {
                        'title': item['analysis'].get('title', None)
                    }
                contracts_map[contract_id] = contract_data
        
        # Convert to list and sort by timestamp (newest first)
        contracts = sorted(
            contracts_map.values(),
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
        # Convert Decimal to float for JSON serialization
        contracts_serializable = convert_decimal_to_float(contracts)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'contracts': contracts_serializable
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
            'body': json.dumps({'error': 'An error occurred while fetching contracts. Please try again.'})
        }
