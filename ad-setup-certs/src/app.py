import boto3
import os
import cfnresponse
import random
import string


def create_physical_resource_id():
    alnum = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(alnum) for _ in range(16))

def import_certificate(certificate_secret_arn, private_key_secret_arn, tags):
    acm = boto3.client("acm")
    sm = boto3.client("secretsmanager")
    print('Reading secrets from Secrets Manager...')
    domain_certificate = sm.get_secret_value(SecretId=certificate_secret_arn)["SecretString"]
    domain_private_key = sm.get_secret_value(SecretId=private_key_secret_arn)["SecretString"]
    print('Importing certificate into ACM...')
    certificate_arn = acm.import_certificate(
        Certificate=domain_certificate, PrivateKey=domain_private_key, Tags=tags
    )["CertificateArn"]
    return certificate_arn

def lambda_handler(event, context):
    print(f"Context: {context}")
    print(f"Event: {event}")
    print(f"Boto version: {boto3.__version__}")

    certificate_secret_arn = event['ResourceProperties']['DomainCertificateSecretArn']
    private_key_secret_arn = event['ResourceProperties']['DomainPrivateKeySecretArn']
    tags = [{ 'Key': 'StackId', 'Value': event['StackId']}]

    response_data = {}
    reason = None
    response_status = cfnresponse.SUCCESS

    physical_resource_id = event.get("PhysicalResourceId", create_physical_resource_id())

    try:
        if event['RequestType'] == 'Create':
            certificate_arn = import_certificate(certificate_secret_arn, private_key_secret_arn, tags)
            response_data['DomainCertificateArn'] = certificate_arn
            response_data['Message'] = f"Resource creation successful! ACM certificate imported: {certificate_arn}"
    except Exception as e:
        response_status = cfnresponse.FAILED
        reason = str(e)
    cfnresponse.send(event, context, response_status, response_data, physical_resource_id, reason)