"""
Pacote da análise de carteiras de FIIs por filtragem em grafos.

Módulos:
    data_load   download e cache dos preços/dividendos (única etapa online)
    filters     seleção determinística do universo a partir do cache
    gpmf        matriz de distância -> GPMF (grafo planar filtrado) e MST
    centrality  centralidades (grau, intermediação, proximidade, autovetor)
    portfolio   carteiras central / periférica / híbrida e seus pesos
    rolling     engine de janela rolante (validação fora da amostra)
    costs       giro, custo de transação e imposto de ganho de capital
    metrics     retorno/risco/Sharpe e testes de significância
    pipeline    preparação dos dados comum a todas as etapas
"""
