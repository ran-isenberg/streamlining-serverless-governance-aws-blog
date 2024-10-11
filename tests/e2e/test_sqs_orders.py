import json
import time

import boto3
import pytest

from tests.utils import generate_random_string, get_stack_output


@pytest.fixture
def queue_url():
    return get_stack_output('QueueUrl')


@pytest.fixture
def bucket_name():
    bucket_name = get_stack_output('BucketName')
    yield bucket_name
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    bucket.objects.all().delete()


def test_insert_message_to_sqs(queue_url: str, bucket_name: str):
    sqs_client = boto3.client('sqs')
    message_body = {'item': {'laptop': generate_random_string(length=5)}}
    response = sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    # fetch item from s3 bucket and compare contents to message body
    # add a retry mechanism to wait for the message to be processed
    time.sleep(10)  # todo replace with proper retry mechanism like tenacity
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for obj in bucket.objects.all():
        if obj.key == f'{response["MessageId"]}.json':
            obj_body = json.loads(obj.get()['Body'].read().decode('utf-8'))
            assert obj_body == message_body['item']
            return
    raise AssertionError('Message not found in S3 bucket')
