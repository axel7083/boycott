import os
import importlib

# Automatically import all .py files in the models directory
models_path = os.path.dirname(__file__)
for file in os.listdir(models_path):
    if file.endswith(".py") and file != "__init__.py":
        module_name = file[:-3]  # Remove ".py" extension
        importlib.import_module(f"{__name__}.{module_name}")