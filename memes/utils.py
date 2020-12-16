from django.conf import settings

import os, boto3, json
from PIL import Image


def check_valid_file_ext(filename: str, valid_extensions: tuple) -> bool:
    """ Check that file has valid extension """
    return os.path.splitext(filename)[1].lower() in valid_extensions


client = boto3.client('lambda', region_name=settings.AWS_S3_REGION_NAME)


def resize_any_image(file_key: str, dimensions: tuple):
    """ Invoke lambda function to resize image and overwrite original image """

    assert len(dimensions) == 2
    assert isinstance(dimensions[0], int) and isinstance(dimensions[1], int)

    client.invoke(
        FunctionName="resize_any_image",
        InvocationType="Event",
        Payload=json.dumps({
            "file_key": file_key,
            "dimensions": dimensions,
        }),
        Qualifier="$LATEST"
    )


def check_gif_info(img: object) -> int:
    """ Check GIF duration in milliseconds and number of frames """
    img.seek(0)
    total_duration = 0

    # Use for loop instead of while True to ensure not stuck in infinite loop
    # 5000 is a random large number that number of frames in GIF should not exceed
    for i in range(1, 5001):
        try:
            # Add frame duration to total duration
            total_duration += img.info["duration"]
            # Move onto next frame
            img.seek(img.tell() + 1)
        except EOFError:
            break

    # Check duration is <= 30 seconds (30000 ms)
    if total_duration > 30000:
        return {"success": False, "message": "GIF must be 30 seconds or less"}
    # Check number of frames <= 1800 (60 frames x 30s) and fps <= 60
    if i > 1800 or i / (total_duration / 1000) > 60:
        return {"success": False, "message": "Maximum 60 frames per second"}

    return {"success": True}


def check_upload_file_valid(file: object) -> dict:
    # Get file extension
    ext = os.path.splitext(file.name)[1].lower()

    # Check content type and file extension is valid
    if (file.content_type not in ("image/jpeg", "image/png", "image/gif", "video/mp4", "video/quicktime")
            or ext not in (".jpg", ".png", ".jpeg", ".mp4", ".mov", ".gif")):
        return {"success": False, "message": "Unsupported file type"}

    if ext in (".jpg", ".png", ".jpeg", ".gif"):
        # Check file size for images
        if file.size > 5242880:
            return {"success": False, "message": "Maximum image file size is 5 MB"}

        with Image.open(file) as img:
            if ext == ".gif":
                # Check GIF dimensions are at least 250x250
                if img.width < 250 or img.height < 250:
                    return {"success": False, "message": "GIF must be at least 250x250 pixels"}
                # Get GIF duration and number of frames
                return check_gif_info(img) # Final check for GIF so returning here
            else:
                # Check image dimensions are at least 320x320 pixels
                if img.width < 320 or img.height < 320:
                    return {"success": False, "message": "Image must be at least 320x320 pixels"}

    elif ext in (".mp4", ".mov") and file.size > 15728640:
        return {"success": False, "message": "Maximum video file size is 15 MB"}

    return {"success": True}
