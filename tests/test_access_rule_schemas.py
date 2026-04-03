"""TC-UNIT-01: full upsert permission payload validation."""

import pytest
from pydantic import ValidationError

from app.schemas.access_rule_schemas import UpsertPermissionsBlock


def test_upsert_permissions_requires_all_flags():
    with pytest.raises(ValidationError):
        UpsertPermissionsBlock.model_validate({"read": True})

    p = UpsertPermissionsBlock.model_validate(
        {
            "read": True,
            "read_all": False,
            "create": False,
            "update": False,
            "update_all": False,
            "delete": False,
            "delete_all": False,
        }
    )
    assert p.read is True


def test_upsert_permissions_rejects_unknown_field():
    with pytest.raises(ValidationError):
        UpsertPermissionsBlock.model_validate(
            {
                "read": True,
                "read_all": False,
                "create": False,
                "update": False,
                "update_all": False,
                "delete": False,
                "delete_all": False,
                "extra": True,
            }
        )
