import uuid
from django.db import models


class StoredFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=512)
    content_type = models.CharField(max_length=128, blank=True, default="")
    file = models.FileField(upload_to="uploads/")
    size = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalysisTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    route_name = models.CharField(max_length=250, null=True, blank=True)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    defects_found = models.IntegerField(default=0)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class TaskImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(AnalysisTask, on_delete=models.CASCADE, related_name="images")
    source_file = models.ForeignKey(StoredFile, on_delete=models.PROTECT, related_name="task_images")
    status = models.CharField(max_length=32, default=AnalysisTask.Status.PENDING)
    summary = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

