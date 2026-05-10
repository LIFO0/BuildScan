from django.urls import path
from . import views


urlpatterns = [
    path("health", views.health),
    path("analysis/history", views.AnalysisHistoryView.as_view()),
    path("analysis/tasks/<uuid:task_id>", views.AnalysisTaskDetailView.as_view()),
    path("analysis/tasks/<uuid:task_id>/images", views.AnalysisTaskImagesView.as_view()),
    path("predict/batch", views.PredictBatchView.as_view()),
    path("files/<uuid:file_id>/download", views.FileDownloadView.as_view()),
]

