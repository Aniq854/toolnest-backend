"""
Sab providers ka common interface. Naya provider add karna ho to
sirf ek nayi file banayein jo LLMProvider ko inherit kare.
"""
from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    pass


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    async def complete(self, system: str, user: str, temperature: float = 0.9) -> str:
        """System + user prompt bhejo, plain text wapas lo."""
        raise NotImplementedError
