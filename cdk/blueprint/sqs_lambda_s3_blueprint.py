from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

import cdk.blueprint.constants as constants
from cdk.blueprint.secure_s3_construct import SecureS3Construct


class SqsLambdaToS3Construct(Construct):
    def __init__(self, scope: Construct, id_: str, is_production_env: bool) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.bucket = SecureS3Construct(self, f'{self.id_}bucket', is_production_env).bucket
        self.lambda_role = self._build_lambda_role(self.bucket)
        self.common_layer = self._build_common_layer()
        self.lambda_function = self._create_lambda_function(self.lambda_role, self.bucket)

    def _build_lambda_role(self, bucket: s3.Bucket) -> iam.Role:
        return iam.Role(
            self,
            constants.SERVICE_ROLE_ARN,
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'bucket': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['s3:PutObject', 's3:PutObjectAcl'],
                            resources=[f'{bucket.bucket_arn}/*'],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
        )

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f'{self.id_}{constants.LAMBDA_LAYER_NAME}',
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_lambda_function(
        self,
        role: iam.Role,
        bucket: s3.Bucket,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.CREATE_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.handle_create_order.lambda_handler',
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
            log_retention=RetentionDays.ONE_DAY,
            log_format=_lambda.LogFormat.JSON.value,
            system_log_level=_lambda.SystemLogLevel.INFO.value,
        )

        return lambda_function
