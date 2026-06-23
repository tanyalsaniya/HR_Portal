# apps/common/middleware.py
import threading

_thread_locals = threading.local()

def get_current_user():
    """
    Retrieves the currently logged-in user from the thread-local storage.
    """
    return getattr(_thread_locals, 'user', None)

def get_current_request():
    """
    Retrieves the current request object from the thread-local storage.
    """
    return getattr(_thread_locals, 'request', None)

class CurrentUserMiddleware:
    """
    Middleware that stores the current request user and request object in thread-local storage.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        _thread_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            # Clean up after request is completed to avoid memory leaks
            if hasattr(_thread_locals, 'user'):
                del _thread_locals.user
            if hasattr(_thread_locals, 'request'):
                del _thread_locals.request
        return response

