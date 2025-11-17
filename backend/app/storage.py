# Simple S3/local storage helper (optional)
import os
import boto3
from botocore.exceptions import BotoCoreError
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET", "")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

def upload_file_s3(local_path, key):
    if not S3_BUCKET:
        raise RuntimeError("S3 bucket not configured")
    s3 = boto3.client("s3",
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    try:
        s3.upload_file(local_path, S3_BUCKET, key)
        return f"s3://{S3_BUCKET}/{key}"
    except BotoCoreError as e:
        raise
