from pybit.unified_trading import HTTP
from funcoes_bybit import busca_velas
import time
from dotenv import load_dotenv
import os

# Load API credentials
load_dotenv()
API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')
cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

# Trading parameters
cripto = 'SOLUSDT'
tempo_grafico = '1'
higher_timeframe = '5'  # Confirmation from 5-min chart
risk_per_trade = 0.02  # 2% risk per trade
alavancagem = 1
emas = [9, 21, 50]  # Added 50 EMA for trend confirmation
ema_rapida, ema_lenta, ema_trend = emas
atr_multiplier = 1.5  # ATR-based stop-loss calculation
trade_risk_reward = 2  # Risk/reward ratio

print('Bot Started')
print(f'Trading {cripto} on {tempo_grafico} min chart with trend from {higher_timeframe} min')

# Function to fetch candlestick data
# def busca_velas(cripto, tempo, emas):
#     response = cliente.get_kline(symbol=cripto, interval=tempo, limit=100)
#     candles = response['result']['list'][::-1]

#     df = pd.DataFrame(candles, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
#     df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
#     df['open'] = df['open'].astype(float)
#     df['high'] = df['high'].astype(float)
#     df['low'] = df['low'].astype(float)
#     df['close'] = df['close'].astype(float)
    
#     for ema in emas:
#         df[f'EMA_{ema}'] = df['close'].ewm(span=ema, adjust=False).mean()
    
#     # ATR Calculation
#     df['ATR'] = df['high'] - df['low']
#     df['ATR'] = df['ATR'].rolling(14).mean()
    
#     return df

# Function to check open trades
def tem_trade_aberto(cripto):
    response = cliente.get_positions(category='linear', symbol=cripto)
    if not response['result']['list']:
        return None, 0, 0, 0  # No open position

    pos = response['result']['list'][0]
    side = pos['side']

    # Handling missing values
    preco_entrada = float(pos['avgPrice']) if pos['avgPrice'] else 0
    preco_stop = float(pos['stopLoss']) if pos['stopLoss'] else 0
    preco_alvo = float(pos['takeProfit']) if pos['takeProfit'] else 0

    estado = None
    if side == 'Buy':
        estado = 'LONG'
    elif side == 'Sell':
        estado = 'SHORT'

    return estado, preco_entrada, preco_stop, preco_alvo


# Function to fetch account balance
def saldo_da_conta():
    response = cliente.get_wallet_balance(accountType='UNIFIED', coin='USDT')
    return float(response['result']['list'][0]['coin'][0]['walletBalance'])

# Function to get min trade size
def quantidade_minima_para_operar(cripto):
    response = cliente.get_instruments_info(category='linear', symbol=cripto)
    return float(response['result']['list'][0]['lotSizeFilter']['minOrderQty'])

# Function to execute trades
def abre_trade(cripto, side, qty, stop_loss, take_profit):
    cliente.place_order(
        category='linear',
        symbol=cripto,
        side=side,
        orderType='Market',
        qty=qty,
        stopLoss=stop_loss,
        takeProfit=take_profit
    )

# Bot loop
estado_de_trade, _, _, _ = tem_trade_aberto(cripto)
vela_fechou_trade = None

while True:
    try:
        df = busca_velas(cripto, tempo_grafico, emas)
        df_higher = busca_velas(cripto, higher_timeframe, [ema_trend])

        if df.empty or df_higher.empty:
            print('No data retrieved')
            time.sleep(1)
            continue
        
        trend = 'UP' if df_higher['EMA_50'].iloc[-1] > df_higher['EMA_50'].iloc[-2] else 'DOWN'

        # Managing existing trades
        if estado_de_trade:
            print(f'Trade Active: {estado_de_trade}')
            trade_status, _, stop_loss, take_profit = tem_trade_aberto(cripto)
            if trade_status is None:
                estado_de_trade = None
                vela_fechou_trade = df['open_time'].iloc[-1]
                print(f'Trade closed')

        # Checking new trade opportunities
        elif df['open_time'].iloc[-1] != vela_fechou_trade:
            saldo = saldo_da_conta() * alavancagem
            min_qty = quantidade_minima_para_operar(cripto)
            atr = df['ATR'].iloc[-1]

            if trend == 'UP':
                if df['close'].iloc[-2] > df['EMA_9'].iloc[-2] > df['EMA_21'].iloc[-2]:
                    if df['high'].iloc[-1] > df['high'].iloc[-2]:
                        risk = saldo * risk_per_trade
                        stop_loss = df['low'].iloc[-3] - (atr * atr_multiplier)
                        take_profit = df['high'].iloc[-2] + (trade_risk_reward * (df['high'].iloc[-2] - stop_loss))
                        qty = round(risk / (df['high'].iloc[-2] - stop_loss), 3)
                        qty = max(qty, min_qty)

                        abre_trade(cripto, 'Buy', qty, stop_loss, take_profit)
                        estado_de_trade = 'LONG'
                        print(f'Long trade placed at {df["high"].iloc[-2]} with TP {take_profit} and SL {stop_loss}')

            elif trend == 'DOWN':
                if df['close'].iloc[-2] < df['EMA_9'].iloc[-2] < df['EMA_21'].iloc[-2]:
                    if df['low'].iloc[-1] < df['low'].iloc[-2]:
                        risk = saldo * risk_per_trade
                        stop_loss = df['high'].iloc[-3] + (atr * atr_multiplier)
                        take_profit = df['low'].iloc[-2] - (trade_risk_reward * (stop_loss - df['low'].iloc[-2]))
                        qty = round(risk / (stop_loss - df['low'].iloc[-2]), 3)
                        qty = max(qty, min_qty)

                        abre_trade(cripto, 'Sell', qty, stop_loss, take_profit)
                        estado_de_trade = 'SHORT'
                        print(f'Short trade placed at {df["low"].iloc[-2]} with TP {take_profit} and SL {stop_loss}')

    except Exception as e:
        print(f'Error: {e}')
    
    time.sleep(0.5)
