from sqlalchemy.ext.asyncio import AsyncSession
from models.log import AuthLog


class LogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: AuthLog) -> AuthLog:
        self.db.add(log)
        await self.db.flush()
        return log
