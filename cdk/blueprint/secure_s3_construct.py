from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

import cdk.blueprint.constants as constants


class SecureS3Construct(Construct):
    def __init__(self, scope: Construct, id_: str, is_production_env: bool) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.log_bucket = self._create_log_bucket(is_production_env)
        self.bucket = self._create_bucket(self.log_bucket, is_production_env)

    def _create_log_bucket(self, is_production_env: bool) -> s3.Bucket:
        log_bucket = s3.Bucket(
            self,
            constants.ACCESS_LOG_BUCKET_NAME,
            versioned=True if is_production_env else False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if not is_production_env else RemovalPolicy.RETAIN,
            enforce_ssl=True,
            auto_delete_objects=True if not is_production_env else False,
        )
        CfnOutput(self, 'LogBucketName', value=log_bucket.bucket_name).override_logical_id('LogBucketName')
        return log_bucket

    def _create_bucket(self, server_access_logs_bucket: s3.Bucket, is_production_env: bool) -> s3.Bucket:
        # Create the S3 bucket with AWS managed encryption
        bucket = s3.Bucket(
            self,
            constants.BUCKET_NAME,
            versioned=True if is_production_env else False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if not is_production_env else RemovalPolicy.RETAIN,
            enforce_ssl=True,
            auto_delete_objects=True if not is_production_env else False,
            object_lock_enabled=True if is_production_env else False,,
            server_access_logs_bucket=server_access_logs_bucket,
        )

        # Add bucket policy to enforce SSL
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=['s3:*'],
                resources=[bucket.bucket_arn, f'{bucket.bucket_arn}/*'],
                conditions={'Bool': {'aws:SecureTransport': 'false'}},
                principals=[iam.ArnPrincipal('*')],
            )
        )

        CfnOutput(self, 'BucketName', value=bucket.bucket_name).override_logical_id('BucketName')

        # Add lifecycle rule to manage old versions
        bucket.add_lifecycle_rule(
            id='LifecycleRule',
            enabled=True,
            noncurrent_version_transitions=[
                s3.NoncurrentVersionTransition(storage_class=s3.StorageClass.INFREQUENT_ACCESS, transition_after=Duration.days(30))
            ],
            noncurrent_version_expiration=Duration.days(365),
        )

        return bucket
