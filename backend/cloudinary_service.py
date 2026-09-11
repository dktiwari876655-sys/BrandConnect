import os

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

_configured = False


def configure_cloudinary():
    global _configured

    values = (
        os.environ.get("CLOUDINARY_CLOUD_NAME"),
        os.environ.get("CLOUDINARY_API_KEY"),
        os.environ.get("CLOUDINARY_API_SECRET"),
    )
    if not all(values):
        return False

    cloudinary.config(
        cloud_name=values[0],
        api_key=values[1],
        api_secret=values[2],
        secure=True,
    )
    _configured = True
    return True


def upload_creator_image(image_file, creator_id):
    if not image_file or not image_file.filename:
        return None
    if not _configured:
        raise RuntimeError("Cloudinary is not configured")

    result = cloudinary.uploader.upload(
        image_file,
        folder="brandconnect/creators",
        public_id=f"creator-{creator_id}",
        overwrite=True,
        resource_type="image",
    )
    return result["secure_url"]
