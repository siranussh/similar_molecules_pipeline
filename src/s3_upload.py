import os

import boto3
from dotenv import load_dotenv

load_dotenv()


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "eu-central-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
    )


def upload_file(local_path, bucket, s3_key):
    client = get_s3_client()
    client.upload_file(local_path, bucket, s3_key)
    return f"s3://{bucket}/{s3_key}"


if __name__ == "__main__":
    bucket = os.environ["S3_BUCKET"]
    subfolder = os.environ["S3_SUBFOLDER"]

    test_file_path = "s3_upload_test.txt"
    with open(test_file_path, "w") as f:
        f.write("connectivity test\n")

    s3_key = f"{subfolder}/s3_upload_test.txt"
    uploaded_uri = upload_file(test_file_path, bucket, s3_key)
    print(f"Uploaded test file to {uploaded_uri}")

    os.remove(test_file_path)
