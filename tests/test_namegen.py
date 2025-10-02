"""Tests for the namegen module."""

import random
from cjlib.namegen import generate_name, is_valid_name, ADJECTIVES, NOUNS


class TestGenerateName:
    """Tests for generate_name() function."""

    def test_returns_string(self):
        """Test that generate_name returns a string."""
        name = generate_name()
        assert isinstance(name, str)

    def test_correct_format(self):
        """Test that generated name follows cj-{adjective}-{noun} format."""
        name = generate_name()
        assert name.startswith("cj-")
        parts = name.split("-")
        assert len(parts) == 3
        assert parts[0] == "cj"
        assert len(parts[1]) > 0
        assert len(parts[2]) > 0

    def test_uses_valid_words(self):
        """Test that generated names use words from the predefined lists."""
        name = generate_name()
        parts = name.split("-")
        adjective = parts[1]
        noun = parts[2]
        assert adjective in ADJECTIVES
        assert noun in NOUNS

    def test_multiple_calls_can_return_different_names(self):
        """Test that multiple calls can generate different names (probabilistic)."""
        # With 20 adjectives and 20 nouns, we have 400 possible combinations
        # If we generate 10 names, it's very unlikely they're all the same
        names = [generate_name() for _ in range(10)]
        unique_names = set(names)
        # We expect at least some variation (not all identical)
        assert len(unique_names) > 1

    def test_with_fixed_seed(self):
        """Test that generate_name is reproducible with a fixed seed."""
        random.seed(42)
        name1 = generate_name()

        random.seed(42)
        name2 = generate_name()

        assert name1 == name2

    def test_fixed_seed_produces_expected_format(self):
        """Test that even with fixed seed, the format is correct."""
        random.seed(12345)
        name = generate_name()
        assert is_valid_name(name)


class TestIsValidName:
    """Tests for is_valid_name() function."""

    def test_valid_name_returns_true(self):
        """Test that valid names return True."""
        assert is_valid_name("cj-happy-turtle") is True
        assert is_valid_name("cj-clever-falcon") is True
        assert is_valid_name("cj-brave-river") is True

    def test_invalid_prefix_returns_false(self):
        """Test that names without 'cj-' prefix return False."""
        assert is_valid_name("no-prefix") is False
        assert is_valid_name("prefix-happy-turtle") is False

    def test_uppercase_returns_false(self):
        """Test that names with uppercase letters return False."""
        assert is_valid_name("CJ-happy-turtle") is False
        assert is_valid_name("cj-Happy-turtle") is False
        assert is_valid_name("cj-happy-Turtle") is False

    def test_numbers_return_false(self):
        """Test that names with numbers return False."""
        assert is_valid_name("cj-happy-turtle123") is False
        assert is_valid_name("cj-happy123-turtle") is False
        assert is_valid_name("cj-123-turtle") is False

    def test_too_few_parts_returns_false(self):
        """Test that names with fewer than 3 parts return False."""
        assert is_valid_name("cj-only") is False
        assert is_valid_name("cj-") is False

    def test_too_many_parts_returns_false(self):
        """Test that names with more than 3 parts return False."""
        assert is_valid_name("cj-happy-turtle-extra") is False
        assert is_valid_name("cj-a-b-c") is False

    def test_empty_parts_return_false(self):
        """Test that names with empty parts return False."""
        assert is_valid_name("cj--turtle") is False
        assert is_valid_name("cj-happy-") is False

    def test_special_characters_return_false(self):
        """Test that names with special characters return False."""
        assert is_valid_name("cj-happy_turtle") is False
        assert is_valid_name("cj-happy.turtle") is False
        assert is_valid_name("cj-happy turtle") is False

    def test_generated_names_are_valid(self):
        """Test that all generated names pass validation."""
        for _ in range(20):
            name = generate_name()
            assert is_valid_name(name) is True
