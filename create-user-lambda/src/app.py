import json
import os
import boto3
from ldap3 import Server, Connection, ALL
import cfnresponse
import uuid
import subprocess

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

def create_user(conn, dn, user_attributes):
    try:
        search_filter = f"(cn={user_attributes['cn']})"
        if conn.search(search_base='OU=Users,OU=tandemai,DC=tandemai,DC=com', search_filter=search_filter, search_scope='SUBTREE', attributes='cn'):
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

def create_certificate(domain):
    try:
        private_key = f"/tmp/{domain}.key"
        certificate = f"/tmp/{domain}.crt"
        cmd = [
            "/var/task/openssl",  # Reference the openssl binary correctly
            "req", "-x509", "-sha256", "-nodes", "-newkey", "rsa:2048",
            "-keyout", private_key, "-days", "365", "-out", certificate,
            "-subj", f"/CN={domain}"
        ]
        subprocess.run(cmd, check=True)
        with open(private_key, 'r') as f:
            private_key_content = f.read()
        with open(certificate, 'r') as f:
            certificate_content = f.read()
        return private_key_content, certificate_content
    except Exception as e:
        print(f"Error creating certificate for {domain}: {e}")
        raise

def lambda_handler(event, context):
    print("lambda location", os.getcwd())
    print("Lambda function is starting")
    print(f"Event received: {json.dumps(event)}")
    response_status = cfnresponse.SUCCESS
    response_data = {}

    try:
        properties = event.get('ResourceProperties', {})
        secret_name = properties.get('AdminSecretArn')
        directory_domain = properties.get('DirectoryDomain')
        dns_ip1 = properties.get('DnsIp1')
        dns_ip2 = properties.get('DnsIp2')
        directory_id = properties.get('DirectoryId')
        cert_secret_arn = properties.get('DomainCertificateSecretArn')
        key_secret_arn = properties.get('DomainPrivateKeySecretArn')

        if not all([secret_name, directory_domain, dns_ip1, dns_ip2, directory_id, cert_secret_arn, key_secret_arn]):
            raise KeyError("One or more required properties are missing")

        secret = get_secret(secret_name)
        admin_dn = secret.get("admin_dn", "Admin")
        admin_password = secret.get("admin_password")

        server_address = f"ldap://{dns_ip1}"
        server = Server(server_address, get_info=ALL, use_ssl=False)
        conn = Connection(server, admin_dn, admin_password, auto_bind=True)

        if conn.bind():
            print("Bind successful")
        else:
            print(f"Bind failed: {conn.result}")

        readonly_password = str(uuid.uuid4())
        tandemviz_password = str(uuid.uuid4())

        readonly_user_dn = "CN=ReadOnlyUser,OU=Users,OU=tandemai,DC=tandemai,DC=com"
        readonly_user_attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': 'ReadOnlyUser',
            'sn': 'User',
            'userPassword': readonly_password,
            'sAMAccountName': 'ReadOnlyUser'
        }
        create_user(conn, readonly_user_dn, readonly_user_attributes)
        response_data['ReadOnlyUserPassword'] = readonly_password

        tandemviz_user_dn = "CN=tandemviz,OU=Users,OU=tandemai,DC=tandemai,DC=com"
        tandemviz_user_attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': 'tandemviz',
            'sn': 'User',
            'userPassword': tandemviz_password,
            'sAMAccountName': 'tandemviz'
        }
        create_user(conn, tandemviz_user_dn, tandemviz_user_attributes)
        response_data['TandemvizPassword'] = tandemviz_password

        # Create and store the certificate
        private_key_content, certificate_content = create_certificate(directory_domain)

        secrets_manager = boto3.client('secretsmanager')

        secrets_manager.put_secret_value(
            SecretId=key_secret_arn,
            SecretString=private_key_content
        )
        secrets_manager.put_secret_value(
            SecretId=cert_secret_arn,
            SecretString=certificate_content
        )

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
