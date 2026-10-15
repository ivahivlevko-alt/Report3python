from .permissions import is_admin


def roles(request):
    return {'is_admin': is_admin(request.user)}
