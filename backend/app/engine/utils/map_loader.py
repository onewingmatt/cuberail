import json
import os
from typing import Dict, Any

class MapLoader:
    @staticmethod
    def load_map(map_name: str) -> Dict[str, Any]:
        """
        Loads a map configuration from a JSON file.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        map_path = os.path.join(current_dir, "..", "maps", f"{map_name}.json")

        with open(map_path, "r") as f:
            return json.load(f)
