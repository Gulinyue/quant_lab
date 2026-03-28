"""Stage execution helpers for the pipeline orchestrator."""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from quant_lab.pipeline.run_context import RunContext
from quant_lab.pipeline.validators import validate_stage_output


def run_stage(
    context: RunContext,
    stage_name: str,
    stage_func: Callable[[], None],
    *,
    critical: bool,
) -> bool:
    """Execute one stage with status tracking and validation."""
    logger.info("Stage start: {}", stage_name)
    try:
        stage_func()
        ok, message = validate_stage_output(stage_name)
        if not ok:
            raise FileNotFoundError(message)
        context.stage_statuses[stage_name] = "success"
        logger.info("Stage finish: {}", stage_name)
        return True
    except Exception as exc:  # noqa: BLE001
        context.stage_statuses[stage_name] = "failed"
        text = f"{stage_name} failed: {exc}"
        if critical:
            context.errors.append(text)
            logger.error(text)
        else:
            context.warnings.append(text)
            logger.warning(text)
        return False
