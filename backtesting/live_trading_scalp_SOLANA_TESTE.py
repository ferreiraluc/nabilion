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
tempo_grafico = '15'
qtd_velas_stop = 17
risco_retorno = 5.0
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2
ATR_MINIMO = 0.5  # ATR mínimo para entrar (ajuste conforme o ativo)

def calcular_atr(df, periodo=40):
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

def mover_stop_para_entrada(preco_entrada):
    try:
        cliente.set_trading_stop(
            category='linear',
            symbol=cripto,
            stop_loss=round(preco_entrada, 4)
        )
        print(f'Stop movido para o preço de entrada: {preco_entrada}')
    except Exception as e:
        print(f'Erro ao mover o stop para o break even: {e}')

def monitorar_parcial(preco_stop_gain, preco_entrada):
    while True:
        try:
            ordens = cliente.get_open_orders(symbol=cripto)['result']['list']
            for ordem in ordens:
                if float(ordem['price']) == round(preco_stop_gain, 4) and float(ordem['leaves_qty']) == 0:
                    print('Parcial de 5% executada! Movendo o stop para o preço de entrada.')
                    mover_stop_para_entrada(preco_entrada)
                    return
        except Exception as e:
            print(f'Erro ao monitorar parcial: {e}')
        time.sleep(1)

print('Bot started', flush=True)

for tentativa in range(5):
    try:
        estado_de_trade, preco_entrada, preco_stop, preco_alvo = tem_trade_aberto(cripto)
        break
    except Exception as e:
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

        if len(df) < qtd_velas_stop + 2:
            time.sleep(1)
            continue

        if estado_de_trade == EstadoDeTrade.COMPRADO:
            _, _, preco_stop, preco_alvo = tem_trade_aberto(cripto)
            if df['high'].iloc[-1] >= preco_alvo or df['low'].iloc[-1] <= preco_stop:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
            elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]

        elif estado_de_trade == EstadoDeTrade.VENDIDO:
            _, _, preco_stop, preco_alvo = tem_trade_aberto(cripto)
            if df['low'].iloc[-1] <= preco_alvo or df['high'].iloc[-1] >= preco_stop:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
            elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]

        elif estado_de_trade == EstadoDeTrade.DE_FORA and df['open_time'].iloc[-1] != vela_fechou_trade:
            saldo = saldo_da_conta() * alavancagem
            qtidade_minima_para_operar = quantidade_minima_para_operar(cripto)
            qtd_cripto_para_operar = quantidade_cripto_para_operar(saldo, qtidade_minima_para_operar, df['close'].iloc[-1])

            atr_atual = df['ATR'].iloc[-1]

            # Filtro ATR Mínimo
            if atr_atual < ATR_MINIMO:
                print(f'ATR ({atr_atual}) abaixo do mínimo ({ATR_MINIMO}), pulando entrada.')
                time.sleep(1)
                continue

            # ======= COMPRA AGRESSIVA =======
            if (
                df['RSI'].iloc[-2] < 30 and
                df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and
                df['high'].iloc[-1] > df['high'].iloc[-2] and
                df['EMA_9'].iloc[-1] > df['EMA_21'].iloc[-1]  # Filtro de tendência
            ):
                preco_entrada = df['high'].iloc[-2]
                preco_stop = preco_entrada - (atr_atual * 4)
                if (preco_entrada - preco_stop) < atr_atual:
                    continue
                preco_alvo = ((preco_entrada - preco_stop) * risco_retorno) + preco_entrada
                preco_stop_gain = preco_entrada * 1.05
                quantidade_parcial = qtd_cripto_para_operar * 0.5

                abre_compra(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                cliente.place_order(
                    category='linear',
                    symbol=cripto,
                    side='Sell',
                    order_type='Limit',
                    qty=quantidade_parcial,
                    price=round(preco_stop_gain, 4),
                    time_in_force='GTC',
                    reduce_only=True
                )
                estado_de_trade = EstadoDeTrade.COMPRADO
                print(f'Compra feita. Stop Gain parcial criado a {preco_stop_gain}')
                monitorar_parcial(preco_stop_gain, preco_entrada)

            # ======= VENDA AGRESSIVA =======
            elif (
                df['RSI'].iloc[-2] > 70 and
                df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and
                df['low'].iloc[-1] < df['low'].iloc[-2] and
                df['EMA_9'].iloc[-1] < df['EMA_21'].iloc[-1]  # Filtro de tendência
            ):
                preco_entrada = df['low'].iloc[-2]
                preco_stop = preco_entrada + (atr_atual * 4)
                if (preco_stop - preco_entrada) < atr_atual:
                    continue
                preco_alvo = preco_entrada - ((preco_stop - preco_entrada) * risco_retorno)
                preco_stop_gain = preco_entrada * 0.95
                quantidade_parcial = qtd_cripto_para_operar * 0.5

                abre_venda(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                cliente.place_order(
                    category='linear',
                    symbol=cripto,
                    side='Buy',
                    order_type='Limit',
                    qty=quantidade_parcial,
                    price=round(preco_stop_gain, 4),
                    time_in_force='GTC',
                    reduce_only=True
                )
                estado_de_trade = EstadoDeTrade.VENDIDO
                print(f'Venda feita. Stop Gain parcial criado a {preco_stop_gain}')
                monitorar_parcial(preco_stop_gain, preco_entrada)

    except Exception as e:
        print(f'Erro: {e}', flush=True)

    time.sleep(0.25)
