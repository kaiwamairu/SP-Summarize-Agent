from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent.parent
_SETTINGS_FILE = _ROOT / "settings.yaml"


class Settings:
    def __init__(self):
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.vault_path = Path(data["vault_path"])
        self.default_platform: str = data["default_platform"]
        self.platforms: dict = data["platforms"]
        self.synthesis_flags: dict = data["synthesis_flags"]
        self.vault_structure: dict = data["vault_structure"]
        self.prompts_dir = _ROOT / "prompts"

    def vault_folder(self, source_type: str) -> Path:
        key = {"paper": "papers", "video": "videos", "repo": "repos"}.get(source_type, "inbox")
        return self.vault_path / self.vault_structure.get(key, "90-Inbox")


settings = Settings()
