import uuid

from service.handlers.handle_sqs_batch import lambda_handler
from tests.utils import generate_context


def test_handler_ok():
    event = {
        'Records': [
            {
                'messageId': str(uuid.uuid4()),
                'receiptHandle': 'AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a',
                'body': '{"item": {"laptop": "amd"}}',
                'attributes': {
                    'ApproximateReceiveCount': '1',
                    'SentTimestamp': '1545082649183',
                    'SenderId': 'AIDAIENQZJOLO23YVJ4VO',
                    'ApproximateFirstReceiveTimestamp': '1545082649185',
                },
                'messageAttributes': {},
                'md5OfBody': 'e4e68fb7bd0e697a0ae8f1bb342846b3',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-east-2: 123456789012:my-queue',
                'awsRegion': 'us-east-1',
            },
            {
                'messageId': str(uuid.uuid4()),
                'receiptHandle': 'AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a',
                'body': '{"item": {"keyboard": "classic"}}',
                'attributes': {
                    'ApproximateReceiveCount': '1',
                    'SentTimestamp': '1545082649183',
                    'SenderId': 'AIDAIENQZJOLO23YVJ4VO',
                    'ApproximateFirstReceiveTimestamp': '1545082649185',
                },
                'messageAttributes': {},
                'md5OfBody': 'e4e68fb7bd0e697a0ae8f1bb342846b3',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-east-2: 123456789012:my-queue',
                'awsRegion': 'us-east-1',
            },
        ]
    }
    context = generate_context()
    lambda_handler(event, context)
    # todo - check S3 item is written properly, mock exceptions etc.
