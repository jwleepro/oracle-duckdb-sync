"""
비밀번호 해싱 및 검증 모듈

bcrypt를 사용하여 안전하게 비밀번호를 해싱하고 검증합니다.
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱

    Args:
        password: 평문 비밀번호

    Returns:
        해시된 비밀번호 (문자열)
    """
    # bcrypt는 bytes를 요구하므로 인코딩
    password_bytes = password.encode('utf-8')

    # 솔트 생성 및 해싱 (기본 rounds=12)
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    # bytes를 문자열로 변환하여 반환
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증

    Args:
        password: 검증할 평문 비밀번호
        hashed_password: 저장된 해시된 비밀번호

    Returns:
        일치 여부 (True/False)
    """
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')

        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        # 잘못된 형식의 해시나 비밀번호
        return False


def is_password_strong(password: str, min_length: int = 8) -> tuple[bool, str]:
    """
    비밀번호 강도 검사

    Args:
        password: 검사할 비밀번호
        min_length: 최소 길이 (기본값: 8)

    Returns:
        (강도 충족 여부, 메시지)
    """
    if len(password) < min_length:
        return False, f"비밀번호는 최소 {min_length}자 이상이어야 합니다."

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        return False, "비밀번호는 대문자, 소문자, 숫자를 각각 하나 이상 포함해야 합니다."

    return True, "강한 비밀번호입니다."
