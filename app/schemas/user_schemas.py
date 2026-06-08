# coding=utf-8
"""
用户管理模块 Pydantic Schema 定义

定义所有用户管理 API 的请求/响应数据模型，含参数校验规则。
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator


# ========== 请求 Schema ==========

class UserUpdateRequest(BaseModel):
    """编辑用户信息请求"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    remark: Optional[str] = Field(None, max_length=500, description="管理员备注")

    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("昵称不能为空字符串")
        return v.strip() if v else None


class RoleUpdateRequest(BaseModel):
    """修改角色请求"""
    role: str = Field(..., description="目标角色: super_admin / user")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed = {"super_admin", "user"}
        if v not in allowed:
            raise ValueError(f"无效的角色值，允许: {allowed}")
        return v


class StatusUpdateRequest(BaseModel):
    """修改账号状态请求"""
    is_active: bool = Field(..., description="是否启用")


class BatchRoleRequest(BaseModel):
    """批量修改角色请求"""
    usernames: List[str] = Field(..., min_length=1, description="目标用户名列表")
    role: str = Field(..., description="目标角色: super_admin / user")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed = {"super_admin", "user"}
        if v not in allowed:
            raise ValueError(f"无效的角色值，允许: {allowed}")
        return v

    @field_validator('usernames')
    @classmethod
    def validate_usernames(cls, v):
        # 去重并过滤空值
        cleaned = [u.strip() for u in v if u and u.strip()]
        if not cleaned:
            raise ValueError("用户名列表不能为空")
        return list(set(cleaned))


class BatchStatusRequest(BaseModel):
    """批量修改状态请求"""
    usernames: List[str] = Field(..., min_length=1, description="目标用户名列表")
    is_active: bool = Field(..., description="是否启用")

    @field_validator('usernames')
    @classmethod
    def validate_usernames(cls, v):
        cleaned = [u.strip() for u in v if u and u.strip()]
        if not cleaned:
            raise ValueError("用户名列表不能为空")
        return list(set(cleaned))


# ========== 响应 Schema ==========

class UserInfoResponse(BaseModel):
    """单个用户信息（列表/详情用）"""
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像 URL")
    email: Optional[str] = Field(None, description="邮箱")
    role: str = Field(..., description="角色标识: super_admin / user")
    role_name: str = Field(..., description="角色显示名称")
    is_active: bool = Field(True, description="是否启用")
    created_at: Optional[datetime] = Field(None, description="注册时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    login_count: int = Field(0, description="登录次数")
    remark: Optional[str] = Field(None, description="管理员备注")
    assigned_at: Optional[datetime] = Field(None, description="角色分配时间")

    model_config = {
        "json_encoders": {datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None}
    }


class UserListResponse(BaseModel):
    """用户列表分页响应"""
    total: int = Field(..., description="总数")
    items: List[UserInfoResponse] = Field(default_factory=list, description="用户列表")


class OperationLogItem(BaseModel):
    """操作日志条目"""
    id: int = Field(..., description="日志 ID")
    operator: str = Field(..., description="操作人")
    action: str = Field(..., description="操作类型")
    target_user: str = Field(..., description="目标用户")
    detail: Optional[str] = Field(None, description="变更详情 JSON")
    ip_address: Optional[str] = Field(None, description="操作 IP")
    created_at: Optional[datetime] = Field(None, description="操作时间")

    model_config = {
        "json_encoders": {datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None}
    }


class OperationLogListResponse(BaseModel):
    """操作日志分页响应"""
    total: int = Field(..., description="总数")
    items: List[OperationLogItem] = Field(default_factory=list, description="日志列表")


class BatchResultResponse(BaseModel):
    """批量操作结果"""
    success_count: int = Field(0, description="成功数量")
    fail_count: int = Field(0, description="失败数量")
    failed_usernames: List[str] = Field(default_factory=list, description="失败的用户名列表")
    message: str = Field("", description="结果描述")


class CurrentUserResponse(BaseModel):
    """当前登录用户信息"""
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="角色标识")
    role_name: str = Field(..., description="角色显示名称")
    permissions: List[str] = Field(default_factory=list, description="权限标识列表")


class PermissionInfo(BaseModel):
    """权限信息（权限列表展示）"""
    id: str = Field(..., description="权限标识")
    name: str = Field(..., description="权限名称")
    category: str = Field(..., description="分类")
    description: Optional[str] = Field(None, description="描述")


class RoleInfo(BaseModel):
    """角色信息"""
    id: str = Field(..., description="角色标识")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    permission_count: int = Field(0, description="关联的权限数量")


# ========== 查询参数 Schema ==========

class UserQueryParams(BaseModel):
    """用户列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页条数 (10/20/50)")
    keyword: Optional[str] = Field(None, description="搜索关键词（用户名/昵称）")
    role: Optional[str] = Field(None, description="按角色筛选: super_admin / user")
    is_active: Optional[bool] = Field(None, description="按状态筛选")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向: asc / desc")

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        allowed = {"created_at", "last_login_at", "login_count", "username"}
        if v not in allowed:
            raise ValueError(f"不支持的排序字段，允许: {allowed}")
        return v

    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v):
        if v not in ("asc", "desc"):
            raise ValueError("排序方向只能是 asc 或 desc")
        return v


class LogQueryParams(BaseModel):
    """操作日志查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页条数")
    operator: Optional[str] = Field(None, description="按操作人筛选")
    action: Optional[str] = Field(None, description="按操作类型筛选")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
