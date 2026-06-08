# coding=utf-8
"""
SSO 单点登录 API 接口
提供热点平台与 we-mp-rss 的统一认证
增强：登录成功后返回用户角色信息
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Body, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["SSO单点登录"])


class SSOLoginRequest(BaseModel):
    """SSO 登录请求"""
    username: str
    password: str
    target_path: str = "/"  # 目标路径，默认跳转到 we-mp-rss 首页


class SSORedirectResponse(BaseModel):
    """SSO 跳转响应"""
    success: bool
    redirect_url: Optional[str] = None
    message: str
    wemp_status: str  # "online" | "offline"
    auto_login_url: Optional[str] = None  # 前端可直接使用的 URL
    user_info: Optional[dict] = None  # 新增：用户角色信息 { username, role, role_name }


@router.post("/login", summary="SSO登录并获取跳转URL")
async def sso_login(req: SSOLoginRequest):
    """
    使用热点平台的账户信息登录 we-mp-rss，返回跳转URL
    
    ## 使用场景
    用户在热点平台点击"进入微信管理"，前端调用此接口，
    获取带认证信息的跳转URL，直接打开 we-mp-rss 完整界面
    
    ## 请求示例
    ```json
    {
        "username": "admin",
        "password": "123456",
        "target_path": "/"
    }
    ```
    
    ## 响应示例（成功）
    ```json
    {
        "success": true,
        "redirect_url": "http://127.0.0.1:8001/?sso_user=admin&sso_token=xxx&...",
        "message": "登录成功，正在跳转...",
        "wemp_status": "online",
        "auto_login_url": "http://127.0.0.1:8001/?sso_user=admin&..."
    }
    ```
    
    ## 响应示例（we-mp-rss 未启动）
    ```json
    {
        "success": false,
        "redirect_url": null,
        "message": "we-mp-rss 服务未启动，请先启动该服务",
        "wemp_status": "offline",
        "auto_login_url": null
    }
    ```
    """
    try:
        from app.services.sso_service import get_sso_service
        
        sso = get_sso_service()
        
        # 检查 we-mp-rss 是否在线
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{sso.wemp_base_url}/")
                wemp_status = "online"
        except Exception:
            return SSORedirectResponse(
                success=False,
                message="❌ we-mp-rss 服务未启动\n\n请按以下步骤启动：\n1. cd we-mp-rss\n2. python main.py -job True\n3. 刷新本页面",
                wemp_status="offline"
            )
        
        # 执行 SSO 登录
        redirect_url = await sso.auto_login_wemp(
            username=req.username,
            password=req.password
        )
        
        if redirect_url:
            # 如果指定了目标路径，更新 URL
            if req.target_path and req.target_path != "/":
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                parsed = urlparse(redirect_url)
                params = parse_qs(parsed.query)
                params["target"] = [req.target_path]
                new_query = urlencode(params, doseq=True)
                redirect_url = urlunparse(parsed._replace(query=new_query))
            
            logger.info(f"SSO 登录成功: {req.username} -> {redirect_url[:50]}...")

            # 获取用户角色信息
            user_role = None
            try:
                from app.services.sso_service import get_sso_service
                sso_svc = get_sso_service()
                user_role = sso_svc.get_current_user_role(req.username)
            except Exception as e:
                logger.warning(f"获取用户角色失败: {e}")

            role_name = "超级管理员" if user_role == "super_admin" else "普通用户"

            return SSORedirectResponse(
                success=True,
                redirect_url=redirect_url,
                message=f"✅ 登录成功！正在跳转到微信公众号管理...",
                wemp_status=wemp_status,
                auto_login_url=redirect_url,
                # 新增：用户角色信息
                user_info={
                    "username": req.username,
                    "role": user_role or "user",
                    "role_name": role_name,
                },
            )
        else:
            return SSORedirectResponse(
                success=False,
                message="⚠️ 登录失败：用户名或密码错误\n\n可能原因：\n1. we-mp-rss 中不存在此用户\n2. 密码不正确\n\n解决方案：\n• 确保两个系统使用相同的账户\n• 或在 we-mp-rss 中注册相同用户名",
                wemp_status=wemp_status
            )
            
    except Exception as e:
        logger.error(f"SSO 登录失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"服务器错误: {str(e)}"
            }
        )


@router.get("/status", summary="检查 SSO 服务状态")
async def sso_status():
    """
    检查 SSO 服务和 we-mp-rss 的状态
    
    返回：
    - sso_ready: SSO服务是否就绪
    - wemp_online: we-mp-rss是否在线
    - cached_users: 已缓存的用户数
    """
    from app.services.sso_service import get_sso_service
    
    sso = get_sso_service()
    
    # 检查 we-mp-rss 是否在线
    wemp_online = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(sso.wemp_base_url)
            wemp_online = True
    except Exception:
        pass
    
    return {
        "sso_ready": True,
        "wemp_online": wemp_online,
        "wemp_url": sso.wemp_base_url,
        "cached_users": len(sso._token_cache),
        "message": "✅ SSO 服务正常" if wemp_online else "⚠️ we-mp-rss 未启动"
    }


@router.get("/generate-url", summary="生成 SSO 跳转链接（已登录用户）")
async def generate_sso_url(
    username: str = Query(..., description="用户名"),
    target: str = Query("/", description="目标路径")
):
    """
    为已缓存 Token 的用户生成快速跳转链接
    
    如果用户之前已经通过 SSO 登录过，可以直接生成跳转链接，
    无需再次提供密码
    """
    from app.services.sso_service import get_sso_service
    
    sso = get_sso_service()
    
    # 检查是否有缓存的 Token
    cached = sso._get_cached_token(username)
    if not cached:
        return {
            "success": False,
            "message": "未找到缓存的登录信息，请先使用 /sso/login 接口登录"
        }
    
    # 生成 URL
    url = sso.generate_sso_url(username, target)
    
    return {
        "success": True,
        "url": url,
        "expires_at": cached["expires_at"].isoformat(),
        "message": "✅ 跳转链接已生成"
    }


@router.post("/logout", summary="SSO 登出")
async def sso_logout(
    username: str = Body(..., embed=True, description="用户名")
):
    """
    清除用户的 SSO 缓存 Token
    
    调用后，用户需要重新登录才能访问 we-mp-rss
    """
    from app.services.sso_service import get_sso_service
    
    sso = get_sso_service()
    
    if username in sso._token_cache:
        del sso._token_cache[username]
        
    return {
        "success": True,
        "message": f"✅ 用户 {username} 的 SSO 会话已清除"
    }
