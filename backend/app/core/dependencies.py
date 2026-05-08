from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Annotated

from ..db import get_db
from ..models.db_models import User
from ..core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if user is None:
        raise credentials_exception

    return user

# The orchestrator is now managed via the Crew classes in app.crews.krishi_crew
# We remove the global KrishiCrewOrchestrator singleton and use the new Crew definitions.
# The endpoints will instantiate the specific Crew they need.

class _OrchestratorStub:
    def __getattr__(self, name):
        raise RuntimeError(
            "The global orchestrator is deprecated. Use Crew classes in app.crews.krishi_crew instead."
        )

orchestrator = _OrchestratorStub()
