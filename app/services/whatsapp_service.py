from urllib.parse import urlencode
from app.services.customer_service import normalize_phone

def build_link(number: str, message: str) -> str:
    digits = normalize_phone(number).lstrip("+")
    return f"https://wa.me/{digits}?{urlencode({'text': message})}"
