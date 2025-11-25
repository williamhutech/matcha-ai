"""Tests for data schema and models."""

import pytest
from app.schema.models_v11 import Profile, ProfileState


def test_profile_creation():
    """Test creating a profile instance."""
    profile = Profile(
        user_id="user_123",
        full_name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        location="San Francisco, CA",
    )

    assert profile.user_id == "user_123"
    assert profile.full_name == "John Doe"
    assert profile.email == "john@example.com"


def test_profile_state_is_complete():
    """Test profile completeness check."""
    # Incomplete profile (missing fields)
    incomplete_state = ProfileState(
        user_id="user_123",
        profile=Profile(user_id="user_123", full_name="John Doe"),
    )

    assert incomplete_state.is_complete() is False

    # Complete profile
    complete_state = ProfileState(
        user_id="user_123",
        profile=Profile(
            user_id="user_123",
            full_name="John Doe",
            email="john@example.com",
            phone="+1234567890",
        ),
    )

    assert complete_state.is_complete() is True


def test_profile_state_to_dict():
    """Test converting profile state to dictionary."""
    state = ProfileState(
        user_id="user_123",
        profile=Profile(
            user_id="user_123",
            full_name="John Doe",
            email="john@example.com",
        ),
    )

    result = state.to_dict()

    assert isinstance(result, dict)
    assert result["user_id"] == "user_123"
    assert "profile" in result


# TODO: Add tests for schema validation once data_schema_v11.yaml is defined
