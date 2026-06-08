# coding=utf-8
"""
密码安全工具
- bcrypt 哈希与校验
- 密码规则验证
- 临时密码生成
"""

import re
import secrets
import string
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    logger.warning("bcrypt 未安装，将使用 fallback 哈希方式")

# ========== 密码规则 ==========

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{' + str(PASSWORD_MIN_LENGTH) + ',' + str(PASSWORD_MAX_LENGTH) + '}$'
)

def validate_password_strength(password: str) -> Tuple[bool, str, int]:
    """
    验证密码强度
    返回: (是否通过, 错误信息, 强度等级 0-4)
    规则: 8位+，必须包含大小写字母、数字、特殊字符
    """
    if not password:
        return False, "密码不能为空", 0

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"密码至少 {PASSWORD_MIN_LENGTH} 位", 0

    if len(password) > PASSWORD_MAX_LENGTH:
        return False, f"密码最多 {PASSWORD_MAX_LENGTH} 位", 0

    score = 0
    errors = []

    if re.search(r'[a-z]', password):
        score += 1
    else:
        errors.append("小写字母")

    if re.search(r'[A-Z]', password):
        score += 1
    else:
        errors.append("大写字母")

    if re.search(r'\d', password):
        score += 1
    else:
        errors.append("数字")

    if re.search(r'[^a-zA-Z0-9]', password):
        score += 1
    else:
        errors.append("特殊字符(!@#$%^&*等)")

    if score == 4:
        return True, "", 4  # 强
    elif score >= 2:
        return False, f"缺少: {'、'.join(errors)}", score
    else:
        return False, f"密码太弱，缺少: {'、'.join(errors)}", score


def get_password_strength_label(score: int) -> str:
    """获取强度标签"""
    labels = {0: "非常弱", 1: "弱", 2: "中等", 3: "强", 4: "非常强"}
    return labels.get(score, "未知")


def get_password_strength_color(score: int) -> str:
    """获取强度颜色（用于前端）"""
    colors = {0: "#ff4d4f", 1: "#ff7875", 2: "#ffc53d", 3: "#73d13d", 2: "#389e0d"}
    return colors.get(score, "#d9d9d9")


# ========== bcrypt 哈希 ==========

def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    if HAS_BCRYPT:
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode('utf-8')
    else:
        # Fallback: 使用 hashlib + salt（不推荐生产使用）
        import hashlib
        import os
        salt = os.urandom(32).hex()
        h = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"fallback${salt}${h}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    if HAS_BCRYPT:
        try:
            pwd_bytes = plain_password.encode('utf-8')
            hash_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(pwd_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"bcrypt 校验失败: {e}")
            return False
    else:
        # Fallback 校验
        try:
            if hashed_password.startswith('fallback$'):
                parts = hashed_password.split('$')
                if len(parts) == 3:
                    _, salt, expected = parts
                    h = hashlib.sha256((plain_password + salt).encode()).hexdigest()
                    return h == expected
        except Exception as e:
            logger.error(f"Fallback 密码校验失败: {e}")
        return False


# ========== 临时密码生成 ==========

def generate_temp_password(length: int = 16) -> str:
    """
    生成随机临时密码
    确保包含大小写字母、数字、特殊字符
    """
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%&*"

    # 确保每种类型至少一个
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    # 剩余长度随机填充
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # 打乱顺序
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


# ========== 用户名规则 ==========

def validate_username(username: str) -> Tuple[bool, str]:
    """验证用户名格式"""
    if not username:
        return False, "用户名不能为空"
    if len(username) < 3:
        return False, "用户名至少 3 个字符"
    if len(username) > 20:
        return False, "用户名最多 20 个字符"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "用户名只能包含字母、数字和下划线"
    return True, ""
