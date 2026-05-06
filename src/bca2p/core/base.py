"""Shared base types and serialization helpers for bca2p core models."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from .exceptions import SchemaVersionError


SCHEMA_METADATA_KEY = "_schema"
CORE_SCHEMA_VERSION = "1.0"


class ProtocolModel(BaseModel):
    """Base model with stable serialization helpers for public protocol objects."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    schema_name: ClassVar[str] = "protocol_model"
    schema_version: ClassVar[str] = CORE_SCHEMA_VERSION

    def to_dict(
        self,
        *,
        exclude_none: bool = True,
        stamp_version: bool = True,
        mode: str = "python",
    ) -> dict[str, Any]:
        data = self.model_dump(mode=mode, exclude_none=exclude_none)
        if stamp_version:
            data[SCHEMA_METADATA_KEY] = {
                "name": self.schema_name,
                "version": self.schema_version,
            }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProtocolModel":
        payload = dict(data)
        schema = payload.pop(SCHEMA_METADATA_KEY, None)
        if schema is not None:
            expected_name = cls.schema_name
            expected_version = cls.schema_version
            received_name = schema.get("name")
            received_version = schema.get("version")
            if received_name != expected_name:
                raise SchemaVersionError(
                    f"Schema name mismatch for {cls.__name__}: "
                    f"expected {expected_name!r}, got {received_name!r}",
                )
            if received_version != expected_version:
                raise SchemaVersionError(
                    f"Schema version mismatch for {cls.__name__}: "
                    f"expected {expected_version!r}, got {received_version!r}",
                )
        return cls.model_validate(payload)
