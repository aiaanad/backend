# Общие экспорты схем из всех модулей
from __future__ import annotations

from .auth import Token
from .base import Blank, DeleteResponse, FindBase, FindDateRange, FindResult, PaginatedResponse
from .notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationSendToProjectRequest,
    NotificationSendToUserRequest,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    NotificationTemplate,
)
from .project import ProjectCreate, ProjectFull, ProjectListItem, ProjectListResponse, ProjectResponse, ProjectUpdate
from .resume import ResumeCreate, ResumeFull, ResumeListResponse, ResumeResponse, ResumeUpdate
from .user import UserBase, UserCreate, UserFull, UserListItem, UserListResponse, UserResponse, UserUpdate

__all__ = [
    "Blank",
    "DeleteResponse",
    "FindBase",
    "FindDateRange",
    "FindResult",
    "NotificationListResponse",
    "NotificationResponse",
    "NotificationSendToProjectRequest",
    "NotificationSendToUserRequest",
    "NotificationSettingsResponse",
    "NotificationSettingsUpdate",
    "NotificationTemplate",
    "PaginatedResponse",
    "ProjectCreate",
    "ProjectFull",
    "ProjectListItem",
    "ProjectListResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "ResumeCreate",
    "ResumeFull",
    "ResumeListResponse",
    "ResumeResponse",
    "ResumeUpdate",
    "Token",
    "UserBase",
    "UserCreate",
    "UserFull",
    "UserListItem",
    "UserListResponse",
    "UserResponse",
    "UserUpdate",
]
