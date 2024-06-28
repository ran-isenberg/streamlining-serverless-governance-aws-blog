import json

import boto3
from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.config import Config

from service.handlers.models.env_vars import MyHandlerEnvVars
from service.handlers.models.sqs_item import OrderSqsRecord
from service.handlers.utils.observability import logger, metrics, tracer

processor = BatchProcessor(event_type=EventType.SQS, model=OrderSqsRecord)

# Create a configuration object with SSL enabled
config = Config(ssl=True)

# Initialize the S3 client with the SSL configuration
s3_client = boto3.client('s3', config=config)


@tracer.capture_method
def record_handler(record: OrderSqsRecord):
    env_vars: MyHandlerEnvVars = get_environment_variables(model=MyHandlerEnvVars)
    logger.info(record.body.item)
    metrics.add_metric(name='ValidSqsItem', unit=MetricUnit.Count, value=1)

    ## your logic here, write to S3
    s3_client.put_object(
        Bucket=env_vars.BUCKET_NAME,
        Key=f'{record.messageId}.json',
        Body=json.dumps(record.body.item).encode('utf-8'),
        ContentType='application/json',
    )

    logger.info('finished handling create order request')


@init_environment_variables(model=MyHandlerEnvVars)
@logger.inject_lambda_context
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event, context: LambdaContext):
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )
