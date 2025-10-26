import shutil
from pathlib import Path
from typing import Iterable


class ArchiveManager:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def list_archives(self) -> Iterable[Path]:
        return sorted(self.root.glob("*.json"))

    def backup(self, destination: str) -> None:
        destination_path = Path(destination)
        destination_path.mkdir(parents=True, exist_ok=True)
        for file in self.list_archives():
            shutil.copy(file, destination_path / file.name)
