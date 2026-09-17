import pytest
from src.application.services.hardware_budget_advisor_service import HardwareBudgetAdvisorService


def test_hardware_detection_structure():
    service = HardwareBudgetAdvisorService()
    hw = service.detect_hardware()
    assert "has_gpu" in hw
    assert "device_name" in hw
    assert "total_vram_gb" in hw
    assert "vram_tier" in hw
    assert hw["vram_tier"] in ["ULTRA", "MID", "ENTRY", "CPU", "NONE"]


def test_budget_advice_ollama_profile():
    service = HardwareBudgetAdvisorService()
    advice = service.get_runtime_advice(provider_override="ollama")
    assert advice["active_provider"] == "ollama"
    assert "optimal_parameters" in advice
    assert "max_tokens" in advice["optimal_parameters"]
    assert "guidance_for_agent" in advice
    assert advice["financial_cost"] == "R$ 0,00" or "Totalmente Local" in advice["financial_cost"]


def test_budget_advice_gemini_profile():
    service = HardwareBudgetAdvisorService()
    advice = service.get_runtime_advice(provider_override="gemini")
    assert advice["active_provider"] == "gemini"
    assert "optimal_parameters" in advice
    assert advice["optimal_parameters"]["use_brain"] is True
