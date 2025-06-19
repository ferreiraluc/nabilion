
from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from funcoes_bybit import busca_velas, tem_trade_aberto, saldo_da_conta, quantidade_minima_para_operar, abre_compra, abre_venda, reduzir_posicao
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
qtd_velas_stop = 17
risco_retorno = 5.0
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2

# ===== Função para calcular ATR =====
def calcular_atr(df, periodo=40):
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

print('Bot started', flush=True)
print(f'Cripto: {cripto}', flush=True)
print(f'Tempo gráfico: {tempo_grafico}', flush=True)
print(f'Velas Stop: {qtd_velas_stop}', flush=True)
print(f'Risco/Retorno: {risco_retorno}', flush=True)
print(f'EMAs: {emas}', flush=True)

for tentativa in range(5):
    try:
        estado_de_trade, preco_entrada, preco_stop, preco_alvo = tem_trade_aberto(cripto)
        print(f'Estado de trade: {estado_de_trade}', flush=True)
        print(f'Preço de entrada: {preco_entrada}', flush=True)
        print(f'Preço de stop: {preco_stop}', flush=True)
        print(f'Preço de alvo: {preco_alvo}', flush=True)
        break
    except Exception as e:
        print(f'Erro ao buscar trade aberto: {e}', flush=True)
        if tentativa < 4:
            print('Tentando novamente...', flush=True)
            time.sleep(2)
        else:
            print('Não foi possível buscar trade aberto. Encerrando programa.', flush=True)
            exit()

vela_fechou_trade = None
meta_parcial_realizada = False
trailing_ativo = False

while True:
    try:
        df = busca_velas(cripto, tempo_grafico, emas)
        if df.empty:
            print('DataFrame vazio')
            continue

        # ====== CALCULAR ATR ======
        df = calcular_atr(df)

        if len(df) < qtd_velas_stop + 2:
            print(f'DataFrame com poucas velas ({len(df)}). Esperando pelo menos {qtd_velas_stop + 2}...')
            time.sleep(1)
            continue

        if estado_de_trade == EstadoDeTrade.COMPRADO:
            print('Está comprado')
            print('Buscando saída no stop ou no alvo...')

            _, preco_entrada, preco_stop, preco_alvo = tem_trade_aberto(cripto)

            preco_atual = df['close'].iloc[-1]
            lucro_atual = ((preco_atual - preco_entrada) / preco_entrada) * 100

            if not meta_parcial_realizada and lucro_atual >= 5:
                print('Lucro atingiu 5%, realizando 50% da posição e movendo stop para o preço de entrada', flush=True)
                reduzir_posicao(cripto, 0.5)
                preco_stop = preco_entrada
                meta_parcial_realizada = True

            alvo_50 = preco_entrada + ((preco_alvo - preco_entrada) * 0.5)
            if preco_atual >= alvo_50 and not trailing_ativo:
                trailing_ativo = True
                print('Ativando trailing stop inteligente após atingir 50% do alvo', flush=True)

            if trailing_ativo:
                novo_stop = max(preco_stop, preco_atual - (df['ATR'].iloc[-1] * 1.5))
                if novo_stop > preco_stop:
                    preco_stop = novo_stop
                    print(f'Trailing ativo! Novo Stop ajustado para {preco_stop}', flush=True)

            if df['high'].iloc[-1] >= preco_alvo:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Bateu alvo na vela que abriu {vela_fechou_trade}, no preço de {preco_alvo}", flush=True)
                print('-' * 10)
                meta_parcial_realizada = False
                trailing_ativo = False
            elif df['low'].iloc[-1] <= preco_stop:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Bateu stop na vela que abriu {vela_fechou_trade}, no preço de {preco_stop}", flush=True)
                print('-' * 10)
                meta_parcial_realizada = False
                trailing_ativo = False
            elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print('Trade fechado manualmente na corretora', flush=True)
                print('-' * 10)
                meta_parcial_realizada = False
                trailing_ativo = False

        elif estado_de_trade == EstadoDeTrade.VENDIDO:
            print('Está vendido')
            print('Buscando saída no stop ou no alvo...')

            _, preco_entrada, preco_stop, preco_alvo = tem_trade_aberto(cripto)

            preco_atual = df['close'].iloc[-1]
            lucro_atual = ((preco_entrada - preco_atual) / preco_entrada) * 100

            if not meta_parcial_realizada and lucro_atual >= 5:
                print('Lucro atingiu 5%, realizando 50% da posição e movendo stop para o preço de entrada', flush=True)
                reduzir_posicao(cripto, 0.5)
                preco_stop = preco_entrada
                meta_parcial_realizada = True

            alvo_50 = preco_entrada - ((preco_entrada - preco_alvo) * 0.5)
            if preco_atual <= alvo_50 and not trailing_ativo:
                trailing_ativo = True
                print('Ativando trailing stop inteligente após atingir 50% do alvo', flush=True)

            if trailing_ativo:
                novo_stop = min(preco_stop, preco_atual + (df['ATR'].iloc[-1] * 1.5))
                if novo_stop < preco_stop:
                    preco_stop = novo_stop
                    print(f'Trailing ativo! Novo Stop ajustado para {preco_stop}', flush=True)

            if df['low'].iloc[-1] <= preco_alvo:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Bateu alvo na vela que abriu {vela_fechou_trade}, no preço de {preco_alvo}", flush=True)
                print('-' * 10)
                meta_parcial_realizada = False
                trailing_ativo = False
            elif df['high'].iloc[-1] >= preco_stop:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f"Bateu stop na vela que abriu {vela_fechou_trade}, no preço de {preco_stop}", flush=True)
                print('-' * 10)
                meta_parcial_realizada = False
                trailing_ativo = False
            elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                estado_de_trade = EstadoDeTrade.DE_FORA
                vela_fechou_trade = df['open_time'].iloc[-1]
                print('Trade fechado manualmente na corretora', flush=True)
                print('-' * 10)
                meta_parcial_realizada = False
                trailing_ativo = False

        elif estado_de_trade == EstadoDeTrade.DE_FORA and df['open_time'].iloc[-1] != vela_fechou_trade:
            print('Procurando trades...')

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
                preco_stop = preco_entrada - (atr_atual * 4)
                if (preco_entrada - preco_stop) >= atr_atual:
                    preco_alvo = ((preco_entrada - preco_stop) * risco_retorno) + preco_entrada
                    abre_compra(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                    print(f"Entrou na compra AGRESSIVA da vela que abriu {df['open_time'].iloc[-1]}, Preço de entrada: {preco_entrada}, Stop: {preco_stop}, Alvo: {preco_alvo}")
                    estado_de_trade = EstadoDeTrade.COMPRADO
                    print('-' * 10)

            # ======= VENDA AGRESSIVA =======
            elif (
                df['RSI'].iloc[-2] > 70 and
                df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and
                df['low'].iloc[-1] < df['low'].iloc[-2]
            ):
                preco_entrada = df['low'].iloc[-2]
                preco_stop = preco_entrada + (atr_atual * 4)
                if (preco_stop - preco_entrada) >= atr_atual:
                    preco_alvo = preco_entrada - ((preco_stop - preco_entrada) * risco_retorno)
                    abre_venda(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                    print(f"Entrou na venda AGRESSIVA da vela que abriu {df['open_time'].iloc[-1]}, Preço de entrada: {preco_entrada}, Stop: {preco_stop}, Alvo: {preco_alvo}")
                    estado_de_trade = EstadoDeTrade.VENDIDO
                    print('-' * 10)

    except ConnectionError as ce:
        print(f'Erro de conexão: {ce}', flush=True)
    except ValueError as ve:
        print(f'Erro de valor: {ve}', flush=True)
    except Exception as e:
        print(f'Erro desconhecido: {e}', flush=True)

    time.sleep(0.25)
