from rest_framework import serializers
from .models import AnalysisTask, TaskImage


class AnalysisTaskSerializer(serializers.ModelSerializer):
    results_archive_file_id = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisTask
        fields = [
            "id",
            "status",
            "route_name",
            "total_files",
            "processed_files",
            "failed_files",
            "defects_found",
            "metadata",
            "results_archive_file_id",
            "created_at",
            "completed_at",
        ]

    def get_results_archive_file_id(self, obj: AnalysisTask):
        # В Django-версии пока не формируем архив результатов
        return None


class TaskImageSerializer(serializers.ModelSerializer):
    file_id = serializers.UUIDField(source="source_file_id")
    file_name = serializers.CharField(source="source_file.original_name", read_only=True)
    file_size = serializers.IntegerField(source="source_file.size", read_only=True)
    status = serializers.CharField(read_only=True)
    summary = serializers.JSONField(required=False, allow_null=True)
    original_url = serializers.SerializerMethodField()
    result_url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = TaskImage
        fields = [
            "id",
            "file_id",
            "file_name",
            "file_size",
            "status",
            "summary",
            "original_url",
            "result_url",
            "thumbnail",
            "created_at",
        ]

    def get_original_url(self, obj: TaskImage) -> str:
        # same-origin relative URL (through Vite proxy /api -> :8000)
        return f"/api/files/{obj.source_file_id}/download"

    def get_result_url(self, obj: TaskImage) -> str:
        # пока результат = исходник (аннотированное изображение можно добавить позже)
        return f"/api/files/{obj.source_file_id}/download"

    def get_thumbnail(self, obj: TaskImage):
        # для совместимости с фронтом; оптимизацию можно добавить позже
        return None

