"""
Tabela estática (dentro da amostra) — base corrigida.

Reconstrói o resultado estático do relatório parcial já com a convenção de
dividendos correta e o universo determinístico. ATENÇÃO: por ser dentro da
amostra (centralidade e avaliação no mesmo período), serve apenas de
comparação; o resultado válido é o fora da amostra (script 03).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import centrality, gpmf, metrics, pipeline, portfolio, riskfree


def main() -> None:
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]
    print(f"universo determinístico: {len(dados['universo'])} FIIs, "
          f"{len(ret_log)} pregões\n")

    # GPMF sobre todo o período
    dist = gpmf.matriz_distancia(ret_log)
    G = gpmf.construir_gpmf(dist)
    resumo = gpmf.resumo_grafo(G)
    print("GPMF:", resumo)

    cent = centrality.calcular_centralidades(G)
    cent.to_csv(config.TABLES_DIR / "centralidade_estatica.csv")

    # carteiras + benchmark (Sharpe sobre o excesso ao CDI diário)
    rf = riskfree.serie_rf_diaria(ret_log.index)
    linhas = []
    for tipo in config.PORTFOLIO_TYPES:
        for tam in config.PORTFOLIO_SIZES:
            pesos = portfolio.selecionar_carteira(cent, tipo, tam)
            ret = portfolio.retorno_carteira(ret_log, pesos)
            est = metrics.estatisticas(ret, rf_diaria=rf)
            linhas.append({"carteira": f"{tipo}_{tam}", **est})

    if dados["benchmark"] is not None:
        linhas.append({"carteira": "benchmark",
                       **metrics.estatisticas(dados["benchmark"], rf_diaria=rf)})

    tabela = pd.DataFrame(linhas).set_index("carteira").round(4)
    print("\n" + tabela.to_string())
    tabela.to_csv(config.TABLES_DIR / "tabela_estatica.csv")
    print(f"\nsalvo em {config.TABLES_DIR / 'tabela_estatica.csv'}")

    _figura_grafo(G, cent)


def _figura_grafo(G, cent) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx

        pos = nx.planar_layout(G)
        c = cent["composite"]
        fig, ax = plt.subplots(figsize=(11, 9))
        nx.draw_networkx_edges(G, pos, alpha=0.3, ax=ax)
        nx.draw_networkx_nodes(G, pos, node_size=c * 3000 + 80,
                               node_color=c, cmap="viridis", ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=7, ax=ax)
        ax.set_title("GPMF dos FIIs (tamanho/cor = escore de centralidade composto)")
        ax.axis("off")
        fig.tight_layout()
        caminho = config.FIGURES_DIR / "gpmf_estatico.png"
        fig.savefig(caminho, dpi=130)
        print(f"figura do grafo em {caminho}")
    except Exception as e:
        print(f"(figura do grafo ignorada: {e})")


if __name__ == "__main__":
    main()
