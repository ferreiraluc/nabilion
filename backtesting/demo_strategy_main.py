# demo_strategy_main.py - Estratégia Quantitativa Completa para Demo
from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from demo_funcoes_bybit import *  # Funções adaptadas para demo
from utilidades import quantidade_cripto_para_operar
from dotenv import load_dotenv
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo_quantitative_strategy.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

API_KEY = os.getenv('BYBIT_DEMO_KEY')
SECRET_KEY = os.getenv('BYBIT_DEMO_SECRET')

if not API_KEY or not SECRET_KEY:
    logging.error("🔑 Chaves de API não encontradas! Verifique seu arquivo .env.")
    raise ValueError("Chaves de API não configuradas corretamente.")

# Cliente demo
cliente = HTTP(
    testnet=True,
    demo=True,  # CRUCIAL para demo
    api_key=API_KEY,
    api_secret=SECRET_KEY,
    log_requests=True
)

# ===== CONFIGURAÇÕES DE TRADING ADAPTADAS PARA DEMO =====
cripto = 'XRPUSDT'  # XRP é boa para demo (preço baixo, boa liquidez)
tempo_grafico = '15'
qtd_velas_stop = 17
risco_retorno = 2.5  # R:R mais conservador para demo
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 1  # SEM alavancagem na demo

# ===== PARÂMETROS QUANTITATIVOS =====
tf_principal = '15'
tf_confirmacao = '60'

# Configurações de filtros
rsi_periodo = 14
adx_periodo = 14
cci_periodo = 20
vwap_periodo = 20
volume_ma_periodo = 20

# Thresholds mais conservadores para demo
rsi_oversold = 30
rsi_overbought = 70
adx_forte = 20  # Menos restritivo
cci_extremo = 100
volume_threshold = 1.3  # Menos restritivo

# Sistema de Score adaptado para demo
score_minimo_entrada = 5  # Menor para ter mais oportunidades na demo
score_maximo = 10

logging.info('🚀 Bot Quantitativo Demo iniciado')
logging.info(f'Cripto: {cripto}')
logging.info(f'Timeframe Principal: {tf_principal}')
logging.info(f'Timeframe Confirmação: {tf_confirmacao}')
logging.info(f'Score Mínimo: {score_minimo_entrada}/{score_maximo}')
logging.info(f'Risco/Retorno: {risco_retorno}')

# ===== INDICADORES QUANTITATIVOS (ADAPTADOS) =====
def calcular_atr(df, periodo=14):
    """Calcula Average True Range com tratamento de erro"""
    try:
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift())
        df['low_close'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['ATR'] = df['tr'].rolling(window=periodo).mean()
        df['ATR'] = df['ATR'].fillna(method='bfill')  # Preencher NaN
        return df
    except Exception as e:
        logging.error(f"Erro no ATR: {e}")
        df['ATR'] = df['close'] * 0.02  # 2% como fallback
        return df

def calcular_adx(df, periodo=14):
    """ADX simplificado para demo"""
    try:
        df['high_diff'] = df['high'].diff()
        df['low_diff'] = df['low'].diff()
        
        df['plus_dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
        df['minus_dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
        
        # Simplificado para evitar divisão por zero
        df['plus_di'] = df['plus_dm'].rolling(window=periodo).mean() * 100
        df['minus_di'] = df['minus_dm'].rolling(window=periodo).mean() * 100
        
        df['dx'] = abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'] + 0.001) * 100
        df['ADX'] = df['dx'].rolling(window=periodo).mean()
        df['ADX'] = df['ADX'].fillna(20)  # Valor neutro como fallback
        
        return df
    except Exception as e:
        logging.error(f"Erro no ADX: {e}")
        df['ADX'] = 25  # Valor padrão
        return df

def calcular_cci(df, periodo=20):
    """CCI simplificado"""
    try:
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=periodo).mean()
        mad = tp.rolling(window=periodo).std()
        df['CCI'] = (tp - sma_tp) / (0.015 * mad)
        df['CCI'] = df['CCI'].fillna(0)
        return df
    except Exception as e:
        logging.error(f"Erro no CCI: {e}")
        df['CCI'] = 0
        return df

def calcular_vwap(df, periodo=20):
    """VWAP simplificado"""
    try:
        df['vwap_num'] = (df['close'] * df['volume']).rolling(window=periodo).sum()
        df['vwap_den'] = df['volume'].rolling(window=periodo).sum()
        df['VWAP'] = df['vwap_num'] / (df['vwap_den'] + 0.001)
        df['VWAP'] = df['VWAP'].fillna(df['close'])
        return df
    except Exception as e:
        logging.error(f"Erro no VWAP: {e}")
        df['VWAP'] = df['close']
        return df

def calcular_williams_r(df, periodo=14):
    """Williams %R"""
    try:
        highest_high = df['high'].rolling(window=periodo).max()
        lowest_low = df['low'].rolling(window=periodo).min()
        range_hl = highest_high - lowest_low + 0.0001  # Evitar divisão por zero
        df['Williams_R'] = -100 * ((highest_high - df['close']) / range_hl)
        df['Williams_R'] = df['Williams_R'].fillna(-50)
        return df
    except Exception as e:
        logging.error(f"Erro no Williams %R: {e}")
        df['Williams_R'] = -50
        return df

def calcular_momentum(df, periodo=10):
    """Momentum"""
    try:
        df['Momentum'] = (df['close'] / df['close'].shift(periodo)) * 100
        df['Momentum'] = df['Momentum'].fillna(100)
        return df
    except Exception as e:
        logging.error(f"Erro no Momentum: {e}")
        df['Momentum'] = 100
        return df

def buscar_dados_multi_timeframe_demo(cripto, tf_principal, tf_confirmacao, emas):
    """Busca dados multi-timeframe da API demo"""
    try:
        # Dados principais
        df_principal = busca_velas(cripto, tf_principal, emas)
        
        # Dados de confirmação via API demo
        klines_conf = cliente.get_kline(
            category="linear",
            symbol=cripto,
            interval=tf_confirmacao,
            limit=100
        )
        
        # Processar dados de confirmação
        data_conf = []
        for kline in reversed(klines_conf['result']['list']):
            data_conf.append({
                'open_time': pd.to_datetime(int(kline[0]), unit='ms'),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        df_confirmacao = pd.DataFrame(data_conf)
        
        # Adicionar EMAs ao timeframe de confirmação
        df_confirmacao[f'EMA_{emas[0]}'] = df_confirmacao['close'].ewm(span=emas[0]).mean()
        df_confirmacao[f'EMA_{emas[1]}'] = df_confirmacao['close'].ewm(span=emas[1]).mean()
        df_confirmacao['EMA_200'] = df_confirmacao['close'].ewm(span=200).mean()
        
        return df_principal, df_confirmacao
        
    except Exception as e:
        logging.error(f'Erro ao buscar dados multi-timeframe: {e}')
        return None, None

def calcular_indicadores_quantitativos_demo(df):
    """Calcula todos os indicadores com tratamento de erro"""
    try:
        # RSI básico
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=rsi_periodo).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=rsi_periodo).mean()
        rs = gain / (loss + 0.0001)  # Evitar divisão por zero
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50)
        
        # Volume EMA
        df['Volume_EMA_20'] = df['volume'].ewm(span=volume_ma_periodo).mean()
        
        # Indicadores avançados
        df = calcular_atr(df, 14)
        df = calcular_adx(df, adx_periodo)
        df = calcular_cci(df, cci_periodo)
        df = calcular_vwap(df, vwap_periodo)
        df = calcular_momentum(df, 10)
        df = calcular_williams_r(df, 14)
        
        # Preencher qualquer NaN restante
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        return df
        
    except Exception as e:
        logging.error(f'Erro ao calcular indicadores: {e}')
        return df

def sistema_score_quantitativo_demo(df_principal, df_confirmacao, direcao='compra'):
    """Sistema de score adaptado para demo"""
    score = 0
    detalhes_score = []
    
    if len(df_principal) < 30 or len(df_confirmacao) < 10:  # Menos restritivo
        return 0, ["Dados insuficientes"]
    
    try:
        ultima_vela = df_principal.iloc[-1]
        ultima_vela_conf = df_confirmacao.iloc[-1]
        
        if direcao == 'compra':
            # 1. Tendência de fundo (2 pontos)
            if (ultima_vela_conf[f'EMA_{ema_rapida}'] > ultima_vela_conf[f'EMA_{ema_lenta}'] and
                ultima_vela_conf[f'EMA_{ema_lenta}'] > ultima_vela_conf['EMA_200']):
                score += 2
                detalhes_score.append("✓ Tendência alta confirmada")
            
            # 2. Alinhamento EMAs (1 ponto)
            if (ultima_vela[f'EMA_{ema_rapida}'] > ultima_vela[f'EMA_{ema_lenta}'] and
                ultima_vela['close'] > ultima_vela[f'EMA_{ema_lenta}']):
                score += 1
                detalhes_score.append("✓ EMAs alinhadas")
            
            # 3. RSI favorável (1 ponto)
            if rsi_oversold <= ultima_vela['RSI'] <= rsi_overbought:
                score += 1
                detalhes_score.append(f"✓ RSI: {ultima_vela['RSI']:.1f}")
            
            # 4. ADX (1 ponto)
            if ultima_vela['ADX'] >= adx_forte:
                score += 1
                detalhes_score.append(f"✓ ADX: {ultima_vela['ADX']:.1f}")
            
            # 5. Volume (1 ponto)
            if ultima_vela['volume'] > ultima_vela['Volume_EMA_20'] * volume_threshold:
                score += 1
                detalhes_score.append("✓ Volume alto")
            
            # 6. VWAP (1 ponto)
            if ultima_vela['close'] > ultima_vela['VWAP']:
                score += 1
                detalhes_score.append("✓ Acima VWAP")
            
            # 7. CCI (1 ponto)
            if ultima_vela['CCI'] > -cci_extremo:
                score += 1
                detalhes_score.append("✓ CCI favorável")
            
            # 8. Williams %R (1 ponto)
            if -80 <= ultima_vela['Williams_R'] <= -20:
                score += 1
                detalhes_score.append("✓ Williams favorável")
            
            # 9. Momentum (1 ponto)
            if ultima_vela['Momentum'] > 100:
                score += 1
                detalhes_score.append("✓ Momentum positivo")
        
        else:  # venda
            # Lógica invertida para venda
            if (ultima_vela_conf[f'EMA_{ema_rapida}'] < ultima_vela_conf[f'EMA_{ema_lenta}'] and
                ultima_vela_conf[f'EMA_{ema_lenta}'] < ultima_vela_conf['EMA_200']):
                score += 2
                detalhes_score.append("✓ Tendência baixa confirmada")
            
            if (ultima_vela[f'EMA_{ema_rapida}'] < ultima_vela[f'EMA_{ema_lenta}'] and
                ultima_vela['close'] < ultima_vela[f'EMA_{ema_lenta}']):
                score += 1
                detalhes_score.append("✓ EMAs alinhadas baixa")
            
            if rsi_oversold <= ultima_vela['RSI'] <= rsi_overbought:
                score += 1
                detalhes_score.append(f"✓ RSI: {ultima_vela['RSI']:.1f}")
            
            if ultima_vela['ADX'] >= adx_forte:
                score += 1
                detalhes_score.append(f"✓ ADX: {ultima_vela['ADX']:.1f}")
            
            if ultima_vela['volume'] > ultima_vela['Volume_EMA_20'] * volume_threshold:
                score += 1
                detalhes_score.append("✓ Volume alto")
            
            if ultima_vela['close'] < ultima_vela['VWAP']:
                score += 1
                detalhes_score.append("✓ Abaixo VWAP")
            
            if ultima_vela['CCI'] < cci_extremo:
                score += 1
                detalhes_score.append("✓ CCI favorável")
            
            if -80 <= ultima_vela['Williams_R'] <= -20:
                score += 1
                detalhes_score.append("✓ Williams favorável")
            
            if ultima_vela['Momentum'] < 100:
                score += 1
                detalhes_score.append("✓ Momentum negativo")
        
        return score, detalhes_score
        
    except Exception as e:
        logging.error(f'Erro no sistema de score: {e}')
        return 0, [f"Erro: {str(e)}"]

def calcular_stop_dinamico_demo(df, direcao, preco_entrada, atr_atual):
    """Stop loss dinâmico adaptado para demo"""
    try:
        # Stop baseado em ATR (mais conservador para demo)
        stop_atr = atr_atual * 2.0  # Menos agressivo
        
        # Stop mínimo de 0.5% para demo
        stop_minimo = preco_entrada * 0.005
        
        # Stop máximo de 2% para demo (limitar risco)
        stop_maximo = preco_entrada * 0.02
        
        stop_final = max(stop_minimo, min(stop_atr, stop_maximo))
        
        return stop_final
        
    except Exception as e:
        logging.error(f'Erro no stop dinâmico: {e}')
        return preco_entrada * 0.01  # 1% como fallback

def verificar_trade_aberto_demo():
    """Wrapper para verificar trade com retry"""
    for tentativa in range(3):
        try:
            return tem_trade_aberto(cripto)
        except Exception as e:
            logging.error(f'Erro ao verificar trade (tentativa {tentativa + 1}): {e}')
            if tentativa < 2:
                time.sleep(2)
    return EstadoDeTrade.DE_FORA, 0, 0, 0

# ===== LOOP PRINCIPAL DEMO =====
def main_demo():
    """Loop principal adaptado para demo"""
    
    # Verificação inicial
    try:
        saldo_inicial = saldo_da_conta()
        logging.info(f"💰 Saldo inicial demo: ${saldo_inicial:.2f}")
        
        if saldo_inicial < 100:
            logging.warning("⚠️ Saldo demo muito baixo! Considere resetar a conta demo.")
        
    except Exception as e:
        logging.error(f"❌ Erro ao verificar saldo inicial: {e}")
        return
    
    # Estado inicial
    estado_de_trade, preco_entrada, preco_stop, preco_alvo = verificar_trade_aberto_demo()
    logging.info(f'Estado inicial: {estado_de_trade}')
    
    vela_fechou_trade = None
    contador_ciclos = 0
    
    while True:
        try:
            contador_ciclos += 1
            logging.info(f"\n🔄 Ciclo #{contador_ciclos} - {datetime.now().strftime('%H:%M:%S')}")
            
            # Buscar dados
            df_principal, df_confirmacao = buscar_dados_multi_timeframe_demo(
                cripto, tf_principal, tf_confirmacao, emas
            )
            
            if df_principal is None or df_confirmacao is None:
                logging.warning('⚠️ Erro ao buscar dados. Aguardando...')
                time.sleep(30)
                continue
            
            # Calcular indicadores
            df_principal = calcular_indicadores_quantitativos_demo(df_principal)
            
            if len(df_principal) < 30:
                logging.warning('⚠️ Dados insuficientes. Aguardando...')
                time.sleep(30)
                continue
            
            preco_atual = df_principal['close'].iloc[-1]
            logging.info(f"💹 Preço atual {cripto}: ${preco_atual:.4f}")
            
            # ===== GESTÃO DE POSIÇÕES =====
            if estado_de_trade == EstadoDeTrade.COMPRADO:
                logging.info('📈 Posição COMPRADA - Monitorando...')
                
                # Atualizar preços de stop/target
                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto_demo()
                
                # Breakeven management
                preco_parcial_compra = preco_entrada * 1.005  # 0.5% para demo
                stop_breakeven_compra(cripto, preco_entrada, preco_parcial_compra, estado_de_trade, preco_atual)
                
                # Verificar saída
                if df_principal['high'].iloc[-1] >= preco_alvo_atual and preco_alvo_atual > 0:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    lucro_pct = ((preco_alvo_atual - preco_entrada) / preco_entrada) * 100
                    logging.info(f"🎯 ALVO ATINGIDO! Lucro: {lucro_pct:.2f}%")
                    logging.info('-' * 50)
                elif df_principal['low'].iloc[-1] <= preco_stop_atual and preco_stop_atual > 0:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    perda_pct = ((preco_entrada - preco_stop_atual) / preco_entrada) * 100
                    logging.info(f"🛑 STOP LOSS! Perda: {perda_pct:.2f}%")
                    logging.info('-' * 50)
                elif verificar_trade_aberto_demo()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    logging.info('🔄 Trade fechado manualmente')
                    logging.info('-' * 50)
            
            elif estado_de_trade == EstadoDeTrade.VENDIDO:
                logging.info('📉 Posição VENDIDA - Monitorando...')
                
                # Atualizar preços de stop/target
                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto_demo()
                
                # Breakeven management
                preco_parcial_venda = preco_entrada * 0.995  # 0.5% para demo
                stop_breakeven_venda(cripto, preco_entrada, preco_parcial_venda, estado_de_trade, preco_atual)
                
                # Verificar saída
                if df_principal['low'].iloc[-1] <= preco_alvo_atual and preco_alvo_atual > 0:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    lucro_pct = ((preco_entrada - preco_alvo_atual) / preco_entrada) * 100
                    logging.info(f"🎯 ALVO ATINGIDO! Lucro: {lucro_pct:.2f}%")
                    logging.info('-' * 50)
                elif df_principal['high'].iloc[-1] >= preco_stop_atual and preco_stop_atual > 0:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    perda_pct = ((preco_stop_atual - preco_entrada) / preco_entrada) * 100
                    logging.info(f"🛑 STOP LOSS! Perda: {perda_pct:.2f}%")
                    logging.info('-' * 50)
                elif verificar_trade_aberto_demo()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    logging.info('🔄 Trade fechado manualmente')
                    logging.info('-' * 50)
            
            # ===== BUSCA POR NOVAS ENTRADAS =====
            elif estado_de_trade == EstadoDeTrade.DE_FORA and df_principal['open_time'].iloc[-1] != vela_fechou_trade:
                logging.info('🔍 Analisando oportunidades...')
                
                # Obter dados para cálculos
                try:
                    saldo = saldo_da_conta() * alavancagem
                    qtidade_minima = quantidade_minima_para_operar(cripto)
                    qtd_cripto = quantidade_cripto_para_operar(saldo, qtidade_minima, preco_atual)
                    atr_atual = df_principal['ATR'].iloc[-1]
                    
                    logging.info(f"💰 Saldo disponível: ${saldo:.2f}")
                    logging.info(f"📊 ATR atual: {atr_atual:.6f}")
                    
                except Exception as e:
                    logging.error(f"❌ Erro ao obter dados de conta: {e}")
                    time.sleep(30)
                    continue
                
                # ===== ANÁLISE QUANTITATIVA =====
                score_compra, detalhes_compra = sistema_score_quantitativo_demo(
                    df_principal, df_confirmacao, 'compra'
                )
                score_venda, detalhes_venda = sistema_score_quantitativo_demo(
                    df_principal, df_confirmacao, 'venda'
                )
                
                logging.info(f'📊 Score Compra: {score_compra}/{score_maximo}')
                logging.info(f'📊 Score Venda: {score_venda}/{score_maximo}')
                
                # ===== ENTRADA EM COMPRA =====
                if score_compra >= score_minimo_entrada and score_compra > score_venda:
                    preco_entrada = preco_atual
                    
                    # Stop loss dinâmico
                    stop_distance = calcular_stop_dinamico_demo(df_principal, 'compra', preco_entrada, atr_atual)
                    preco_stop = preco_entrada - stop_distance
                    preco_alvo = preco_entrada + (stop_distance * risco_retorno)
                    
                    # Validar preços
                    if preco_stop > 0 and preco_alvo > preco_entrada:
                        try:
                            # Calcular quantidade para demo (máximo $20 por trade)
                            valor_trade = min(saldo * 0.01, 20)
                            qtd_ajustada = valor_trade / preco_entrada
                            
                            # Arredondar para quantidade mínima
                            if 'XRP' in cripto:
                                qtd_ajustada = round(qtd_ajustada, 1)
                            else:
                                qtd_ajustada = round(qtd_ajustada, 3)
                            
                            if qtd_ajustada >= qtidade_minima:
                                # Executar ordem
                                order = abre_compra(cripto, qtd_ajustada, preco_stop, preco_alvo)
                                
                                if order:
                                    estado_de_trade = EstadoDeTrade.COMPRADO
                                    
                                    logging.info(f"\n🚀 COMPRA EXECUTADA!")
                                    logging.info(f"📈 Quantidade: {qtd_ajustada} {cripto}")
                                    logging.info(f"💵 Valor: ${valor_trade:.2f}")
                                    logging.info(f"🔹 Entrada: ${preco_entrada:.4f}")
                                    logging.info(f"🛑 Stop: ${preco_stop:.4f}")
                                    logging.info(f"🎯 Alvo: ${preco_alvo:.4f}")
                                    logging.info(f"📊 Score: {score_compra}/{score_maximo}")
                                    logging.info("✅ Critérios:")
                                    for detalhe in detalhes_compra:
                                        logging.info(f"   {detalhe}")
                                    logging.info('-' * 50)
                                    
                                    # Configurar take profit parcial
                                    try:
                                        abre_parcial_compra(cripto, qtd_ajustada, preco_entrada)
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro no take profit parcial: {e}")
                            else:
                                logging.warning(f"⚠️ Quantidade muito pequena: {qtd_ajustada}")
                                
                        except Exception as e:
                            logging.error(f'❌ Erro ao executar compra: {e}')
                    else:
                        logging.warning("⚠️ Preços de stop/target inválidos")
                
                # ===== ENTRADA EM VENDA =====
                elif score_venda >= score_minimo_entrada and score_venda > score_compra:
                    preco_entrada = preco_atual
                    
                    # Stop loss dinâmico
                    stop_distance = calcular_stop_dinamico_demo(df_principal, 'venda', preco_entrada, atr_atual)
                    preco_stop = preco_entrada + stop_distance
                    preco_alvo = preco_entrada - (stop_distance * risco_retorno)
                    
                    # Validar preços
                    if preco_stop > preco_entrada and preco_alvo > 0:
                        try:
                            # Calcular quantidade para demo
                            valor_trade = min(saldo * 0.01, 20)
                            qtd_ajustada = valor_trade / preco_entrada
                            
                            # Arredondar para quantidade mínima
                            if 'XRP' in cripto:
                                qtd_ajustada = round(qtd_ajustada, 1)
                            else:
                                qtd_ajustada = round(qtd_ajustada, 3)
                            
                            if qtd_ajustada >= qtidade_minima:
                                # Executar ordem
                                order = abre_venda(cripto, qtd_ajustada, preco_stop, preco_alvo)
                                
                                if order:
                                    estado_de_trade = EstadoDeTrade.VENDIDO
                                    
                                    logging.info(f"\n🔻 VENDA EXECUTADA!")
                                    logging.info(f"📉 Quantidade: {qtd_ajustada} {cripto}")
                                    logging.info(f"💵 Valor: ${valor_trade:.2f}")
                                    logging.info(f"🔹 Entrada: ${preco_entrada:.4f}")
                                    logging.info(f"🛑 Stop: ${preco_stop:.4f}")
                                    logging.info(f"🎯 Alvo: ${preco_alvo:.4f}")
                                    logging.info(f"📊 Score: {score_venda}/{score_maximo}")
                                    logging.info("✅ Critérios:")
                                    for detalhe in detalhes_venda:
                                        logging.info(f"   {detalhe}")
                                    logging.info('-' * 50)
                                    
                                    # Configurar take profit parcial
                                    try:
                                        abre_parcial_venda(cripto, qtd_ajustada, preco_entrada)
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro no take profit parcial: {e}")
                            else:
                                logging.warning(f"⚠️ Quantidade muito pequena: {qtd_ajustada}")
                                
                        except Exception as e:
                            logging.error(f'❌ Erro ao executar venda: {e}')
                    else:
                        logging.warning("⚠️ Preços de stop/target inválidos")
                
                else:
                    logging.info(f"❌ Scores insuficientes (mín: {score_minimo_entrada})")
                    if score_compra > 0:
                        logging.info("   Top critérios compra:")
                        for detalhe in detalhes_compra[:3]:
                            logging.info(f"   {detalhe}")
                    if score_venda > 0:
                        logging.info("   Top critérios venda:")
                        for detalhe in detalhes_venda[:3]:
                            logging.info(f"   {detalhe}")
            
            # ===== STATUS REPORT A CADA 10 CICLOS =====
            if contador_ciclos % 10 == 0:
                try:
                    saldo_atual = saldo_da_conta()
                    variacao = ((saldo_atual - saldo_inicial) / saldo_inicial) * 100
                    logging.info(f"\n📊 RELATÓRIO (Ciclo {contador_ciclos})")
                    logging.info(f"💰 Saldo atual: ${saldo_atual:.2f}")
                    logging.info(f"📈 Variação: {variacao:+.2f}%")
                    logging.info(f"🕐 Tempo ativo: {contador_ciclos * 30 / 60:.1f} min")
                except Exception as e:
                    logging.error(f"❌ Erro no relatório: {e}")
        
        except Exception as e:
            logging.error(f'❌ Erro no loop principal: {e}')
        
        # Aguardar próxima análise (30 segundos para demo)
        time.sleep(30)

if __name__ == "__main__":
    try:
        logging.info("🚀 Iniciando estratégia quantitativa demo...")
        main_demo()
    except KeyboardInterrupt:
        logging.info("\n🛑 Bot demo interrompido pelo usuário")
    except Exception as e:
        logging.error(f"\n❌ Erro crítico: {e}")
        logging.info("🔄 Tentando reiniciar em 60 segundos...")
        time.sleep(60)
        main_demo()