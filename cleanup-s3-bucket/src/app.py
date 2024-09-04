import boto3
import cfnresponse
import logging
import sys
from botocore.config import Config
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _delete_s3_artifacts(event):
    """
    Delete artifacts under the directory that is passed in.

    It exits gracefully if directory does not exist.
    :param bucket_name: bucket containing cluster artifacts
    """
    bucket_name = event["ResourceProperties"]["S3Bucket"]
    try:
        if bucket_name != "NONE":
            bucket = boto3.resource("s3", config=Config(retries={"max_attempts": 60})).Bucket(bucket_name)
            logger.info("Cluster S3 artifact in %s deletion: STARTED", bucket_name)
            bucket.objects.all().delete()
            bucket.object_versions.delete()
            logger.info("Cluster S3 artifact in %s deletion: COMPLETED", bucket_name)
    except boto3.client("s3").exceptions.NoSuchBucket as ex:
        logger.warning("S3 bucket %s not found. Bucket was probably manually deleted.", bucket_name)
        logger.warning(ex, exc_info=True)
    except Exception as e:
        logger.error(
            "Failed when deleting cluster S3 artifact in %s with error %s", bucket_name, e
        )
        raise

def handler(event, context):
    try:
        if event["RequestType"] == "Delete":
            _delete_s3_artifacts(event)
        response_status = cfnresponse.SUCCESS
        reason = ""
    except Exception as e:
        response_status = cfnresponse.FAILED
        reason = str(e)
    cfnresponse.send(event, context, response_status, {}, event.get('PhysicalResourceId', 'CleanupS3bucketCustomResource'), reason)