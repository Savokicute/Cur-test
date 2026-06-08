# coding=utf-8
"""
SSO 单点登录服务
实现热点平台与 we-mp-rss 的账户统一和 Token 共享
扩展：Token 缓存携带角色信息，供权限中间件使用
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote
import hashlib
import secrets

logger = logging.getLogger(__name__)

# 默认角色：未分配角色的用户默认为普通用户
DEFAULT_ROLE = "user"


class SSOService:
    """SSO 单点登录服务"""
    
    def __init__(self):
        # we-mp-rss 配置
        self.wemp_base_url = "http://127.0.0.1:8001"
        self.wemp_api_base = f"{self.wemp_base_url}/api/v1"
        
        # SSO 密钥（用于签名验证，生产环境应从配置读取）
        self.sso_secret = "trendradar-wemp-sso-secret-2026"
        
        # Token 缓存（生产环境应使用 Redis）
        # 结构: {username: {access_token, token_type, expires_in, wemp_url, login_time,
        #                    expires_at, role, permissions}}  -- RBAC 扩展
        self._token_cache = {}
    
    async def get_wemp_token(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        使用用户名密码登录 we-mp-rss，获取 Token
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            {
                "access_token": "jwt_token",
                "token_type": "bearer",
                "expires_in": 3600,
                "wemp_url": "http://127.0.0.1:8001"
            }
            或 None（登录失败）
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 调用 we-mp-rss 登录接口
                response = await client.post(
                    f"{self.wemp_api_base}/auth/login",
                    data={
                        "username": username,
                        "password": password,
                        "grant_type": "password"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查是否成功
                    if data.get("success") or data.get("access_token"):
                        # 查询用户角色（RBAC）
                        role = self._query_user_role(username)

                        result = {
                            "access_token": data.get("access_token"),
                            "token_type": data.get("token_type", "bearer"),
                            "expires_in": data.get("expires_in", 3600),
                            "wemp_url": self.wemp_base_url,
                            "login_time": datetime.now().isoformat(),
                            "role": role,  # RBAC 扩展：角色标识
                        }
                        
                        # 缓存 Token
                        self._cache_token(username, result)
                        
                        logger.info(f"用户 {username} 成功登录 we-mp-rss")
                        return result
                
                logger.warning(f"we-mp-rss 登录失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"登录 we-mp-rss 失败: {str(e)}", exc_info=True)
            return None
    
    def _cache_token(self, username: str, token_data: Dict):
        """缓存 Token"""
        expires_seconds = token_data.get("expires_in", 3600)
        self._token_cache[username] = {
            **token_data,
            "expires_at": datetime.now() + timedelta(seconds=expires_seconds)
        }
    
    def _get_cached_token(self, username: str) -> Optional[Dict]:
        """获取缓存的 Token"""
        cached = self._token_cache.get(username)
        if not cached:
            return None

        # 检查是否过期
        if datetime.now() > cached.get("expires_at"):
            del self._token_cache[username]
            return None

        return cached

    def _query_user_role(self, username: str) -> str:
        """
        从数据库查询用户角色

        Args:
            username: 用户名（关联 we-mp-rss users.username）

        Returns:
            角色标识: "super_admin" 或 "user"
        """
        try:
            from app.models import get_session_factory, UserRole
            session_factory = get_session_factory()
            db = session_factory()
            try:
                user_role = db.query(UserRole).filter_by(username=username).first()
                if user_role and user_role.role_id:
                    return user_role.role_id
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"查询用户 {username} 角色失败，使用默认角色: {e}")
        return DEFAULT_ROLE

    def get_current_user_role(self, username: str) -> str:
        """
        获取当前用户的角色（优先从缓存读取）

        Args:
            username: 用户名

        Returns:
            角色标识
        """
        # 优先从 Token 缓存获取
        cached = self._get_cached_token(username)
        if cached and "role" in cached:
            return cached["role"]

        # 缓存未命中，查数据库
        role = self._query_user_role(username)

        # 更新缓存中的角色信息（如果缓存存在）
        if cached is not None:
            cached["role"] = role

        return role

    def get_current_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        获取当前登录用户的完整信息（从缓存）

        Returns:
            {
                "username": str,
                "role": str,
                "access_token": str,
                "login_time": str,
                "expires_at": datetime,
            }
            或 None（未登录/已过期）
        """
        cached = self._get_cached_token(username)
        if not cached:
            return None

        return {
            "username": username,
            "role": cached.get("role", DEFAULT_ROLE),
            "access_token": cached.get("access_token"),
            "login_time": cached.get("login_time"),
            "expires_at": cached.get("expires_at").isoformat() if isinstance(cached.get("expires_at"), datetime) else cached.get("expires_at"),
        }
    
    def generate_sso_url(self, username: str, target_path: str = "/") -> str:
        """
        生成 SSO 跳转 URL
        
        通过 URL 参数传递加密的认证信息，
        we-mp-rss 收到后自动完成登录
        
        Args:
            username: 用户名
            target_path: 目标路径（如 /wechat/mp 或 /）
            
        Returns:
            完整的跳转 URL
        """
        # 获取缓存的 Token
        cached = self._get_cached_token(username)
        if not cached:
            return f"{self.wemp_base_url}{target_path}?sso_error=no_cached_token"
        
        access_token = cached["access_token"]
        
        # 生成签名（防止篡改）
        timestamp = int(datetime.now().timestamp())
        sign_str = f"{username}:{access_token}:{timestamp}:{self.sso_secret}"
        signature = hashlib.sha256(sign_str.encode()).hexdigest()
        
        # 构建参数
        params = {
            "sso_user": username,
            "sso_token": access_token,
            "sso_time": str(timestamp),
            "sso_sign": signature,
            "target": target_path
        }
        
        # 编码 URL
        query_string = "&".join([f"{k}={quote(v)}" for k, v in params.items()])
        
        return f"{self.wemp_base_url}?{query_string}"
    
    def verify_sso_params(self, params: Dict[str, str]) -> bool:
        """
        验证 SSO 参数有效性
        
        Args:
            params: URL 参数字典
            
        Returns:
            是否有效
        """
        try:
            sso_user = params.get("sso_user")
            sso_token = params.get("sso_token")
            sso_time = params.get("sso_time")
            sso_sign = params.get("sso_sign")
            
            if not all([sso_user, sso_token, sso_time, sso_sign]):
                return False
            
            # 检查时间戳（5分钟内有效）
            timestamp = int(sso_time)
            now = int(datetime.now().timestamp())
            if abs(now - timestamp) > 300:  # 5分钟超时
                logger.warning(f"SSO 参数已过期: 时间差 {abs(now - timestamp)} 秒")
                return False
            
            # 验证签名
            sign_str = f"{sso_user}:{sso_token}:{sso_time}:{self.sso_secret}"
            expected_sign = hashlib.sha256(sign_str.encode()).hexdigest()
            
            if sso_sign != expected_sign:
                logger.warning("SSO 签名验证失败")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证 SSO 参数失败: {str(e)}", exc_info=True)
            return False
    
    async def auto_login_wemp(self, username: str, password: str) -> Optional[str]:
        """
        一键登录 we-mp-rss 并返回跳转 URL
        
        这是主要的外部接口
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            可直接跳转的 URL，或 None
        """
        # 尝试获取 Token（优先使用缓存）
        cached = self._get_cached_token(username)
        if not cached:
            # 缓存不存在或过期，重新登录
            token_data = await self.get_wemp_token(username, password)
            if not token_data:
                return None
        else:
            token_data = cached
        
        # 生成带 SSO 参数的 URL
        sso_url = self.generate_sso_url(username, "/")
        
        return sso_url


# 全局单例
_sso_service: Optional[SSOService] = None


def get_sso_service() -> SSOService:
    """获取 SSO 服务实例（单例）"""
    global _sso_service
    if _sso_service is None:
        _sso_service = SSOService()
    return _sso_service
