"""Parser and validator for raw requirement definitions."""

import json
from typing import Any, Dict, Union
from pydantic import ValidationError

from member_2_compliance_engine.schemas.requirement import StructuredRequirement


class RequirementParser:
    """Parses and validates requirement definitions from dicts, JSON strings, or objects."""

    @staticmethod
    def parse(data: Union[str, Dict[str, Any], StructuredRequirement]) -> StructuredRequirement:
        """Parse input data into a validated StructuredRequirement.

        Args:
            data: JSON string, dictionary, or existing StructuredRequirement

        Returns:
            StructuredRequirement: Strongly typed, validated requirement

        Raises:
            ValueError: If input format or data is invalid.
        """
        if isinstance(data, StructuredRequirement):
            return data

        if isinstance(data, str):
            text = data.strip()
            if text.startswith("{") and text.endswith("}"):
                try:
                    parsed = json.loads(text)
                    return StructuredRequirement.model_validate(parsed)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON string for requirement: {exc}") from exc
                except ValidationError as exc:
                    raise ValueError(f"Requirement schema validation error: {exc}") from exc
            else:
                raise ValueError("String input must be a valid JSON object representation.")

        if isinstance(data, dict):
            try:
                return StructuredRequirement.model_validate(data)
            except ValidationError as exc:
                raise ValueError(f"Requirement schema validation error: {exc}") from exc

        raise TypeError(f"Cannot parse requirement from type {type(data)}.")

