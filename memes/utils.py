from django.conf import settings

import boto3, json


client = boto3.client('lambda', region_name=settings.AWS_S3_REGION_NAME)


def resize_any_image(file_key: str, dimensions: tuple):
    """ Invoke lambda function to resize image and overwrite original image """
    assert len(dimensions) == 2

    client.invoke(
        FunctionName="resize_any_image",
        InvocationType="Event",
        Payload=json.dumps({
            "file_key": file_key,
            "dimensions": dimensions,
        }),
        Qualifier="$LATEST"
    )
