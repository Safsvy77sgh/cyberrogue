# systems/save_system.py
import json
import os


class SaveSystem:
    def __init__(self, filename: str = "save_data.json"):
        self.filename = filename

    def save(self, data: dict) -> bool:
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def load(self) -> dict:
        if not os.path.exists(self.filename):
            return {}
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def delete(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)