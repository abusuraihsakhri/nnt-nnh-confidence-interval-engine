"""Local demonstration response provider. No external LLM integration is implemented."""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "NNT / NNH Confidence Interval Engine"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            "Demonstration mode: no language model was called and no clinical "
            "or scientific assessment was performed. Use the NNT calculator "
            "for quantitative results."
        )


class LLMFactory:
    @staticmethod
    def create(provider: str = "mock", system_name: str = "NNT / NNH Confidence Interval Engine"):
        if str(provider).lower() not in ("mock", "deterministic", "test"):
            raise ValueError("No external LLM provider is implemented; use provider='mock'")
        return MockLLM(system_name)
