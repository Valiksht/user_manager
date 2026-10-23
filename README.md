# Установка и запуск

## Подготовка виртульальнго окружения

### Создание виртуального окружения

python -m venv venv

### Установка зависимостей

pip install -r requirements.txt

### Активация виртального окружения

source venv/Scripts/activate

## Создание файла с секретами

### Создагние файла

в корне проекта создайте файл ".env"

### Добавление данных в файл .env

Внесите данные согласно фалу .env.example

### Важно

при DEBUG=True проект работает в тестовом режимне на базе данных sqlite

при DEBUG=False Проекту нужно сперва запустить сервер PostqreSQL

Генерировать SECRET_KEY лучше командой:

python -c "import secrets; print(secrets.token_urlsafe(32))"

Но подойдет и любой случайный набор символов

### Запуск сервера PostgreSQL в контейнере Docker

Внесите данные в файл docker-compose.jml согласно .env

Запустите командой 
docker compose up -d

Проверить работу контейнера
docker compose ps

Выключить контейнер 
docker compose down
выключить и удалить контейнер 
docker compose down -v

## Создание и применеие миграций

### Создание миграций
alembic revision --autogenerate -m "init base"

### Применение миграций

alembic upgrade head

### Создание суперпользователя

python -m app.services.create_superuser

## Запуск сервера

uvicorn app.main:app --reload

### Для тестирования создана postman коллекция

Team_app.postman_collection.json

## Выключение сервера

комбинация клавиш ctrl + c

## Запуск тестов

### Создание тестовой базы в postgresql

docker exec -it user_manager_postgres psql -U postgres -d postgres -c "CREATE DATABASE team_manager_test;"

### Запуск тестов в однопоточном режине

pytest 
или 
python -m pytest

### Запуск тестов в многопоточном режимне

Не реализован

### Переименовать ветку
git branch -M main
git push -u origin main --force

