import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

tickers = [
    # Estados Unidos (USA)
    "AAPL",     # Apple
    "MSFT",     # Microsoft
    "AMZN",     # Amazon
    "GOOGL",    # Alphabet (Google)
    "NVDA",     # Nvidia
    "BRK-B",    # Berkshire Hathaway
    "V",        # Visa
    "MA",       # Mastercard
    "UNH",      # UnitedHealth
    "COST",     # Costco
    "JPM",      # JPMorgan Chase
    "PG",       # Procter & Gamble
    "JNJ",      # Johnson & Johnson
    "PEP",      # PepsiCo
    "KO",       # Coca-Cola
    "MCD",      # McDonald's
    "HD",       # Home Depot
    "TSLA",     # Tesla

    # España (Bolsa de Madrid, .MC)
    "ITX.MC",   # Inditex
    "SAN.MC",   # Banco Santander
    "BBVA.MC",  # BBVA
    "IBE.MC",   # Iberdrola
    "REP.MC",   # Repsol
    "AMS.MC",   # Amadeus IT Group
    "FER.MC",   # Ferrovial
    "GRF.MC",   # Grifols
    "AENA.MC",  # AENA
    "CLNX.MC",  # Cellnex
    "CABK.MC",  # CaixaBank

    # Europa
    "ASML.AS",   # ASML (Países Bajos)
    "LVMH.PA",   # LVMH (Francia)
    "OR.PA",     # L'Oréal (Francia)
    "MC.PA",     # LVMH (Francia, ticker alternativo)
    "NESN.SW",   # Nestlé (Suiza)
    "ROG.SW",    # Roche (Suiza)
    "NOVN.SW",   # Novartis (Suiza)
    "SAP.DE",    # SAP (Alemania)
    "SIE.DE",    # Siemens (Alemania)
    "ADS.DE",    # Adidas (Alemania)
    "AIR.PA",    # Airbus (Francia)

    # Reino Unido
    "ULVR.L",    # Unilever
    "AZN.L",     # AstraZeneca
    "HSBA.L",    # HSBC
    "BP.L",      # BP
    "RIO.L",     # Rio Tinto

    # Japón
    "7203.T",    # Toyota
    "6758.T",    # Sony
    "9984.T",    # SoftBank Group
    "8035.T",    # Tokyo Electron
    "6861.T",    # Keyence

    # Otros países (Canadá, Australia, etc.)
    "SHOP.TO",   # Shopify (Canadá)
    "BNS.TO",    # Scotiabank (Canadá)
    "BHP.AX",    # BHP Group (Australia)
]



def analizar_drawdown(data_ticker, ticker, ventana_dias, umbral_drawdown):
    """
    Aplica lógica de drawdown a un único ticker.
    """
    df = data_ticker[["Close"]].copy()
    df["Maximo_Ventana"] = df["Close"].rolling(window=ventana_dias, min_periods=1).max()
    df["Drawdown_%"] = np.where(
        df["Maximo_Ventana"] != 0,
        (df["Close"] - df["Maximo_Ventana"]) / df["Maximo_Ventana"],
        np.nan,
    )
    df["Alerta_Activa"] = df["Drawdown_%"] < umbral_drawdown
    df["Ticker"] = ticker
    return df


def graficar_drawdown(df, ticker, ventana_dias, umbral_drawdown):
    """
    Visualiza la serie temporal con anotaciones.
    """
    primeros_eventos = df[
        df["Alerta_Activa"] & (~df["Alerta_Activa"].shift(1, fill_value=False))
    ]

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.plot(
        df.index,
        df["Close"],
        label="Precio de Cierre",
        color="deepskyblue",
        linewidth=1.5,
    )
    ax.plot(
        df.index,
        df["Maximo_Ventana"],
        label=f"Máximo de {ventana_dias} días",
        color="lightcoral",
        linestyle="--",
    )

    ax.scatter(
        primeros_eventos.index,
        primeros_eventos["Close"],
        color="red",
        marker="v",
        s=150,
        zorder=5,
        label=f"Alerta > {abs(umbral_drawdown):.0%}",
    )

    for index, row in primeros_eventos.iterrows():
        texto_caida = f"{row['Drawdown_%']:.1%}"
        ax.text(
            index,
            row["Close"] * 0.99,
            texto_caida,
            color="black",
            backgroundcolor="white",
            ha="center",
            va="top",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_title(f"Análisis de Drawdown para {ticker}", fontsize=16)
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Precio (USD)")
    ax.legend()
    plt.tight_layout()
    plt.show()


def analizar_tickers(tickers, inicio, fin, ventana_dias=60, umbral_drawdown=-0.20):
    datos = yf.download(
        tickers,
        start=inicio,
        end=fin,
        group_by="ticker",
        progress=False,
        auto_adjust=True,
    )
    if isinstance(tickers, str):
        tickers = [tickers]

    eventos_todas_empresas = []

    for ticker in tickers:
        print(f"\n📈 Analizando {ticker} entre {inicio} y {fin}")
        if ticker not in datos.columns.get_level_values(0):
            print(f"⚠️  No hay datos para {ticker}")
            continue
        df_ticker = datos[ticker].dropna()
        if df_ticker.empty:
            print(f"⚠️  Datos vacíos para {ticker}")
            continue

        df = analizar_drawdown(df_ticker, ticker, ventana_dias, umbral_drawdown)

        eventos = df[
            df["Alerta_Activa"] & (~df["Alerta_Activa"].shift(1, fill_value=False))
        ]
        if not eventos.empty:
            print(f"✅ {len(eventos)} evento(s) de drawdown detectados:")
            print(eventos[["Close", "Maximo_Ventana", "Drawdown_%"]])
        else:
            print("❌ No se detectaron caídas que cumplan el criterio.")

        graficar_drawdown(df, ticker, ventana_dias, umbral_drawdown)
        eventos_todas_empresas.append(eventos.reset_index())
    # Concatenar todos los eventos de todas las empresas en un solo DataFrame
    eventos_todas_empresas = pd.concat(eventos_todas_empresas, ignore_index=True)
    # set index as datetime
    eventos_todas_empresas.set_index("Date", inplace=True)
    # Renombrar las columnas para mayor claridad
    return eventos_todas_empresas


def crear_mensaje_alerta(
    destinatario, cuerpo_html, asunto="📉 Nueva alerta de inversión"
):
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = destinatario
    msg.set_content("Tu cliente de correo no soporta HTML.")
    msg.add_alternative(cuerpo_html, subtype="html")
    return msg


def enviar_alerta_inversion(df_alertas):
    """
    Envía un correo si hay nuevas alertas de drawdown detectadas.
    """
    if df_alertas.empty:
        print("✅ No hay alertas nuevas hoy.")
        return

    df_alertas = df_alertas.reset_index()
    # Sort
    df_alertas.sort_values(by="Date", ascending=False, inplace=True)
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    EMAIL_TO = os.getenv("EMAIL_TO")
    if not all([EMAIL_USER, EMAIL_PASS]):
        print("❌ Faltan variables de entorno necesarias.")
        return

    # Formatear tabla HTML
    html_tabla = df_alertas.to_html(index=False, justify="center", border=0)
    fecha = datetime.today().strftime("%Y-%m-%d")
    cuerpo_html = f"""
    <html>
    <body>
        <h2>📊 Alertas de inversión - {fecha}</h2>
        <p>Se detectaron nuevas oportunidades según el criterio de drawdown.</p>
        {html_tabla}
        <p style="font-size: small; color: gray;">Este correo fue generado automáticamente.</p>
    </body>
    </html>
    """

    asunto = f"📉 {len(df_alertas)} nueva(s) alerta(s) de drawdown - {fecha}"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            msg = crear_mensaje_alerta(EMAIL_TO, cuerpo_html, asunto)
            smtp.send_message(msg)
            print("✅ Alerta enviada")
    except Exception as e:
        print(f"❌ Error al enviar correos: {e}")

if __name__ == "__main__":

    eventos = analizar_tickers(
        tickers=tickers,  # Puedes poner los que quieras
        inicio="2020-01-01",
        fin="2025-07-08",
        ventana_dias=60,
        umbral_drawdown=-0.3,
    )

    hoy = pd.Timestamp(datetime.today().date())  # Solo fecha, sin hora
    eventos_hoy = eventos[eventos.index.date == hoy.date()]
    if not eventos_hoy.empty:
        print("🚨 NUEVAS OPORTUNIDADES")
        print(eventos_hoy)
    enviar_alerta_inversion(eventos_hoy)
