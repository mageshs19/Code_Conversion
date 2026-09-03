from __future__ import annotations

from idms_db2_phase2.domain.models import ConversionInput, ConversionResult
from idms_db2_phase2.orchestration.conversion.conversion_component_factory import (
    ConversionComponentFactory,
)
from idms_db2_phase2.orchestration.conversion.conversion_message_utils import (
    ConversionMessageUtils,
)
from idms_db2_phase2.orchestration.conversion.conversion_pipeline import (
    ConversionPipeline,
)
from idms_db2_phase2.validators.input_validator import InputValidator
from idms_db2_phase2.validators.production_validator import ProductionValidator


class ConversionService(
    ConversionComponentFactory,
    ConversionPipeline,
    ConversionMessageUtils,
):
    """Main orchestration service for IDMS COBOL to DB2 COBOL conversion."""

    def convert(self, conversion_input: ConversionInput) -> ConversionResult:
        validation_messages: list[str] = []

        input_messages = InputValidator().validate(conversion_input)
        validation_messages.extend(input_messages)
        if input_messages:
            return ConversionResult(
                converted_cobol="",
                validation_messages=self._unique_messages(validation_messages),
                operations=[],
            )

        converted_cobol, operations, dclgen_repository = self._run_pipeline(
            conversion_input=conversion_input,
            validation_messages=validation_messages,
        )

        validation_messages.extend(
            ProductionValidator(dclgen_repository=dclgen_repository).validate(
                converted_cobol
            )
        )

        return ConversionResult(
            converted_cobol=converted_cobol,
            validation_messages=self._unique_messages(validation_messages),
            operations=operations,
        )