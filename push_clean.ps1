# Скрипт: одна чистая история без старого коммита с ключом
# Запуск: .\push_clean.ps1

Set-Location $PSScriptRoot

Write-Host "1. Создаём новую ветку без истории (orphan)..." -ForegroundColor Cyan
git checkout --orphan temp-main

Write-Host "2. Добавляем все текущие файлы..." -ForegroundColor Cyan
git add -A

Write-Host "3. Первый коммит (без старой истории)..." -ForegroundColor Cyan
git commit -m "Initial: Learning Assistant, конспект урока VPf05"

Write-Host "4. Удаляем старую main, переименовываем ветку в main..." -ForegroundColor Cyan
git branch -D main
git branch -m main

Write-Host "5. Отправляем в origin (--force, т.к. история изменилась)..." -ForegroundColor Cyan
git push --force -u origin main

Write-Host "Готово." -ForegroundColor Green
