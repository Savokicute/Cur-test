# coding=utf-8
"""
RBAC 权限校验中间件

提供 FastAPI 依赖注入，用于接口级别的权限控制：
- require_permission("user:list")   → 校验用户是否拥有指定权限
- require_superuser()               → 仅允许超级管理员访问
- get_current_user()                → 获取当前登录用户信息（含角色）
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 安全方案：支持从 Header 获取用户名（与前端 localStorage 配合）
security = HTTPBearer(auto_error=False)


def _extract_username_from_request(request: Request) -> Optional[str]:
    """
    从请求中提取用户名（多种来源，按优先级）

    优先级：
    1. X-Session-Token（独立认证体系的 session token）
    2. X-Username 自定义 Header（前端通过 axios 拦截器注入）
    3. Cookie 中的用户信息

    Returns:
        用户名或 None
    """
    # 方式1：X-Session-Token（独立认证体系）
    session_token = request.headers.get("X-Session-Token")
    if session_token and session_token.strip():
        # 通过 auth 模块的 session store 验证
        try:
            from app.api.auth import get_current_user_from_token
            user = get_current_user_from_token(session_token.strip())
            if user:
                return user.username
        except Exception:
            pass  # token 无效，尝试其他方式

    # 方式2：X-Username Header
    username = request.headers.get("X-Username")
    if username and username.strip():
        return username.strip()

    # 方式3：Cookie 中的用户信息
    username_cookie = request.cookies.get("trendradar_user")
    if username_cookie and username_cookie.strip():
        return username_cookie.strip()

    return None


async def get_current_user(
    request: Request,
) -> Dict[str, Any]:
    """
    获取当前登录用户的基本信息（不含权限校验）

    用于需要知道"谁在操作"但不限制权限的场景。
    优先从独立用户体系 User 表获取，回退到 SSO 服务。

    Raises:
        HTTPException(401): 未提供身份信息或 Token 已过期

    Returns:
        {"username": str, "role": str}
    """
    from app.services.sso_service import get_sso_service, DEFAULT_ROLE
    from app.models import User, get_db

    username = _extract_username_from_request(request)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="未登录：请先登录后再访问",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 优先从独立用户体系 User 表查询
    db = next(get_db())
    try:
        local_user = db.query(User).filter_by(username=username).first()
        if local_user and local_user.is_active:
            return {
                "username": username,
                "role": local_user.role,
            }
    finally:
        db.close()

    # 回退到 SSO 服务
    sso = get_sso_service()
    user_info = sso.get_current_user_info(username)

    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="登录已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "username": username,
        "role": user_info.get("role", DEFAULT_ROLE),
    }


async def get_current_user_role(
    request: Request,
) -> str:
    """
    获取当前用户的角色标识

    用于前端判断菜单/按钮显隐等轻量场景。

    Returns:
        角色标识: "super_admin" | "user"
    """
    from app.services.sso_service import get_sso_service, DEFAULT_ROLE

    username = _extract_username_from_request(request)
    if not username:
        return None  # 未登录时返回 None，由调用方决定处理方式

    sso = get_sso_service()
    return sso.get_current_user_role(username)


def _get_role_permissions(role_id: str) -> List[str]:
    """
    查询指定角色的所有权限标识列表

    Args:
        role_id: 角色标识 ("super_admin" | "user")

    Returns:
        权限标识列表，如 ["user:list", "hotspot:view", ...]
    """
    try:
        from app.models import get_session_factory, RolePermission
        session_factory = get_session_factory()
        db = session_factory()
        try:
            perms = (
                db.query(RolePermission.permission_id)
                .filter_by(role_id=role_id)
                .all()
            )
            return [p.permission_id for p in perms]
        finally:
            db.close()
    except Exception as e:
        logger.error(f"查询角色 {role_id} 的权限失败: {e}")
        return []


def get_user_permissions(username: str) -> List[str]:
    """
    获取指定用户的所有权限标识

    流程：查用户角色 → 查角色权限 → 返回权限列表

    Args:
        username: 用户名

    Returns:
        权限标识列表
    """
    from app.services.sso_service import get_sso_service

    sso = get_sso_service()
    role = sso.get_current_user_role(username)

    if not role:
        return []

    return _get_role_permissions(role)


def require_permission(permission_id: str):
    """
    权限校验依赖工厂函数

    用法示例：
        @router.get("/users", dependencies=[Depends(require_permission("user:list"))])
        async def list_users(): ...

        @router.put("/users/{username}", dependencies=[Depends(require_permission("user:edit"))])
        async def update_user(...): ...

    Args:
        permission_id: 需要校验的权限标识，如 "user:list"

    Returns:
        FastAPI 可调用依赖

    Raises:
        HTTPException(401): 未登录
        HTTPException(403): 无该权限
    """

    async def _check_permission(
        request: Request,
    ) -> Dict[str, Any]:
        """内部校验逻辑"""
        from app.services.sso_service import get_sso_service, DEFAULT_ROLE
        from app.models import User, get_db

        # 1. 提取用户名
        username = _extract_username_from_request(request)
        if not username:
            raise HTTPException(
                status_code=401,
                detail="未登录：请先登录",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. 验证登录状态（优先从独立用户体系 User 表查询）
        db = next(get_db())
        try:
            local_user = db.query(User).filter_by(username=username).first()
            if local_user and local_user.is_active:
                role = local_user.role
                # 超级管理员放行所有请求
                if role == "super_admin":
                    logger.debug(f"[RBAC] 超级管理员 {username} 放行: {permission_id}")
                    return {
                        "username": username,
                        "role": role,
                        "permission_id": permission_id,
                    }
                # 普通用户：检查权限
                user_perms = _get_role_permissions(role)
                if permission_id in user_perms:
                    logger.debug(f"[RBAC] 用户 {username}({role}) 拥有权限: {permission_id}")
                    return {
                        "username": username,
                        "role": role,
                        "permission_id": permission_id,
                    }
                # 无权限
                raise HTTPException(
                    status_code=403,
                    detail=f"权限不足: 需要 [{permission_id}]",
                )
        finally:
            db.close()

        # 回退到 SSO 服务验证
        sso = get_sso_service()
        user_info = sso.get_current_user_info(username)
        if not user_info:
            raise HTTPException(
                status_code=401,
                detail="登录已过期，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # SSO 用户：超级管理员放行
        role = user_info.get("role", DEFAULT_ROLE)
        if role == "super_admin":
            logger.debug(f"[RBAC] 超级管理员 {username} 放行: {permission_id}")
            return {
                "username": username,
                "role": role,
                "permission_id": permission_id,
            }

        # SSO 普通用户：检查权限
        user_perms = _get_role_permissions(role)
        if permission_id in user_perms:
            logger.debug(f"[RBAC] 用户 {username}({role}) 拥有权限: {permission_id}")
            return {
                "username": username,
                "role": role,
                "permission_id": permission_id,
            }

        # 无权限 → 403
        logger.warning(
            f"[RBAC] 权限拒绝: 用户={username}, 角色={role}, "
            f"所需权限={permission_id}, 拥有权限={user_perms}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"权限不足：需要 [{permission_id}] 权限",
        )

    return _check_permission


def require_superuser():
    """
    仅超级管理员可访问的依赖

    比 require_permission 更严格，不检查具体权限，
    只要求角色为 super_admin。

    Returns:
        FastAPI 可调用依赖
    """

    async def _check_superadmin(request: Request) -> Dict[str, Any]:
        from app.services.sso_service import get_sso_service, DEFAULT_ROLE

        username = _extract_username_from_request(request)
        if not username:
            raise HTTPException(status_code=401, detail="未登录")

        sso = get_sso_service()
        user_info = sso.get_current_user_info(username)
        if not user_info:
            raise HTTPException(status_code=401, detail="登录已过期")

        role = user_info.get("role", DEFAULT_ROLE)
        if role != "super_admin":
            logger.warning(f"[RBAC] 非管理员拒绝: 用户={username}, 角色={role}")
            raise HTTPException(
                status_code=403,
                detail="此功能仅限超级管理员使用",
            )

        return {"username": username, "role": role}

    return _check_superadmin


# ========== 辅助工具函数 ==========

def check_has_permission(username: str, permission_id: str) -> bool:
    """
    同步检查用户是否拥有某权限（用于非 FastAPI 场景，如业务逻辑中）

    Args:
        username: 用户名
        permission_id: 权限标识

    Returns:
        是否拥有权限
    """
    from app.services.sso_service import get_sso_service, DEFAULT_ROLE

    sso = get_sso_service()
    role = sso.get_current_user_role(username)

    if role == "super_admin":
        return True

    perms = _get_role_permissions(role)
    return permission_id in perms


def invalidate_user_cache(username: str) -> None:
    """
    清除用户的缓存信息（角色变更后调用）

    当管理员的修改了某用户的角色后，应调用此方法清除缓存，
    使其下次请求时重新查询数据库。

    Args:
        username: 要清除缓存的用户名
    """
    from app.services.sso_service import get_sso_service

    sso = get_sso_service()
    # 清除 Token 缓存，强制下次重新登录或刷新
    if hasattr(sso, '_token_cache') and username in sso._token_cache:
        del sso._token_cache[username]
        logger.info(f"[RBAC] 已清除用户 {username} 的缓存")
