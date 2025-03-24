from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from funcoes_bybit import busca_velas, tem_trade_aberto, saldo_da_conta, quantidade_minima_para_operar, abre_compra, abre_venda
from utilidades import quantidade_cripto_para_operar
import time
from dotenv import load_dotenv
import os   

load_dotenv()

API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')

cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

cripto = 'LTCUSDT'
tempo_grafico = '15'
qtd_velas_stop = 17
risco_retorno = 2.5
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2

print('Bot started', flush=True)
print(f'Cripto: {cripto}', flush=True)
print(f'Tempo grafico: {tempo_grafico}', flush=True)
print(f'Velas Stop: {qtd_velas_stop}', flush=True)
print(f'Risco/Retorno: {risco_retorno}', flush=True)
print(f'EMAs: {emas}', flush=True)

for tentativa in range(5):
    try:
        estado_de_trade, preco_entrada, preco_stop, preco_alvo = tem_trade_aberto(cripto)
        print(f'Estado de trade: {estado_de_trade}', flush=True)
        print(f'Preco de entrada: {preco_entrada}', flush=True)
        print(f'Preco de stop: {preco_stop}', flush=True)
        print(f'Preco de alvo: {preco_alvo}', flush=True)
        break
    except Exception as e:
        print(f'Erro ao buscar trade aberto: {e}', flush=True)
        if tentativa < 4:
            print('Tentando novamente...', flush=True)
            time.sleep(2)
        elif tentativa == 4:
            print('Não foi possível buscar trade aberto. Encerrando programa.', flush=True)
            exit()

vela_fechou_trade = None

while True:
    try:
        df = busca_velas(cripto, tempo_grafico, emas)
        if df.empty:
            print('DataFrame vazio')
        else:
            if estado_de_trade == EstadoDeTrade.COMPRADO:
                print('esta comprado')
                print('buscando saida no stop ou no alvo...')
                
                _, _, preco_stop, preco_alvo = tem_trade_aberto(cripto)
                
                if df['high'].iloc[-1] >= preco_alvo:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df['open_time'].iloc[-1]
                    print(f"Bateu alvo na vela que abriu {df['open_time'].iloc[-1]}, no preço de {preco_alvo}", flush=True)
                    print('-' * 10)
                elif df['low'].iloc[-1] <= preco_stop:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df['open_time'].iloc[-1]
                    print(f"Bateu stop na vela que abriu {df['open_time'].iloc[-1]}, no preço de {preco_stop}", flush=True)
                    print('-' * 10)
                elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df['open_time'].iloc[-1]
                    print('Trade fechado manualmente na corretora', flush=True)
                    print('-' * 10)
            
            elif estado_de_trade == EstadoDeTrade.VENDIDO:
                print('esta vendido')
                print('buscando saida no stop ou no alvo...')
                
                _, _, preco_stop, preco_alvo = tem_trade_aberto(cripto)
                
                if df['low'].iloc[-1] <= preco_alvo:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df['open_time'].iloc[-1]
                    print(f"Bateu alvo na vela que abriu {df['open_time'].iloc[-1]}, no preço de {preco_alvo}", flush=True)
                    print('-' * 10)
                elif df['high'].iloc[-1] >= preco_stop:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df['open_time'].iloc[-1]
                    print(f"Bateu stop na vela que abriu {df['open_time'].iloc[-1]}, no preço de {preco_stop}", flush=True)
                    print('-' * 10)
                elif tem_trade_aberto(cripto)[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df['open_time'].iloc[-1]
                    print('Trade fechado manualmente na corretora', flush=True)
                    print('-' * 10)
            
            elif estado_de_trade == EstadoDeTrade.DE_FORA and df['open_time'].iloc[-1] != vela_fechou_trade:
                print('Procurando trades...')
                
                # Condição para compra
                if (df['close'].iloc[-2] > df[f'EMA_{ema_rapida}'].iloc[-2] and 
                    df['close'].iloc[-2] > df[f'EMA_{ema_lenta}'].iloc[-2] and 
                    df['close'].iloc[-2] > df['EMA_200'].iloc[-2] and  # Tendência de alta
                    df['RSI'].iloc[-1] < 70 and  # Não sobrecomprado
                    df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and  # Volume confirma
                    df['high'].iloc[-1] > df['high'].iloc[-2]):
                    
                    saldo = saldo_da_conta() * alavancagem
                    qtidade_minima_para_operar = quantidade_minima_para_operar(cripto)
                    qtd_cripto_para_operar = quantidade_cripto_para_operar(saldo, qtidade_minima_para_operar, df['close'].iloc[-1])
                    
                    preco_entrada = df['high'].iloc[-2]
                    preco_stop = df['low'].iloc[-qtd_velas_stop: -1].min()
                    preco_alvo = ((preco_entrada - preco_stop) * risco_retorno) + preco_entrada
                    
                    abre_compra(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                    
                    print(f"Entrou na compra da vela que abriu {df['open_time'].iloc[-1]}, Preco de entrada: {preco_entrada}, preco stop: {preco_stop}, preco alvo: {preco_alvo}")
                    estado_de_trade = EstadoDeTrade.COMPRADO
                    print('-' * 10)
                
                # Condição para venda
                elif (df['close'].iloc[-2] < df[f'EMA_{ema_rapida}'].iloc[-2] and 
                      df['close'].iloc[-2] < df[f'EMA_{ema_lenta}'].iloc[-2] and 
                      df['close'].iloc[-2] < df['EMA_200'].iloc[-2] and  # Tendência de baixa
                      df['RSI'].iloc[-1] > 30 and  # Não sobrevendido
                      df['volume'].iloc[-1] > df['Volume_EMA_20'].iloc[-1] and  # Volume confirma
                      df['low'].iloc[-1] < df['low'].iloc[-2]):
                    
                    saldo = saldo_da_conta() * alavancagem
                    qtidade_minima_para_operar = quantidade_minima_para_operar(cripto)
                    qtd_cripto_para_operar = quantidade_cripto_para_operar(saldo, qtidade_minima_para_operar, df['close'].iloc[-1])
                    
                    preco_entrada = df['low'].iloc[-2]
                    preco_stop = df['high'].iloc[-qtd_velas_stop: -1].max()
                    preco_alvo = preco_entrada - ((preco_stop - preco_entrada) * risco_retorno)
                    
                    abre_venda(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo)
                    
                    print(f"Entrou na venda da vela que abriu {df['open_time'].iloc[-1]}, Preco de entrada: {preco_entrada}, preco stop: {preco_stop}, preco alvo: {preco_alvo}")
                    estado_de_trade = EstadoDeTrade.VENDIDO
                    print('-' * 10)
            
    except ConnectionError as ce:
        print(f'Erro de conexão: {ce}', flush=True)
    except ValueError as ve:
        print(f'Erro de valor: {ve}', flush=True)
    except Exception as e:
        print(f'Erro desconhecido: {e}', flush=True)
    
    time.sleep(0.25)
