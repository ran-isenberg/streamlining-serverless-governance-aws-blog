from aws_cdk import Duration, RemovalPolicy, aws_sqs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from aws_cdk import aws_s3 as s3
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct

import cdk.blueprint.constants as constants
from cdk.blueprint.secure_s3_construct import SecureS3Construct
from cdk.blueprint.sqs_redrive_construct import RedrivableSQS


class SqsLambdaToS3Construct(Construct):
    def __init__(self, scope: Construct, id_: str, is_production_env: bool) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.common_layer = self._build_common_layer()
        self.SecureBucket = SecureS3Construct(self, 'destination', is_production_env)
        self.bucket = self.SecureBucket.bucket
        self.redrive_queue = RedrivableSQS(
            self,
            identifier='queue',
            redrive_lambda_layer=self.common_layer,
            redrive_lambda_runtime=_lambda.Runtime.PYTHON_3_13,
            minute='0',
            hour='0',
            month='*',
            week_day='*',
            max_retry_attempts=3,
        )
        self.lambda_role = self._build_lambda_role(self.bucket)
        self.lambda_function = self._create_lambda_function(self.lambda_role, self.bucket, self.redrive_queue.sqs_queue)

    def _build_lambda_role(self, bucket: s3.Bucket) -> iam.Role:
        return iam.Role(
            self,
            constants.SERVICE_ROLE_ARN,
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'Bucket': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['s3:PutObject', 's3:PutObjectAcl'],
                            resources=[bucket.bucket_arn, f'{bucket.bucket_arn}/*'],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                # similar to https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaBasicExecutionRole.html
                'CloudwatchLogs': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                'logs:CreateLogGroup',
                                'logs:CreateLogStream',
                                'logs:PutLogEvents',
                            ],
                            resources=['*'],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
            },
        )

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f'{self.id_}{constants.LAMBDA_LAYER_NAME}',
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_lambda_function(
        self,
        role: iam.Role,
        bucket: s3.Bucket,
        sqs_queue: aws_sqs.Queue,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.CREATE_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.handle_sqs_batch.lambda_handler',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
                'BUCKET_NAME': bucket.bucket_name,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[self.common_layer],
            role=role,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            application_log_level_v2=_lambda.ApplicationLogLevel.INFO,
        )

        # set sqs queue as event source for the lambda functions
        lambda_function.add_event_source(lambda_event_sources.SqsEventSource(sqs_queue))

        return lambda_function
