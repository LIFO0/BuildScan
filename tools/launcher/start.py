import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _print(prefix: str, msg: str) -> None:
    print(f"[{prefix}] {msg}", flush=True)


def require_cmd(cmd: str, hint: str) -> bool:
    from shutil import which

    if which(cmd) is None:
        _print("ERROR", f"Missing tool: {cmd}. {hint}")
        return False
    return True


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, shell=False)
    return int(p.returncode)


def ensure_venv(service_dir: Path) -> Path:
    py = service_dir / ".venv" / "Scripts" / "python.exe"
    if py.exists():
        return py
    _print("INFO", f"Creating venv: {service_dir.relative_to(ROOT)}\\.venv")
    rc = run([sys.executable, "-m", "venv", ".venv"], cwd=service_dir)
    if rc != 0:
        raise RuntimeError(f"venv creation failed (rc={rc})")
    return py


def pip_install(venv_python: Path, requirements: Path) -> None:
    # Torch on Windows can be sensitive to setuptools upper bounds.
    # Keep setuptools<82 to avoid known conflicts (we've observed torch requiring it).
    run([str(venv_python), "-m", "pip", "install", "-U", "pip", "wheel", "setuptools<82"])
    rc = run([str(venv_python), "-m", "pip", "install", "-r", str(requirements)])
    if rc != 0:
        raise RuntimeError(f"pip install failed for {requirements}")


def deps_need_install(marker: Path, requirements: Path) -> bool:
    """
    Reinstall deps when requirements.txt changed after marker was written.
    """
    if not marker.exists():
        return True
    try:
        return requirements.stat().st_mtime > marker.stat().st_mtime
    except OSError:
        return True


def start_new_console(title: str, cmdline: str, cwd: Path) -> None:
    # Use cmd.exe to keep a visible window with logs.
    subprocess.Popen(
        ["cmd", "/k", cmdline],
        cwd=str(cwd),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=os.environ.copy(),
    )
    _print("OK", f"Started: {title}")


def start_frontend() -> None:
    fe = ROOT / "frontend-service"
    if not (fe / "package.json").exists():
        raise RuntimeError("frontend-service/package.json not found")
    if not require_cmd("node", "Install Node.js (LTS) and re-run.") or not require_cmd(
        "npm", "Install Node.js (includes npm) and re-run."
    ):
        raise SystemExit(1)
    # Install deps if missing
    if not (fe / "node_modules").exists():
        _print("INFO", "Installing frontend deps (npm install)...")
        rc = run(["npm", "install"], cwd=fe)
        if rc != 0:
            raise RuntimeError("npm install failed")
    start_new_console("Frontend (Vite)", "npm run dev", fe)
    _print("INFO", "UI: http://localhost:5173")


def start_django() -> None:
    be = ROOT / "backend-django"
    if not (be / "manage.py").exists():
        raise RuntimeError("backend-django/manage.py not found")

    venv_py = ensure_venv(be)
    marker = be / ".venv" / ".deps_ok"
    if deps_need_install(marker, be / "requirements.txt"):
        _print("INFO", "Installing Django deps...")
        pip_install(venv_py, be / "requirements.txt")
        _print("INFO", "Running migrations...")
        rc = run([str(venv_py), "manage.py", "migrate"], cwd=be)
        if rc != 0:
            raise RuntimeError("Django migrate failed")
        marker.write_text("ok", encoding="utf-8")

    start_new_console(
        "Django API (uvicorn)",
        r".\.venv\Scripts\uvicorn.exe lineguard.asgi:application --host 0.0.0.0 --port 8000",
        be,
    )
    _print("INFO", "API: http://localhost:8000/api/health")


def start_yolo() -> None:
    yo = ROOT / "yolov8-model-service"
    if not (yo / "requirements.txt").exists():
        raise RuntimeError("yolov8-model-service/requirements.txt not found")

    venv_py = ensure_venv(yo)
    marker = yo / ".venv" / ".deps_ok"
    if deps_need_install(marker, yo / "requirements.txt"):
        _print("INFO", "Installing YOLO deps (torch can be large)...")
        pip_install(venv_py, yo / "requirements.txt")
        marker.write_text("ok", encoding="utf-8")

    model = ROOT / "models" / "best.pt"
    if not model.exists():
        _print("WARN", f"Model not found: {model} (service may fail on first request)")

    env = os.environ.copy()
    env["MODEL_PATH"] = str(model)
    env["PORT"] = env.get("PORT", "8001")

    subprocess.Popen(
        ["cmd", "/k", r".\.venv\Scripts\python.exe -m app.main"],
        cwd=str(yo),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )
    _print("OK", "Started: YOLOv8 service")
    _print("INFO", "YOLO: http://localhost:8001/health")


def main(argv: list[str]) -> int:
    target = (argv[1].lower() if len(argv) > 1 else "all").strip()

    # Lightweight env template copies (best-effort)
    for src, dst in [
        (ROOT / ".env.example", ROOT / ".env"),
        (ROOT / "backend-django" / ".env.example", ROOT / "backend-django" / ".env"),
        (ROOT / "yolov8-model-service" / ".env.example", ROOT / "yolov8-model-service" / ".env"),
    ]:
        if src.exists() and not dst.exists():
            try:
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                _print("WARN", f"Created {dst.relative_to(ROOT)} from template")
            except Exception:
                pass

    try:
        if target in ("all", ""):
            start_frontend()
            start_django()
            start_yolo()
        elif target == "frontend":
            start_frontend()
        elif target == "django":
            start_django()
        elif target == "yolo":
            start_yolo()
        else:
            _print("ERROR", f"Unknown target '{target}'. Use: all|frontend|django|yolo|stop")
            return 2
    except Exception as e:
        _print("ERROR", str(e))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

