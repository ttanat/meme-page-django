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
    # Count total duration
    total_duration = 0
    # Ensure all frames and their durations are counted
    all_frames_counted = False

    # Use for loop instead of while True to ensure not stuck in infinite loop
    # 1800 frames because 30 seconds x 60 fps = 1800 frames
    # On 1800th loop, i == 1799:
    #   If 1800 frames in GIF, after 1800th frame info is read, img.seek() causes EOFError, all_frames_counted = True
    #   If 1801st frame or more exists, img.seek() will NOT cause EOFError, all_frames_counted = False
    for i in range(1800):
        try:
            frame_duration = img.info["duration"]
            total_duration += frame_duration
            img.seek(img.tell() + 1)
        except EOFError:
            all_frames_counted = True
            break

    # Check duration is <= 30 seconds (30000 ms)
    if total_duration > 30000:
        return {"success": False, "message": "GIF must be 30 seconds or less"}
    # Check number of frames <= 1800
    if not all_frames_counted:
        return {"success": False, "message": "GIF contains too many frames"}

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
