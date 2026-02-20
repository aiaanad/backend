from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from src.core.container import get_notification_service, get_notification_settings_service
from src.core.dependencies import get_current_user
from src.core.logging_config import api_logger
from src.model.models import User
from src.notifications.templates import build_notification_examples
from src.schema.notification import (
    NotificationListResponse,
    NotificationMarkAllReadRequest,
    NotificationReadUpdateRequest,
    NotificationResponse,
    NotificationSendToProjectRequest,
    NotificationSendToUserRequest,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from src.services.notification_service import NotificationService
from src.services.notification_settings_service import NotificationSettingsService

notification_router = APIRouter(tags=["notification"])


@notification_router.get(
    "/notifications",
    response_model=NotificationListResponse,
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        200: {
            "description": "Notifications list",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "n-1",
                                "recipient_id": 1,
                                "sender_id": 2,
                                "project_id": 42,
                                "type": "project_announcement",
                                "status": "read",
                                "title": "Объявление проекта",
                                "body": "Новое объявление в проекте «Alpha»: Standup at 10:00",
                                "channels": ["in_app"],
                                "created_at": "2026-02-17T10:00:00Z",
                                "sent_at": "2026-02-17T10:00:05Z",
                                "read_at": "2026-02-17T10:05:00Z",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "limit": 10,
                        "total_pages": 1,
                    }
                }
            },
        },
    },
)
async def fetch_my_notifications(
    request: Request,
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=100, description="Количество уведомлений на странице"),
    notification_service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """Возвращает список уведомлений текущего пользователя с пагинацией"""
    client_ip = request.client.host if request.client else "unknown"
    try:
        notifications, total = await notification_service.list_user_notifications(current_user.id, page, limit)
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        items = [NotificationResponse.model_validate(notification) for notification in notifications]
        response = NotificationListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
    except Exception as e:
        api_logger.log_error(method="GET", path="/notifications", error=e, user_id=current_user.id)
        raise
    else:
        api_logger.log_request(
            method="GET",
            path="/notifications",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return response


@notification_router.post(
    "/users/{user_id}/notifications",
    response_model=NotificationResponse,
    responses={
        400: {
            "description": "Invalid template or missing payload fields",
            "content": {"application/json": {"example": {"detail": "Missing payload fields"}}},
        },
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        200: {
            "description": "Notification created",
            "content": {
                "application/json": {
                    "example": {
                        "id": "n-1",
                        "recipient_id": 1,
                        "sender_id": 2,
                        "project_id": 42,
                        "type": "project_invitation",
                        "status": "pending",
                        "title": "Приглашение в проект",
                        "body": "Вас пригласили в проект «Alpha».",
                        "channels": ["in_app"],
                        "created_at": "2026-02-17T10:00:00Z",
                        "sent_at": None,
                        "read_at": None,
                    }
                }
            },
        },
    },
)
async def send_notification_to_user(
    request: Request,
    user_id: int,
    request_data: NotificationSendToUserRequest = Body(
        ...,
        examples=build_notification_examples(include_project_id=True, include_author=False),
    ),
    notification_service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Отправляет уведомление одному пользователю"""
    client_ip = request.client.host if request.client else "unknown"
    try:
        notification = await notification_service.send_to_user(
            recipient_id=user_id,
            sender_id=current_user.id,
            template_key=request_data.template_key.value,
            payload=request_data.payload,
            project_id=request_data.project_id,
            channels=[channel.value for channel in request_data.channels],
        )
    except Exception as e:
        api_logger.log_error(method="POST", path="/users/{user_id}/notifications", error=e, user_id=current_user.id)
        raise
    else:
        api_logger.log_request(
            method="POST",
            path="/users/{user_id}/notifications",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return NotificationResponse.model_validate(notification)


@notification_router.post(
    "/projects/{project_id}/notifications",
    response_model=list[NotificationResponse],
    responses={
        400: {
            "description": "Invalid template or missing payload fields",
            "content": {"application/json": {"example": {"detail": "Missing payload fields"}}},
        },
        401: {"description": "Unauthorized"},
        404: {"description": "Project not found"},
        422: {"description": "Validation error"},
        200: {
            "description": "Notifications created",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "n-1",
                            "recipient_id": 10,
                            "sender_id": 2,
                            "project_id": 42,
                            "type": "project_announcement",
                            "status": "pending",
                            "title": "Объявление проекта",
                            "body": "Новое объявление в проекте «Alpha»: Standup at 10:00",
                            "channels": ["in_app"],
                            "created_at": "2026-02-17T10:00:00Z",
                            "sent_at": None,
                            "read_at": None,
                        }
                    ]
                }
            },
        },
    },
)
async def send_notification_to_project(
    request: Request,
    project_id: int,
    request_data: NotificationSendToProjectRequest = Body(
        ...,
        examples=build_notification_examples(include_project_id=False, include_author=True),
    ),
    notification_service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    """Отправляет уведомления участникам проекта"""
    client_ip = request.client.host if request.client else "unknown"
    try:
        notifications = await notification_service.send_to_project_participants(
            project_id=project_id,
            sender_id=current_user.id,
            template_key=request_data.template_key.value,
            payload=request_data.payload,
            include_author=request_data.include_author,
            channels=[channel.value for channel in request_data.channels],
        )
    except Exception as e:
        api_logger.log_error(
            method="POST",
            path="/projects/{project_id}/notifications",
            error=e,
            user_id=current_user.id,
        )
        raise
    else:
        api_logger.log_request(
            method="POST",
            path="/projects/{project_id}/notifications",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return [NotificationResponse.model_validate(notification) for notification in notifications]


@notification_router.get(
    "/notifications/templates",
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        200: {
            "description": "Templates required fields",
            "content": {
                "application/json": {
                    "example": {
                        "project_invitation": {"required": ["project_name"]},
                        "project_announcement": {"required": ["project_name", "message"]},
                        "system_alert": {"required": ["message"]},
                    }
                }
            },
        },
    },
)
async def get_notification_templates(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Возвращает список обязательных полей шаблонов"""
    client_ip = request.client.host if request.client else "unknown"
    try:
        templates = notification_service.list_templates()
    except Exception as e:
        api_logger.log_error(method="GET", path="/notifications/templates", error=e, user_id=None)
        raise
    else:
        api_logger.log_request(
            method="GET",
            path="/notifications/templates",
            user_id=None,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return templates


@notification_router.get(
    "/notifications/settings",
    response_model=NotificationSettingsResponse,
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        200: {
            "description": "Notification settings",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "email_enabled": True,
                        "telegram_enabled": False,
                        "in_app_enabled": True,
                        "project_invitation_enabled": True,
                        "project_removal_enabled": True,
                        "join_request_enabled": True,
                        "join_response_enabled": True,
                        "project_announcement_enabled": True,
                        "system_alert_enabled": True,
                    }
                }
            },
        },
    },
)
async def get_notification_settings(
    request: Request,
    notification_settings_service: NotificationSettingsService = Depends(get_notification_settings_service),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    """Возвращает настройки уведомлений текущего пользователя"""
    client_ip = request.client.host if request.client else "unknown"
    try:
        settings = await notification_settings_service.get_settings(current_user.id)
    except Exception as e:
        api_logger.log_error(method="GET", path="/notifications/settings", error=e, user_id=current_user.id)
        raise
    else:
        api_logger.log_request(
            method="GET",
            path="/notifications/settings",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return NotificationSettingsResponse.model_validate(settings)


@notification_router.patch(
    "/notifications/settings",
    response_model=NotificationSettingsResponse,
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        200: {
            "description": "Notification settings updated",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "email_enabled": True,
                        "telegram_enabled": True,
                        "in_app_enabled": True,
                        "project_invitation_enabled": True,
                        "join_request_enabled": True,
                        "join_response_enabled": True,
                        "project_announcement_enabled": True,
                        "system_alert_enabled": True,
                    }
                }
            },
        },
    },
)
async def update_notification_settings(
    request: Request,
    request_data: NotificationSettingsUpdate = Body(
        ...,
        example={
            "email_enabled": True,
            "telegram_enabled": True,
            "in_app_enabled": True,
            "project_invitation_enabled": True,
            "project_removal_enabled": False,
            "join_request_enabled": True,
            "join_response_enabled": True,
            "project_announcement_enabled": False,
            "system_alert_enabled": True,
        },
    ),
    notification_settings_service: NotificationSettingsService = Depends(get_notification_settings_service),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    """Обновляет настройки уведомлений текущего пользователя"""
    client_ip = request.client.host if request.client else "unknown"
    try:
        settings = await notification_settings_service.update_settings(current_user.id, request_data)
    except Exception as e:
        api_logger.log_error(method="PATCH", path="/notifications/settings", error=e, user_id=current_user.id)
        raise
    else:
        api_logger.log_request(
            method="PATCH",
            path="/notifications/settings",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return NotificationSettingsResponse.model_validate(settings)


@notification_router.patch(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
    responses={
        400: {
            "description": "Invalid body",
            "content": {"application/json": {"example": {"detail": "Only is_read=true is supported"}}},
        },
        401: {"description": "Unauthorized"},
        404: {"description": "Notification not found"},
        422: {"description": "Validation error"},
        200: {
            "description": "Notification marked as read",
            "content": {
                "application/json": {
                    "example": {
                        "id": "n-1",
                        "recipient_id": 1,
                        "sender_id": 2,
                        "project_id": 42,
                        "type": "project_announcement",
                        "status": "read",
                        "title": "Объявление проекта",
                        "body": "Новое объявление в проекте «Alpha»: Standup at 10:00",
                        "channels": ["in_app"],
                        "created_at": "2026-02-17T10:00:00Z",
                        "sent_at": "2026-02-17T10:00:05Z",
                        "read_at": "2026-02-17T10:05:00Z",
                    }
                }
            },
        },
    },
)
async def mark_notification_read(
    request: Request,
    notification_id: str,
    request_data: NotificationReadUpdateRequest = Body(..., example={"is_read": True}),
    notification_service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Помечает уведомление как прочитанное"""
    if not request_data.is_read:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only is_read=true is supported",
        )
    client_ip = request.client.host if request.client else "unknown"
    try:
        notification = await notification_service.mark_read(current_user.id, notification_id)
    except Exception as e:
        api_logger.log_error(method="PATCH", path="/notifications/{notification_id}", error=e, user_id=current_user.id)
        raise
    else:
        api_logger.log_request(
            method="PATCH",
            path="/notifications/{notification_id}",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return NotificationResponse.model_validate(notification)


@notification_router.patch(
    "/notifications",
    responses={
        400: {
            "description": "Invalid body",
            "content": {"application/json": {"example": {"detail": "Only mark_all_read=true is supported"}}},
        },
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        200: {
            "description": "All notifications marked as read",
            "content": {"application/json": {"example": {"updated": 3}}},
        },
    },
)
async def mark_all_notifications_read(
    request: Request,
    request_data: NotificationMarkAllReadRequest = Body(..., example={"mark_all_read": True}),
    notification_service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Помечает все уведомления пользователя как прочитанные"""
    if not request_data.mark_all_read:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only mark_all_read=true is supported",
        )
    client_ip = request.client.host if request.client else "unknown"
    try:
        updated = await notification_service.mark_all_read(current_user.id)
    except Exception as e:
        api_logger.log_error(method="PATCH", path="/notifications", error=e, user_id=current_user.id)
        raise
    else:
        api_logger.log_request(
            method="PATCH",
            path="/notifications",
            user_id=current_user.id,
            ip_address=client_ip,
            status_code=200,
            response_time=0.0,
        )
        return {"updated": updated}
