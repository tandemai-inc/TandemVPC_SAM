import boto3
import cfnresponse
import ipaddress
          
def calculate_subnets_with_public_private(cidr_input, subnet_count):
    network = ipaddress.ip_network(cidr_input,strict = False)
    # prefix_len = int(cidr_input.split('/')[-1])
    # network = ipaddress.ip_network(cidr_input, strict=False) if prefix_len <= 6 else ipaddress.ip_network(cidr_input)
    print(f"Received CIDR: {cidr_input}")
    print(f"Received subnet count: {subnet_count}")
    # Initialize lists for CIDRs
    public_subnet_cidrs = []
    private_subnet_cidrs = []
    if network.prefixlen >= 22:  # Adjust for /22 and larger networks
        if subnet_count in[5,6] and network.prefixlen != 24:
            # Calculate size of each segment based on the subnet count
            segment_size = network.num_addresses // subnet_count
            #print(f"Segment size: {segment_size}")
            segment_size = network.num_addresses // subnet_count
            for i in range(subnet_count):
                segment_start = i * segment_size
                public_subnet_start = network.network_address + segment_start
                public_subnet = ipaddress.ip_network(f"{public_subnet_start}/28", strict=False)
                public_subnet_cidrs.append(str(public_subnet))
                #print(f"Public subnet {i}: {public_subnet}")
                private_subnet_start = public_subnet.broadcast_address + 1
                if i == subnet_count - 1:
                    private_subnet_end = network.broadcast_address
                else:
                    private_subnet_end = network.network_address + (i + 1) * segment_size - 1
                #print(f"Initial private subnet start: {private_subnet_start}, end: {private_subnet_end}")
                # Use the largest available block for the private subnet
                private_subnet = ipaddress.summarize_address_range(private_subnet_start, private_subnet_end)
                largest_private_subnet = max(private_subnet, key=lambda n: n.num_addresses, default=None)
                if largest_private_subnet:
                    private_subnet_cidrs.append(str(largest_private_subnet))
                    #print(f"Allocated private subnet {i}: {largest_private_subnet} with size /{largest_private_subnet.prefixlen}")
        #######
        elif subnet_count in[5,6] and network.prefixlen == 24:
            public_subnet_cidrs = ['10.0.0.0/28', '10.0.0.32/28', '10.0.0.64/28', '10.0.0.96/28', '10.0.0.128/28'] if subnet_count == 5 else ['10.0.0.0/28', '10.0.0.32/28', '10.0.0.64/28', '10.0.0.96/28', '10.0.0.128/28', '10.0.0.160/28']
            private_subnet_cidrs = ['10.0.0.16/28', '10.0.0.48/28', '10.0.0.80/28', '10.0.0.112/28', '10.0.0.144/27'] if subnet_count == 5 else ['10.0.0.16/28', '10.0.0.48/28', '10.0.0.80/28', '10.0.0.112/28', '10.0.0.144/28', '10.0.0.176/26']
        else:
            segment_prefix_length = 26
            segments = list(network.subnets(new_prefix=segment_prefix_length))
            segments = segments[:subnet_count]
            for segment in segments:
                public_subnet = next(segment.subnets(new_prefix=28))
                public_subnet_cidrs.append(str(public_subnet))
                remaining_for_private = list(segment.address_exclude(public_subnet))
                if remaining_for_private:
                    private_subnet_cidrs.append(str(remaining_for_private[0]))
    else:
        #print("Handling larger networks differently")
        segment_size = network.num_addresses // subnet_count
        #print(f"Segment size for each split: {segment_size}")
        for i in range(subnet_count):
            public_subnet_start = network.network_address + (i * segment_size)
            public_subnet = ipaddress.ip_network(f"{public_subnet_start}/28", strict=False)
            public_subnet_cidrs.append(str(public_subnet))
            #print(f"Public subnet {i}: {public_subnet}")
            private_subnet_start = public_subnet.broadcast_address + 1
            if i == subnet_count - 1:
                private_subnet_end = network.broadcast_address
            else:
                private_subnet_end = public_subnet_start + segment_size - 1
            #print(f"Private subnet starts at: {private_subnet_start}, ends at: {private_subnet_end}")
            if private_subnet_start <= private_subnet_end:
                private_subnet_generator = ipaddress.summarize_address_range(private_subnet_start, private_subnet_end)
                try:
                    largest_private_subnet = max(private_subnet_generator, key=lambda n: n.num_addresses)
                    #print(f"Largest private subnet for index {i}: {largest_private_subnet} with size /{largest_private_subnet.prefixlen}")
                    private_subnet_cidrs.append(str(largest_private_subnet))
                except ValueError:
                    print(f"No valid private subnet found for index {i} within {private_subnet_start} to {private_subnet_end}")
    # Output the results
    print("Public Subnet Information:")
    print("\nPrivate Subnet Information:")
    return public_subnet_cidrs, private_subnet_cidrs

def lambda_handler(event, context):
    response_data = {}
    try:
        if event['RequestType'] == 'Delete':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
            return
        az_list = event['ResourceProperties']['AZList'].split(",")
        if len(az_list) < 2:
            cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": "@split-cidr SAM: You need to choose more than one AZ"})
            return

        print(f"az list: {az_list}")
        region = event['ResourceProperties']['Region']
        print (region)
        print (az_list)
        for az in az_list:
            if region not in az:
                cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": "@split-cidr SAM: All AZs must be in the current region"})
                return
        lettersOnly = [ item[-1] for item in az_list ]
        # index list - Cloudformation should really makes this easier
        az_count = len(az_list)
        index_list = list(range(az_count))
        index_list_str = [str(index) for index in index_list]
        # cidr calculation
        cidr_input= event['ResourceProperties'].get('AvailableCIDR') if event['ResourceProperties'].get('VpcId') else event['ResourceProperties'].get('VpcCIDR')
        public_subnet_cidrs, private_subnet_cidrs = calculate_subnets_with_public_private(cidr_input, az_count)
        #### return ####
        response_data = {
                        "joined_string": ",".join(az_list),
                        "letters_only": ",".join(lettersOnly), 
                        "IndexList": ','.join(index_list_str),
                        "PublicSubnetCidrs": ",".join(public_subnet_cidrs),
                        "PrivateSubnetCidrs": ",".join(private_subnet_cidrs)
                        }
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
    except Exception as e:
        print("Error: " + str(e))
        response_data = {'Error': str(e)}
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data)