# Используем официальный образ Python 3.10 (легкий вариант)
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями в контейнер
COPY requirements.txt .

# Устанавливаем зависимости через pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код в контейнер
COPY .env .

# Устанавливаем переменные окружения (опционально, можно задать через хостинг)
# ENV TELEGRAM_TOKEN=your_telegram_token
# ENV OPENAI_API_KEY=your_openai_key

# Команда запуска бота
CMD ["python3", "bot.py"]
