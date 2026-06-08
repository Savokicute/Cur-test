# coding=utf-8
"""
认证相关 Pydantic Schema
- 注册请求/响应
- 登录请求/响应
- 个人中心请求/响应
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, EmailStr


# ========== 注册 ==========

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    email: Optional[EmailStr] = Field(None, description="邮箱（选填）")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('两次输入的密码不一致')
        return v


class RegisterResponse(BaseModel):
    """注册响应"""
    success: bool
    message: str
    username: Optional[str] = None


# ========== 登录 ==========

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    user: Optional[dict] = None  # { username, role, role_name, nickname, force_change_password }
    token: Optional[str] = None  # session token


class LogoutResponse(BaseModel):
    """退出响应"""
    success: bool
    message: str


# ========== 当前用户信息 ==========

class UserInfoResponse(BaseModel):
    """当前用户信息"""
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    role_name: str
    is_active: bool
    force_change_password: bool
    login_count: int
    last_login_at: Optional[str] = None
    created_at: Optional[str] = None


class PermissionInfoResponse(BaseModel):
    """权限信息响应"""
    username: str
    role: str
    role_name: str
    permissions: list  # 权限标识列表


# ========== 个人中心 ==========

class ProfileUpdateRequest(BaseModel):
    """个人信息更新请求"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    avatar: Optional[str] = Field(None, max_length=500, description="头像 URL")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v


class LoginHistoryItem(BaseModel):
    """登录历史条目"""
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    failure_reason: Optional[str] = None
    created_at: str


# ========== 管理员重置密码 ==========

class ResetPasswordResponse(BaseModel):
    """重置密码响应"""
    success: bool
    message: str
    temp_password: Optional[str] = None  # 临时密码（仅返回一次）
