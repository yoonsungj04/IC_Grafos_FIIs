"""
Download e cache dos dados dos FIIs.

Este é o único módulo que acessa a internet. A política do projeto é baixar uma
vez para data/raw/, congelar e nunca mais fazer chamada de rede no meio da
análise — tudo a jusante lê os arquivos em cache.

O Yahoo bloqueia requisições simples pela impressão digital TLS (devolve HTTP
429 mesmo com User-Agent de navegador) e o yfinance ignora a sessão passada por
parâmetro. Por isso acessamos o endpoint "chart" diretamente com uma sessão do
curl_cffi imitando o Chrome. Uma única resposta traz tudo que precisamos:
    indicators.quote[0].close       -> fechamento bruto
    indicators.adjclose[0].adjclose -> fechamento ajustado por proventos
    events.dividends                -> proventos pagos
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd
from curl_cffi import requests as cffi_requests

import config

_SESSION = cffi_requests.Session(impersonate="chrome")
_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

PRECOS_CSV = config.RAW_DIR / "precos_ajustados.csv"
PRECOS_BRUTOS_CSV = config.RAW_DIR / "precos_brutos.csv"
DIVIDENDOS_CSV = config.RAW_DIR / "dividendos.csv"


def _epoch(data: str) -> int:
    return int(datetime.strptime(data, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def baixar_serie(symbol: str, start: str = config.START_DATE,
                 end: str = config.END_DATE) -> pd.DataFrame:
    """Baixa uma série e devolve DataFrame com fechamento bruto, ajustado e dividendo."""
    params = {
        "period1": _epoch(start),
        "period2": _epoch(end),
        "interval": "1d",
        "events": "div,splits",
    }
    r = _SESSION.get(_CHART_URL.format(symbol=symbol), params=params, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]

    ts = (pd.to_datetime(res["timestamp"], unit="s", utc=True)
          .tz_convert(None).normalize())
    bruto = pd.Series(res["indicators"]["quote"][0]["close"], index=ts, name="bruto")
    ajustado = pd.Series(res["indicators"]["adjclose"][0]["adjclose"], index=ts,
                         name="ajustado")

    div = pd.Series(0.0, index=ts, name="dividendo")
    for ev in res.get("events", {}).get("dividends", {}).values():
        d = pd.to_datetime(ev["date"], unit="s", utc=True).tz_convert(None).normalize()
        pos = ts.get_indexer([d], method="nearest")[0]
        div.iloc[pos] += float(ev["amount"])

    return pd.concat([bruto, ajustado, div], axis=1)


def baixar_universo(tickers: list[str] | None = None, pausa: float = 0.8,
                    salvar: bool = True) -> dict[str, pd.DataFrame]:
    """Baixa todos os candidatos, monta os painéis e grava o cache em data/raw/."""
    tickers = tickers or list(dict.fromkeys(config.TICKERS_CANDIDATOS))  # remove duplicatas
    ajustados, brutos, dividendos = {}, {}, {}
    falhas = []

    for i, tk in enumerate(tickers, 1):
        symbol = f"{tk}{config.YF_SUFFIX}"
        try:
            df = baixar_serie(symbol)
            if df["ajustado"].dropna().empty:
                raise ValueError("série vazia")
            ajustados[tk] = df["ajustado"]
            brutos[tk] = df["bruto"]
            dividendos[tk] = df["dividendo"]
            print(f"[{i:>2}/{len(tickers)}] {tk}: {df['ajustado'].dropna().shape[0]} pregões")
        except Exception as e:  # registra falha e segue
            falhas.append(tk)
            print(f"[{i:>2}/{len(tickers)}] {tk}: FALHA ({e})")
        time.sleep(pausa)

    painel_aj = pd.DataFrame(ajustados).sort_index()
    painel_br = pd.DataFrame(brutos).sort_index()
    painel_dv = pd.DataFrame(dividendos).sort_index()

    if salvar:
        painel_aj.to_csv(PRECOS_CSV)
        painel_br.to_csv(PRECOS_BRUTOS_CSV)
        painel_dv.to_csv(DIVIDENDOS_CSV)
        print(f"\ncache salvo em {config.RAW_DIR} "
              f"({painel_aj.shape[1]} tickers, {painel_aj.shape[0]} datas)")
    if falhas:
        print(f"tickers sem dados: {', '.join(falhas)}")

    return {"ajustado": painel_aj, "bruto": painel_br, "dividendo": painel_dv}


def carregar_precos(ajustado: bool = True) -> pd.DataFrame:
    """Carrega o painel de preços do cache (offline)."""
    caminho = PRECOS_CSV if ajustado else PRECOS_BRUTOS_CSV
    if not caminho.exists():
        raise FileNotFoundError(f"cache não encontrado: {caminho}. Rode o download primeiro.")
    return pd.read_csv(caminho, index_col=0, parse_dates=True).sort_index()


def carregar_dividendos() -> pd.DataFrame:
    return pd.read_csv(DIVIDENDOS_CSV, index_col=0, parse_dates=True).sort_index()


def calcular_retornos(precos: pd.DataFrame) -> pd.DataFrame:
    """Retornos logarítmicos do fechamento ajustado: Rt = ln(Pt/Pt-1)."""
    if config.RETURN_TYPE == "log":
        import numpy as np
        return np.log(precos / precos.shift(1)).dropna(how="all")
    return (precos / precos.shift(1) - 1.0).dropna(how="all")
