from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_notifications as s3_notifications,
    aws_s3_deployment as s3_deployment,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_cognito_identitypool_alpha as cognito_identity,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    CfnOutput
)
from constructs import Construct

class ContractAnalyzerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for contract documents
        # CORS required for Amplify Storage browser uploads
        contracts_bucket = s3.Bucket(
            self, "ContractsBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[s3.CorsRule(
                allowed_methods=[
                    s3.HttpMethods.GET,
                    s3.HttpMethods.PUT,
                    s3.HttpMethods.POST,
                    s3.HttpMethods.DELETE,
                    s3.HttpMethods.HEAD
                ],
                allowed_origins=["*"],
                allowed_headers=["*"],
                exposed_headers=[
                    "ETag",
                    "x-amz-server-side-encryption",
                    "x-amz-request-id",
                    "x-amz-id-2"
                ],
                max_age=3000
            )]
        )

        # DynamoDB table for contract metadata
        contracts_table = dynamodb.Table(
            self, "ContractsTable",
            partition_key=dynamodb.Attribute(name="contractId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True
        )

        # Cognito User Pool
        user_pool = cognito.UserPool(
            self, "ContractAnalyzerUserPool",
            self_sign_up_enabled=True, # Change to False if you don't need self sign-up feature
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        user_pool_client = user_pool.add_client(
            "ContractAnalyzerClient",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            generate_secret=False
        )
        
        # Cognito Identity Pool for AWS service access (S3, etc.)
        identity_pool = cognito_identity.IdentityPool(
            self, "ContractAnalyzerIdentityPool",
            identity_pool_name="ContractAnalyzerIdentityPool",
            allow_unauthenticated_identities=False,
            authentication_providers=cognito_identity.IdentityPoolAuthenticationProviders(
                user_pools=[cognito_identity.UserPoolAuthenticationProvider(
                    user_pool=user_pool,
                    user_pool_client=user_pool_client
                )]
            )
        )
        
        # Grant authenticated users access to S3 bucket
        identity_pool.authenticated_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:PutObject",
                "s3:GetObject"
            ],
            resources=[f"{contracts_bucket.bucket_arn}/*"]
        ))
        
        # Allow listing bucket (needed for Amplify Storage)
        identity_pool.authenticated_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:ListBucket"],
            resources=[contracts_bucket.bucket_arn]
        ))

        # Lambda execution role with restricted permissions
        lambda_role = iam.Role(
            self, "ContractAnalyzerLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Bedrock permissions - broad access for any region and model
        # Allows Strands to use default model and cross-region inference profiles
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))
        
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "textract:StartDocumentTextDetection",
                "textract:GetDocumentTextDetection"
            ],
            resources=["*"]
        ))

        contracts_bucket.grant_read_write(lambda_role)
        contracts_table.grant_read_write_data(lambda_role)

        # Lambda function to initialize upload
        upload_function = lambda_.Function(
            self, "UploadFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="upload.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            role=lambda_role,
            environment={
                "BUCKET_NAME": contracts_bucket.bucket_name,
                "TABLE_NAME": contracts_table.table_name
            }
        )

        # Lambda layer with Strands Agents Framework
        dependencies_layer = lambda_.LayerVersion(
            self, "DependenciesLayer",
            code=lambda_.Code.from_asset("lambda_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Strands Agents Framework and dependencies"
        )
        
        # Lambda function for async contract analysis (triggered by S3)
        # Using Python 3.12 runtime with Strands Agents layer
        analyze_function = lambda_.Function(
            self, "AnalyzeFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="analyze.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(900),  # 15 minutes for long documents
            memory_size=1024,
            role=lambda_role,
            layers=[dependencies_layer],
            environment={
                "BUCKET_NAME": contracts_bucket.bucket_name,
                "TABLE_NAME": contracts_table.table_name,
                "AWS_REGION_NAME": self.region
            }
        )
        
        # S3 event trigger for automatic analysis on upload
        # Only trigger on PDF files to avoid triggering on extracted_text.txt
        contracts_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(analyze_function),
            s3.NotificationKeyFilter(prefix="contracts/", suffix=".pdf")
        )
        
        # Lambda function to list user's contracts
        list_contracts_function = lambda_.Function(
            self, "ListContractsFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="list_contracts.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            role=lambda_role,
            environment={
                "TABLE_NAME": contracts_table.table_name
            }
        )

        # Lambda function to get contract results
        get_results_function = lambda_.Function(
            self, "GetResultsFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="get_results.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            role=lambda_role,
            environment={
                "TABLE_NAME": contracts_table.table_name
            }
        )
        
        # Lambda function for chatbot interactions
        chat_function = lambda_.Function(
            self, "ChatFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="chat.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),
            memory_size=512,
            role=lambda_role,
            layers=[dependencies_layer],
            environment={
                "TABLE_NAME": contracts_table.table_name,
                "BUCKET_NAME": contracts_bucket.bucket_name,
                "AWS_REGION_NAME": self.region
            }
        )

        # API Gateway with Cognito authorizer and rate limiting
        api = apigw.RestApi(
            self, "ContractAnalyzerApi",
            rest_api_name="Contract Analyzer API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"]
            ),
            deploy_options=apigw.StageOptions(
                throttling_rate_limit=100,  # 100 requests per second
                throttling_burst_limit=200  # 200 concurrent requests
            )
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool]
        )

        # API endpoints
        contracts = api.root.add_resource("contracts")
        
        # Initialize upload
        contracts.add_method(
            "POST",
            apigw.LambdaIntegration(upload_function),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # List all contracts for the user
        contracts.add_method(
            "GET",
            apigw.LambdaIntegration(list_contracts_function),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        contract_resource = contracts.add_resource("{contractId}")
        
        results = contract_resource.add_resource("results")
        results.add_method(
            "GET",
            apigw.LambdaIntegration(get_results_function),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )
        
        # Chat endpoint
        chat = contract_resource.add_resource("chat")
        chat.add_method(
            "POST",
            apigw.LambdaIntegration(chat_function),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ========================================
        # Frontend Hosting (S3 + CloudFront)
        # ========================================
        
        # S3 bucket for frontend static files
        frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            public_read_access=False,  # CloudFront will access via OAI
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # CloudFront Origin Access Identity (OAI)
        # Allows CloudFront to access private S3 bucket
        oai = cloudfront.OriginAccessIdentity(
            self, "FrontendOAI",
            comment="OAI for Contract Analyzer Frontend"
        )
        
        # Grant CloudFront read access to S3 bucket
        frontend_bucket.grant_read(oai)
        
        # CloudFront distribution with HTTPS
        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    frontend_bucket,
                    origin_access_identity=oai
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                compress=True,  # Enable gzip/brotli compression
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            ),
            default_root_object="index.html",
            error_responses=[
                # Handle React Router - return index.html for all routes
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            comment="Contract Analyzer Frontend Distribution"
        )
        
        # Deploy frontend files (optional - can also deploy manually)
        # Uncomment this section after building your frontend
        # s3_deployment.BucketDeployment(
        #     self, "DeployFrontend",
        #     sources=[s3_deployment.Source.asset("../frontend/build")],
        #     destination_bucket=frontend_bucket,
        #     distribution=distribution,
        #     distribution_paths=["/*"]  # Invalidate all paths on deployment
        # )

        # Outputs
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "IdentityPoolId", value=identity_pool.identity_pool_id)
        CfnOutput(self, "BucketName", value=contracts_bucket.bucket_name)
        CfnOutput(self, "FrontendBucketName", value=frontend_bucket.bucket_name)
        CfnOutput(
            self, "FrontendURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="Frontend URL (HTTPS enabled)"
        )
        CfnOutput(
            self, "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="CloudFront Distribution ID for cache invalidation"
        )
