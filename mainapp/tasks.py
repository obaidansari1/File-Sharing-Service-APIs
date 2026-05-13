from celery import shared_task
from PIL import Image
from .models import File
import os
from django.conf import settings
import subprocess

@shared_task
def process_image(file_id):

    try:

        file_obj = File.objects.get(id=file_id)

        file_path = file_obj.file.path

        filename = os.path.basename(file_path)

        name, ext = os.path.splitext(filename)

        ext = ext.lower()

        video_extensions = [".mp4", ".mov", ".avi", ".mkv"]

        image_extensions = [".png", ".jpg", ".jpeg", ".webp"]

        # ------------------------
        # PDF Processing
        # ------------------------

        if ext == ".pdf":

            import fitz

            pdf = fitz.open(file_path)

            page = pdf.load_page(0)

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            thumb_relative_path = f"thumbnails/{name}_thumb.png"

            thumb_full_path = os.path.join(
                settings.MEDIA_ROOT,
                thumb_relative_path
            )

            os.makedirs(
                os.path.dirname(thumb_full_path),
                exist_ok=True
            )

            pix.save(thumb_full_path)

            File.objects.filter(id=file_id).update(
                thumbnail_file=thumb_relative_path,
                processing_status="completed"
            )

            print("PDF thumbnail generated")

        # ------------------------
        # Video Processing
        # ------------------------

        elif ext in video_extensions:

            # Thumbnail generation

            thumb_relative_path = f"thumbnails/{name}_thumb.jpg"

            thumb_full_path = os.path.join(
                settings.MEDIA_ROOT,
                thumb_relative_path
            )

            os.makedirs(
                os.path.dirname(thumb_full_path),
                exist_ok=True
            )

            subprocess.run([
                "ffmpeg",
                "-i", file_path,
                "-ss", "00:00:01",
                "-vframes", "1",
                thumb_full_path
            ])

            # Optimized video

            resized_relative_path = f"resized/{name}_720p.mp4"

            resized_full_path = os.path.join(
                settings.MEDIA_ROOT,
                resized_relative_path
            )

            os.makedirs(
                os.path.dirname(resized_full_path),
                exist_ok=True
            )

            subprocess.run([
                "ffmpeg",
                "-i", file_path,
                "-vf", "scale=-1:720",
                "-c:v", "libx264",
                "-crf", "28",
                resized_full_path
            ])

            File.objects.filter(id=file_id).update(
                thumbnail_file=thumb_relative_path,
                resized_file=resized_relative_path,
                processing_status="completed"
            )

            print("Video processing completed")

        # ------------------------
        # Image Processing
        # ------------------------

        elif ext in image_extensions:

            img = Image.open(file_path)

            # Thumbnail

            thumbnail = img.copy()

            thumbnail.thumbnail((200, 200))

            thumb_relative_path = f"thumbnails/{name}_thumb.webp"

            thumb_full_path = os.path.join(
                settings.MEDIA_ROOT,
                thumb_relative_path
            )

            os.makedirs(
                os.path.dirname(thumb_full_path),
                exist_ok=True
            )

            thumbnail.save(
                thumb_full_path,
                "WEBP",
                quality=80
            )

            # Resized image

            resized = img.copy()

            resized.thumbnail((1200, 1200))

            resized_relative_path = f"resized/{name}_resized.webp"

            resized_full_path = os.path.join(
                settings.MEDIA_ROOT,
                resized_relative_path
            )

            os.makedirs(
                os.path.dirname(resized_full_path),
                exist_ok=True
            )

            resized.save(
                resized_full_path,
                "WEBP",
                quality=90
            )

            File.objects.filter(id=file_id).update(
                thumbnail_file=thumb_relative_path,
                resized_file=resized_relative_path,
                processing_status="completed"
            )

            print("Image processing completed")

            File.objects.filter(id=file_id).update(
                processing_status="completed"
            )

            print("Unsupported file type")

    except Exception as e:

        File.objects.filter(id=file_id).update(
            processing_status="failed"
        )

        print("Error:", str(e))