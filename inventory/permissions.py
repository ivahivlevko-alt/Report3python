WORKER_GROUP = 'Працівник'


def is_admin(user):
    """Адміністратор (superuser) має повний доступ до керування даними."""
    return user.is_authenticated and user.is_superuser
