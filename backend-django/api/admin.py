from django.contrib import admin
from .models import AnalysisTask, StoredFile, TaskImage


admin.site.register(AnalysisTask)
admin.site.register(StoredFile)
admin.site.register(TaskImage)

