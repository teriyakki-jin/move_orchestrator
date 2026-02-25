from .search_services import search_services
from .get_service_detail import get_service_detail
from .get_form_schema import get_form_schema
from .create_draft import create_application_draft


class ToolNotAllowedError(Exception):
    pass


TOOL_WHITELIST: dict[str, callable] = {
    "search_services": search_services,
    "get_service_detail": get_service_detail,
    "get_form_schema": get_form_schema,
    "create_application_draft": create_application_draft,
}


def dispatch(tool_name: str, **kwargs) -> dict:
    """화이트리스트에 등록된 툴만 실행합니다."""
    if tool_name not in TOOL_WHITELIST:
        raise ToolNotAllowedError(f"허용되지 않은 툴: {tool_name}")
    return TOOL_WHITELIST[tool_name](**kwargs)
