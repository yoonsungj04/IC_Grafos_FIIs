"""
Verificação da convenção de dividendos / auto_adjust.

Pergunta: o fechamento ajustado do Yahoo (auto_adjust=True) já reinveste os
dividendos? Se sim, usar Rt = ln((Pt + Dt)/Pt-1) sobre o ajustado conta o
provento duas vezes.

Teste decisivo, num FII de alto dividend yield (MXRF11): comparar dois retornos
diários ao longo da janela:
    r_aj          = ajustado_t / ajustado_{t-1} - 1            (auto_adjust=True)
    r_bruto_div   = (bruto_t + div_t) / bruto_{t-1} - 1        (preço + provento)
Se baterem, o ajustado já embute os proventos e somar Dt de novo é duplicidade.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import data_load


def main() -> None:
    symbol = f"{config.DIVIDEND_VERIFY_TICKER}{config.YF_SUFFIX}"
    print(f"verificando {symbol} de {config.START_DATE} a {config.END_DATE}\n")

    df = data_load.baixar_serie(symbol).dropna(subset=["bruto", "ajustado"])
    bruto, ajustado, div = df["bruto"], df["ajustado"], df["dividendo"]

    n_eventos = int((div > 0).sum())
    razao = ajustado / bruto

    r_aj = ajustado / ajustado.shift(1) - 1.0
    r_bruto_div = (bruto + div) / bruto.shift(1) - 1.0
    r_bruto_so = bruto / bruto.shift(1) - 1.0

    cmp = pd.concat([r_aj, r_bruto_div, r_bruto_so], axis=1).dropna()
    cmp.columns = ["r_aj", "r_bruto_div", "r_bruto_so"]
    dif_div = (cmp["r_aj"] - cmp["r_bruto_div"]).abs()
    dif_so = (cmp["r_aj"] - cmp["r_bruto_so"]).abs()

    print(f"proventos na janela: R$ {div.sum():.4f} em {n_eventos} eventos")
    print(f"razao ajustado/bruto: min={razao.min():.4f} max={razao.max():.4f}\n")
    print(f"max |r_aj - r_bruto_div| = {dif_div.max():.2e}  (media {dif_div.mean():.2e})")
    print(f"max |r_aj - r_bruto_so|  = {dif_so.max():.2e}\n")

    if dif_div.max() < 1e-3 and dif_so.max() > 1e-3:
        print("CONFIRMADO: auto_adjust=True ja reinveste os dividendos.")
        print("Usar Rt = ln(Pt/Pt-1) sobre o ajustado; NAO somar Dt.")
    elif dif_so.max() < 1e-3:
        print("auto_adjust=True NAO ajusta por dividendos; somar Dt explicitamente.")
    else:
        print("Inconclusivo — inspecionar as series.")

    saida = pd.DataFrame({"bruto": bruto, "ajustado": ajustado,
                          "dividendo": div, "razao": razao})
    caminho = config.TABLES_DIR / "verifica_dividendos_MXRF11.csv"
    saida.to_csv(caminho)
    print(f"\nevidencia salva em {caminho}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
        ax[0].plot(bruto.index, bruto, label="bruto (auto_adjust=False)")
        ax[0].plot(ajustado.index, ajustado, label="ajustado (auto_adjust=True)")
        ax[0].set_title(f"{symbol}: fechamento bruto vs ajustado")
        ax[0].legend()
        ax[1].plot(razao.index, razao, color="C3")
        ax[1].axhline(1.0, ls="--", color="k", lw=0.8)
        ax[1].set_title("razao ajustado/bruto (degraus = dividendos reinvestidos)")
        fig.tight_layout()
        fig_path = config.FIGURES_DIR / "verifica_dividendos_MXRF11.png"
        fig.savefig(fig_path, dpi=120)
        print(f"figura salva em {fig_path}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()
