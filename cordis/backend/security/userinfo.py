from typing import Any

from starlette.authentication import BaseUser


class UserInfo(BaseUser, dict[str, Any]):
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def email(self) -> str:
        return str(self.get("email", ""))

    @property
    def display_name(self) -> str:
        return self.get("display_name") or self.email or self.identity

    @property
    def identity(self) -> str:
        return str(self["identity"])
