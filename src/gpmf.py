"""
Construção do Grafo Planar Maximamente Filtrado (GPMF).

A partir dos retornos calcula-se a matriz de correlação, dela a matriz de
distância d_ij = sqrt(2 * (1 - rho_ij)) e, por fim, o GPMF: ordenam-se as arestas
por distância crescente (pares mais correlacionados primeiro) e adicionam-se uma
a uma enquanto o grafo continua planar (teste Left-Right de planaridade via
networkx.check_planarity). Um GPMF conexo sobre N vértices tem exatamente
3N - 6 arestas.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

import config


def matriz_correlacao(retornos: pd.DataFrame, metodo: str = config.CORR_METHOD) -> pd.DataFrame:
    return retornos.corr(method=metodo)


def matriz_distancia(retornos: pd.DataFrame, metodo: str = config.CORR_METHOD) -> pd.DataFrame:
    """Distância métrica de Mantegna: d = sqrt(2 (1 - rho))."""
    rho = matriz_correlacao(retornos, metodo)
    d = np.sqrt(2.0 * (1.0 - rho))
    np.fill_diagonal(d.values, 0.0)
    return d


def construir_gpmf(distancia: pd.DataFrame) -> nx.Graph:
    """Adiciona arestas de menor distância preservando a planaridade."""
    nos = list(distancia.columns)
    n = len(nos)

    # lista de arestas candidatas ordenada por distância crescente
    arestas = []
    for a in range(n):
        for b in range(a + 1, n):
            arestas.append((distancia.iloc[a, b], nos[a], nos[b]))
    arestas.sort(key=lambda t: t[0])

    G = nx.Graph()
    G.add_nodes_from(nos)
    limite = config.limite_arestas_planar(n)

    for peso, u, v in arestas:
        if G.number_of_edges() >= limite:
            break
        G.add_edge(u, v, weight=float(peso))
        planar, _ = nx.check_planarity(G)
        if not planar:
            G.remove_edge(u, v)

    return G


def construir_mst(distancia: pd.DataFrame) -> nx.Graph:
    """
    Árvore Geradora Mínima (AGM/MST) sobre o grafo completo ponderado pela
    distância. É o filtro do braço comparativo (Mantegna, 1999): N-1 arestas,
    contra as 3N-6 do GPMF. Usada para comparar GPMF vs MST no mesmo universo.
    """
    nos = list(distancia.columns)
    completo = nx.Graph()
    completo.add_nodes_from(nos)
    n = len(nos)
    for a in range(n):
        for b in range(a + 1, n):
            completo.add_edge(nos[a], nos[b], weight=float(distancia.iloc[a, b]))
    return nx.minimum_spanning_tree(completo, weight="weight")


def resumo_grafo(G: nx.Graph) -> dict:
    """Estatísticas básicas para conferir planaridade e conectividade."""
    n = G.number_of_nodes()
    planar, _ = nx.check_planarity(G)
    return {
        "vertices": n,
        "arestas": G.number_of_edges(),
        "limite_3n_6": config.limite_arestas_planar(n),
        "planar": planar,
        "conexo": nx.is_connected(G) if n else False,
    }
