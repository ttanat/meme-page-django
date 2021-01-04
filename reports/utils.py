from django.conf import settings

from memes.models import Meme, Comment

import boto3


def get_moderation_labels(obj):
    labels = None
    if isinstance(obj, Meme):
        if obj.get_original_ext() in (".jpg", ".png", ".jpeg"):
            labels = analyze_image(obj.original.name)
    elif isinstance(obj, Comment):
        if obj.image:
            labels = analyze_image(obj.image.name)

    return labels


def analyze_image(name):
    client = boto3.client('rekognition', region_name=settings.AWS_S3_REGION_NAME)

    response = client.detect_moderation_labels(
        Image={'S3Object': {'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Name': name}}
    )

    return response


# Full list = Explicit Nudity, Suggestive, Violence, Visually Disturbing, Rude Gestures, Drugs, Tobacco, Alcohol, Gambling, Hate Symbols
top_level_categories = {"Explicit Nudity", "Hate Symbols"}
second_level_categories = {
    "Graphic Violence Or Gore", "Self Injury", # Violence
    "Emaciated Bodies", "Corpses", "Hanging", # Visually Disturbing
}
all_categories = top_level_categories.union(second_level_categories)


def analyze_labels(labels):
    for label in labels["ModerationLabels"]:
        if label["Confidence"] >= 75:
            if label["ParentName"] in top_level_categories or label["Name"] in all_categories:
                return {"hide": True}

    return {"hide": False}
