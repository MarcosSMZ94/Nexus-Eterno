from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from nexus.application.engine import Engine
from nexus.presentation.window import run_window

if __name__ == "__main__":
    engine = Engine()
    run_window(engine)   
