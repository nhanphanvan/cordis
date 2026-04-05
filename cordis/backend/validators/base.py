from typing import Any


class BaseValidator:
    @classmethod
    async def validate(cls, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
