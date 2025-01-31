from aws_cdk import Aspects, Stack, Tags
from cdk_nag import AwsSolutionsChecks, NagPackSuppression, NagSuppressions
from constructs import Construct

from cdk.blueprint.constants import OWNER_TAG, SERVICE_NAME, SERVICE_NAME_TAG
from cdk.blueprint.monitoring import Monitoring
from cdk.blueprint.sqs_lambda_s3_blueprint import SqsLambdaToS3Construct
from cdk.blueprint.utils import get_construct_name, get_username


class ServiceStack(Stack):
    def __init__(self, scope: Construct, id: str, is_production_env: bool, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self._add_stack_tags()

        self.blueprint = SqsLambdaToS3Construct(
            self,
            get_construct_name(stack_prefix=id, construct_name='blueprint'),
            is_production_env=is_production_env,
        )

        self.monitoring = Monitoring(
            self,
            get_construct_name(stack_prefix=id, construct_name='monitoring'),
            self.blueprint.bucket,
            self.blueprint.redrive_queue.sqs_queue,
            self.blueprint.redrive_queue.dead_letter_queue,
            [self.blueprint.lambda_function],
        )

        # add security check
        self._add_security_tests()

    def _add_stack_tags(self) -> None:
        # best practice to help identify resources in the console
        Tags.of(self).add(SERVICE_NAME_TAG, SERVICE_NAME)
        Tags.of(self).add(OWNER_TAG, get_username())

    def _add_security_tests(self) -> None:
        Aspects.of(self).add(AwsSolutionsChecks(verbose=True))
        # Suppress a specific rule for this resource
        NagSuppressions.add_stack_suppressions(
            stack=self,
            suppressions=[
                NagPackSuppression(
                    id='AwsSolutions-IAM5',
                    reason='Suppressed for logs:* and PutObject * for S3  and xray permissions on all resources',
                ),
                NagPackSuppression(
                    id='AwsSolutions-IAM4',
                    reason='using AWS managed policy AWSLambdaBasicExecutionRole',
                ),
            ],
        )
