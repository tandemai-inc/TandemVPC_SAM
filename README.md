# TandemVPC_SAM
Repository for AWS SAM being used in TandemVPC


# Instructions
You need SAM cli tool (https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

## Build

	sam build --template-file template.yaml
## Package

        sam package --s3-bucket tandemserverless --s3-prefix master/<sub-folder> --output-template-file packaged-template.yaml

## Then add to AWS Serverless Application Repository
