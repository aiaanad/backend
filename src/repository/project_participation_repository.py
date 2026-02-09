from __future__ import annotations

from sqlalchemy import select

from src.core.uow import IUnitOfWork
from src.model.models import ProjectParticipation
from src.repository.base_repository import BaseRepository


class ProjectParticipationRepository(BaseRepository[ProjectParticipation, dict, dict]):
    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)
        self._model = ProjectParticipation

    async def get_participant_ids_by_project_id(self, project_id: int) -> list[int]:
        result = await self.uow.session.execute(
            select(ProjectParticipation.participant_id).where(ProjectParticipation.project_id == project_id)
        )
        return [row[0] for row in result.all()]
