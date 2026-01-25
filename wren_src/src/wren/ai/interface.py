"""
Wren AI Module

Core AI interface providing intelligent text processing with automatic type inference.
Uses Portkey as the unified gateway to all AI providers.
"""

import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from ..core.context import context
from ..core.types import convert_to_type, extract_type_from_assignment
from ..errors.base import AIProviderError, ConfigurationError, TypeInferenceError
from .llm import llm_router

T = TypeVar("T")
logger = logging.getLogger(__name__)


class AI:
    """Main AI interface for Wren.

    Uses Portkey as the unified gateway to all AI providers.
    """

    def __init__(self):
        self._router = llm_router

    def _complete(self, prompt: str, **kwargs) -> str:
        """Get completion from AI provider via Portkey.

        Args:
            prompt: The prompt to send
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            The completion text
        """
        try:
            return self._router.complete(prompt, **kwargs)
        except (ConfigurationError, AIProviderError):
            raise
        except Exception as e:
            raise AIProviderError.api_error("Portkey", e)

    def __call__(self, prompt: str, text: str | None = None, **kwargs) -> Any:
        """Main AI interface - callable with automatic type inference.

        Args:
            prompt: The instruction or question
            text: Optional text to analyze
            **kwargs: Additional parameters

        Returns:
            Result with type based on context or prompt

        Example:
            if wren.ai("Is this urgent?", email):
                escalate()
        """
        # Build full prompt
        full_prompt = f"{prompt}\n\nText:\n{text}" if text else prompt

        # For boolean questions, be explicit about wanting yes/no
        prompt_lower = prompt.lower()
        if (
            any(
                word in prompt_lower
                for word in [
                    "is",
                    "are",
                    "does",
                    "do",
                    "can",
                    "should",
                    "will",
                    "would",
                    "has",
                    "have",
                ]
            )
            and "?" in prompt
        ):
            full_prompt += "\n\nAnswer with only 'Yes' or 'No'."

        # Add context if available
        if context.all_data:
            context_str = json.dumps(context.all_data, default=str)
            full_prompt = f"Context: {context_str}\n\n{full_prompt}"

        # Get completion
        response = self._complete(full_prompt, **kwargs)

        # Infer return type from prompt
        return self._infer_response_type(prompt, response)

    def _infer_response_type(self, prompt: str, response: str) -> Any:
        """Infer the appropriate type for the response based on prompt."""
        prompt_lower = prompt.lower()

        # Boolean questions - check for yes/no anywhere in response
        if any(
            word in prompt_lower
            for word in [
                "is",
                "are",
                "does",
                "do",
                "can",
                "should",
                "will",
                "would",
                "has",
                "have",
                "?",
            ]
        ):
            response_lower = response.lower().strip()
            # Check exact match first
            if response_lower in ["yes", "true", "1", "correct", "affirmative"]:
                return True
            if response_lower in ["no", "false", "0", "incorrect", "negative"]:
                return False
            # Check if response starts with yes/no
            if response_lower.startswith("yes") or response_lower.startswith("**yes"):
                return True
            if response_lower.startswith("no") or response_lower.startswith("**no"):
                return False

        # Try to parse as JSON
        try:
            return json.loads(response)
        except (json.JSONDecodeError, ValueError):
            pass

        # Return as string by default
        return response.strip()

    def extract(self, text: str, target_type: type[T] | None = None, **kwargs) -> T:
        """Extract structured data from text.

        Args:
            text: Text to extract from
            target_type: Optional type to extract (can be inferred from assignment)
            **kwargs: Additional parameters

        Returns:
            Extracted data of the specified type

        Example:
            booking: BookingRequest = wren.ai.extract(email_text)
        """
        # Try to infer type from assignment if not provided
        if target_type is None:
            target_type = extract_type_from_assignment()

        if target_type is None:
            # No type specified - require explicit type
            # TODO: Consider lazy LLM extraction on attribute access
            raise TypeInferenceError(
                message="No target type specified for extraction",
                expected="Type hint on assignment or explicit target_type parameter",
                fix="Add a type hint: `result: MyModel = wren.ai.extract(text)` "
                "or pass target_type: `wren.ai.extract(text, MyModel)`",
            )

        # Build extraction prompt
        if isinstance(target_type, type) and issubclass(target_type, BaseModel):
            # Pydantic model - get schema
            schema = target_type.model_json_schema()
            prompt = f"""Extract the following information from the text and return as JSON:

Schema:
{json.dumps(schema, indent=2)}

Text:
{text}

Return only valid JSON that matches the schema."""

        elif hasattr(target_type, "__annotations__"):
            # Dataclass or similar
            fields = target_type.__annotations__
            prompt = f"""Extract the following fields from the text and return as JSON:

Fields:
{json.dumps({k: str(v) for k, v in fields.items()}, indent=2)}

Text:
{text}

Return only valid JSON with the specified fields."""

        else:
            # Require structured type (Pydantic model or dataclass)
            raise TypeInferenceError(
                message=f"Cannot extract to type {target_type}",
                expected="Pydantic BaseModel or dataclass with type annotations",
                fix="Define a Pydantic model or dataclass for extraction",
            )

        # Get completion
        response = self._complete(prompt, **kwargs)

        # Parse response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise TypeInferenceError(
                    message="Failed to parse AI response as JSON",
                    expected="Valid JSON response",
                    found=response[:100] + "...",
                    fix="The AI model didn't return valid JSON",
                )

        # Convert to target type
        try:
            return convert_to_type(data, target_type)
        except Exception:
            raise TypeInferenceError.cannot_convert(data, target_type)

    def classify(self, text: str, categories: list[str], **kwargs) -> str:
        """Classify text into one of the given categories.

        Args:
            text: Text to classify
            categories: List of possible categories
            **kwargs: Additional parameters

        Returns:
            The selected category

        Example:
            category = wren.ai.classify(email, ["urgent", "normal", "spam"])
        """
        prompt = f"""Classify the following text into one of these categories: {", ".join(categories)}

Text:
{text}

Return only the category name, nothing else."""

        response = self._complete(prompt, **kwargs)

        # Clean and validate response
        category = response.strip().lower()
        categories_lower = [c.lower() for c in categories]

        if category in categories_lower:
            # Return original case
            idx = categories_lower.index(category)
            return categories[idx]

        # Try fuzzy matching
        for i, cat in enumerate(categories_lower):
            if cat in category or category in cat:
                return categories[i]

        # Default to first category if no match
        logger.warning(f"Could not match '{response}' to categories {categories}")
        return categories[0]

    def sentiment(self, text: str, **kwargs) -> str:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze
            **kwargs: Additional parameters

        Returns:
            Sentiment: "positive", "negative", "neutral"

        Example:
            if wren.ai.sentiment(feedback) == "negative":
                escalate_to_support()
        """
        return self.classify(text, ["positive", "negative", "neutral"], **kwargs)

    def summarize(self, text: str, max_length: int | None = None, **kwargs) -> str:
        """Summarize text.

        Args:
            text: Text to summarize
            max_length: Optional maximum length
            **kwargs: Additional parameters

        Returns:
            Summary of the text

        Example:
            summary = wren.ai.summarize(article, max_length=100)
        """
        prompt = "Summarize the following text"
        if max_length:
            prompt += f" in no more than {max_length} characters"
        prompt += f":\n\n{text}"

        return self._complete(prompt, **kwargs)

    def translate(self, text: str, target_language: str, **kwargs) -> str:
        """Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language
            **kwargs: Additional parameters

        Returns:
            Translated text

        Example:
            spanish = wren.ai.translate(message, "Spanish")
        """
        prompt = f"Translate the following text to {target_language}:\n\n{text}"
        return self._complete(prompt, **kwargs)

    # Simple type extraction methods
    def extract_bool(self, text: str, **kwargs) -> bool:
        """Extract boolean from text.

        Example:
            if wren.ai.extract_bool("Is the sky blue?"):
                print("Yes!")
        """
        response = self(text, **kwargs)
        if isinstance(response, bool):
            return response
        return str(response).lower() in ["yes", "true", "1"]

    def extract_int(self, prompt: str, text: str | None = None, **kwargs) -> int:
        """Extract integer from text.

        Example:
            count = wren.ai.extract_int("How many items?", order_text)
        """
        response = self(prompt, text, **kwargs)
        # Extract first number from response
        numbers = re.findall(r"\d+", str(response))
        if numbers:
            return int(numbers[0])
        raise ValueError(f"No integer found in response: {response}")

    def extract_float(self, prompt: str, text: str | None = None, **kwargs) -> float:
        """Extract float from text.

        Example:
            price = wren.ai.extract_float("What's the total price?", invoice)
        """
        response = self(prompt, text, **kwargs)
        # Extract first float from response
        numbers = re.findall(r"\d+\.?\d*", str(response))
        if numbers:
            return float(numbers[0])
        raise ValueError(f"No float found in response: {response}")

    def extract_str(self, prompt: str, text: str | None = None, **kwargs) -> str:
        """Extract string response.

        Example:
            name = wren.ai.extract_str("What's the customer name?", email)
        """
        response = self(prompt, text, **kwargs)
        return str(response)

    def extract_date(self, prompt: str, text: str | None = None, **kwargs):
        """Extract date from text.

        Example:
            meeting_date = wren.ai.extract_date("When is the meeting?", email)
        """
        from ..core.types import parse_date

        response = self(prompt, text, **kwargs)
        return parse_date(response)


# Global AI instance
ai = AI()
