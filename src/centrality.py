"""
Medidas de centralidade sobre o GPMF.

Para os caminhos mínimos (intermediação e proximidade) usa-se a distância como
peso da aresta: quanto menor a distância, mais forte o vínculo. Grau e
autovetor são calculados sobre a topologia. O autovetor é uma exigência da
proposta e mede a importância de um vértice considerando a importância dos
vizinhos.
"""
from __future__ import annotations

import networkx as nx
import pandas as pd

import config


def calcular_centralidades(G: nx.Graph,
                           medidas=config.CENTRALITY_MEASURES) -> pd.DataFrame:
    """Devolve um DataFrame indexado por ticker, uma coluna por medida."""
    colunas = {}

    if "degree" in medidas:
        colunas["degree"] = nx.degree_centrality(G)
    if "betweenness" in medidas:
        colunas["betweenness"] = nx.betweenness_centrality(G, weight="weight")
    if "closeness" in medidas:
        # distance="weight": usa o peso (distância) nos caminhos mínimos
        colunas["closeness"] = nx.closeness_centrality(G, distance="weight")
    if "eigenvector" in medidas:
        try:
            colunas["eigenvector"] = nx.eigenvector_centrality(G, max_iter=1000, tol=1e-8)
        except nx.PowerIterationFailedConvergence:
            colunas["eigenvector"] = nx.eigenvector_centrality_numpy(G)

    df = pd.DataFrame(colunas)

    # Score composto (média das medidas normalizadas, exceto autovetor) — é o
    # ranking usado pelo braço AGM; incluído aqui para comparar os dois métodos
    # sob exatamente a mesma regra de seleção.
    base = [m for m in ("degree", "betweenness", "closeness") if m in df.columns]
    if base:
        norm = (df[base] - df[base].min()) / (df[base].max() - df[base].min() + 1e-9)
        df["composite"] = norm.mean(axis=1)

    return df.reindex(sorted(df.index))
