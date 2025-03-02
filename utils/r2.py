import boto3
from botocore.config import Config
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import discord
import logging
import os
from datetime import datetime, timezone, timedelta
import ffmpeg

load_dotenv()

logger = logging.getLogger(__name__)

s3_client = None
if (
    os.getenv("R2_URL")
    and os.getenv("ACCESS_KEY_ID")
    and os.getenv("SECRET_ACCESS_KEY")
    and os.getenv("BUCKET")
):
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


import ffmpeg
from io import BytesIO


async def CompressVideo(video_bytes: bytes) -> bytes:
    input_file = BytesIO(video_bytes)
    output_file = BytesIO()
    process = (
        ffmpeg.input("pipe:0", format="mp4")
        .output(
            "pipe:1",
            format="mp4",
            vcodec="libx264",
            crf=30,
            movflags="+faststart+frag_keyframe+empty_moov",
        )
        .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )

    stdout, stderr = process.communicate(input=input_file.read())

    if process.returncode != 0:
        return b""

    output_file.write(stdout)
    return output_file.getvalue()


async def upload_file_to_r2(
    file_bytes: bytes, filename: str, message: discord.Message
) -> str:
    if s3_client is None:
        return ""

    if filename.lower().endswith(("png", "jpg", "jpeg", "gif", "bmp")):
        file_bytes = await CompressImage(file_bytes)
        content_type = "image/jpeg"
    elif filename.lower().endswith(("mp4", "avi", "mov", "webm")):
        content_type = "video/mp4"
        file_bytes = await CompressVideo(file_bytes)
    elif filename.lower().endswith(("mp3", "wav", "ogg")):
        content_type = "audio/mpeg"
    else:
        content_type = "application/octet-stream"

    s3_client.upload_fileobj(
        BytesIO(file_bytes),
        os.getenv("BUCKET"),
        f"{message.id}/{filename}",
        ExtraArgs={"ContentType": content_type},
    )

    return f"{os.getenv('FILE_URL')}/{message.id}/{filename}"


async def ClearOldFiles():
    if s3_client is None:
        return

    continuation_token = None
    list_params = {"Bucket": os.getenv("BUCKET")}
    if continuation_token:
        list_params["ContinuationToken"] = continuation_token

    response = s3_client.list_objects_v2(**list_params)
    if "Contents" in response:
        for obj in response["Contents"]:
            last_modified = obj["LastModified"]
            file_extension = obj["Key"].split(".")[-1].lower()
            if file_extension in ["mp4", "avi", "mov", "webm"] and (
                datetime.now(timezone.utc) - last_modified
            ) > timedelta(days=15):
                s3_client.delete_object(Bucket=os.getenv("BUCKET"), Key=obj["Key"])

            elif (datetime.now(timezone.utc) - last_modified) > timedelta(days=31):
                s3_client.delete_object(Bucket=os.getenv("BUCKET"), Key=obj["Key"])

    continuation_token = response.get("NextContinuationToken")
    if not continuation_token:
        return
