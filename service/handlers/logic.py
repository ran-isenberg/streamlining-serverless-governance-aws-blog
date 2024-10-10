from json import dumps as json_dumps
from os import getenv

from aws_lambda_powertools.metrics import MetricUnit
from boto3 import client
from botocore.config import Config

from service.handlers.models.sqs_item import OrderSqsRecord
from service.handlers.utils.observability import logger, metrics, tracer

# Define custom boto3 configuration for timeout and retry (including jitter)
custom_config = Config(
    retries={
        'max_attempts': 5,  # Maximum retry attempts
        'mode': 'adaptive',  # Adaptive mode for retry. Can be also standard. Read more: https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html
    },
    read_timeout=30,  # Custom read timeout in seconds
    connect_timeout=10,  # Custom connect timeout in seconds
)

# Initialize the S3 client with the custom configuration
s3_client = client('s3', config=custom_config)


@tracer.capture_method
def record_handler(record: OrderSqsRecord):
    logger.debug(record.body.item)

    s3_client.put_object(
        Bucket=getenv('BUCKET_NAME'),
        Key=f'{record.messageId}.json',
        Body=json_dumps(record.body.item).encode('utf-8'),
        ContentType='application/json',
    )
    metrics.add_metric(name='BucketItems', unit=MetricUnit.Count, value=1)
