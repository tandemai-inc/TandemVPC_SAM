import json
import os
import boto3
from ldap3 import Server, Connection, ALL
import cfnresponse
import uuid

def get_secret(secret_name):
    #region_name = "us-west-2"
    region_name = os.environ['AWS_REGION']
    client = boto3.client("secretsmanager", region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        print(f"Retrieved secret: {secret}")

        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return {"admin_password": secret}
    except Exception as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        raise

def create_user(conn, dn, user_attributes, ad_search_base):
    try:
        search_filter = f"(cn={user_attributes['cn']})"
        if conn.search(search_base=ad_search_base, search_filter=search_filter, search_scope='SUBTREE', attributes='cn'):
            print(f"User {dn} already exists")
        else:
            conn.add(dn, attributes=user_attributes)
            if conn.result['description'] == 'success':
                print(f"User {dn} created successfully")
            else:
                print(f"Failed to add user: {conn.result}")
    except Exception as e:
        print(f"Error creating user {dn}: {e}")
        raise

def lambda_handler(event, context):
    print("lambda location", os.getcwd())

    print("Lambda function is starting")
    print(f"Event received: {json.dumps(event)}")
    response_status = cfnresponse.SUCCESS
    response_data = {}
    region_name = os.environ['AWS_REGION']
    sm = boto3.client("secretsmanager", region_name=region_name)
    try:
        properties = event.get('ResourceProperties', {})
        admin_secret_arn = properties.get('AdminSecretArn')
        readonly_secret_arn = properties.get('ADReadOnlySecretArn')
        directory_domain = properties.get('DirectoryDomain')
        dns_ip1 = properties.get('DnsIp1')
        dns_ip2 = properties.get('DnsIp2')
        directory_id = properties.get('DirectoryId')
        ad_search_base = properties.get('SearchBase') # OU=Users,OU=example,DC=example,DC=com
        admin_dn = f"cn=Admin,{ad_search_base}"

        if not all([admin_secret_arn, readonly_secret_arn, directory_domain, dns_ip1, dns_ip2, directory_id]):
            raise KeyError("One or more required properties are missing")

        admin_password = sm.get_secret_value(SecretId=admin_secret_arn)["SecretString"]
        readonly_password = sm.get_secret_value(SecretId=readonly_secret_arn)["SecretString"]
        tandemviz_password = readonly_password

        server_address = f"ldap://{dns_ip1}"
        server = Server(server_address, get_info=ALL, use_ssl=False)
        conn = Connection(server, admin_dn, admin_password, auto_bind=True)

        if conn.bind():
            print("Bind successful")
        else:
            print(f"Bind failed: {conn.result}")


        readonly_user_dn = f"CN=ReadOnlyUser,{ad_search_base}"
        readonly_user_attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': 'ReadOnlyUser',
            'sn': 'User',
            'userPassword': readonly_password,
            'sAMAccountName': 'ReadOnlyUser'
        }
        create_user(conn, readonly_user_dn, readonly_user_attributes, ad_search_base)
        response_data['ReadOnlyUserPassword'] = readonly_password

        tandemviz_user_dn = f"CN=tandemviz,{ad_search_base}"
        tandemviz_user_attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': 'tandemviz',
            'sn': 'User',
            'userPassword': tandemviz_password,
            'sAMAccountName': 'tandemviz'
        }
        create_user(conn, tandemviz_user_dn, tandemviz_user_attributes, ad_search_base)
        response_data['TandemvizPassword'] = tandemviz_password

    except KeyError as e:
        print(f"KeyError: {e}")
        response_status = cfnresponse.FAILED
        response_data['Error'] = f"KeyError: {e}"
    except Exception as e:
        print(f"An error occurred: {e}")
        response_status = cfnresponse.FAILED
        response_data['Error'] = f"Exception: {e}"
    finally:
        if 'ResponseURL' in event:
            cfnresponse.send(event, context, response_status, response_data)
        else:
            print("Test complete without ResponseURL")

    return {
        'statusCode': 200,
        'body': json.dumps('Check complete')
    }
