import json
import threading
import time
from datetime import datetime, timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import AnalysisTask, TaskImage


def _send_task_update(task: AnalysisTask):
    channel_layer = get_channel_layer()
    payload = {
        "task_id": str(task.id),
        "status": task.status,
        "processed_files": task.processed_files,
        "total_files": task.total_files,
        "failed_files": task.failed_files,
        "defects_found": task.defects_found,
        "message": "",
    }

    async_to_sync(channel_layer.group_send)(
        f"task-{task.id}", {"type": "task.message", "text": json.dumps(payload)}
    )
    async_to_sync(channel_layer.group_send)(
        "history", {"type": "task.message", "text": json.dumps(payload)}
    )


def start_processing(task_id):
    """
    Локальная обработка без Docker/очередей:
    - берем загруженные файлы из БД
    - отправляем в yolov8-model-service (http://localhost:8001/predict)
    - сохраняем summary (detections/statistics/report) в TaskImage.summary
    - обновляем прогресс через WebSocket группы task-<id> и history
    """

    def run():
        import requests

        task = AnalysisTask.objects.get(id=task_id)
        task.status = AnalysisTask.Status.PROCESSING
        task.metadata = {
            "total_objects": 0,
            "defects_found": 0,
            "class_stats": {},
        }
        task.save(update_fields=["status", "metadata"])
        _send_task_update(task)

        images = list(TaskImage.objects.filter(task_id=task_id).select_related("source_file").order_by("created_at"))

        defects_found_total = 0
        processed = 0
        failed = 0
        total_objects_total = 0
        class_stats: dict[str, int] = {}

        for img in images:
            try:
                img.status = AnalysisTask.Status.PROCESSING
                img.save(update_fields=["status"])

                with img.source_file.file.open("rb") as f:
                    files = {"file": (img.source_file.original_name, f, img.source_file.content_type or "application/octet-stream")}
                    resp = requests.post("http://localhost:8001/predict?conf=0.25", files=files, timeout=120)
                resp.raise_for_status()
                summary = resp.json()

                img.summary = summary
                img.status = AnalysisTask.Status.COMPLETED
                img.error_message = None
                img.save(update_fields=["summary", "status", "error_message"])

                defects_found_total += int(summary.get("defects_count", 0) or 0)
                total_objects_total += int(summary.get("total_objects", 0) or 0)
                stats = summary.get("statistics") or {}
                if isinstance(stats, dict):
                    for k, v in stats.items():
                        try:
                            class_stats[k] = int(class_stats.get(k, 0) + int(v))
                        except Exception:
                            continue
                processed += 1

            except Exception as e:
                failed += 1
                img.status = AnalysisTask.Status.FAILED
                img.error_message = str(e)
                img.save(update_fields=["status", "error_message"])
            finally:
                task.refresh_from_db()
                task.processed_files = processed
                task.failed_files = failed
                task.defects_found = defects_found_total
                task.metadata = {
                    "total_objects": total_objects_total,
                    "defects_found": defects_found_total,
                    "class_stats": class_stats,
                }
                task.save(update_fields=["processed_files", "failed_files", "defects_found", "metadata"])
                _send_task_update(task)

                # небольшая пауза, чтобы UI успевал обновляться
                time.sleep(0.05)

        task.refresh_from_db()
        task.status = AnalysisTask.Status.COMPLETED if failed == 0 else AnalysisTask.Status.FAILED
        task.completed_at = datetime.now(timezone.utc)
        task.save(update_fields=["status", "completed_at"])
        _send_task_update(task)

    threading.Thread(target=run, daemon=True).start()

