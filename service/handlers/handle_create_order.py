from typing import Any

from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.models.env_vars import MyHandlerEnvVars
from service.handlers.utils.observability import logger, metrics, tracer
from service.models.output import CreateOrderOutput


def handle_create_order() -> CreateOrderOutput:
    env_vars: MyHandlerEnvVars = get_environment_variables(model=MyHandlerEnvVars)
    logger.debug('environment variables', env_vars=env_vars.model_dump())

    metrics.add_metric(name='ValidCreateOrderEvents', unit=MetricUnit.Count, value=1)

    logger.info('finished handling create order request')
    return None


@init_environment_variables(model=MyHandlerEnvVars)
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    # return app.resolve(event, context)
    return {}
