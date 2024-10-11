import aws_cdk.aws_sns as sns
from aws_cdk import CfnOutput, Duration, RemovalPolicy, aws_sqs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from cdk_monitoring_constructs import (
    AlarmFactoryDefaults,
    CustomMetricGroup,
    ErrorRateThreshold,
    LatencyThreshold,
    MetricStatistic,
    MonitoringFacade,
    SnsAlarmActionStrategy,
)
from constructs import Construct

from cdk.blueprint import constants


class Monitoring(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        bucket: s3.Bucket,
        queue: aws_sqs.Queue,
        dlq: aws_sqs.Queue,
        functions: list[_lambda.Function],
    ) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.notification_topic = self._build_topic()
        self._build_high_level_dashboard(self.notification_topic, bucket, queue, dlq)
        self._build_low_level_dashboard(functions, self.notification_topic)

    def _build_topic(self) -> sns.Topic:
        key = kms.Key(
            self,
            'MonitoringKey',
            description='KMS Key for SNS Topic Encryption',
            enable_key_rotation=True,  # Enables automatic key rotation
            removal_policy=RemovalPolicy.DESTROY,
            pending_window=Duration.days(7),
        )
        topic = sns.Topic(self, f'{self.id_}alarms', display_name=f'{self.id_}alarms', master_key=key)
        # Grant CloudWatch permissions to publish to the SNS topic
        topic.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=['sns:Publish'],
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal('cloudwatch.amazonaws.com')],
                resources=[topic.topic_arn],
            )
        )
        CfnOutput(self, id=constants.MONITORING_TOPIC, value=topic.topic_name).override_logical_id(constants.MONITORING_TOPIC)
        return topic

    def _build_high_level_dashboard(
        self,
        topic: sns.Topic,
        bucket: s3.Bucket,
        queue: aws_sqs.Queue,
        dlq: aws_sqs.Queue,
    ):
        high_level_facade = MonitoringFacade(
            self,
            f'{self.id_}HighFacade',
            alarm_factory_defaults=AlarmFactoryDefaults(
                actions_enabled=True,
                alarm_name_prefix=self.id_,
                action=SnsAlarmActionStrategy(on_alarm_topic=topic),
            ),
        )
        high_level_facade.add_large_header('SQS to S3 REST High Level Dashboard')
        high_level_facade.monitor_sqs_queue(queue=queue)
        high_level_facade.monitor_sqs_queue(queue=dlq)
        high_level_facade.monitor_s3_bucket(bucket=bucket)
        metric_factory = high_level_facade.create_metric_factory()
        create_metric = metric_factory.create_metric(
            metric_name='BucketItems',
            namespace=constants.METRICS_NAMESPACE,
            statistic=MetricStatistic.N,
            dimensions_map={constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME},
            label='batch objects in bucket',
            period=Duration.days(1),
        )

        group = CustomMetricGroup(metrics=[create_metric], title='Daily Batch Objects')
        high_level_facade.monitor_custom(metric_groups=[group], human_readable_name='Daily KPIs', alarm_friendly_name='KPIs')

    def _build_low_level_dashboard(self, functions: list[_lambda.Function], topic: sns.Topic):
        low_level_facade = MonitoringFacade(
            self,
            f'{self.id_}LowFacade',
            alarm_factory_defaults=AlarmFactoryDefaults(
                actions_enabled=True,
                alarm_name_prefix=self.id_,
                action=SnsAlarmActionStrategy(on_alarm_topic=topic),
            ),
        )
        low_level_facade.add_large_header('SQS to S3 REST Low Level Dashboard')
        for func in functions:
            low_level_facade.monitor_lambda_function(
                lambda_function=func,
                add_latency_p90_alarm={'p90': LatencyThreshold(max_latency=Duration.seconds(60))},
                add_fault_rate_alarm={'error_rate': ErrorRateThreshold(max_error_rate=0.01)},
            )
            low_level_facade.monitor_log(
                log_group_name=func.log_group.log_group_name,
                human_readable_name='Error logs',
                pattern='ERROR',
                alarm_friendly_name='error logs',
            )
