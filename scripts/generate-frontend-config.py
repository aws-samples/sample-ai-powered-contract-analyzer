#!/usr/bin/env python3
"""
Generate frontend AWS configuration from CDK outputs
This script reads CloudFormation outputs and generates aws-config.js
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 generate-frontend-config.py <cdk-outputs.json> <output-file>")
        sys.exit(1)
    
    outputs_file = sys.argv[1]
    config_file = sys.argv[2]
    
    # Read CDK outputs
    print(f"Reading CDK outputs from {outputs_file}...")
    with open(outputs_file, 'r') as f:
        outputs = json.load(f)
    
    # Parse outputs into a dictionary
    output_dict = {}
    for output in outputs:
        output_dict[output['OutputKey']] = output['OutputValue']
    
    # Extract required values
    user_pool_id = output_dict.get('UserPoolId')
    user_pool_client_id = output_dict.get('UserPoolClientId')
    identity_pool_id = output_dict.get('IdentityPoolId')
    api_url = output_dict.get('ApiUrl')
    bucket_name = output_dict.get('BucketName')
    
    # Validate all required values are present
    if not all([user_pool_id, user_pool_client_id, identity_pool_id, api_url, bucket_name]):
        print("❌ Error: Missing required CDK outputs")
        print(f"Available outputs: {list(output_dict.keys())}")
        sys.exit(1)
    
    # Extract region from User Pool ID (format: region_xxxxxxxxx)
    region = user_pool_id.split('_')[0]
    
    print(f"✓ User Pool ID: {user_pool_id}")
    print(f"✓ User Pool Client ID: {user_pool_client_id}")
    print(f"✓ Identity Pool ID: {identity_pool_id}")
    print(f"✓ API URL: {api_url}")
    print(f"✓ Bucket Name: {bucket_name}")
    print(f"✓ Region: {region}")
    
    # Generate aws-config.js content
    config_content = f"""// Auto-generated AWS configuration
// Generated from CDK outputs by scripts/generate-frontend-config.py
// DO NOT EDIT MANUALLY - This file is overwritten on each deployment

export const awsConfig = {{
  Auth: {{
    Cognito: {{
      userPoolId: '{user_pool_id}',
      userPoolClientId: '{user_pool_client_id}',
      identityPoolId: '{identity_pool_id}',
      region: '{region}'
    }}
  }},
  API: {{
    REST: {{
      ContractAnalyzer: {{
        endpoint: '{api_url}',
        region: '{region}'
      }}
    }}
  }},
  Storage: {{
    S3: {{
      bucket: '{bucket_name}',
      region: '{region}'
    }}
  }}
}};
"""
    
    # Write to output file
    print(f"\nWriting configuration to {config_file}...")
    output_path = Path(config_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print("✅ Frontend configuration generated successfully!")


if __name__ == '__main__':
    main()
