import re
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.customer import Customer

def normalize_phone(value: str) -> str:
    raw = value.strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return "+" + digits
    raise ValueError("Enter a valid phone number with country code, or a 10-digit Indian number.")

def find_or_create(db: Session, name: str, phone: str, whatsapp_number: str, email: str | None = None) -> Customer:
    normalized = normalize_phone(phone)
    whatsapp = normalize_phone(whatsapp_number)
    customer = db.scalar(select(Customer).where(Customer.phone == normalized))
    if customer:
        if not customer.email and email:
            customer.email = email
        return customer
    customer = Customer(name=name.strip(), phone=normalized, whatsapp_number=whatsapp, email=email)
    try:
        with db.begin_nested():
            db.add(customer)
            db.flush()
    except IntegrityError:
        customer = db.scalar(select(Customer).where(Customer.phone == normalized))
        if customer is None:
            raise
        if not customer.email and email:
            customer.email = email
    return customer
