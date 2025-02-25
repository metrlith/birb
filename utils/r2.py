import boto3
from botocore.config import Config
from dotenv import load_dotenv  
from PIL import Image
from io import BytesIO
import discord
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
load_dotenv()



logger = logging.getLogger(__name__)

s3_client = None
if (os.getenv("R2_URL") and os.getenv("ACCESS_KEY_ID") and os.getenv("SECRET_ACCESS_KEY") and os.getenv("BUCKET")):
    s3_client = boto3.client(
        service_name="s3",
        endpoint_url=os.getenv("R2_URL"),
        aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="weur",
    )


async def CompressImage(image_bytes: bytes) -> bytes:
    if s3_client is None:
        return ""
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("RGB")  
    output = BytesIO()
    img.save(output, format="JPEG", quality=50)  
    return output.getvalue()

async def upload_file_to_r2(file_bytes: bytes, filename: str, message: discord.Message) -> str:
    if s3_client is None:
        return ""
    
    if filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
        file_bytes = await CompressImage(file_bytes)
        content_type = 'image/jpeg'
    elif filename.lower().endswith(('mp4', 'avi', 'mov', 'webm')):
        content_type = 'video/mp4' 
    elif filename.lower().endswith(('mp3', 'wav', 'ogg')):
        content_type = 'audio/mpeg'  
    else:
        content_type = 'application/octet-stream'  
    
    s3_client.upload_fileobj(
        BytesIO(file_bytes),
        os.getenv('BUCKET'),
        f"{message.id}/{filename}",
        ExtraArgs={'ContentType': content_type}
    )
    
    return f"{os.getenv('FILE_URL')}/{message.id}/{filename}"


async def ClearOldFiles():
    if s3_client is None:
        return
    response = s3_client.list_objects_v2(Bucket=os.getenv("BUCKET"))
    if "Contents" in response:
        for obj in response["Contents"]:
            last_modified = obj["LastModified"]
            if (datetime.now(timezone.utc) - last_modified) > timedelta(days=31):
                s3_client.delete_object(Bucket=os.getenv("BUCKET"), Key=obj["Key"])
