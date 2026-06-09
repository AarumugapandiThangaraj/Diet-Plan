from exceptions.base import NutriException

class NutritionCalculationException(NutriException):
    """Raised when calculation metrics like BMR, BMR multipliers, or macro distributions fail."""
    pass

class SwapEngineException(NutriException):
    """Raised when swap operations fail or encounter incompatible item selections."""
    pass

class PlanGenerationException(NutriException):
    """Raised when compilation, ranking, or scheduling tasks in the planner fail."""
    pass
