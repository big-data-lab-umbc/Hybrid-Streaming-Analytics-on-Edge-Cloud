import json
import boto3
import time
import sys
import os

s3 = boto3.client('s3')
bucket ='edge-to-cloud-hybrid-learning'

#################################

def store_to_s3(event, Lambda_get_time):

	transactionToUpload = event
	#Lambda_get_time = str(time.time())
	transactionToUpload['Lambda_get_time'] = Lambda_get_time

	fileName = 'hybrid_result_%s'%Lambda_get_time + '.json'

	uploadByteStream = bytes(json.dumps(transactionToUpload).encode('UTF-8'))
	s3.put_object(Bucket=bucket, Key=fileName, Body=uploadByteStream)
	print("Hybrid learning Lambda Result <%s> sends to <%s>"%(fileName, bucket))

	return {
        'statusCode': 200,
        'body': json.dumps('Hybrid learning Lambda Result Put Complete!')
    }

#################################

def lambda_handler(event, context):
	Lambda_get_time = str(time.time())
	store_to_s3(event, Lambda_get_time)
	