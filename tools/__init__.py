import pkgutil
import importlib
import inspect
import logging
from langchain_core.tools import BaseTool # Import BaseTool for isinstance check

# Use a named logger for this module
logger = logging.getLogger(__name__)

# Ensure basicConfig is called if no handlers are configured for the root logger.
# This is a defensive measure; ideally, logging is configured at the application entry point.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"--- [{__name__}] Root logger basicConfig applied by tools/__init__.py as it was not yet configured. ---")

__all__ = []
tool_box = {} # Initialize tool_box as a dictionary

logger.debug(f"--- [{__name__}] Starting tool discovery in path: {__path__} ---")

for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
    logger.debug(f"--- [{__name__}] Found potential module: {module_name}, is_pkg: {is_pkg} ---")
    if is_pkg:
        logger.debug(f"--- [{__name__}] Skipping package: {module_name} ---")
        continue

    full_module_name = f"{__name__}.{module_name}"
    try:
        logger.debug(f"--- [{__name__}] Attempting to import module: {full_module_name} ---")
        module = importlib.import_module(full_module_name)
        logger.debug(f"--- [{__name__}] Successfully imported module: {full_module_name} ---")

        logger.debug(f"--- [{__name__}] Members of {module_name}: ---")
        for name, obj in inspect.getmembers(module):
            logger.debug(f"--- [{__name__}]   Member: {name}, Type: {type(obj)} ---")

            # Check if the object is an instance of BaseTool (which @tool decorated functions become)
            # and also adheres to our naming convention.
            if isinstance(obj, BaseTool):
                logger.debug(f"--- [{__name__}] Member '{name}' is an instance of BaseTool. Checking naming convention. ---")
                if name.endswith("_tool"): # Ensure we only add actual tools by convention
                    logger.info(f"--- [{__name__}] SUCCESS: Found and adding tool: '{name}' (Type: {type(obj)}) from module '{module_name}' ---")
                    
                    # Log details of the StructuredTool instance
                    tool_name_attr = getattr(obj, 'name', 'N/A')
                    tool_desc_attr = getattr(obj, 'description', 'N/A')
                    tool_args_schema_attr = getattr(obj, 'args_schema', None)
                    args_schema_str = tool_args_schema_attr.schema() if tool_args_schema_attr else 'None'
                    logger.debug(f"--- [{__name__}] Tool '{name}' details: Name='{tool_name_attr}', Desc='{tool_desc_attr}', ArgsSchema={args_schema_str}")

                    tool_box[name] = obj # Add to tool_box dictionary
                    __all__.append(name)
                else:
                    logger.warning(f"--- [{__name__}] Member '{name}' (Type: {type(obj)}) is a BaseTool but does not end with '_tool'. Skipping. ---")
            elif name.endswith("_tool") and callable(obj) and not isinstance(obj, BaseTool):
                logger.warning(f"--- [{__name__}] Member '{name}' in '{module_name}' ends with _tool and is callable, but is NOT a BaseTool instance (Type: {type(obj)}). Check decorator. ---")

    except ImportError as e: # Catch ImportError specifically
        logger.error(f"--- [{__name__}] ImportError when importing module {module_name} (tried as {full_module_name}): {e} ---", exc_info=True)
    except Exception as e:
        logger.error(f"--- [{__name__}] Generic error processing module {module_name} (tried as {full_module_name}): {e} ---", exc_info=True)

logger.debug(f"--- [{__name__}] Tool discovery complete. tool_box: {list(tool_box.keys())} ---")
