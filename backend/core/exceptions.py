"""Manejador de excepciones unificado para respuestas de error consistentes."""

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Envuelve los errores de DRF en un formato uniforme para el frontend.

    Formato de salida::

        {
            "success": false,
            "status_code": 400,
            "errors": { ... }   # detalle original de DRF
        }
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    response.data = {
        "success": False,
        "status_code": response.status_code,
        "errors": detail,
    }
    return response
