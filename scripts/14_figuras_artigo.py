"""
Figuras do artigo, em inglês e sem título interno (a legenda do artigo faz
esse papel, como pedem as revistas).

  fig1_filters_side_by_side  AGM e GPMF na mesma rede, mesmas posições dos nós;
                             cor e tamanho = escore composto de cada filtro
  fig2_pmfg_labeled          GPMF com todos os fundos; os 8 mais centrais em negrito
  fig3_growth_oos            crescimento de R$ 1 fora da amostra (GPMF, k = 10),
                             líquido de custos e IR, com o IFIX e o CDI

Desenhadas perto do tamanho de impressão (largura útil do template sn-jnl:
31 pc = 13,1 cm) para que as fontes saiam legíveis. Gera PDF vetorial e PNG
(300 dpi) em results/figures/.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import centrality, costs, gpmf, pipeline, riskfree, rolling

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "pdf.fonttype": 42})
CMAP = plt.cm.viridis
N_DESTAQUE = 8


def _salvar(fig, nome):
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(config.FIGURES_DIR / f"{nome}.{ext}", bbox_inches="tight", **kw)
    plt.close(fig)
    print(f"figura: {nome}")


def _layout(G, tentativas=40):
    """Layout de molas escolhido, entre sementes fixas, pelo maior
    espaçamento mínimo entre nós: determinístico e sem sobreposição visível."""
    n = G.number_of_nodes()
    melhor, pos_melhor = -1.0, None
    for semente in range(tentativas):
        pos = nx.spring_layout(G, seed=semente, k=1.8 / np.sqrt(n),
                               iterations=500, weight=None)
        xy = np.array(list(pos.values()))
        xy = (xy - xy.min(0)) / (xy.max(0) - xy.min(0))
        d = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
        np.fill_diagonal(d, np.inf)
        if d.min() > melhor:
            melhor, pos_melhor = d.min(), dict(zip(pos, xy))
    return pos_melhor


def _rotulos(pos, largura=0.105, altura=0.034, acima=0.022, passos=400):
    """Posições dos rótulos (acima de cada nó), afastando na horizontal e na
    vertical os pares cujas caixas se sobrepõem. Coordenadas normalizadas."""
    nomes = list(pos)
    xy = np.array([[pos[n][0], pos[n][1] + acima] for n in nomes], dtype=float)
    for _ in range(passos):
        mexeu = False
        for i in range(len(nomes)):
            for j in range(i + 1, len(nomes)):
                dx, dy = xy[j] - xy[i]
                sx = largura - abs(dx)
                sy = altura - abs(dy)
                if sx > 0 and sy > 0:            # caixas se tocam
                    mexeu = True
                    if sx < sy:                  # separa pelo eixo mais barato
                        d = (sx / 2 + 1e-4) * (1 if dx >= 0 else -1)
                        xy[i, 0] -= d; xy[j, 0] += d
                    else:
                        d = (sy / 2 + 1e-4) * (1 if dy >= 0 else -1)
                        xy[i, 1] -= d; xy[j, 1] += d
        if not mexeu:
            break
    return dict(zip(nomes, map(tuple, xy)))


def _nos(G, pos, score, ax, tam_min, tam_var):
    nos = list(G.nodes())
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#c4c4c4", width=0.6)
    nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=nos,
                           node_color=[CMAP(score[n]) for n in nos],
                           node_size=[tam_min + tam_var * score[n] for n in nos],
                           edgecolors="white", linewidths=0.4)
    ax.set_axis_off()
    ax.margins(0.04)


def _barra(fig, axes, **kw):
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, 1))
    fig.colorbar(sm, ax=axes, label="Composite centrality score", **kw)


def main() -> None:
    dados = pipeline.preparar_dados()
    ret = dados["retornos_log"]

    # ---- redes na janela completa -------------------------------------
    dist = gpmf.matriz_distancia(ret)
    G_p, G_m = gpmf.construir_gpmf(dist), gpmf.construir_mst(dist)
    s_p = centrality.calcular_centralidades(G_p)["composite"]
    s_m = centrality.calcular_centralidades(G_m)["composite"]
    pos = _layout(G_p)

    # Figura 1: os dois filtros, mesmas posições
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))
    for ax, G, s, rot in ((axes[0], G_m, s_m, f"(a) MST, {G_m.number_of_edges()} edges"),
                          (axes[1], G_p, s_p, f"(b) PMFG, {G_p.number_of_edges()} edges")):
        _nos(G, pos, s, ax, tam_min=10, tam_var=230)
        ax.set_title(rot)
    _barra(fig, axes, shrink=0.8, pad=0.02)
    _salvar(fig, "fig1_filters_side_by_side")

    # Figura 2: GPMF com todos os fundos identificados
    destaque = set(s_p.sort_values(ascending=False).index[:N_DESTAQUE])
    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    _nos(G_p, pos, s_p, ax, tam_min=30, tam_var=520)
    for n, (x, y) in _rotulos(pos).items():
        ax.text(x, y, n, ha="center", va="bottom", fontsize=6.3,
                fontweight="bold" if n in destaque else "normal", color="black",
                path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])
    _barra(fig, ax, shrink=0.7, pad=0.01)
    _salvar(fig, "fig2_pmfg_labeled")
    print(f"  em negrito ({len(destaque)}): {', '.join(sorted(destaque))}")

    # ---- Figura 3: fora da amostra, GPMF k = 10, líquido ------------------
    res = rolling.backtest_rolling(ret, retornos_preco=dados["retornos_log_preco"])
    oos, giros, preco = res["retornos"], res["giros"], res["retornos_preco"]
    rf = riskfree.serie_rf_diaria(oos.index)
    bench = dados["benchmark"].reindex(oos.index).dropna()

    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    for rotulo, nome, cor in (("peripheral_10", "Peripheral-10", "#1a9850"),
                              ("hybrid_10", "Hybrid-10", "#4575b4"),
                              ("central_10", "Central-10", "#d73027")):
        liq = costs.aplicar_custos_serie(oos[rotulo], giros[rotulo],
                                         retornos_preco=preco[rotulo])
        ax.plot((1 + liq).cumprod(), label=nome, color=cor, lw=1.2)
        print(f"  {nome}: valor final {(1 + liq).prod():.3f}")
    ax.plot((1 + bench).cumprod(), label="IFIX (XFIX11)", color="black", ls="--", lw=1.0)
    ax.plot((1 + rf).cumprod(), label="CDI", color="#888888", ls=":", lw=1.3)
    ax.axhline(1.0, color="#d9d9d9", lw=0.7, zorder=0)
    ax.set_ylabel("Growth of BRL 1, net of costs and tax")
    ax.legend(frameon=False, loc="upper left", ncol=2)
    ax.grid(alpha=0.25)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    _salvar(fig, "fig3_growth_oos")


if __name__ == "__main__":
    main()
