"""
Estilo de figuras em PRETO E BRANCO (tons de cinza) para o artigo.

O template da SBC pede que todas as imagens estejam em preto e branco ou tons de
cinza, com 150-300 dpi para tons de cinza e sem resolução excessiva. Este módulo
centraliza essa escolha: aplica um estilo de cinza, fornece um ciclo de
(cor, traço, marcador) distinguível sem cor, um mapa de cores cinza para o grafo
e um utilitário que salva a figura e a converte para escala de cinza real.
"""
from __future__ import annotations

from pathlib import Path

import config

# Mapa de cores em cinza para o grafo (claro = periférico, escuro = central).
CMAP_PB = "Greys"


def aplicar_estilo_pb() -> None:
    """Configura o matplotlib para saída em tons de cinza, segura para impressão."""
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    plt.style.use("grayscale")
    mpl.rcParams.update({
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "black",
        "axes.labelcolor": "black",
        "text.color": "black",
        "xtick.color": "black",
        "ytick.color": "black",
        "axes.grid": True,
        "grid.color": "0.8",
        "grid.linewidth": 0.5,
        "savefig.dpi": config.FIG_DPI,
    })


# Combinações (cor em cinza, estilo de traço, marcador) que continuam
# distinguíveis quando impressas em preto e branco.
_CICLO_PB = [
    ("0.0", "-", ""),     # preto, sólido
    ("0.45", "--", ""),   # cinza médio, tracejado
    ("0.0", ":", "o"),    # preto, pontilhado, círculo
    ("0.45", "-.", "s"),  # cinza médio, traço-ponto, quadrado
    ("0.0", "--", "^"),   # preto, tracejado, triângulo
    ("0.6", "-", "D"),    # cinza claro, sólido, losango
]


def estilo_linha(i: int) -> dict:
    """Devolve kwargs (color/linestyle/marker) em P&B para a i-ésima série."""
    cor, traco, marca = _CICLO_PB[i % len(_CICLO_PB)]
    kw = {"color": cor, "linestyle": traco, "linewidth": 1.6}
    if marca:
        kw.update({"marker": marca, "markevery": 0.12, "markersize": 4})
    return kw


def salvar_pb(fig, caminho: Path, dpi: int = config.FIG_DPI) -> None:
    """
    Salva a figura e garante escala de cinza REAL (modo 'L'), o que também evita
    resolução/peso excessivos. Se o Pillow não estiver disponível, salva mesmo
    assim (as cores já são cinza por causa do estilo).
    """
    fig.savefig(caminho, dpi=dpi, bbox_inches="tight")
    try:
        from PIL import Image
        with Image.open(caminho) as im:
            im.convert("L").save(caminho, optimize=True)
    except Exception:
        pass
