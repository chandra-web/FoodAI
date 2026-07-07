import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.skills.recipe import _MODEL_NAME
print("Model Name:", _MODEL_NAME)
