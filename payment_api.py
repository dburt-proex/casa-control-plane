"""
payment_api.py — Venmo-style mobile payment backend.

Endpoints
---------
Auth
  POST /auth/register       Register a new user
  POST /auth/login          Login and receive a JWT access token

Users
  GET  /users/me            Current user profile
  GET  /users/search        Search users by username or email

Cards (debit cards – stored masked, never in full)
  POST   /cards             Add a debit card
  GET    /cards             List saved cards (masked)
  DELETE /cards/{card_id}   Remove a card

Balance
  GET  /balance             Get wallet balance
  POST /balance/fund        Fund wallet from a saved card

Transactions
  POST /transactions/send              Send money to another user
  POST /transactions/request           Request money from another user
  GET  /transactions                   Transaction history
  GET  /transactions/{txn_id}          Single transaction detail
  POST /transactions/requests/{req_id}/respond   Accept or decline a money request

Friends
  POST   /friends             Add a friend by username
  GET    /friends             List friends
  DELETE /friends/{username}  Remove a friend
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_secret_key_env = os.getenv("PAYMENT_SECRET_KEY")
if not _secret_key_env:
    import warnings
    _secret_key_env = os.urandom(32).hex()
    warnings.warn(
        "PAYMENT_SECRET_KEY is not set. A random key has been generated which "
        "will invalidate all JWT tokens on every restart. Set PAYMENT_SECRET_KEY "
        "in production.",
        RuntimeWarning,
        stacklevel=2,
    )
SECRET_KEY = _secret_key_env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

DATABASE_URL = os.getenv("PAYMENT_DATABASE_URL", "sqlite:///./payments.db")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    # Balance stored in cents to avoid floating-point issues
    balance_cents = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cards = relationship("PaymentMethodORM", back_populates="user")
    sent_transactions = relationship("TransactionORM", foreign_keys="TransactionORM.sender_id", back_populates="sender")
    received_transactions = relationship("TransactionORM", foreign_keys="TransactionORM.recipient_id", back_populates="recipient")
    sent_requests = relationship("MoneyRequestORM", foreign_keys="MoneyRequestORM.requester_id", back_populates="requester")
    received_requests = relationship("MoneyRequestORM", foreign_keys="MoneyRequestORM.target_id", back_populates="target")


class PaymentMethodORM(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    card_last_four = Column(String(4), nullable=False)
    card_brand = Column(String, nullable=False)
    card_holder_name = Column(String, nullable=False)
    # Deterministic masked token – not the real PAN
    card_token = Column(String, unique=True, nullable=False)
    expiry_month = Column(Integer, nullable=False)
    expiry_year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserORM", back_populates="cards")


class TransactionORM(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(String, ForeignKey("users.id"), nullable=False)
    # Amount stored in cents
    amount_cents = Column(Integer, nullable=False)
    note = Column(String, default="")
    # COMPLETED | FAILED
    txn_status = Column(String, default="COMPLETED", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sender = relationship("UserORM", foreign_keys=[sender_id], back_populates="sent_transactions")
    recipient = relationship("UserORM", foreign_keys=[recipient_id], back_populates="received_transactions")


class MoneyRequestORM(Base):
    __tablename__ = "money_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id = Column(String, ForeignKey("users.id"), nullable=False)
    target_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    note = Column(String, default="")
    # PENDING | ACCEPTED | DECLINED
    req_status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    requester = relationship("UserORM", foreign_keys=[requester_id], back_populates="sent_requests")
    target = relationship("UserORM", foreign_keys=[target_id], back_populates="received_requests")


class FriendshipORM(Base):
    __tablename__ = "friendships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    friend_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _mask_card_token(card_number: str, user_id: str) -> str:
    """Return a one-way HMAC token derived from the card number.

    The real PAN is never stored – only this token and the last four digits.
    """
    return hmac.new(
        SECRET_KEY.encode(),
        f"{card_number}:{user_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _detect_card_brand(card_number: str) -> str:
    """Infer card brand from IIN/BIN prefix."""
    n = card_number.replace(" ", "")
    if len(n) < 4:
        return "Unknown"
    if n.startswith("4"):
        return "Visa"
    if n[:2] in {"51", "52", "53", "54", "55"} or (2221 <= int(n[:4]) <= 2720):
        return "Mastercard"
    if n[:4] in {"6011"} or n[:2] == "65":
        return "Discover"
    if n[:2] in {"34", "37"}:
        return "Amex"
    return "Unknown"


# ---------------------------------------------------------------------------
# DB dependency & current-user helper
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserORM:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.get(UserORM, user_id)
    if not user:
        raise credentials_exception
    return user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    phone: Optional[str]
    created_at: datetime


class AddCardRequest(BaseModel):
    card_number: str = Field(..., min_length=13, max_length=19)
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2024)
    cvv: str = Field(..., min_length=3, max_length=4)
    card_holder_name: str = Field(..., min_length=2)

    @field_validator("card_number")
    @classmethod
    def validate_luhn(cls, v: str) -> str:
        digits = v.replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Card number must contain only digits")
        # Luhn algorithm check
        total = 0
        reverse_digits = digits[::-1]
        for i, ch in enumerate(reverse_digits):
            n = int(ch)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        if total % 10 != 0:
            raise ValueError("Invalid card number (Luhn check failed)")
        return digits


class CardResponse(BaseModel):
    id: str
    card_last_four: str
    card_brand: str
    card_holder_name: str
    expiry_month: int
    expiry_year: int
    is_active: bool
    created_at: datetime


class BalanceResponse(BaseModel):
    balance_dollars: float
    balance_cents: int


class FundWalletRequest(BaseModel):
    card_id: str
    amount: float = Field(..., gt=0, le=10000, description="Amount in dollars")


class SendMoneyRequest(BaseModel):
    recipient_username: str
    amount: float = Field(..., gt=0, le=10000, description="Amount in dollars")
    note: str = Field("", max_length=200)
    # If omitted the sender's wallet balance is used
    card_id: Optional[str] = None


class RequestMoneyRequest(BaseModel):
    target_username: str
    amount: float = Field(..., gt=0, le=10000, description="Amount in dollars")
    note: str = Field("", max_length=200)


class TransactionResponse(BaseModel):
    id: str
    sender_username: str
    recipient_username: str
    amount_dollars: float
    note: str
    txn_status: str
    created_at: datetime


class MoneyRequestResponse(BaseModel):
    id: str
    requester_username: str
    target_username: str
    amount_dollars: float
    note: str
    req_status: str
    created_at: datetime


class RespondToRequestBody(BaseModel):
    accept: bool


class AddFriendRequest(BaseModel):
    username: str


class FriendResponse(BaseModel):
    id: str
    username: str
    email: str


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Payment API",
    description="Venmo-style mobile payment backend",
    version="1.0",
)

_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
# allow_credentials requires explicit origins; cannot be used with wildcard "*"
_allow_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    if db.query(UserORM).filter(UserORM.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(UserORM).filter(UserORM.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = UserORM(
        id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        phone=body.phone,
        hashed_password=hash_password(body.password),
        balance_cents=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return LoginResponse(access_token=create_access_token(user.id))


@app.post("/auth/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login with username (or email) and password. Returns a JWT access token."""
    user = (
        db.query(UserORM)
        .filter(
            (UserORM.username == form_data.username)
            | (UserORM.email == form_data.username)
        )
        .first()
    )
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(access_token=create_access_token(user.id))


# ---------------------------------------------------------------------------
# User routes
# ---------------------------------------------------------------------------

@app.get("/users/me", response_model=UserProfile)
def get_me(current_user: UserORM = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        created_at=current_user.created_at,
    )


@app.get("/users/search")
def search_users(
    q: str,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    """Search for users by username or email (case-insensitive prefix match)."""
    pattern = f"%{q.lower()}%"
    users = (
        db.query(UserORM)
        .filter(
            (UserORM.username.ilike(pattern)) | (UserORM.email.ilike(pattern))
        )
        .filter(UserORM.id != current_user.id)
        .limit(20)
        .all()
    )
    return [
        {"id": u.id, "username": u.username, "email": u.email}
        for u in users
    ]


# ---------------------------------------------------------------------------
# Card routes
# ---------------------------------------------------------------------------

@app.post("/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def add_card(
    body: AddCardRequest,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a debit card. Only the last four digits and a masked token are stored."""
    token = _mask_card_token(body.card_number, current_user.id)

    # Prevent duplicate cards per user
    existing = (
        db.query(PaymentMethodORM)
        .filter(
            PaymentMethodORM.user_id == current_user.id,
            PaymentMethodORM.card_token == token,
            PaymentMethodORM.is_active.is_(True),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Card already added")

    card = PaymentMethodORM(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        card_last_four=body.card_number[-4:],
        card_brand=_detect_card_brand(body.card_number),
        card_holder_name=body.card_holder_name,
        card_token=token,
        expiry_month=body.expiry_month,
        expiry_year=body.expiry_year,
        is_active=True,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    return CardResponse(
        id=card.id,
        card_last_four=card.card_last_four,
        card_brand=card.card_brand,
        card_holder_name=card.card_holder_name,
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        is_active=card.is_active,
        created_at=card.created_at,
    )


@app.get("/cards", response_model=list[CardResponse])
def list_cards(
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the authenticated user's saved cards (masked)."""
    cards = (
        db.query(PaymentMethodORM)
        .filter(
            PaymentMethodORM.user_id == current_user.id,
            PaymentMethodORM.is_active.is_(True),
        )
        .all()
    )
    return [
        CardResponse(
            id=c.id,
            card_last_four=c.card_last_four,
            card_brand=c.card_brand,
            card_holder_name=c.card_holder_name,
            expiry_month=c.expiry_month,
            expiry_year=c.expiry_year,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in cards
    ]


@app.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_card(
    card_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate (soft-delete) a saved card."""
    card = (
        db.query(PaymentMethodORM)
        .filter(
            PaymentMethodORM.id == card_id,
            PaymentMethodORM.user_id == current_user.id,
            PaymentMethodORM.is_active.is_(True),
        )
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Balance routes
# ---------------------------------------------------------------------------

@app.get("/balance", response_model=BalanceResponse)
def get_balance(current_user: UserORM = Depends(get_current_user)):
    """Return the current wallet balance."""
    return BalanceResponse(
        balance_dollars=current_user.balance_cents / 100,
        balance_cents=current_user.balance_cents,
    )


@app.post("/balance/fund", response_model=BalanceResponse)
def fund_wallet(
    body: FundWalletRequest,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fund the wallet by charging the specified saved card."""
    card = (
        db.query(PaymentMethodORM)
        .filter(
            PaymentMethodORM.id == body.card_id,
            PaymentMethodORM.user_id == current_user.id,
            PaymentMethodORM.is_active.is_(True),
        )
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    amount_cents = int(round(body.amount * 100))
    # Re-fetch user inside this session to safely mutate
    user = db.get(UserORM, current_user.id)
    user.balance_cents += amount_cents
    db.commit()
    db.refresh(user)

    return BalanceResponse(
        balance_dollars=user.balance_cents / 100,
        balance_cents=user.balance_cents,
    )


# ---------------------------------------------------------------------------
# Transaction routes
# ---------------------------------------------------------------------------

@app.post("/transactions/send", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def send_money(
    body: SendMoneyRequest,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send money to another user.

    Payment source priority:
    1. If ``card_id`` is provided, the card is charged and funds go directly to
       the recipient (wallet-to-wallet transfer without touching your balance).
    2. Otherwise the sender's wallet balance is debited.
    """
    if body.recipient_username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot send money to yourself")

    recipient = (
        db.query(UserORM)
        .filter(UserORM.username == body.recipient_username)
        .first()
    )
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    amount_cents = int(round(body.amount * 100))

    # Use the ORM instance already loaded by get_current_user; merge into this
    # session to allow mutation.
    sender = db.merge(current_user)

    if body.card_id:
        # Verify card belongs to sender
        card = (
            db.query(PaymentMethodORM)
            .filter(
                PaymentMethodORM.id == body.card_id,
                PaymentMethodORM.user_id == current_user.id,
                PaymentMethodORM.is_active.is_(True),
            )
            .first()
        )
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        # Card charged externally in production; here we just record the transfer
    else:
        if sender.balance_cents < amount_cents:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        sender.balance_cents -= amount_cents

    recipient.balance_cents += amount_cents

    txn = TransactionORM(
        id=str(uuid.uuid4()),
        sender_id=sender.id,
        recipient_id=recipient.id,
        amount_cents=amount_cents,
        note=body.note,
        txn_status="COMPLETED",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return TransactionResponse(
        id=txn.id,
        sender_username=sender.username,
        recipient_username=recipient.username,
        amount_dollars=txn.amount_cents / 100,
        note=txn.note,
        txn_status=txn.txn_status,
        created_at=txn.created_at,
    )


@app.post("/transactions/request", response_model=MoneyRequestResponse, status_code=status.HTTP_201_CREATED)
def request_money(
    body: RequestMoneyRequest,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request money from another user."""
    if body.target_username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot request money from yourself")

    target = (
        db.query(UserORM).filter(UserORM.username == body.target_username).first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    amount_cents = int(round(body.amount * 100))

    req = MoneyRequestORM(
        id=str(uuid.uuid4()),
        requester_id=current_user.id,
        target_id=target.id,
        amount_cents=amount_cents,
        note=body.note,
        req_status="PENDING",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return MoneyRequestResponse(
        id=req.id,
        requester_username=current_user.username,
        target_username=target.username,
        amount_dollars=req.amount_cents / 100,
        note=req.note,
        req_status=req.req_status,
        created_at=req.created_at,
    )


@app.get("/transactions", response_model=list[TransactionResponse])
def list_transactions(
    limit: int = 50,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the last ``limit`` transactions for the authenticated user."""
    txns = (
        db.query(TransactionORM)
        .filter(
            (TransactionORM.sender_id == current_user.id)
            | (TransactionORM.recipient_id == current_user.id)
        )
        .order_by(TransactionORM.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        TransactionResponse(
            id=t.id,
            sender_username=t.sender.username,
            recipient_username=t.recipient.username,
            amount_dollars=t.amount_cents / 100,
            note=t.note,
            txn_status=t.txn_status,
            created_at=t.created_at,
        )
        for t in txns
    ]


@app.get("/transactions/{txn_id}", response_model=TransactionResponse)
def get_transaction(
    txn_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single transaction by ID (must be sender or recipient)."""
    txn = db.get(TransactionORM, txn_id)
    if not txn or (txn.sender_id != current_user.id and txn.recipient_id != current_user.id):
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse(
        id=txn.id,
        sender_username=txn.sender.username,
        recipient_username=txn.recipient.username,
        amount_dollars=txn.amount_cents / 100,
        note=txn.note,
        txn_status=txn.txn_status,
        created_at=txn.created_at,
    )


@app.post("/transactions/requests/{req_id}/respond", response_model=MoneyRequestResponse)
def respond_to_request(
    req_id: str,
    body: RespondToRequestBody,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept or decline an incoming money request.

    When accepted, the target user's wallet is debited and the requester's
    wallet is credited.
    """
    req = db.get(MoneyRequestORM, req_id)
    if not req or req.target_id != current_user.id:
        raise HTTPException(status_code=404, detail="Money request not found")
    if req.req_status != "PENDING":
        raise HTTPException(status_code=400, detail="Request already resolved")

    if body.accept:
        target = db.get(UserORM, current_user.id)
        if target.balance_cents < req.amount_cents:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        target.balance_cents -= req.amount_cents

        requester = db.get(UserORM, req.requester_id)
        requester.balance_cents += req.amount_cents

        # Record as a transaction
        txn = TransactionORM(
            id=str(uuid.uuid4()),
            sender_id=current_user.id,
            recipient_id=req.requester_id,
            amount_cents=req.amount_cents,
            note=req.note,
            txn_status="COMPLETED",
        )
        db.add(txn)
        req.req_status = "ACCEPTED"
    else:
        req.req_status = "DECLINED"

    db.commit()
    db.refresh(req)

    return MoneyRequestResponse(
        id=req.id,
        requester_username=req.requester.username,
        target_username=req.target.username,
        amount_dollars=req.amount_cents / 100,
        note=req.note,
        req_status=req.req_status,
        created_at=req.created_at,
    )


# ---------------------------------------------------------------------------
# Friends routes
# ---------------------------------------------------------------------------

@app.post("/friends", response_model=FriendResponse, status_code=status.HTTP_201_CREATED)
def add_friend(
    body: AddFriendRequest,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a user as a friend by username."""
    if body.username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a friend")

    friend = db.query(UserORM).filter(UserORM.username == body.username).first()
    if not friend:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(FriendshipORM)
        .filter(
            FriendshipORM.user_id == current_user.id,
            FriendshipORM.friend_id == friend.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already friends")

    friendship = FriendshipORM(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        friend_id=friend.id,
    )
    db.add(friendship)
    db.commit()

    return FriendResponse(id=friend.id, username=friend.username, email=friend.email)


@app.get("/friends", response_model=list[FriendResponse])
def list_friends(
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all friends of the authenticated user."""
    friendships = (
        db.query(FriendshipORM)
        .filter(FriendshipORM.user_id == current_user.id)
        .all()
    )
    result = []
    for f in friendships:
        friend = db.get(UserORM, f.friend_id)
        if friend:
            result.append(FriendResponse(id=friend.id, username=friend.username, email=friend.email))
    return result


@app.delete("/friends/{username}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(
    username: str,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a friend by username."""
    friend = db.query(UserORM).filter(UserORM.username == username).first()
    if not friend:
        raise HTTPException(status_code=404, detail="User not found")

    friendship = (
        db.query(FriendshipORM)
        .filter(
            FriendshipORM.user_id == current_user.id,
            FriendshipORM.friend_id == friend.id,
        )
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="Not friends")

    db.delete(friendship)
    db.commit()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/payment/health")
def payment_health():
    return {"status": "Payment API running"}
