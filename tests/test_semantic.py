"""Tests for the Semantic Intelligence Layer."""

import pytest
from signalforge.semantic.config import SemanticConfig
from signalforge.semantic.provider import NoOpProvider, OpenAIProvider
from signalforge.semantic.prompts import (
    SOURCE_ENRICHMENT_SYSTEM,
    SOURCE_ENRICHMENT_USER,
    COMPARISON_ENRICHMENT_SYSTEM,
    CONTRADICTION_ENRICHMENT_SYSTEM,
    CALIBRATION_SYSTEM,
)
from signalforge.semantic.evidence import extract_evidence_chain


class TestSemanticConfig:
    def test_defaults(self):
        config = SemanticConfig()
        assert config.provider in ("openai", "none")
    
    def test_from_env(self):
        config = SemanticConfig.from_env()
        assert isinstance(config, SemanticConfig)


class TestNoOpProvider:
    def test_not_available(self):
        provider = NoOpProvider()
        assert not provider.available()
    
    def test_complete_returns_none_or_empty(self):
        provider = NoOpProvider()
        result = provider.complete(system="You are helpful", user="test prompt")
        # NoOp returns None (no LLM available)
        assert result is None or result == ""


class TestPrompts:
    def test_source_enrichment_prompts_exist(self):
        assert isinstance(SOURCE_ENRICHMENT_SYSTEM, str)
        assert isinstance(SOURCE_ENRICHMENT_USER, str)
    
    def test_comparison_prompt_exists(self):
        assert isinstance(COMPARISON_ENRICHMENT_SYSTEM, str)
    
    def test_contradiction_prompt_exists(self):
        assert isinstance(CONTRADICTION_ENRICHMENT_SYSTEM, str)
    
    def test_calibration_prompt_exists(self):
        assert isinstance(CALIBRATION_SYSTEM, str)


class TestEvidenceChain:
    def test_noop_provider_returns_none(self):
        provider = NoOpProvider()
        # With NoOp provider, extraction returns None (no LLM)
        chain = extract_evidence_chain({"id": "t1"}, provider)
        assert chain is None  # Expected: NoOp can't extract evidence
    
    def test_empty_thesis_with_noop(self):
        provider = NoOpProvider()
        chain = extract_evidence_chain({}, provider)
        # NoOp provider can't extract, returns None
        assert chain is None
