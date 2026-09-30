import logging

from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import JSONResponse

from app.deps import get_current_identity

MESSAGES = {
    400: ("Не вдалося виконати запит", "Перевірте введені дані та спробуйте ще раз."),
    401: ("Увійдіть до свого акаунта", "Щоб відкрити цю сторінку, потрібно увійти. Можливо, термін вашого сеансу завершився."),
    403: ("Доступ обмежено", "Ваш обліковий запис не має доступу до цієї дії. Адміністративні розділи доступні лише адміністраторам."),
    404: ("Сторінку не знайдено", "Можливо, адресу змінено або матеріал уже видалено."),
    405: ("Ця дія недоступна", "Відкрийте потрібний розділ сайту та повторіть дію звідти."),
    422: ("Перевірте введені дані", "Деякі обов’язкові поля не заповнені або мають неправильний формат."),
    429: ("Забагато запитів", "Зачекайте трохи й спробуйте ще раз."),
    500: ("Щось пішло не так", "Не вдалося завантажити сторінку. Спробуйте пізніше."),
}


def wants_html(request):
    path = request.url.path
    if path.startswith(("/api/", "/static/")) or path in {"/assistant/query", "/analytics/page-duration", "/openapi.json"}:
        return False
    if "application/json" in request.headers.get("content-type", ""):
        return False
    accepted = {}
    for value in request.headers.get("accept", "").split(","):
        media, *parameters = value.strip().lower().split(";")
        quality = 1.0
        for parameter in parameters:
            if parameter.strip().startswith("q="):
                try:
                    quality = float(parameter.strip()[2:])
                except ValueError:
                    quality = 0
        accepted[media] = quality
    return accepted.get("text/html", 0) > 0 and accepted.get("text/html", 0) >= accepted.get("application/json", 0)


def error_page(request, status_code, headers=None):
    code = status_code if status_code in MESSAGES else (500 if status_code >= 500 else 400)
    title, message = MESSAGES[code]
    identity = None
    try:
        identity = get_current_identity(request.cookies.get("session"))
    except (ValueError, TypeError, AttributeError):
        pass
    return request.app.state.templates.TemplateResponse(request, "error.html", {
        "request": request, "ident": identity, "status_code": status_code,
        "error_key": code, "error_title": title, "error_message": message,
    }, status_code=status_code, headers={**(headers or {}), "Cache-Control": "no-store", "Vary": "Accept"})


async def handle_http_error(request, exc):
    if wants_html(request):
        return error_page(request, exc.status_code, exc.headers)
    return await http_exception_handler(request, exc)


async def handle_validation_error(request, exc):
    if wants_html(request):
        return error_page(request, 422)
    return await request_validation_exception_handler(request, exc)


async def handle_server_error(request, exc):
    logging.getLogger(__name__).error("Unhandled application error", exc_info=(type(exc), exc, exc.__traceback__))
    if wants_html(request):
        return error_page(request, 500)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
