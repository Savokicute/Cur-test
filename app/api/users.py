# coding=utf-8
"""
用户管理与权限控制 API

提供完整的用户管理 RESTful 接口：
- 用户列表/详情（分页、搜索、筛选）
- 编辑用户信息 / 修改角色 / 禁用启用
- 批量操作（改角色、改状态）
- 操作日志查询
- 当前用户信息与权限查询

所有写操作自动记录操作日志。
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.models import (
    get_db,
    User,
    LoginLog,
    Role,
    UserOperationLog,
)
from app.schemas.user_schemas import (
    # 请求
    UserUpdateRequest,
    RoleUpdateRequest,
    StatusUpdateRequest,
    BatchRoleRequest,
    BatchStatusRequest,
    UserQueryParams,
    LogQueryParams,
    # 响应
    UserInfoResponse,
    UserListResponse,
    OperationLogItem,
    OperationLogListResponse,
    BatchResultResponse,
    CurrentUserResponse,
    PermissionInfo,
    RoleInfo,
)
from app.core.permission import (
    get_current_user,
    require_permission,
    require_superuser,
    invalidate_user_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["用户管理"])


# ========== 辅助函数 ==========

def _record_log(
    db: Session,
    operator: str,
    action: str,
    target_user: str,
    detail: Optional[Dict] = None,
    request: Optional[Request] = None,
):
    """记录操作日志"""
    log = UserOperationLog(
        operator=operator,
        action=action,
        target_user=target_user,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
    )
    db.add(log)


def _get_role_name(role_id: str) -> str:
    """获取角色显示名称"""
    names = {"super_admin": "超级管理员", "user": "普通用户"}
    return names.get(role_id, role_id)


def _build_user_info(db: Session, user: User) -> Dict[str, Any]:
    """
    构建单个用户的完整信息字典

    从独立用户体系 users 表获取数据
    """
    role_name = _get_role_name(user.role)

    return {
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "email": user.email,
        "role": user.role,
        "role_name": role_name,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "login_count": user.login_count or 0,
        "remark": user.remark,
    }


def _check_last_admin(db: Session, target_username: str, new_role: str) -> bool:
    """
    检查是否是最后一个超级管理员

    Returns:
        True 表示可以修改，False 表示不能修改（最后一个管理员保护）
    """
    if new_role != "super_admin":
        return True  # 不是降级为普通用户，放行

    # 统计当前超级管理员数量
    admin_count = db.query(User).filter_by(role="super_admin").count()

    # 如果目标用户当前是超级管理员且只有 1 个，则阻止
    target = db.query(User).filter_by(username=target_username).first()
    if target and target.role == "super_admin" and admin_count <= 1:
        return False

    return True


# ========== 用户列表 & 详情 ==========

@router.get("", summary="用户列表",
            dependencies=[Depends(require_permission("user:list"))])
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    role: Optional[str] = Query(None, description="按角色筛选"),
    is_active: Optional[bool] = Query(None, description="按状态筛选"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """获取用户列表（支持搜索、筛选、排序、分页）"""
    query = db.query(User)

    # 关键词搜索（用户名或昵称）
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            (User.username.like(kw)) | (User.nickname.like(kw))
        )

    # 角色筛选
    if role:
        query = query.filter(User.role == role)

    # 状态筛选
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # 排序
    sort_column = getattr(User, sort_by, None)
    if sort_column is None:
        sort_column = User.created_at
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()

    # 构建响应
    items = [_build_user_info(db, u) for u in users]

    return UserListResponse(total=total, items=items)


@router.get("/me", summary="当前用户信息")
async def get_me(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户的完整信息和权限列表"""
    username = current_user["username"]
    role = current_user["role"]

    from app.core.permission import _get_role_permissions

    permissions = _get_role_permissions(role)

    return CurrentUserResponse(
        username=username,
        role=role,
        role_name=_get_role_name(role),
        permissions=permissions,
    )


@router.get("/{username}", summary="用户详情",
            dependencies=[Depends(require_permission("user:list"))])
async def get_user_detail(username: str, db: Session = Depends(get_db)):
    """获取单个用户的详细信息"""
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

    return UserInfoResponse(**_build_user_info(db, user))


# ========== 编辑用户 ==========

@router.put("/{username}", summary="编辑用户信息",
           dependencies=[Depends(require_permission("user:edit"))])
async def update_user(
    username: str,
    req: UserUpdateRequest,
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑用户基本信息（昵称、邮箱、备注）"""
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

    old_values = {}
    new_values = {}

    if req.nickname is not None:
        old_values["nickname"] = user.nickname
        user.nickname = req.nickname
        new_values["nickname"] = req.nickname

    if req.email is not None:
        old_values["email"] = user.email
        user.email = req.email
        new_values["email"] = str(req.email)

    if req.remark is not None:
        old_values["remark"] = user.remark
        user.remark = req.remark
        new_values["remark"] = req.remark

    detail = {"old": old_values, "new": new_values}
    _record_log(db, current_user["username"], "update_info", username, detail, request)
    db.commit()

    return {"code": 0, "message": "用户信息已更新"}


# ========== 修改角色 ==========

@router.put("/{username}/role", summary="修改用户角色",
           dependencies=[Depends(require_permission("user:edit"))])
async def update_user_role(
    username: str,
    req: RoleUpdateRequest,
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改指定用户的角色"""
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

    old_role = user.role
    new_role = req.role

    if old_role == new_role:
        return {"code": 0, "message": "角色未变化"}

    # 最后一个超级管理员保护
    if not _check_last_admin(db, username, new_role):
        raise HTTPException(
            status_code=40003,
            detail="不能移除最后一个超级管理员",
        )

    # 执行角色变更
    user.role = new_role

    detail = {"old_role": old_role, "new_role": new_role}
    _record_log(db, current_user["username"], "update_role", username, detail, request)

    # 清除目标用户的缓存
    invalidate_user_cache(username)

    db.commit()

    return {"code": 0, "message": "角色已更新"}


# ========== 禁用/启用 ==========

@router.put("/{username}/status", summary="禁用/启用用户账号",
           dependencies=[Depends(require_permission("user:disable"))])
async def update_user_status(
    username: str,
    req: StatusUpdateRequest,
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """禁用或启用用户账号"""
    # 不能禁用自己
    if username == current_user["username"] and not req.is_active:
        raise HTTPException(status_code=400, detail="不能禁用当前登录的账号")

    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")

    user.is_active = req.is_active

    action = "enable" if req.is_active else "disable"
    detail = {"is_active": req.is_active}
    _record_log(db, current_user["username"], action, username, detail, request)

    # 清除目标用户的缓存
    invalidate_user_cache(username)

    db.commit()

    return {
        "code": 0,
        "message": f"用户已{'启用' if req.is_active else '禁用'}",
    }


# ========== 批量操作 ==========

@router.post("/batch-role", summary="批量修改角色",
             dependencies=[Depends(require_permission("user:batch"))])
async def batch_update_role(
    req: BatchRoleRequest,
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量修改多个用户的角色"""
    success_count = 0
    fail_count = 0
    failed_usernames = []

    for uname in req.usernames:
        user = db.query(User).filter_by(username=uname).first()
        if not user:
            fail_count += 1
            failed_usernames.append(uname)
            continue

        old_role = user.role

        # 最后一个管理员保护
        if not _check_last_admin(db, uname, req.role):
            fail_count += 1
            failed_usernames.append(uname)
            continue

        user.role = req.role
        invalidate_user_cache(uname)
        success_count += 1

    # 记录批量操作日志
    _record_log(
        db, current_user["username"], "batch_update",
        ",".join(req.usernames),
        {"action": "batch_role", "target_role": req.role,
         "success_count": success_count, "fail_count": fail_count},
        request,
    )

    db.commit()

    message = f"批量修改完成：成功 {success_count} 个，失败 {fail_count} 个"
    return BatchResultResponse(
        success_count=success_count,
        fail_count=fail_count,
        failed_usernames=failed_usernames,
        message=message,
    )


@router.post("/batch-status", summary="批量禁用/启用",
             dependencies=[Depends(require_permission("user:batch"))])
async def batch_update_status(
    req: BatchStatusRequest,
    request: Request,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量禁用或启用多个用户账号"""
    success_count = 0
    fail_count = 0
    failed_usernames = []

    for uname in req.usernames:
        # 不能禁用自己
        if uname == current_user["username"] and not req.is_active:
            fail_count += 1
            failed_usernames.append(uname)
            continue

        user = db.query(User).filter_by(username=uname).first()
        if not user:
            fail_count += 1
            failed_usernames.append(uname)
            continue

        user.is_active = req.is_active
        invalidate_user_cache(uname)
        success_count += 1

    action = "batch_enable" if req.is_active else "batch_disable"
    _record_log(
        db, current_user["username"], "batch_update",
        ",".join(req.usernames),
        {"action": action, "is_active": req.is_active,
         "success_count": success_count, "fail_count": fail_count},
        request,
    )

    db.commit()

    status_text = "启用" if req.is_active else "禁用"
    message = f"批量{status_text}完成：成功 {success_count} 个，失败 {fail_count} 个"
    return BatchResultResponse(
        success_count=success_count,
        fail_count=fail_count,
        failed_usernames=failed_usernames,
        message=message,
    )


# ========== 操作日志 ==========

@router.get("/logs", summary="操作日志列表",
            dependencies=[Depends(require_permission("user:list"))])
async def list_operation_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    operator: Optional[str] = Query(None, description="按操作人筛选"),
    action: Optional[str] = Query(None, description="按操作类型筛选"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db),
):
    """获取操作日志列表（支持筛选和分页）"""
    query = db.query(UserOperationLog)

    if operator:
        query = query.filter(UserOperationLog.operator == operator)
    if action:
        query = query.filter(UserOperationLog.action == action)
    if start_time:
        query = query.filter(UserOperationLog.created_at >= start_time)
    if end_time:
        query = query.filter(UserOperationLog.created_at <= end_time)

    total = query.count()

    offset = (page - 1) * size
    logs = query.order_by(desc(UserOperationLog.created_at)).offset(offset).limit(size).all()

    items = [
        OperationLogItem(
            id=log.id,
            operator=log.operator,
            action=log.action,
            target_user=log.target_user,
            detail=log.detail,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return OperationLogListResponse(total=total, items=items)


# ========== 权限 & 角色信息（供前端使用）==========

@router.get("/auth/permissions", summary="当前用户权限列表")
async def get_my_permissions(
    current_user: Dict = Depends(get_current_user),
):
    """获取当前登录用户的所有权限标识"""
    from app.core.permission import _get_role_permissions

    permissions = _get_role_permissions(current_user["role"])
    return {
        "code": 0,
        "data": {
            "username": current_user["username"],
            "role": current_user["role"],
            "permissions": permissions,
        },
    }


@router.get("/meta/roles", summary="角色列表（元数据）")
async def list_roles_meta(
    db: Session = Depends(get_db),
):
    """获取系统中所有角色定义（供前端下拉框使用）"""
    roles = db.query(Role).all()
    return [
        RoleInfo(
            id=r.id,
            name=r.name,
            description=r.description,
            permission_count=db.query(User).filter_by(role=r.id).count(),
        )
        for r in roles
    ]


@router.get("/meta/permissions", summary="权限列表（元数据）")
async def list_permissions_meta(
    category: Optional[str] = Query(None, description="按分类筛选"),
    db: Session = Depends(get_db),
):
    """获取系统中所有权限定义（供管理界面展示）"""
    from app.models import Permission

    query = db.query(Permission)
    if category:
        query = query.filter(Permission.category == category)

    perms = query.order_by(Permission.category, Permission.id).all()
    return [
        PermissionInfo(
            id=p.id,
            name=p.name,
            category=p.category,
            description=p.description,
        )
        for p in perms
    ]
