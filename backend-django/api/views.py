from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalysisTask, StoredFile, TaskImage
from .serializers import AnalysisTaskSerializer, TaskImageSerializer
from .services import start_processing


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "django-backend"})


class AnalysisHistoryView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", "100"))
        qs = AnalysisTask.objects.order_by("-created_at")[:limit]
        return Response(AnalysisTaskSerializer(qs, many=True).data)


class AnalysisTaskDetailView(APIView):
    def get(self, request, task_id):
        task = get_object_or_404(AnalysisTask, id=task_id)
        return Response(AnalysisTaskSerializer(task).data)


class AnalysisTaskImagesView(APIView):
    def get(self, request, task_id):
        task = get_object_or_404(AnalysisTask, id=task_id)
        images = TaskImage.objects.filter(task=task).order_by("created_at")
        data = TaskImageSerializer(images, many=True).data
        return Response({"images": data, "total": len(data)})


class PredictBatchView(APIView):
    """
    Контракт под фронт:
    - принимает multipart с полями `files` (много)
    - возвращает `{ task_id: "..." }`
    """

    def post(self, request):
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        task = AnalysisTask.objects.create(
            status=AnalysisTask.Status.PENDING,
            total_files=len(files),
            processed_files=0,
            failed_files=0,
            defects_found=0,
        )

        for f in files:
            stored = StoredFile.objects.create(
                original_name=f.name,
                content_type=getattr(f, "content_type", "") or "",
                file=f,
                size=getattr(f, "size", 0) or 0,
            )
            TaskImage.objects.create(task=task, source_file=stored)

        start_processing(task.id)
        return Response({"task_id": str(task.id)})


class FileDownloadView(APIView):
    def get(self, request, file_id):
        stored = get_object_or_404(StoredFile, id=file_id)
        if not stored.file:
            raise Http404()
        response = FileResponse(stored.file.open("rb"), as_attachment=True, filename=stored.original_name)
        return response

