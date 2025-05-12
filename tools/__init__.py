import pkgutil, importlib, inspect

__all__ = []
tools = []

for _, module_name, _ in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")
    for name, obj in inspect.getmembers(module):
        # pick up any StructuredTool that the @tool decorator created
        if hasattr(obj, "_tool_config"):
            globals()[name] = obj
            __all__.append(name)
            tools.append(obj)
