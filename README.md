# GPMF para FIIs

Formação de carteiras de Fundos de Investimento Imobiliário (FIIs) por filtragem
em grafos. A partir da correlação dos retornos, constrói-se o Grafo Planar
Maximamente Filtrado (GPMF) e selecionam-se carteiras Central, Periférica e
Híbrida por centralidade, avaliadas contra o IFIX. Pergunta central: a
recomendação de Pozzi et al. (2013) de "investir na periferia" vale para FIIs?

## Pipeline

retornos dos FIIs → correlação → distância `d = √(2(1−ρ))` → **GPMF** (planar,
≤ 3N−6 arestas) → carteiras por centralidade → avaliação risco/retorno, custos e
tributos, validação rolante fora da amostra, e comparação com a MST/AGM.

## Ambiente

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Apenas o download (`scripts/01_download.py`) acessa a internet. Depois disso os
dados ficam congelados em `data/raw/` e toda a análise roda offline.

## Estrutura

```
config.py            parâmetros (janela, custos, grafo, janela rolante)
requirements.txt     dependências fixadas
src/                 data_load filters gpmf centrality portfolio rolling costs metrics pipeline
scripts/             pontos de entrada executáveis (01..05 + verifica_dividendos)
data/raw|processed/  raw = cache congelado; processed = intermediários
results/figures|tables/
docs/                relatório e rascunho do artigo
notebooks/           driver enxuto (Colab)
```

## Como reproduzir

```bash
.venv/bin/python scripts/01_download.py          # baixa e congela os dados
.venv/bin/python scripts/verifica_dividendos.py  # convenção de dividendos
.venv/bin/python scripts/02_estatica.py          # tabela estática (referência)
.venv/bin/python scripts/03_rolling.py           # fora da amostra (principal)
.venv/bin/python scripts/04_custos.py            # custos, IR e significância
.venv/bin/python scripts/05_comparacao.py        # GPMF vs MST
```

Para gerar o relatório final em `.docx` (após rodar os scripts acima):

```bash
.venv/bin/python scripts/06_relatorio.py        # docs/Relatorio_Final_Yoon.docx
```

## Principais resultados

- Universo determinístico de 51 FIIs; janela mar/2022–nov/2025 (920 pregões);
  GPMF com 147 arestas (= 3·51−6), planar e conexo.
- Fora da amostra (550 pregões, 25 rebalanceamentos), as carteiras
  **periféricas superam as centrais em todos os tamanhos** — a favor de Pozzi.
- O **GPMF supera a AGM/MST** sob metodologia idêntica.
- Líquido de custos, o benchmark passivo é difícil de bater e nenhuma diferença
  de Sharpe é significativa na janela disponível.

Relatório final: [docs/Relatorio_Final_Yoon.docx](docs/Relatorio_Final_Yoon.docx).
Rascunho do artigo: [docs/artigo.md](docs/artigo.md).
