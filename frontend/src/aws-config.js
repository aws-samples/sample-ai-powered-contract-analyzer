// Update these values after deploying the backend
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'YOUR_USER_POOL_ID',
      userPoolClientId: 'YOUR_USER_POOL_CLIENT_ID',
      identityPoolId: 'YOUR_IDENTITY_POOL_ID',
      region: 'YOUR_AWS_REGION'
    }
  },
  API: {
    REST: {
      ContractAnalyzer: {
        endpoint: 'YOUR_API_GATEWAY_ENDPOINT',
        region: 'YOUR_AWS_REGION'
      }
    }
  },
  Storage: {
    S3: {
      bucket: 'YOUR_S3_BUCKET_NAME',
      region: 'YOUR_AWS_REGION'
    }
  }
};
