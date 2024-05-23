import boto3
import os
import cfnresponse
import random
import string
import time

def create_physical_resource_id():
    alnum = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(alnum) for _ in range(16))

def delete_certificate(certificate_arn):
    print(f"Deleting ACM certificate {certificate_arn}...")
    acm = boto3.client("acm")
    max_attempts = 10
    sleep_time = 60
    for attempt in range(1, max_attempts+1):
        try:
            acm.delete_certificate(CertificateArn=certificate_arn)
            break
        except acm.exceptions.ResourceInUseException as e:
            print(f"(Attempt {attempt}/{max_attempts}) Cannot delete ACM certificate because it is in use. Retrying in {sleep_time} seconds...")
        if attempt == max_attempts:
            raise Exception(f"Cannot delete certificate {certificate_arn}: {e}")
        else:
            time.sleep(sleep_time)
        
def lambda_handler(event, context):
    print(f"Context: {context}")
    print(f"Event: {event}")
    print(f"Boto version: {boto3.__version__}")

    response_data = {}
    reason = None
    response_status = cfnresponse.SUCCESS

    physical_resource_id = event.get("PhysicalResourceId", create_physical_resource_id())

    try:
        if event['RequestType'] == 'Delete':
            certificate_arn = event['ResourceProperties']['DomainCertificateArn']
            delete_certificate(certificate_arn)
    except Exception as e:
        response_status = cfnresponse.FAILED
        reason = str(e)
    cfnresponse.send(event, context, response_status, response_data, physical_resource_id, reason)