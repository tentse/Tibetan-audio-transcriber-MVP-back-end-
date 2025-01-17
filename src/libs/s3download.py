import boto3
import os
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException
import requests

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_REGION")

async def download_file_from_s3(file_url: str):

    try:
        # print(file_url)

        # Send a GET request to the public S3 URL
        response = requests.get(file_url)

        # Check if the request was successful
        if response.status_code == 200:
            file_content = response.content  # Read the content of the file
            # print(file_content)  # Print or process the content as needed
            return file_content
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to download file")
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))