# apps/common/middleware.py
import threading

_thread_locals = threading.local()

def get_current_user():
    """
    Retrieves the currently logged-in user from the thread-local storage.
    """
    return getattr(_thread_locals, 'user', None)

class CurrentUserMiddleware:
    """
    Middleware that stores the current request user in thread-local storage.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        try:
            response = self.get_response(request)
        finally:
            # Clean up after request is completed to avoid memory leaks
            if hasattr(_thread_locals, 'user'):
                del _thread_locals.user
        return response
