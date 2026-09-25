# Formação de carteiras de FIIs por filtragem em grafos: GPMF, centralidade e a hipótese da periferia

**Resumo.** Avaliamos se a estratégia de "investir na periferia" da rede de
ativos (Pozzi et al., 2013) se aplica a Fundos de Investimento Imobiliário
(FIIs) brasileiros. A partir da matriz de correlação de 51 FIIs (mar/2022 a
nov/2025), construímos o Grafo Planar Maximamente Filtrado (GPMF) e formamos
carteiras Central, Periférica e Híbrida por centralidade. Numa validação rolante
fora da amostra (formação de 360 pregões, manutenção de 22; 550 pregões e 25
rebalanceamentos de teste), as carteiras periféricas superam as centrais em todos
os tamanhos, em linha com Pozzi et al. O GPMF supera a Árvore Geradora Mínima
(AGM) sob metodologia idêntica. Líquido de custos e tributos, porém, o benchmark
passivo (IFIX) é difícil de superar e nenhuma diferença de Sharpe é
estatisticamente significativa, refletindo a janela ainda curta.

## 1. Introdução

Métodos de filtragem em grafos resumem a estrutura de dependência de um mercado
em poucas arestas relevantes. A AGM (Mantegna, 1999) retém N-1 ligações; o GPMF
(Tumminello et al., 2005), por exigir apenas planaridade, retém 3N-6, preservando
mais estrutura (clusters e ciclos curtos). Pozzi et al. (2013) mostraram, para
ações, que ativos periféricos nessas redes tendem a oferecer melhor relação
risco-retorno. Este trabalho testa essa hipótese para FIIs, classe ainda pouco
estudada sob essa ótica e relevante para o investidor pessoa física brasileiro.

## 2. Metodologia

**Dados.** Fechamentos diários ajustados por proventos de 51 FIIs com histórico
completo entre 2022-03-01 e 2025-11-04 (920 pregões). Verificou-se que o ajuste
do provedor já reinveste dividendos, de modo que o retorno é
`R_t = ln(P_t/P_{t-1})` sobre o preço ajustado, sem soma adicional de proventos.

**Grafo.** Correlação de Pearson → distância `d_ij = sqrt(2(1-ρ_ij))` → GPMF por
inserção gulosa de arestas de menor distância preservando a planaridade
(teste Left-Right de planaridade).

**Carteiras.** Centralidades de grau, intermediação, proximidade e autovetor.
Carteiras de 10/15/20 ativos: Central (topo), Periférica (base) e Híbrida, com
pesos iguais.

**Validação fora da amostra.** Janela rolante: forma com 360 pregões, mantém 22,
avança 22; reconstrói o GPMF a cada passo e emenda as séries de manutenção. Isso
remove o viés de look-ahead da avaliação estática.

**Custos.** 0,3% sobre o giro por rebalanceamento e 20% de imposto sobre ganho
de capital realizado (dividendos isentos para PF). Significância pelo teste de
Jobson-Korkie com correção de Memmel (2003).

## 3. Resultados

Com a metodologia corrigida, as carteiras periféricas superam as centrais já
dentro da amostra (Sharpe 1,40 vs 1,16 no tamanho 10) — ao contrário do
resultado preliminar que via vantagem das centrais, afetado pela dupla contagem
de dividendos. Fora da amostra a conclusão se confirma e se fortalece: a
periferia supera o centro em todos os tamanhos (no tamanho 10, Sharpe bruto 0,47
vs 0,03). O GPMF domina a AGM em todas as carteiras. Líquido de custos, contudo,
o benchmark passivo (Sharpe 0,69) supera as carteiras ativas — o giro mensal
corrói o ganho bruto — e o teste de Jobson-Korkie não rejeita igualdade de Sharpe
entre as carteiras (a única diferença próxima da significância é a desvantagem da
Central-10 frente ao benchmark, p ≈ 0,05).

## 4. Conclusão

Para FIIs e no período analisado, a evidência fora da amostra é **favorável à
periferia** em todos os tamanhos e ao GPMF frente à AGM, mas o ganho não
sobrevive aos custos nem atinge significância estatística na janela disponível.
Trabalhos futuros: janelas mais longas, regras de seleção que controlem o giro,
inclusão de mais centralidades e a comparação direta com o braço AGM do parceiro.

## Referências

- Mantegna, R. N. (1999). Hierarchical structure in financial markets. *EPJB*.
- Tumminello, M. et al. (2005). A tool for filtering information in complex
  systems. *PNAS*.
- Pozzi, F., Di Matteo, T., Aste, T. (2013). Spread of risk across financial
  markets. *Scientific Reports*.
- Peralta, G., Zareei, A. (2016). A network approach to portfolio selection.
  *Journal of Empirical Finance*.
- Memmel, C. (2003). Performance hypothesis testing with the Sharpe ratio.
  *Finance Letters*.
