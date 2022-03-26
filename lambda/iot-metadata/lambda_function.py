import json
import boto3
import time
import sys
import os

credentials = ["us-west-2","AKIASHT7xxxxxxxxxx","36E3p9vvc1Ttsxxxxxxxxxx"]   #region,access_key,secret_key
InstanceId = 'i-084d540069d0d3431'  #ec2 instance ID, for training

s3 = boto3.client('s3')
bucket_metadata ='edge-to-cloud-metadata'
bucket_model ='edge-to-cloud-streaming-model'

def get_ec2_instances_id(region,access_key,secret_key):
    ec2_conn = boto3.resource('ec2',region_name=region,aws_access_key_id=access_key,aws_secret_access_key=secret_key)
    
    if ec2_conn:
        for instance in ec2_conn.instances.all():
            if instance.state['Name'] == 'running' and instance.security_groups[0]['GroupName'] == 'distributed_dl_starly':
                masterInstanceId = instance.instance_id
                print("Master Instance Id is ",masterInstanceId)
        return masterInstanceId
    else:
        print('Region failed', region)
        return None
    
    #return InstanceId

def send_command_to_master(InstanceId,command,ssm_client):
    print("Ssm run command: ",command)
    response = ssm_client.send_command(InstanceIds=[InstanceId],DocumentName="AWS-RunShellScript",Parameters={'commands': [command]})

    command_id = response['Command']['CommandId']
    waiter = ssm_client.get_waiter("command_executed")

    while True:
        try:
            waiter.wait(CommandId=command_id,InstanceId=InstanceId)
            break
        except:
            print("SSM in progress")
            time.sleep(5)

    output = ssm_client.get_command_invocation(CommandId=command_id,InstanceId=InstanceId)
    if output['Status'] == 'Success':
        print('SSM success')
    else:
        print('SSM failed')

def s3_put_object(filename,path):
    return "aws s3 sync /home/ubuntu/%s s3://%s"%(filename,path) #aws s3 cp /home/ubuntu/result.txt s3://aws-sam-cli-managed-default-samclisourcebucket-xscicpwnc0z3/26d1eef0-6875-42eb-b987-689213e25c66/result.txt

def s3_object_version(bucketname,s3prefix):
    return "aws s3api list-object-versions --bucket %s --prefix %s --output text --query 'Versions[?IsLatest].[VersionId]'"%(bucketname,s3prefix)

def s3_get_latest_version(bucketname,s3prefix):
    versions = s3.Bucket(bucketname).object_versions.filter(Prefix=s3prefix)
    for version in versions:
        obj = version.get()
        return obj.get('VersionId')
        break

def s3_get_object(bucketname,s3prefix,localpath,version):
    if version:
        return "aws s3api get-object --bucket %s --key %s %s --version-id %s"%(bucketname,s3prefix,localpath,version)
    else:
        return "aws s3api get-object --bucket %s --key %s %s"%(bucketname,s3prefix,localpath)

def lambda_handler(event, context):
    #event is PAYLOAD
    masterInstanceId = get_ec2_instances_id(credentials[0],credentials[1],credentials[2])
    ssm_client = boto3.client('ssm',region_name=credentials[0],aws_access_key_id=credentials[1],aws_secret_access_key=credentials[2])
    
    # make sure you have run the install_depandencies.sh in ec2!!!
    
    Lambda_get_time = str(time.time())

    # store metadata to s3 archive bucket <bucket_metadata>
    transactionToUpload = event
    transactionToUpload['Lambda_get_time'] = Lambda_get_time

    fileName = 'metadata_%s'%Lambda_get_time + '.json'

    uploadByteStream = bytes(json.dumps(transactionToUpload).encode('UTF-8'))
    s3.put_object(Bucket=bucket_metadata, Key=fileName, Body=uploadByteStream)
    print("Hybrid learning Lambda Metadata <%s> sends to <%s>"%(fileName, bucket_metadata))

    # download metadata to ec2 folder
    #send_command_to_master(masterInstanceId,\
    #    "echo "+json.dumps(event).replace('\"','\\"').replace('`','`\'').replace('`\'','\`\'',1)+" | tee -a /home/ubuntu/metadata/metadata_"+Lambda_get_time+'.json',\
    #    ssm_client)        #SSM command has argument length limit.
    send_command_to_master(masterInstanceId,\
        s3_get_object(bucket_metadata, fileName, "/home/ubuntu/metadata/"+fileName, None),\
        ssm_client)
    
    # training stream model in ec2
    send_command_to_master(masterInstanceId,\
        "docker run --rm -v /home/ubuntu/stream_training.py:/root/stream_training.py -v /home/ubuntu/stream_layer_model:/root/stream_layer_model -v /home/ubuntu/metadata:/root/metadata starlyxxx/hybrid-learning-edge-to-cloud:latest sh -c 'spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.3 /root/stream_training.py %s'"%Lambda_get_time,\
        ssm_client)
    Model_train_endtime = str(time.time())
    
    # store stream model in ec2 to s3 model bucket <bucket_model>
    stream_model_path = "stream_layer_model/model_"+Lambda_get_time
    stream_model_s3_path = bucket_model+"/model_"+Lambda_get_time+"-"+Model_train_endtime
    
    send_command_to_master(masterInstanceId,\
        s3_put_object(stream_model_path,stream_model_s3_path),\
        ssm_client)
            
    # release metadata and trained model in ec2
    send_command_to_master(masterInstanceId,\
        "rm /home/ubuntu/metadata/%s && rm -rf /home/ubuntu/stream_layer_model/model_%s"%(fileName,Lambda_get_time),\
        ssm_client)

    return {
        'statusCode': 200,
        'body': json.dumps('Hybrid learning Lambda Metadata Put Complete!')
    }