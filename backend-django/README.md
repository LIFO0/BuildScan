## Django backend

API для фронтенда BuildScan: задачи анализа, файлы, история, WebSocket.

### Запуск (Windows / PowerShell)

```powershell
cd backend-django
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### Подключение фронтенда

Фронтенд уже настроен проксировать `"/api"` на `http://localhost:8000` (см. `frontend-service/vite.config.ts`).

- UI: `http://localhost:5173`
- API: `http://localhost:8000/api/...`
- WS: `ws://localhost:8000/api/ws/...`

