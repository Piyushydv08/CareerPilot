import json
import os
from typing import List, Dict, Optional

class TaxonomyManager:
    """
    Loads and manages the skill taxonomy.
    Maps specific tools/skills to their broader parent categories.
    """
    def __init__(self, taxonomy_path: Optional[str] = None):
        if not taxonomy_path:
            taxonomy_path = os.path.join(os.path.dirname(__file__), "taxonomy.json")
        self.taxonomy = self._load_taxonomy(taxonomy_path)

    def _load_taxonomy(self, path: str) -> Dict[str, List[str]]:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading taxonomy: {e}")
        return {}

    def get_parents(self, skill: str) -> List[str]:
        """
        Returns the parent skills for a given normalized skill.
        Example: 'pytorch' -> ['deep learning', 'machine learning', 'artificial intelligence']
        """
        return self.taxonomy.get(skill.lower(), [])
