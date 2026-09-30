# GPMF para FIIs

Formação de carteiras de Fundos de Investimento Imobiliário (FIIs) por filtragem
em grafos. A partir da correlação dos retornos, constroem-se o Grafo Planar
Maximamente Filtrado (GPMF) e a Árvore Geradora Mínima (AGM), e selecionam-se
carteiras Central, Periférica e Híbrida por centralidade, avaliadas fora da
amostra, com custos e imposto, contra o IFIX e contra benchmarks de Markowitz.
Pergunta central: a recomendação de Pozzi et al. (2013) de "investir na
periferia" vale para FIIs?

**O guia completo, com o funcionamento de cada etapa, o mapa do código e os
resultados, está em [GUIA.md](GUIA.md).**

## Pipeline

retornos dos FIIs → correlação → distância `d = √(2(1−ρ))` → **GPMF** (3N−6
arestas) ou **AGM** (N−1 arestas) → centralidade composta → carteiras → janela
rolante 360/22 fora da amostra → custo de 0,3% e IR de 20% sobre o ganho de
preço realizado → Sharpe sobre o CDI e testes de significância.

## Como rodar

Requer Python 3.12. Os dados já estão em `data/raw/`; tudo roda offline.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# resultados do relatório
.venv/bin/python scripts/02_estatica.py
.venv/bin/python scripts/03_rolling.py
.venv/bin/python scripts/04_custos.py
.venv/bin/python scripts/07_comparacao_completa.py
.venv/bin/python scripts/09_subperiodos.py

# resultados do artigo (depois dos anteriores)
.venv/bin/python scripts/05_comparacao.py
.venv/bin/python scripts/11_benchmarks_classicos.py
.venv/bin/python scripts/12_significancia_benchmarks.py
.venv/bin/python scripts/13_auditoria.py
.venv/bin/python scripts/14_figuras_artigo.py
```

## Estrutura

```
config.py            todos os parâmetros
src/                 data_load filters gpmf centrality portfolio rolling costs
                     metrics riskfree pipeline benchmarks
scripts/             pontos de entrada numerados (ver GUIA.md, seção 4)
data/raw/            dados congelados (preços, dividendos, benchmark, CDI)
results/tables/      tabelas geradas
results/figures/     figuras geradas
notebooks/           driver para o Colab
docs/                rascunho do artigo e versões antigas do relatório
```

## Principais resultados

Universo de 51 FIIs, mar/2022–nov/2025; 550 pregões fora da amostra e 25
rebalanceamentos. Todos os Sharpes são negativos porque o CDI (≈ 12% a.a.)
superou todas as carteiras; menos negativo é melhor.

- **No GPMF, a periferia supera o centro nos três tamanhos** (10, 15 e 20),
  bruto e líquido, e nas duas metades do período. A diferença não é
  estatisticamente significativa (p = 0,34).
- **Na AGM, o padrão falha em k = 10**: o giro maior da periférica inverte o
  resultado depois dos custos.
- **A carteira Central-10 do GPMF perdeu para o IFIX** (p = 0,04 no bootstrap;
  0,20 no Jobson-Korkie). Nenhuma carteira superou o índice com significância.
- **A mínima variância teve o maior Sharpe do estudo** (−0,77, contra −0,91 do
  IFIX e −0,94 da melhor carteira de rede), mas também sem diferença
  significativa.

Rascunho do artigo: [docs/artigo.md](docs/artigo.md).

## Licença

Código sob a licença MIT (ver [LICENSE](LICENSE)). Os dados em `data/raw/`
vêm do Yahoo Finance e do Banco Central do Brasil e seguem os termos dessas
fontes; a licença não se aplica a eles.

## Como citar

Os dados de citação estão em [CITATION.cff](CITATION.cff). O GitHub usa esse
arquivo para o botão *Cite this repository*, e o Zenodo, para os autores do
DOI.
