import cfnresponse
import boto3
import random
import string


def create_physical_resource_id():
    alnum = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(alnum) for _ in range(16))

def lambda_handler(event, context):
    ds = boto3.client("ds")
    print( 'boto version {}'.format(boto3.__version__))
    print(event)
    domain = event['ResourceProperties'].get('DomainName')
    vpc_id = event['ResourceProperties'].get('Vpc')
    directory_id = event['ResourceProperties'].get('DirectoryId')

    # Debug: Print out what is inside ResourceProperties
    print("ResourceProperties: " +  str(event['ResourceProperties']))

    directory = ds.describe_directories(DirectoryIds=[directory_id])['DirectoryDescriptions'][0]
    dns_ip_addrs = directory['DnsIpAddrs']

    response_data = {}
    reason = None
    response_status = cfnresponse.SUCCESS
    stack_id_suffix = event['StackId'].split("/")[1]

    if event['RequestType'] == 'Create':
        response_data['Message'] = 'Resource creation successful!'
        physical_resource_id = create_physical_resource_id()

        # Provide outputs
        response_data['DomainName'] = domain
        response_data['DomainShortName'] = domain.split(".")[0].upper() if domain else "N/A"
        response_data['VpcId'] = vpc_id

        response_data['DnsIpAddresses'] = dns_ip_addrs
        for i, addr in enumerate(dns_ip_addrs, start=1):
            response_data[f'DnsIpAddress{i}'] = addr
    else:
        physical_resource_id = event.get('PhysicalResourceId', 'N/A')

    cfnresponse.send(event, context, response_status, response_data, physical_resource_id, reason)
