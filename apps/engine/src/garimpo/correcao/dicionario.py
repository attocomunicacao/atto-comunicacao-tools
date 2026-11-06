"""Dicionário pessoal de termos. Cada usuário tem o seu, salvo localmente e nunca compartilhado."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def caminho_padrao() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "ATTO Tools" / "dicionario.json"


@dataclass
class Dicionario:
    """termos: forma correta -> variantes erradas já confirmadas pelo usuário."""

    caminho: Path = field(default_factory=caminho_padrao)
    termos: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> "Dicionario":
        caminho = caminho or caminho_padrao()
        termos: dict[str, list[str]] = {}
        if caminho.exists():
            termos = json.loads(caminho.read_text(encoding="utf-8")).get("termos", {})
        return cls(caminho=caminho, termos=termos)

    def salvar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        dados = {"versao": 1, "termos": self.termos}
        self.caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    def adicionar_termo(self, termo: str) -> None:
        self.termos.setdefault(termo, [])

    def aprender(self, original: str, termo: str) -> None:
        """Registra que `original` foi corrigido para `termo` (aprovação do usuário)."""
        variantes = self.termos.setdefault(termo, [])
        if original.lower() not in (v.lower() for v in variantes):
            variantes.append(original)
