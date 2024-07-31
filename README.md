# TandemVPC_SAM
Repository for AWS SAM being used in TandemVPC


# Instructions
You need SAM cli tool (https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

## Build

	sam build --template-file template.yaml
## Package

        sam package --s3-bucket tandemserverless --s3-prefix master/<sub-folder> --output-template-file packaged-template.yaml

## Then add to AWS Serverless Application Repository


### assume role
aws sts assume-role --role-arn arn:aws:iam::258001727749:role/owner --profile tandem_us --role-session-name "RoleSessionUSProd"


export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export AWS_SESSION_TOKEN=
export AWS_DEFAULT_REGION="us-east-1"