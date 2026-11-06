"""Estruturas de dados do Garimpo. Todo tempo é guardado em segundos e em quadros."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Palavra:
    texto: str
    ini: float
    fim: float
    quadro_ini: int = 0
    quadro_fim: int = 0


@dataclass
class Frase:
    palavras: list[Palavra]

    @property
    def texto(self) -> str:
        return " ".join(p.texto for p in self.palavras)

    @property
    def ini(self) -> float:
        return self.palavras[0].ini

    @property
    def fim(self) -> float:
        return self.palavras[-1].fim


@dataclass
class Paragrafo:
    frases: list[Frase]

    @property
    def ini(self) -> float:
        return self.frases[0].ini

    @property
    def fim(self) -> float:
        return self.frases[-1].fim

    @property
    def texto(self) -> str:
        return " ".join(f.texto for f in self.frases)


@dataclass
class Tema:
    titulo: str
    paragrafos: list[Paragrafo]
    palavras_chave: list[str] = field(default_factory=list)

    @property
    def ini(self) -> float:
        return self.paragrafos[0].ini

    @property
    def fim(self) -> float:
        return self.paragrafos[-1].fim

    @property
    def frases(self) -> list[Frase]:
        return [f for p in self.paragrafos for f in p.frases]


@dataclass
class Corte:
    tema: str
    frases: list[Frase]
    pontuacao: float

    @property
    def ini(self) -> float:
        return self.frases[0].ini

    @property
    def fim(self) -> float:
        return self.frases[-1].fim

    @property
    def duracao(self) -> float:
        return self.fim - self.ini

    @property
    def texto(self) -> str:
        return " ".join(f.texto for f in self.frases)
