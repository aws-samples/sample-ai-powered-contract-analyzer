// Update these values after deploying the backend
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-west-2_uRwcPL4Zq',
      userPoolClientId: 'o7pr9hg1hj8gj6sasqiumh0n4',
      identityPoolId: 'us-west-2:341eb9d3-4ceb-41cb-875c-2394e4ae1972',
      region: 'us-west-2'
    }
  },
  API: {
    REST: {
      ContractAnalyzer: {
        endpoint: 'https://ke9atav445.execute-api.us-west-2.amazonaws.com/prod/',
        region: 'us-west-2'
      }
    }
  },
  Storage: {
    S3: {
      bucket: 'contractanalyzerstack-contractsbucketf9ac583d-tuacrmwrxcbp',
      region: 'us-west-2'
    }
  }
};
