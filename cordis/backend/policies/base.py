from collections.abc import Awaitable, Callable
from typing import Any

from cordis.backend.exceptions import AppStatus, ForbiddenOperationError, UnauthorizedError
from cordis.backend.models import User

PolicyAction = Callable[..., Awaitable[bool]]


async def is_authorized(actor: User | None, policy_action: PolicyAction, *args: Any, **kwargs: Any) -> bool:
    return await policy_action(actor, *args, **kwargs)


async def authorize(
    actor: User | None,
    policy_action: PolicyAction,
    *args: Any,
    message: str = "Operation not permitted",
    app_status: AppStatus = AppStatus.ERROR_REPOSITORY_ACCESS_DENIED,
    unauthorized_message: str | None = None,
    unauthorized_app_status: AppStatus | None = None,
    **kwargs: Any,
) -> None:
    if not await is_authorized(actor, policy_action, *args, **kwargs):
        if actor is None and unauthorized_message is not None and unauthorized_app_status is not None:
            raise UnauthorizedError(unauthorized_message, app_status=unauthorized_app_status)
        raise ForbiddenOperationError(message, app_status=app_status)
