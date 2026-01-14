#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.contract_analyzer_stack import ContractAnalyzerStack

app = cdk.App()

# Get region from environment variable (set by CodeBuild/CloudShell)
# Falls back to CDK context, then to us-west-2 as last resort
region = os.environ.get("AWS_REGION") or \
         os.environ.get("AWS_DEFAULT_REGION") or \
         app.node.try_get_context("region") or \
         "us-west-2"

ContractAnalyzerStack(app, "ContractAnalyzerStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=region
    )
)

app.synth()
