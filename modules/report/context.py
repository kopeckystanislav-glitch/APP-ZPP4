
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from . import storage
from .utils import ui_key

@dataclass
class ReportCtx:
    rid: str
    data: dict
    oec: str

    def path(self) -> Path:
        return storage.report_path(self.rid)

    def save(self) -> None:
        storage.write_json(self.path(), self.data)

    def key(self, prefix: str) -> str:
        return ui_key(prefix, self.rid)

    def attachments_dir(self) -> Path:
        return storage.attachments_dir(self.rid)
