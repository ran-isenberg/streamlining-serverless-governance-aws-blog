from aws_cdk import Duration, RemovalPolicy, aws_events, aws_events_targets, aws_sqs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from constructs import Construct


class RedrivableSQS(Construct):
    """
    The RedrivableSQS class is a construct for AWS CDK that creates a main SQS queue and a dead-letter queue (DLQ),
    along with their associated AWS Lambda functions for re-driving messages from the DLQ back to the main queue on a schedule. #pylint: disable=line-too-long

    Args:
        scope (Construct): The parent construct that this construct will be a part of.
        identifier (str): The unique identifier for this construct and all resources within the scope.
        redrive_lambda_layer (_lambda.LayerVersion): The AWS Lambda layer to be used by the dead-letter queue processing function.
        dlq_lambda_runtime (_lambda.Runtime): The runtime for the dead-letter queue processing function. Required for the Lambda function settings.
        minute (str): The minute of the hour to run the DLQ redrive processing function. Valid values see https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html #pylint: disable=line-too-long
        hour (str): The hour of the day to run the DLQ redrive processing function. Valid values see https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html #pylint: disable=line-too-long
        month (str): The month of the year to run the DLQ redrive processing function. Valid values see https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html #pylint: disable=line-too-long
        week_day (str): The day of the week to run the DLQ redrive processing function. Valid values see https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html #pylint: disable=line-too-long
        max_retry_attempts (int): The maximum number of times to retry processing a message in the SQS before sending it to the DLQ. Default is 3. #pylint: disable=line-too-long
    """

    LAMBDA_BASIC_EXECUTION_ROLE = 'AWSLambdaBasicExecutionRole'

    def __init__(
        self,
        scope: Construct,
        identifier: str,
        redrive_lambda_layer: _lambda.LayerVersion,
        redrive_lambda_runtime: _lambda.Runtime,
        minute: str,
        hour: str,
        month: str,
        week_day: str,
        max_retry_attempts: int,
    ) -> None:
        super().__init__(scope, identifier)

        self.dead_letter_queue = aws_sqs.Queue(
            self,
            f'{identifier}dlq',
            queue_name=f'{identifier}dlq',
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,
        )
        self.sqs_queue = aws_sqs.Queue(
            self,
            f'{identifier}queue',
            queue_name=f'{identifier}queue',
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
            retention_period=Duration.days(14),
            dead_letter_queue=aws_sqs.DeadLetterQueue(max_receive_count=max_retry_attempts, queue=self.dead_letter_queue),
            visibility_timeout=Duration.minutes(5),
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,
        )
        self.dlq_lambda = self._create_redrive_function(
            identifier,
            redrive_lambda_layer,
            redrive_lambda_runtime,
            self.sqs_queue,
            self.dead_letter_queue,
        )
        self._create_scheduler_cron(identifier, self.dlq_lambda, minute, hour, month, week_day)  # pylint: disable=too-many-function-args

    def _create_redrive_function(
        self, identifier: str, layer: _lambda.LayerVersion, runtime: _lambda.Runtime, main_queue: aws_sqs.Queue, dead_letter_queue: aws_sqs.Queue
    ) -> _lambda.Function:
        # policy defined by https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-api-permissions-reference.html
        role = iam.Role(
            self,
            f'{identifier}DlqRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'dlq_policy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                'sqs:StartMessageMoveTask',
                                'sqs:ReceiveMessage',
                                'sqs:DeleteMessage',
                                'sqs:GetQueueAttributes',
                                'sqs:SendMessage',
                            ],
                            resources=[dead_letter_queue.queue_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                'sqs_policy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                'sqs:SendMessage',
                            ],
                            resources=[main_queue.queue_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    managed_policy_name=f'service-role/{RedrivableSQS.LAMBDA_BASIC_EXECUTION_ROLE}',
                )
            ],
        )

        return _lambda.Function(
            self,
            f'{identifier}Func',
            function_name=f'{identifier}Func'[-64:],
            runtime=runtime,
            handler='redrive_lambda.redrive_handler',
            code=_lambda.Code.from_asset('cdk/blueprint/_redrive_lambda'),
            role=role,
            environment={
                'LOGGER_SERVICE_NAME': 'dlq_redrive'.lower(),  # used for logger service name
                'SQS_ARN': main_queue.queue_arn,
                'DLQ_ARN': dead_letter_queue.queue_arn,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            layers=[layer],
        )

    def _create_scheduler_cron(
        self, identifier: str, dlq_lambda: _lambda.Function, minute: str, hour: str, month: str, week_day: str
    ) -> aws_events.Rule:
        return aws_events.Rule(
            self,
            f'{identifier}CronSchedulerRole',
            schedule=aws_events.Schedule.cron(
                minute=minute,
                hour=hour,
                month=month,
                week_day=week_day,
            ),
            targets=[aws_events_targets.LambdaFunction(handler=dlq_lambda)],
            rule_name=f'{identifier}Redrive'[-64:],
        )
