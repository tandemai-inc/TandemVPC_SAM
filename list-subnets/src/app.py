import boto3
import os
import cfnresponse

def lambda_handler(event, context):
    try:
        ec2 = boto3.client('ec2')
        vpc_id = event['ResourceProperties']['VpcId']
        print(f"vpcid: {vpc_id}")

        if event['RequestType'] == 'Delete':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            return

        az_list = event['ResourceProperties']['AZList'].split(",")
        if not az_list[0]:
            cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": "Invalid AZ List"})
            return
        print(f"az list: {az_list}")
        region = event['ResourceProperties']['SubnetRegion']
        print(f"region: {region}")
        public_subnet_ids = []
        private_subnet_ids = []
        private_subnets_ids_only = []
        first_az_private_subnet_id = ''
        for az in az_list:
            az = az.strip()
            print (f"az without region: {az}")
            az_with_region = f"{region}{az}"
            print (f"az with region: {az_with_region}")
            filters = [{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'availability-zone', 'Values': [az_with_region]}]
            subnets = ec2.describe_subnets(Filters=filters)['Subnets']
            print(f"subnet: {subnets}")

            for subnet in subnets:
                if subnet['MapPublicIpOnLaunch']:
                    public_subnet_ids.append(subnet['SubnetId'])
                else:
                    if not first_az_private_subnet_id:
                        first_az_private_subnet_id = subnet['SubnetId']
                    private_subnet_ids.append(subnet['SubnetId'])
                    # get rid of subnet-
                    private_subnets_ids_only.append(subnet['SubnetId'].replace("subnet-", ""))


        print("About to send output")
        responseData = {
            'PublicSubnetIds': ','.join(list(public_subnet_ids)),
            'PrivateSubnetIds': ','.join(private_subnet_ids),
            'PrivateSubnetIdsOnly': ','.join(private_subnets_ids_only),
            'FirstAZPrivateSubnetId': first_az_private_subnet_id
        }
        print(f"Send {responseData}")
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
    except Exception as e:
        print ("Failedddd")
        print(str(e))
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": str(e)})