import boto3
import os
import cfnresponse
import time
import random
import string

def create_physical_resource_id():
    alnum = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(alnum) for _ in range(16))

def redact_keys(event: dict, redactions: set):
    ret = {}
    for k in event.keys():
        if k in redactions:
            ret[k] = "[REDACTED]"
        else:
            ret[k] = redact_keys(event[k], redactions) if type(event[k]) is dict else event[k] # handle nesting
    return ret

def lambda_handler(event, context):
    ds = boto3.client("ds")
    sm = boto3.client("secretsmanager")

    print(redact_keys(event, {"ReadOnlyPassword", "AdminPassword"}))
    print( 'boto version {}'.format(boto3.__version__))

    directory_id = event['ResourceProperties']['DirectoryId']
    
    read_only_arn = event['ResourceProperties']['ReadOnlyPassword']
    admin_pass_arn = event['ResourceProperties']['AdminPassword']
    read_only_password = sm.get_secret_value(SecretId=read_only_arn)["SecretString"]
    admin_password = sm.get_secret_value(SecretId=admin_pass_arn)["SecretString"]
    
    
    response_data = {}
    reason = None
    response_status = cfnresponse.SUCCESS

    if event['RequestType'] == 'Create':
        response_data['Message'] = 'Resource creation successful!'
        physical_resource_id = create_physical_resource_id()
        ds.reset_user_password(DirectoryId=directory_id, UserName='ReadOnlyUser', NewPassword=read_only_password)
        ds.reset_user_password(DirectoryId=directory_id, UserName='Admin', NewPassword=admin_password)
        ds.reset_user_password(DirectoryId=directory_id, UserName='tandemviz', NewPassword=admin_password)
        time.sleep(30)
    else:
        physical_resource_id = event['PhysicalResourceId']
    cfnresponse.send(event, context, response_status, response_data, physical_resource_id, reason)