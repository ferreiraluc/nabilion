from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from funcoes_bybit import busca_velas, tem_trade_aberto, saldo_da_conta, quantidade_minima_para_operar, abre_compra, abre_venda
from utilidades import quantidade_cripto_para_operar
import time
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')

cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

cripto = 'SOLUSDT'
tempo_grafico = '1'
risco_retorno = 5.0
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2

def calcular_atr(df, periodo=14):
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

print('Bot started', flush=True)
print(f'Cripto: {cripto}', flush=True)
print(f'Tempo gráfico: {tempo_grafico}', flush=True)
print(f'Risco/Retorno: {risco_retorno}', flush=True)
print(f'EMAs: {emas}', flush=True)

for tentativa in range(5):
    try:
        estado_de_trade, preco_entrada, preco_stop, preco_alvo = tem_trade_aberto(cripto)
        print(f'Estado de trade: {estado_de_trade}', flush=True)
        break
    except Exception as e:
        print(f'Erro ao buscar trade aberto: {e}', flush=True)
        if tentativa < 4:
            time.sleep(2)
        else:
            exit()

vela_fechou_trade = None

while True:
    try:
        df = busca_velas(cripto, tempo_grafico, emas)
        if df.empty:
            continue

        df = calcular_atr(df)

        if df['ATR'].iloc[-1] == 0 or pd.isna(df['ATR'].iloc[-1]):
            print('ATR inválido, aguardando próximo ciclo...')
            time.sleep(1)
            continue

        if estado_de_trade == EstadoDeTrade.COMPRADO:
            _, _, preco_stop, preco_alvo = tem_trade_aberto(cripto)
            if df['high'].iloc[-1] >= preco_alvo:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Alvo atingido: {preco_alvo}", flush=True)
            elif df['low'].iloc[-1] <= preco_stop:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Stop atingido: {preco_stop}", flush=True)
            elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print('Trade fechado manualmente', flush=True)

        elif estado_de_trade == EstadoDeTrade.VENDIDO:
            _, _, preco_stop, preco_alvo = tem_trade_aberto(cripto)
            if df['low'].iloc[-1] <= preco_alvo:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Alvo atingido: {preco_alvo}", flush=True)
            elif df['high'].iloc[-1] >= preco_stop:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Stop atingido: {preco_stop}", flush=True)
            elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print('Trade fechado manualmente', flush=True)

        elif estado_de_trade == EstadoDeTrade.DE_FORA and df['open_time'].iloc[-1] != vela_fechou_trade:
            saldo = saldo_da_conta() * alavancagem
            qtidade_minima_para_operar = quantidade_minima_para_operar(cripto)
            qtd_cripto_para_operar = quantidade_cripto_para_operar(saldo, qtidade_minima_para_operar, df['close'].iloc[-1])

            atr_atual = df['ATR'].iloc[-1]

            # ======= COMPRA AGRESSIVA =======
            if (
                df['RSI'].iloc[-2] < 30 and
                df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and
                df['high'].iloc[-1] > df['high'].iloc[-2]
            ):
                preco_entrada = df['high'].iloc[-2]
                preco_stop = preco_entrada - (atr_atual * 2)

                # Filtro: stop mínimo = 1x ATR
                if (preco_entrada - preco_stop) < atr_atual:
                    print('Stop de compra muito curto comparado ao ATR, ignorando entrada')
                else:
                    preco_alvo = ((preco_entrada - preco_stop) * risco_retorno) + preco_entrada
                    abre_compra(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                    print(f"Compra: entrada={preco_entrada}, stop={preco_stop}, alvo={preco_alvo}")
                    estado_de_trade = EstadoDeTrade.COMPRADO

            # ======= VENDA AGRESSIVA =======
            elif (
                df['RSI'].iloc[-2] > 70 and
                df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and
                df['low'].iloc[-1] < df['low'].iloc[-2]
            ):
                preco_entrada = df['low'].iloc[-2]
                preco_stop = preco_entrada + (atr_atual * 2)

                if (preco_stop - preco_entrada) < atr_atual:
                    print('Stop de venda muito curto comparado ao ATR, ignorando entrada')
                else:
                    preco_alvo = preco_entrada - ((preco_stop - preco_entrada) * risco_retorno)
                    abre_venda(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                    print(f"Venda: entrada={preco_entrada}, stop={preco_stop}, alvo={preco_alvo}")
                    estado_de_trade = EstadoDeTrade.VENDIDO

    except ConnectionError as ce:
        print(f'Erro de conexão: {ce}', flush=True)
    except ValueError as ve:
        print(f'Erro de valor: {ve}', flush=True)
    except Exception as e:
        print(f'Erro desconhecido: {e}', flush=True)

    time.sleep(0.25)
