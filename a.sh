#!/bin/bash

# Путь к папке с распакованным Gologin
GOLOGIN_DIR="/home/vatsok/"

# Переход в директорию Gologin
cd "$GOLOGIN_DIR" || { echo "Ошибка: папка не найдена"; exit 1; }

# Запуск Gologin (он создаст /tmp/.mount_GoLogi*)
./GoLogin-4.0.6 &

# Ожидание создания временного каталога (максимум 30 сек)
echo "Ожидание создания временного каталога..."
for i in {1..30}; do
    SANDBOX_PATH=$(find /tmp -maxdepth 2 -name "chrome-sandbox" 2>/dev/null | head -1)
    if [ -n "$SANDBOX_PATH" ]; then
        echo "Найден chrome-sandbox: $SANDBOX_PATH"
        break
    fi
    sleep 1
done

# Если файл не найден — ошибка
if [ -z "$SANDBOX_PATH" ]; then
    echo "Ошибка: не удалось найти chrome-sandbox в /tmp"
    exit 1
fi

# Установка правильных прав
echo "Настройка прав для $SANDBOX_PATH"
sudo chown root:root "$SANDBOX_PATH"
sudo chmod 4755 "$SANDBOX_PATH"

# Проверка
ls -l "$SANDBOX_PATH"

echo "Готово! Gologin запущен с песочницей."