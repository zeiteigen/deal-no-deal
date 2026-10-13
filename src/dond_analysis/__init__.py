"""Deal or No Deal analysis without import-time execution."""

from .data import load_results
from .utility import UtilityModel, load_utility

__all__ = ["load_results", "UtilityModel", "load_utility"]
