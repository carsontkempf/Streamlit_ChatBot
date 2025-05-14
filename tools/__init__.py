import pkgutil
import importlib
import inspect
import logging

# Configure basic logging to capture messages
logging.basicConfig(level=logging.DEBUG)

__all__ = []
tool_box = {} # Initialize tool_box as a dictionary

for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if is_pkg:
        continue

    full_module_name = f"{__name__}.{module_name}"
    try:
        module = importlib.import_module(full_module_name)

        for name, obj in inspect.getmembers(module):
            # pick up any StructuredTool that the @tool decorator created
            if hasattr(obj, "_tool_config"):
                if name.endswith("_tool"): # Ensure we only add actual tools by convention
                    if callable(obj): # Ensure it's a callable function
                        tool_box[name] = obj # Add to tool_box dictionary
                        __all__.append(name)

    except ImportError as e: # Catch ImportError specifically
        logging.error(f"[tools/__init__.py] ImportError when importing module {module_name} (tried as {full_module_name}): {e}", exc_info=True)
    except Exception as e:
        logging.error(f"[tools/__init__.py] Generic error processing module {module_name} (tried as {full_module_name}): {e}", exc_info=True) # Print full traceback for import errors
