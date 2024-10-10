import json

import boto3
import pytest

from tests.utils import generate_random_string, get_stack_output


@pytest.fixture
def queue_url():
    return get_stack_output('QueueUrl')


def test_insert_message_to_sqs(queue_url: str):
    sqs_client = boto3.client('sqs')
    message_body = {'item': {'laptop': generate_random_string(length=5)}}
    response = sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200
