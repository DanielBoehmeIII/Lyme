"""Zero-friction workflow — intent inference, natural-language execution, smart defaults."""
from .inference import IntentInferrer
from .suggestions import ContextualSuggestions
from .execute import NaturalLanguageExecutor

__all__ = ["IntentInferrer", "ContextualSuggestions", "NaturalLanguageExecutor"]
