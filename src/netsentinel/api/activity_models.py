"""Modelos de entrada de la API de actividad autorizada.

Se mantienen separados de las rutas para que cada subrouter comparta las
validaciones sin depender del punto de composición.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ActivitySessionCreate(BaseModel):
    device_id: int = Field(ge=1)
    duration_minutes: int = Field(default=60, ge=5, le=720)
    source_mode: str = Field(min_length=1, max_length=32)


class ActivityEventIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: int = Field(ge=1)
    collector_token: str = Field(min_length=32, max_length=128)
    device_id: int = Field(ge=1)
    event_type: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=32)
    observed_at: str | None = Field(default=None, max_length=64)
    domain: str | None = Field(default=None, max_length=253)
    source_ip: str | None = Field(default=None, max_length=64)
    source_port: int | None = Field(default=None, ge=1, le=65535, strict=True)
    destination_ip: str | None = Field(default=None, max_length=64)
    destination_port: int | None = Field(default=None, ge=1, le=65535, strict=True)
    protocol: str | None = Field(default=None, max_length=16)
    bytes_sent: int | None = Field(default=None, ge=0, le=9_223_372_036_854_775_807, strict=True)
    bytes_received: int | None = Field(default=None, ge=0, le=9_223_372_036_854_775_807, strict=True)
    packets_sent: int | None = Field(default=None, ge=0, le=9_223_372_036_854_775_807, strict=True)
    packets_received: int | None = Field(default=None, ge=0, le=9_223_372_036_854_775_807, strict=True)
    network_interface: str | None = Field(default=None, max_length=64)
    source_event_id: str | None = Field(default=None, max_length=160)
    app_name: str | None = Field(default=None, max_length=100)
    page_url: str | None = Field(default=None, max_length=4096)
    search_engine: str | None = Field(default=None, max_length=40)
    search_terms: str | None = Field(default=None, max_length=500)
    email_provider: str | None = Field(default=None, max_length=60)
    email_from: str | None = Field(default=None, max_length=1500)
    email_to: str | None = Field(default=None, max_length=1500)
    email_subject: str | None = Field(default=None, max_length=200)
    blocked: bool = False


class ActivityCSVImport(BaseModel):
    device_id: int = Field(ge=1)
    csv_data: str = Field(min_length=1, max_length=1_000_000)


class ActivityRetentionUpdate(BaseModel):
    retention_days: int = Field(ge=1, le=90, strict=True)


class ActivityDeleteSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: int | None = Field(default=None, ge=1)
    event_type: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, max_length=32)
    from_date: str | None = Field(default=None, min_length=10, max_length=10)
    to_date: str | None = Field(default=None, min_length=10, max_length=10)


class ActivityDeleteRequest(ActivityDeleteSelection):
    confirmation: str = Field(min_length=1, max_length=40)
