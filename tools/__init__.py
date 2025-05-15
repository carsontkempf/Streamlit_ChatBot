import pkgutil
import importlib
import inspect
from langchain_core.tools import BaseTool # Import BaseTool for isinstance check

__all__ = []
tool_box = {} # Initialize tool_box as a dictionary


for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if is_pkg:
        continue
    full_module_name = f"{__name__}.{module_name}"
    try:
        module = importlib.import_module(full_module_name)
        for name, obj in inspect.getmembers(module):
            # Check if the object is an instance of BaseTool (which @tool decorated functions become)
            if isinstance(obj, BaseTool):
                tool_lc_name = getattr(obj, 'name', 'N/A')
                if name.endswith("_tool"): # Convention based on Python function/identifier name
                    tool_desc_attr = getattr(obj, 'description', 'N/A')
                    tool_args_schema_attr = getattr(obj, 'args_schema', None)
                    args_schema_str = tool_args_schema_attr.schema() if tool_args_schema_attr else 'None'
                    tool_box[name] = obj # Add to tool_box dictionary
                    __all__.append(name)
    except ImportError as e: # Catch ImportError specifically
        pass
    except Exception as e:
        pass
