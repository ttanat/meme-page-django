from django.conf import settings

import os, boto3, json
from PIL import Image, ImageSequence


def check_file_ext(filename: str, valid_extensions: tuple) -> bool:
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


def check_upload_file_metadata(name: str, size: int, content_type: str) -> dict:
    """ Check file name, extension, content_type, and size """

    # Check file name and extension exists + get extension in lowercase
    tmp, ext = os.path.splitext(name.lower())
    if not tmp or not ext:
        return {"success": False, "message": "Invalid file name"}

    # Check content type
    if content_type not in ("image/jpeg", "image/png", "image/gif", "video/mp4", "video/quicktime"):
        return {"success": False, "message": "Invalid file type"}

    # Check sizes and extensions
    if ext in (".jpg", ".png", ".jpeg", ".gif"):
        if size > 5242880:
            return {"success": False, "message": "Maximum image file size is 5 MB"}
    elif ext in (".mp4", ".mov"):
        if size > 15728640:
            return {"success": False, "message": "Maximum video file size is 15 MB"}
    else:
        return {"success": False, "message": "Unsupported file type"}

    return {"success": True}


def check_upload_image_file(file: object) -> dict:
    """ Check image file """
    with Image.open(file) as img:
        # Check aspect ratio for both image and GIF (Allow some extra room past 16:9 aspect ratio, e.g. for 720x404)
        if not 1 / 1.8 < img.width / img.height < 1.8:
            return {"success": False, "message": "Aspect ratio must be between 16:9 and 9:16"}

        if os.path.splitext(file.name)[1].lower() == ".gif":
            # Check GIF dimensions are at least 250x250
            if img.width < 250 or img.height < 250:
                return {"success": False, "message": "GIF must be at least 250x250 pixels"}
            # Get GIF duration and number of frames
            return check_gif_info(img) # Final check for GIF so returning here
        else:
            # Check image dimensions are at least 320x320 pixels
            if img.width < 320 or img.height < 320:
                return {"success": False, "message": "Image must be at least 320x320 pixels"}

    return {"success": True}


def check_gif_info(img: object) -> dict:
    """ Check GIF duration and framerate """
    try:
        duration = sum([frame.info["duration"] for frame in ImageSequence.Iterator(img)])
    except:
        return {"success": False, "message": "Unexpected error occurred: Could not read GIF file"}

    # Check duration is <= 30 seconds (30000 ms)
    if duration > 30000:
        return {"success": False, "message": "GIF must be 30 seconds or less"}
    # Check framerate is <= 60
    if img.n_frames / (duration / 1000) > 60:
        return {"success": False, "message": "Maximum 60 frames per second"}

    return {"success": True}


def get_upload_tags(tags: list) -> list:
    """ Remove duplicate tags (case-insensitive) """
    result = []
    marker = set()
    for t in tags:
        tl = t.lower()
        if tl not in marker:
            marker.add(tl)
            result.append(t)

    return result
