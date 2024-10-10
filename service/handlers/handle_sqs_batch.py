from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response

from service.handlers.logic import record_handler
from service.handlers.models.sqs_item import OrderSqsRecord
from service.handlers.utils.observability import logger, metrics, tracer

processor = BatchProcessor(event_type=EventType.SQS, model=OrderSqsRecord)


@logger.inject_lambda_context
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event, context):
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )
