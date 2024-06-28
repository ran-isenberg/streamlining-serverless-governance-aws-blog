from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_s3 as s3
from constructs import Construct

import cdk.blueprint.constants as constants


class SecureS3Construct(Construct):
    def __init__(self, scope: Construct, id_: str, is_production_env: bool) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.bucket = self._create_bucket(is_production_env)

    def _create_bucket(self, is_production_env: bool) -> s3.Bucket:
        # Create the S3 bucket with AWS managed encryption
        bucket = s3.Bucket(
            self,
            constants.BUCKET_NAME,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if not is_production_env else RemovalPolicy.RETAIN,
            enforce_ssl=True,
            auto_delete_objects=True if not is_production_env else False,
            public_read_access=False,
        )

        CfnOutput(self, 'BucketName', value=bucket.bucket_name).override_logical_id('BucketName')

        # Enable Object Lock
        s3.Bucket(self, 'ObjectLockBucket', object_lock_enabled=True, removal_policy=RemovalPolicy.DESTROY)

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
