"""
ULTRON SQLAlchemy 2.0 ORM Models
Maps directly to the 11 relational tables in MySQL 8+ (database/schema.sql).
"""
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    role = Column(String(64), nullable=False, default="ADMIN")
    created_at = Column(DateTime, default=datetime.utcnow)


class ObjectiveModel(Base):
    __tablename__ = "objectives"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(64), nullable=False, default="PLANNING")
    budget_limit = Column(Float, nullable=True)
    currency = Column(String(16), nullable=False, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConstraintModel(Base):
    __tablename__ = "constraints"

    id = Column(String(64), primary_key=True)
    objective_id = Column(
        String(64), ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    constraint_type = Column(String(64), nullable=False)
    constraint_value = Column(String(512), nullable=False)
    is_hard_constraint = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MissionModel(Base):
    __tablename__ = "missions"

    id = Column(String(64), primary_key=True)
    objective_id = Column(
        String(64), ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String(64), nullable=False, default="RUNNING")
    current_stage = Column(String(255), nullable=False)
    agent_assigned = Column(String(128), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ProductSnapshotModel(Base):
    __tablename__ = "product_snapshots"

    id = Column(String(64), primary_key=True)
    external_id = Column(String(128), nullable=False)
    source = Column(String(64), nullable=False, default="Channel3")
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False, default="USD")
    vendor = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False)
    image_url = Column(String(1024), nullable=False)
    product_url = Column(String(1024), nullable=True)
    rating = Column(Float, nullable=False, default=4.5)
    in_stock = Column(Boolean, nullable=False, default=True)
    specs_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchasePlanModel(Base):
    __tablename__ = "plans"

    id = Column(String(64), primary_key=True)
    objective_id = Column(
        String(64), ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(64), nullable=False, default="SUBMITTED")
    total_amount = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False, default="USD")
    notes = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanItemModel(Base):
    __tablename__ = "plan_items"

    id = Column(String(64), primary_key=True)
    plan_id = Column(String(64), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    product_snapshot_id = Column(String(64), nullable=False)
    title = Column(String(512), nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)


class ApprovalModel(Base):
    __tablename__ = "approvals"

    id = Column(String(64), primary_key=True)
    plan_id = Column(String(64), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    plan_version = Column(Integer, nullable=False, default=1)
    approver_name = Column(String(255), nullable=False)
    approver_role = Column(String(128), nullable=False)
    status = Column(String(64), nullable=False, default="PENDING")
    approved_amount = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False, default="USD")
    comments = Column(Text, nullable=False)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PaymentOrderModel(Base):
    __tablename__ = "payment_orders"

    id = Column(String(64), primary_key=True)
    plan_id = Column(String(64), nullable=False)
    approval_id = Column(String(64), nullable=False)
    paypal_order_id = Column(String(128), nullable=False)
    capture_id = Column(String(128), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False, default="USD")
    environment = Column(String(32), nullable=False, default="sandbox")
    status = Column(String(64), nullable=False, default="CREATED")
    checkout_url = Column(String(1024), nullable=True)
    payment_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIRunModel(Base):
    __tablename__ = "ai_runs"

    id = Column(String(64), primary_key=True)
    objective_id = Column(String(64), nullable=True)
    mission_id = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    agent_role = Column(String(128), nullable=False)
    prompt_summary = Column(Text, nullable=False)
    response_summary = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    status = Column(String(64), nullable=False, default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow)


class ObjectiveEventModel(Base):
    __tablename__ = "objective_events"

    id = Column(String(64), primary_key=True)
    objective_id = Column(String(64), nullable=False)
    event_type = Column(String(128), nullable=False)
    actor = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
