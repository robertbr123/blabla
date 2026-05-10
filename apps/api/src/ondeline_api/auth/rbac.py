"""Role-based access control dependency factory."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status

from ondeline_api.auth.deps import get_current_user
from ondeline_api.db.models.identity import Role, User


def require_role(*allowed: Role) -> Callable[[User], Awaitable[User]]:
    """Returns a FastAPI dependency that 403s when user.role not in `allowed`."""
    allowed_set = set(allowed)

    async def _dep(user: User = Depends(get_current_user)) -> User:  # noqa: B008
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient role",
            )
        return user

    return _dep
