from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Connector(Base):
    __tablename__ = "connectors"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False, default="gemini")
    model_id = Column(String(100), nullable=False, default="gemini-2.5-flash")
    system_prompt = Column(Text, nullable=False)
    routing_strategy = Column(String(50), nullable=False, default="specific")
    fallback_enabled = Column(Boolean, nullable=False, default=True)
    fallback_provider = Column(String(50), nullable=True)
    fallback_model = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    inputs = relationship("ConnectorInput", back_populates="connector", cascade="all, delete-orphan", lazy="selectin")
    schema_definition = relationship("ConnectorSchema", back_populates="connector", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    logs = relationship("RequestLog", back_populates="connector", cascade="all, delete-orphan", lazy="selectin")

class ConnectorInput(Base):
    __tablename__ = "connector_inputs"

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # text, number, boolean, image, file, json
    is_required = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    default_value = Column(Text, nullable=True)
    validation_rules = Column(Text, nullable=True)  # JSON formatted rules: min, max, allowed_extensions, etc.

    connector = relationship("Connector", back_populates="inputs")

class ConnectorSchema(Base):
    __tablename__ = "connector_schemas"

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("connectors.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    schema_json = Column(Text, nullable=False)  # JSON mapping of expected output fields and types
    description = Column(Text, nullable=True)

    connector = relationship("Connector", back_populates="schema_definition")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)
    hashed_key = Column(String(128), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True, nullable=False)
    connector_id = Column(Integer, ForeignKey("connectors.id", ondelete="SET NULL"), nullable=True, index=True)
    connector_slug = Column(String(100), index=True, nullable=False)
    timestamp = Column(DateTime, default=utcnow, index=True, nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False)  # success, failure, repaired
    response_time_ms = Column(Float, nullable=False, default=0.0)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost = Column(Float, default=0.0, nullable=False)
    routing_strategy = Column(String(50), nullable=True)
    routing_reason = Column(Text, nullable=True)
    fallback_used = Column(Boolean, default=False, nullable=False)
    fallback_provider = Column(String(50), nullable=True)
    fallback_model = Column(String(100), nullable=True)
    repair_attempted = Column(Boolean, default=False, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)

    connector = relationship("Connector", back_populates="logs")

    __table_args__ = (
        Index("idx_logs_timestamp_status", "timestamp", "status"),
        Index("idx_logs_connector_timestamp", "connector_slug", "timestamp"),
    )

class ModelCatalogEntry(Base):
    __tablename__ = "model_catalog"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    model_id = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(150), nullable=False)
    supports_text = Column(Boolean, default=True, nullable=False)
    supports_vision = Column(Boolean, default=False, nullable=False)
    supports_json = Column(Boolean, default=True, nullable=False)
    input_cost_per_m = Column(Float, default=0.0, nullable=False)   # USD per 1M input tokens
    output_cost_per_m = Column(Float, default=0.0, nullable=False)  # USD per 1M output tokens
    quality_score = Column(Float, default=80.0, nullable=False)     # 1-100 configuration estimate
    speed_score = Column(Float, default=80.0, nullable=False)       # 1-100 configuration estimate
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_updated = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
