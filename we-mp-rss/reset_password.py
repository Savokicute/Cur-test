#!/usr/bin/env python
from core.models.user import User
from core.db import Db, DB
from core.config import cfg
from core.auth import pwd_context
from core.print import print_info, print_error

def reset_admin_password():
    try:
        # 使用环境变量或默认值
        import os
        username = os.getenv("USERNAME", "admin")
        password = os.getenv("PASSWORD", "admin@123")
        
        session = DB.get_session()
        
        # 查找用户
        user = session.query(User).filter(User.username == username).first()
        
        if user:
            # 更新密码
            user.password_hash = pwd_context.hash(password)
            user.is_active = True
            user.role = 'admin'
            session.commit()
            print_info(f"密码重置成功！")
            print_info(f"用户名: {username}")
            print_info(f"密码: {password}")
        else:
            # 创建新用户
            import uuid
            session.add(User(
                id=0,
                username=username,
                password_hash=pwd_context.hash(password),
                role='admin',
                is_active=True,
            ))
            session.commit()
            print_info(f"用户创建成功！")
            print_info(f"用户名: {username}")
            print_info(f"密码: {password}")
        
        session.close()
        
    except Exception as e:
        print_error(f"重置密码错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_admin_password()
