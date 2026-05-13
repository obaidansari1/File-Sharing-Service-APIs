from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.name} owned by {self.user.username}"


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    file = models.FileField(upload_to='originals/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)
    resized_file = models.FileField(
        upload_to="uploads/resized/",
        null=True,
        blank=True
    )

    thumbnail_file = models.FileField(
        upload_to="uploads/thumbnails/",
        null=True,
        blank=True
    )

    processing_status = models.CharField(
        max_length=20,
        default="processing"
    )

    def __str__(self):
        return f"{self.filename} uploaded by {self.user.username}"

