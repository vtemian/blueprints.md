"""Factory functions for creating configured code generators."""

from typing import Optional

from .generator import CodeGenerator
from .iterative_quality_improver import QualityEnhancedCodeGenerator
from .logging_config import get_logger


def create_quality_enhanced_generator(api_key: Optional[str] = None, 
                                     model: Optional[str] = None,
                                     enable_quality_improvement: bool = True,
                                     max_quality_iterations: int = 2) -> CodeGenerator:
    """Create a code generator with optional iterative quality improvement.
    
    Args:
        api_key: Anthropic API key
        model: Model to use
        enable_quality_improvement: Whether to enable iterative improvement
        max_quality_iterations: Maximum quality improvement iterations
    
    Returns:
        CodeGenerator instance, optionally wrapped with quality improvement
    """
    logger = get_logger('factory')
    logger.debug(f"Creating generator with quality_improvement={enable_quality_improvement}")
    logger.debug(f"API key provided: {'Yes' if api_key else 'No'}")
    logger.debug(f"Model: {model or 'default'}")
    
    # Create a base generator instance using the compatibility wrapper
    logger.debug("Creating base CodeGenerator...")
    base_generator = CodeGenerator(api_key, model)
    logger.debug("Base generator created successfully")
    
    if enable_quality_improvement:
        logger.debug(f"Enabling quality improvement (max {max_quality_iterations} iterations)...")
        try:
            enhanced_generator = QualityEnhancedCodeGenerator(base_generator, max_quality_iterations)
            logger.debug("Quality-enhanced generator created successfully")
            return enhanced_generator
        except Exception as e:
            logger.warning(f"Quality enhancement failed: {e}, using base generator")
            return base_generator
    
    logger.debug("Using base generator without quality improvement")
    return base_generator