@echo off
setlocal

cd /d "%~dp0"

if not exist node_modules (
  echo Installing frontend deps...
  npm install
) else (
  echo node_modules already exists
)

echo Starting Vite dev server...
npm run dev

