import json

import boto3
import pytest
from botocore.exceptions import ClientError

from tests.utils import generate_random_string, get_stack_output


@pytest.fixture
def queue_url():
    return get_stack_output('QueueUrl')


def test_insert_message_to_sqs(queue_url: str):
    sqs_client = boto3.client('sqs')
    message_body = {'item': {'laptop': generate_random_string(length=5)}}

    try:
        response = sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    except ClientError as e:
        pytest.fail(f'Failed to send message to SQS: {e}')
