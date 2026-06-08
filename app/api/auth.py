# coding=utf-8
"""
独立用户体系 - 认证 API
- POST /api/auth/register    注册
- POST /api/auth/login       本地登录
- POST /api/auth/logout      退出登录
- GET  /api/auth/me          当前用户信息
- GET  /api/auth/permissions 当前权限列表
- GET  /api/profile          个人信息
- PUT  /api/profile          修改个人信息
- POST /api/profile/change-password  修改密码
- GET  /api/profile/login-history   登录历史
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.orm import Session
from pydantic import ValidationError as PydanticValidationError

from app.core.database import get_db
from app.models import Base, User, LoginLog, Role, Permission, RolePermission
from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    generate_temp_password, validate_username,
)
from app.schemas.auth_schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse, LogoutResponse,
    UserInfoResponse, PermissionInfoResponse,
    ProfileUpdateRequest, ChangePasswordRequest,
    LoginHistoryItem, ResetPasswordResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

# ========== 常量 ==========

MAX_FAILED_ATTEMPTS = 5       # 最大失败次数
LOCK_DURATION_MINUTES = 15    # 锁定时长（分钟）
SESSION_EXPIRE_DAYS = 7       # 默认会话有效期（天）
REMEMBER_ME_DAYS = 30         # 记住我有效期（天）

# 内存中的 session 存储（生产环境应使用 Redis）
sessions: dict[str, dict] = {}


# ========== 工具函数 ==========

def get_session_token(username: str, remember_me: bool) -> str:
    """生成 session token"""
    import hashlib, secrets, time
    raw = f"{username}:{secrets.token_hex(32)}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def create_session(user: User, remember_me: bool, request: Request) -> str:
    """创建用户会话（单点登录：新会话使旧会话失效）"""
    # 使旧会话失效
    invalidate_old_sessions(user.username)

    token = get_session_token(user.username, remember_me)
    expire_days = REMEMBER_ME_DAYS if remember_me else SESSION_EXPIRE_DAYS

    sessions[token] = {
        "username": user.username,
        "role": user.role,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=expire_days),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
    }

    logger.info(f"用户 {user.username} 创建新会话 (记住我={remember_me})")
    return token


def invalidate_old_sessions(username: str):
    """使指定用户的旧会话失效（单点登录）"""
    to_remove = [t for t, s in sessions.items() if s.get("username") == username]
    for t in to_remove:
        del sessions[t]
    if to_remove:
        logger.info(f"用户 {username} 的 {len(to_remove)} 个旧会话已失效")


def get_current_user_from_token(token: str) -> Optional[User]:
    """从 token 获取当前用户"""
    session = sessions.get(token)
    if not session:
        return None

    # 检查过期
    if session["expires_at"] < datetime.utcnow():
        del sessions[token]
        return None

    db = next(get_db())
    try:
        user = db.query(User).filter(User.username == session["username"]).first()
        return user
    finally:
        db.close()


def require_auth(token: str = Header(..., alias="X-Session-Token")) -> User:
    """依赖注入：要求已登录"""
    user = get_current_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user


def log_login_attempt(db: Session, username: str, success: bool,
                      ip: str = None, ua: str = None, reason: str = None):
    """记录登录尝试"""
    log = LoginLog(
        username=username,
        ip_address=ip,
        user_agent=ua,
        success=success,
        failure_reason=reason,
    )
    db.add(log)
    db.commit()


def get_role_name(role_id: str) -> str:
    """获取角色显示名称"""
    names = {"super_admin": "超级管理员", "user": "普通用户"}
    return names.get(role_id, role_id)


def get_user_permissions(db: Session, role: str) -> list:
    """获取角色对应的权限列表"""
    perms = (
        db.query(Permission.id)
        .join(RolePermission).filter(RolePermission.role_id == role)
        .all()
    )
    return [p[0] for p in perms]


# ========== 注册 ==========

@router.post("/register", response_model=RegisterResponse, summary="用户注册")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    注册新用户
    - 用户名：3-20 位字母/数字/下划线，唯一
    - 密码：8位+，必须含大小写+数字+特殊字符
    - 邮箱：选填
    - 注册成功后自动分配「普通用户」角色
    """
    # 1. 校验用户名格式
    valid, err_msg = validate_username(req.username)
    if not valid:
        raise HTTPException(status_code=400, detail=f"用户名无效: {err_msg}")

    # 2. 检查用户名是否已存在
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="用户名已被注册")

    # 3. 检查邮箱是否已存在（如果提供了邮箱）
    if req.email:
        existing_email = db.query(User).filter(User.email == req.email).first()
        if existing_email:
            raise HTTPException(status_code=409, detail="该邮箱已被使用")

    # 4. 校验密码强度
    valid, err_msg, strength = validate_password_strength(req.password)
    if not valid:
        raise HTTPException(status_code=400, detail=f"密码不符合要求: {err_msg}")

    # 5. 创建用户
    try:
        user = User(
            username=req.username,
            password_hash=hash_password(req.password),
            nickname=req.nickname or req.username,
            email=req.email,
            role="user",  # 默认普通用户
            is_active=True,
        )
        db.add(user)
        db.commit()

        logger.info(f"新用户注册成功: {req.username}")
        return RegisterResponse(
            success=True,
            message="注册成功",
            username=req.username,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"注册失败: {e}")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")


# ========== 登录 ==========

@router.post("/login", response_model=LoginResponse, summary="本地登录")
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    使用本地账号密码登录
    - 单点登录：新登录会使旧会话失效
    - 连续 5 次失败锁定 15 分钟
    - 返回 session token
    """
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    # 1. 查找用户
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        log_login_attempt(db, req.username, False, ip, ua, "用户不存在")
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 2. 检查账号状态
    if not user.is_active:
        log_login_attempt(db, req.username, False, ip, ua, "账号已禁用")
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    # 3. 检查锁定状态
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60 + 1
        log_login_attempt(db, req.username, False, ip, ua, f"账号锁定中")
        raise HTTPException(
            status_code=423,
            detail=f"账号已锁定，请 {remaining} 分钟后重试"
        )

    # 4. 验证密码
    if not verify_password(req.password, user.password_hash):
        # 失败计数 +1
        user.failed_attempts = (user.failed_attempts or 0) + 1

        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
            db.commit()
            log_login_attempt(db, req.username, False, ip, ua, f"连续{MAX_FAILED_ATTEMPTS}次失败，已锁定")
            raise HTTPException(
                status_code=423,
                detail=f"密码错误次数过多，账号已锁定 {LOCK_DURATION_MINUTES} 分钟"
            )

        db.commit()
        log_login_attempt(db, req.username, False, ip, ua, f"密码错误({user.failed_attempts}/{MAX_FAILED_ATTEMPTS})")
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 5. 登录成功
    # 清除失败计数和锁定
    user.failed_attempts = 0
    user.locked_until = None
    user.login_count = (user.login_count or 0) + 1
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = ip
    db.commit()

    # 记录登录日志
    log_login_attempt(db, req.username, True, ip, ua)

    # 创建会话
    token = create_session(user, req.remember_me, request)

    # 构建响应
    user_info = {
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "avatar": user.avatar,
        "role": user.role,
        "role_name": get_role_name(user.role),
        "is_active": user.is_active,
        "force_change_password": user.force_change_password or False,
        "login_count": user.login_count,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }

    logger.info(f"用户 {req.username} 登录成功")
    return LoginResponse(
        success=True,
        message="登录成功",
        user=user_info,
        token=token,
    )


# ========== 退出登录 ==========

@router.post("/logout", response_model=LogoutResponse, summary="退出登录")
async def logout(request: Request):
    """退出当前登录，清除会话"""
    token = request.headers.get("X-Session-Token")
    if token and token in sessions:
        username = sessions[token].get("username", "unknown")
        del sessions[token]
        logger.info(f"用户 {username} 已退出登录")
        return LogoutResponse(success=True, message="已退出登录")

    return LogoutResponse(success=True, message="未找到会话")


# ========== 当前用户信息 ==========

@router.get("/me", response_model=UserInfoResponse, summary="当前用户信息")
async def get_me(current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """获取当前登录用户的详细信息"""
    return UserInfoResponse(
        username=current_user.username,
        nickname=current_user.nickname,
        email=current_user.email,
        avatar=current_user.avatar,
        role=current_user.role,
        role_name=get_role_name(current_user.role),
        is_active=current_user.is_active,
        force_change_password=current_user.force_change_password or False,
        login_count=current_user.login_count or 0,
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@router.get("/permissions", response_model=PermissionInfoResponse, summary="当前权限列表")
async def get_permissions(current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """获取当前用户的角色和权限列表"""
    perms = get_user_permissions(db, current_user.role)
    return PermissionInfoResponse(
        username=current_user.username,
        role=current_user.role,
        role_name=get_role_name(current_user.role),
        permissions=perms,
    )


# ========== 个人中心 ==========

@router.get("/profile", response_model=dict, summary="个人信息")
async def get_profile(current_user: User = Depends(require_auth)):
    """获取个人中心信息"""
    return {
        "code": 0,
        "data": {
            "username": current_user.username,
            "nickname": current_user.nickname,
            "email": current_user.email,
            "avatar": current_user.avatar,
            "role": current_user.role,
            "role_name": get_role_name(current_user.role),
            "is_active": current_user.is_active,
            "force_change_password": current_user.force_change_password or False,
            "login_count": current_user.login_count or 0,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        }
    }


@router.put("/profile", response_model=dict, summary="修改个人信息")
async def update_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """修改昵称、邮箱、头像"""
    updated_fields = []

    if req.nickname is not None:
        current_user.nickname = req.nickname
        updated_fields.append("昵称")

    if req.email is not None:
        # 检查邮箱唯一性
        existing = db.query(User).filter(
            User.email == req.email,
            User.username != current_user.username,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="该邮箱已被其他用户使用")
        current_user.email = req.email
        updated_fields.append("邮箱")

    if req.avatar is not None:
        current_user.avatar = req.avatar
        updated_fields.append("头像")

    if not updated_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    current_user.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"用户 {current_user.username} 更新了: {', '.join(updated_fields)}")
    return {"code": 0, "message": f"{'、'.join(updated_fields)}更新成功"}


@router.post("/profile/change-password", response_model=dict, summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """修改自己的密码"""
    # 1. 验证旧密码
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    # 2. 新密码不能与旧密码相同
    if verify_password(req.new_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    # 3. 校验新密码强度
    valid, err_msg, _ = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=f"新密码不符合要求: {err_msg}")

    # 4. 更新密码
    current_user.password_hash = hash_password(req.new_password)
    current_user.force_change_password = False  # 清除强制改密标记
    current_user.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"用户 {current_user.username} 已修改密码")
    return {"code": 0, "message": "密码修改成功"}


@router.get("/profile/login-history", response_model=dict, summary="登录历史")
async def get_login_history(
    limit: int = 10,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """获取最近 N 条登录记录"""
    logs = (
        db.query(LoginLog)
        .filter(LoginLog.username == current_user.username)
        .order_by(LoginLog.created_at.desc())
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": log.id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent[:100] if log.user_agent else None,
            "success": log.success,
            "failure_reason": log.failure_reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    return {"code": 0, "data": {"total": len(items), "items": items}}


# ========== 管理员重置密码 ==========

@router.put("/users/{username}/reset-password", response_model=ResetPasswordResponse,
             summary="管理员重置密码")
async def reset_user_password(
    username: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """管理员重置指定用户的密码（需要 super_admin 权限）"""
    # 权限检查
    if current_user.role != 'super_admin':
        raise HTTPException(status_code=403, detail="仅超级管理员可执行此操作")

    # 不能重置自己
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="不能重置自己的密码")

    # 查找目标用户
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 生成临时密码
    temp_pwd = generate_temp_password(16)
    target.password_hash = hash_password(temp_pwd)
    target.force_change_password = True  # 强制改密标记
    target.updated_at = datetime.utcnow()
    db.commit()

    logger.warning(f"管理员 {current_user.username} 重置了用户 {username} 的密码")
    return ResetPasswordResponse(
        success=True,
        message=f"已为用户 {username} 重置密码，请将临时密码告知对方",
        temp_password=temp_pwd,
    )


# ========== 初始化种子数据 ==========

def init_seed_users(db: Session):
    """初始化种子用户（首次运行时）"""
    # 检查是否已有用户
    existing = db.query(User).count()
    if existing > 0:
        logger.info(f"已有 {existing} 个用户，跳过种子初始化")
        return

    # 创建默认管理员账号
    admin = User(
        username="admin",
        password_hash=hash_password("Admin@2026!"),
        nickname="系统管理员",
        email="admin@trendradar.dev",
        role="super_admin",
        is_active=True,
        remark="系统初始创建的超级管理员账号",
    )
    db.add(admin)

    # 创建测试普通用户
    test_user = User(
        username="testuser",
        password_hash=hash_password("Test@2026!"),
        nickname="测试用户",
        role="user",
        is_active=True,
        remark="用于功能测试的普通用户",
    )
    db.add(test_user)

    db.commit()
    logger.info("种子用户初始化完成: admin / testuser")


def init_auth_tables():
    """确保认证相关表已创建"""
    from app.core.database import get_engine
    _engine = get_engine()
    Base.metadata.create_all(bind=_engine, tables=[
        User.__table__,
        LoginLog.__table__,
    ])
    logger.info("认证表创建/验证完成")
