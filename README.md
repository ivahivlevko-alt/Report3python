# Облік товарів, клієнтів та замовлень у супермаркеті (Django)

## Встановлення і запуск
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env            # впишіть DB_PASSWORD та DJANGO_SECRET_KEY
    python manage.py migrate
    python manage.py seed           # групи, користувачі, демо-дані
    python manage.py runserver
База даних: створіть порожню БД `supermarket_site` у MySQL (utf8mb4).
Сайт: http://127.0.0.1:8000/

| Роль | Логін / пароль | Права |
|---|---|---|
| Адміністратор | admin / admin12345 | керує всім: товари, категорії, замовлення, /admin/ |
| Працівник | worker / worker12345 | продаж: перегляд товарів і категорій, створення замовлень (кошик із багатьох товарів) та зміна їх статусу |

Тести: `python manage.py test`
