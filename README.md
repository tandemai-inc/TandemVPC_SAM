# TandemVPC_SAM
Repository for AWS SAM being used in TandemVPC


# Instructions
You need SAM cli tool (https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

## Build

	sam build --template-file template.yaml
## Package

        sam package --s3-bucket serverlessbucket --s3-prefix master/<sub-folder> --output-template-file packaged-template.yaml

## Then add to AWS Serverless Application Repository
aws sts assume-role --role-arn arn:aws:iam::xxxx:role/xxxx --profile profile --role-session-name "RoleSessionUSProd"


export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export AWS_SESSION_TOKEN=
export AWS_DEFAULT_REGION="us-east-1"

