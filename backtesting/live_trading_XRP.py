from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from funcoes_bybit import busca_velas, tem_trade_aberto, saldo_da_conta, quantidade_minima_para_operar, abre_compra, abre_venda, abre_parcial_venda, abre_parcial_compra, stop_breakeven_compra, stop_breakeven_venda
from utilidades import quantidade_cripto_para_operar
import time
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

load_dotenv()

API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')

cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

# ===== CONFIGURAÇÕES APRIMORADAS =====
cripto = 'XRPUSDT'
tempo_grafico = '15'
qtd_velas_stop = 17
risco_retorno = 3.1
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2

# ===== NOVOS PARÂMETROS QUANTITATIVOS =====
# Períodos para análise multi-timeframe
tf_principal = '15'  # Timeframe principal
tf_confirmacao = '60'  # Timeframe de confirmação (1h)

# Configurações de filtros
rsi_periodo = 14
adx_periodo = 14
cci_periodo = 20
vwap_periodo = 20
volume_ma_periodo = 20

# Thresholds para sinais
rsi_oversold = 35
rsi_overbought = 65
adx_forte = 25
cci_extremo = 100
volume_threshold = 1.5  # Volume deve ser 1.5x maior que a média

# Configurações de Score System
score_minimo_entrada = 6  # Mínimo para entrada
score_maximo = 10  # Score máximo possível

print('Bot Quantitativo Aprimorado iniciado', flush=True)
print(f'Cripto: {cripto}', flush=True)
print(f'Timeframe Principal: {tf_principal}', flush=True)
print(f'Timeframe Confirmação: {tf_confirmacao}', flush=True)
print(f'Score Mínimo para Entrada: {score_minimo_entrada}/{score_maximo}', flush=True)

# ===== INDICADORES QUANTITATIVOS APRIMORADOS =====
def calcular_atr(df, periodo=14):
    """Calcula Average True Range otimizado"""
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

def calcular_adx(df, periodo=14):
    """Calcula Average Directional Index - força da tendência"""
    df['high_diff'] = df['high'].diff()
    df['low_diff'] = df['low'].diff()
    
    df['plus_dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
    df['minus_dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
    
    df['plus_di'] = 100 * (df['plus_dm'].rolling(window=periodo).sum() / df['ATR'].rolling(window=periodo).sum())
    df['minus_di'] = 100 * (df['minus_dm'].rolling(window=periodo).sum() / df['ATR'].rolling(window=periodo).sum())
    
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['ADX'] = df['dx'].rolling(window=periodo).mean()
    
    return df

def calcular_cci(df, periodo=20):
    """Calcula Commodity Channel Index - identificação de extremos"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(window=periodo).mean()
    mad = tp.rolling(window=periodo).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    df['CCI'] = (tp - sma_tp) / (0.015 * mad)
    return df

def calcular_vwap(df, periodo=20):
    """Calcula Volume Weighted Average Price - preço médio ponderado por volume"""
    df['vwap_num'] = (df['close'] * df['volume']).rolling(window=periodo).sum()
    df['vwap_den'] = df['volume'].rolling(window=periodo).sum()
    df['VWAP'] = df['vwap_num'] / df['vwap_den']
    return df

def calcular_momentum(df, periodo=10):
    """Calcula Momentum - velocidade da mudança de preço"""
    df['Momentum'] = df['close'] / df['close'].shift(periodo) * 100
    return df

def calcular_williams_r(df, periodo=14):
    """Calcula Williams %R - oscilador de momentum"""
    highest_high = df['high'].rolling(window=periodo).max()
    lowest_low = df['low'].rolling(window=periodo).min()
    df['Williams_R'] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
    return df

def buscar_dados_multi_timeframe(cripto, tf_principal, tf_confirmacao, emas):
    """Busca dados em múltiplos timeframes para análise confirmatória"""
    try:
        # Dados do timeframe principal
        df_principal = busca_velas(cripto, tf_principal, emas)
        
        # Dados do timeframe de confirmação
        resposta_confirmacao = cliente.get_kline(symbol=cripto, interval=tf_confirmacao, limit=100)
        velas_confirmacao = resposta_confirmacao['result']['list'][::-1]
        
        colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
        df_confirmacao = pd.DataFrame(velas_confirmacao, columns=colunas)
        
        # Converter tipos
        df_confirmacao['open_time'] = pd.to_datetime(df_confirmacao['open_time'].astype(np.int64), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_confirmacao[col] = df_confirmacao[col].astype(float)
        
        # Adicionar EMAs ao timeframe de confirmação
        df_confirmacao[f'EMA_{emas[0]}'] = df_confirmacao['close'].ewm(span=emas[0], adjust=False).mean()
        df_confirmacao[f'EMA_{emas[1]}'] = df_confirmacao['close'].ewm(span=emas[1], adjust=False).mean()
        df_confirmacao['EMA_200'] = df_confirmacao['close'].ewm(span=200, adjust=False).mean()
        
        return df_principal, df_confirmacao
        
    except Exception as e:
        print(f'Erro ao buscar dados multi-timeframe: {e}', flush=True)
        return None, None

def calcular_indicadores_quantitativos(df):
    """Calcula todos os indicadores quantitativos"""
    try:
        # Indicadores básicos (já existentes)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_periodo).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_periodo).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['Volume_EMA_20'] = df['volume'].ewm(span=volume_ma_periodo, adjust=False).mean()
        
        # Novos indicadores quantitativos
        df = calcular_atr(df, 14)
        df = calcular_adx(df, adx_periodo)
        df = calcular_cci(df, cci_periodo)
        df = calcular_vwap(df, vwap_periodo)
        df = calcular_momentum(df, 10)
        df = calcular_williams_r(df, 14)
        
        return df
        
    except Exception as e:
        print(f'Erro ao calcular indicadores: {e}', flush=True)
        return df

def sistema_score_quantitativo(df_principal, df_confirmacao, direcao='compra'):
    """Sistema de pontuação quantitativa para confirmar sinais"""
    score = 0
    detalhes_score = []
    
    if len(df_principal) < 50 or len(df_confirmacao) < 20:
        return 0, ["Dados insuficientes"]
    
    try:
        # Dados da última vela
        ultima_vela = df_principal.iloc[-1]
        penultima_vela = df_principal.iloc[-2]
        ultima_vela_conf = df_confirmacao.iloc[-1]
        
        if direcao == 'compra':
            # 1. Tendência de fundo (timeframe maior) - 2 pontos
            if (ultima_vela_conf[f'EMA_{ema_rapida}'] > ultima_vela_conf[f'EMA_{ema_lenta}'] and
                ultima_vela_conf[f'EMA_{ema_lenta}'] > ultima_vela_conf['EMA_200']):
                score += 2
                detalhes_score.append("✓ Tendência de alta confirmada no TF maior")
            
            # 2. Alinhamento de EMAs no TF principal - 1 ponto
            if (ultima_vela[f'EMA_{ema_rapida}'] > ultima_vela[f'EMA_{ema_lenta}'] and
                ultima_vela[f'EMA_{ema_lenta}'] > ultima_vela['EMA_200']):
                score += 1
                detalhes_score.append("✓ EMAs alinhadas para alta")
            
            # 3. RSI em zona favorável - 1 ponto
            if rsi_oversold <= ultima_vela['RSI'] <= 70:
                score += 1
                detalhes_score.append(f"✓ RSI favorável: {ultima_vela['RSI']:.1f}")
            
            # 4. ADX confirmando força da tendência - 1 ponto
            if ultima_vela['ADX'] >= adx_forte:
                score += 1
                detalhes_score.append(f"✓ ADX forte: {ultima_vela['ADX']:.1f}")
            
            # 5. Volume significativo - 1 ponto
            if ultima_vela['volume'] > ultima_vela['Volume_EMA_20'] * volume_threshold:
                score += 1
                detalhes_score.append("✓ Volume acima da média")
            
            # 6. Preço acima do VWAP - 1 ponto
            if ultima_vela['close'] > ultima_vela['VWAP']:
                score += 1
                detalhes_score.append("✓ Preço acima do VWAP")
            
            # 7. CCI não em extremo negativo - 1 ponto
            if ultima_vela['CCI'] > -cci_extremo:
                score += 1
                detalhes_score.append("✓ CCI não em extremo negativo")
            
            # 8. Williams %R em zona de recuperação - 1 ponto
            if -80 <= ultima_vela['Williams_R'] <= -20:
                score += 1
                detalhes_score.append("✓ Williams %R em zona favorável")
            
            # 9. Momentum positivo - 1 ponto
            if ultima_vela['Momentum'] > 100:
                score += 1
                detalhes_score.append("✓ Momentum positivo")
            
        else:  # venda
            # 1. Tendência de fundo (timeframe maior) - 2 pontos
            if (ultima_vela_conf[f'EMA_{ema_rapida}'] < ultima_vela_conf[f'EMA_{ema_lenta}'] and
                ultima_vela_conf[f'EMA_{ema_lenta}'] < ultima_vela_conf['EMA_200']):
                score += 2
                detalhes_score.append("✓ Tendência de baixa confirmada no TF maior")
            
            # 2. Alinhamento de EMAs no TF principal - 1 ponto
            if (ultima_vela[f'EMA_{ema_rapida}'] < ultima_vela[f'EMA_{ema_lenta}'] and
                ultima_vela[f'EMA_{ema_lenta}'] < ultima_vela['EMA_200']):
                score += 1
                detalhes_score.append("✓ EMAs alinhadas para baixa")
            
            # 3. RSI em zona favorável - 1 ponto
            if 30 <= ultima_vela['RSI'] <= rsi_overbought:
                score += 1
                detalhes_score.append(f"✓ RSI favorável: {ultima_vela['RSI']:.1f}")
            
            # 4. ADX confirmando força da tendência - 1 ponto
            if ultima_vela['ADX'] >= adx_forte:
                score += 1
                detalhes_score.append(f"✓ ADX forte: {ultima_vela['ADX']:.1f}")
            
            # 5. Volume significativo - 1 ponto
            if ultima_vela['volume'] > ultima_vela['Volume_EMA_20'] * volume_threshold:
                score += 1
                detalhes_score.append("✓ Volume acima da média")
            
            # 6. Preço abaixo do VWAP - 1 ponto
            if ultima_vela['close'] < ultima_vela['VWAP']:
                score += 1
                detalhes_score.append("✓ Preço abaixo do VWAP")
            
            # 7. CCI não em extremo positivo - 1 ponto
            if ultima_vela['CCI'] < cci_extremo:
                score += 1
                detalhes_score.append("✓ CCI não em extremo positivo")
            
            # 8. Williams %R em zona de distribuição - 1 ponto
            if -80 <= ultima_vela['Williams_R'] <= -20:
                score += 1
                detalhes_score.append("✓ Williams %R em zona favorável")
            
            # 9. Momentum negativo - 1 ponto
            if ultima_vela['Momentum'] < 100:
                score += 1
                detalhes_score.append("✓ Momentum negativo")
        
        return score, detalhes_score
        
    except Exception as e:
        print(f'Erro no sistema de score: {e}', flush=True)
        return 0, [f"Erro: {str(e)}"]

def calcular_stop_dinamico(df, direcao, preco_entrada, atr_atual):
    """Calcula stop loss dinâmico baseado em múltiplos fatores"""
    try:
        # Stop baseado em ATR (padrão)
        stop_atr = atr_atual * 2.5
        
        # Stop baseado em suporte/resistência recente
        if direcao == 'compra':
            low_recente = df['low'].tail(10).min()
            stop_sr = preco_entrada - low_recente
        else:
            high_recente = df['high'].tail(10).max()
            stop_sr = high_recente - preco_entrada
        
        # Stop baseado em volatilidade (Williams %R)
        williams_atual = df['Williams_R'].iloc[-1]
        if abs(williams_atual) > 80:  # Alta volatilidade
            stop_volatilidade = stop_atr * 1.5
        else:
            stop_volatilidade = stop_atr * 1.2
        
        # Usar o menor dos stops (mais conservador)
        stop_final = min(stop_atr, stop_sr, stop_volatilidade)
        
        # Não permitir stop menor que 0.5% do preço
        stop_minimo = preco_entrada * 0.005
        stop_final = max(stop_final, stop_minimo)
        
        return stop_final
        
    except Exception as e:
        print(f'Erro ao calcular stop dinâmico: {e}', flush=True)
        return atr_atual * 2  # Fallback

def verificar_trade_aberto():
    """Verifica se há trade aberto com tratamento de erro"""
    for tentativa in range(3):
        try:
            return tem_trade_aberto(cripto)
        except Exception as e:
            print(f'Erro ao verificar trade aberto (tentativa {tentativa + 1}): {e}', flush=True)
            if tentativa < 2:
                time.sleep(2)
    return EstadoDeTrade.DE_FORA, 0, 0, 0

# ===== LOOP PRINCIPAL =====
def main():
    # Inicialização
    estado_de_trade, preco_entrada, preco_stop, preco_alvo = verificar_trade_aberto()
    print(f'Estado inicial: {estado_de_trade}', flush=True)
    
    vela_fechou_trade = None
    
    while True:
        try:
            # Buscar dados multi-timeframe
            df_principal, df_confirmacao = buscar_dados_multi_timeframe(cripto, tf_principal, tf_confirmacao, emas)
            
            if df_principal is None or df_confirmacao is None:
                print('Erro ao buscar dados. Aguardando...', flush=True)
                time.sleep(30)
                continue
            
            # Calcular indicadores quantitativos
            df_principal = calcular_indicadores_quantitativos(df_principal)
            
            # Verificar se há dados suficientes
            if len(df_principal) < 50:
                print('Dados insuficientes. Aguardando...', flush=True)
                time.sleep(30)
                continue
            
            # ===== GESTÃO DE POSIÇÕES ABERTAS =====
            if estado_de_trade == EstadoDeTrade.COMPRADO:
                print('Posição COMPRADA - Monitorando saída...', flush=True)
                
                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto()
                preco_atual = df_principal['close'].iloc[-1]
                
                # Breakeven management
                preco_parcial_compra = preco_entrada * 1.01  # 1% de lucro
                stop_breakeven_compra(cripto, preco_entrada, preco_parcial_compra, estado_de_trade, preco_atual)
                
                # Verificar saída
                if df_principal['high'].iloc[-1] >= preco_alvo_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🎯 ALVO ATINGIDO! Preço: {preco_alvo_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif df_principal['low'].iloc[-1] <= preco_stop_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🛑 STOP LOSS! Preço: {preco_stop_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif verificar_trade_aberto()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print('Trade fechado manualmente', flush=True)
                    print('-' * 50, flush=True)
            
            elif estado_de_trade == EstadoDeTrade.VENDIDO:
                print('Posição VENDIDA - Monitorando saída...', flush=True)
                
                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto()
                preco_atual = df_principal['close'].iloc[-1]
                
                # Breakeven management
                preco_parcial_venda = preco_entrada * 0.99  # 1% de lucro
                stop_breakeven_venda(cripto, preco_entrada, preco_parcial_venda, estado_de_trade, preco_atual)
                
                # Verificar saída
                if df_principal['low'].iloc[-1] <= preco_alvo_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🎯 ALVO ATINGIDO! Preço: {preco_alvo_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif df_principal['high'].iloc[-1] >= preco_stop_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🛑 STOP LOSS! Preço: {preco_stop_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif verificar_trade_aberto()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print('Trade fechado manualmente', flush=True)
                    print('-' * 50, flush=True)
            
            # ===== BUSCA POR NOVAS ENTRADAS =====
            elif estado_de_trade == EstadoDeTrade.DE_FORA and df_principal['open_time'].iloc[-1] != vela_fechou_trade:
                print('Analisando oportunidades de entrada...', flush=True)
                
                # Obter dados para cálculos
                saldo = saldo_da_conta() * alavancagem
                qtidade_minima = quantidade_minima_para_operar(cripto)
                qtd_cripto = quantidade_cripto_para_operar(saldo, qtidade_minima, df_principal['close'].iloc[-1])
                atr_atual = df_principal['ATR'].iloc[-1]
                
                # ===== ANÁLISE QUANTITATIVA PARA COMPRA =====
                score_compra, detalhes_compra = sistema_score_quantitativo(df_principal, df_confirmacao, 'compra')
                
                # ===== ANÁLISE QUANTITATIVA PARA VENDA =====
                score_venda, detalhes_venda = sistema_score_quantitativo(df_principal, df_confirmacao, 'venda')
                
                print(f'📊 Score Compra: {score_compra}/{score_maximo}', flush=True)
                print(f'📊 Score Venda: {score_venda}/{score_maximo}', flush=True)
                
                # ===== ENTRADA EM COMPRA =====
                if score_compra >= score_minimo_entrada and score_compra > score_venda:
                    preco_entrada = df_principal['close'].iloc[-1]
                    
                    # Stop loss dinâmico
                    stop_distance = calcular_stop_dinamico(df_principal, 'compra', preco_entrada, atr_atual)
                    preco_stop = preco_entrada - stop_distance
                    
                    # Take profit baseado no R:R
                    preco_alvo = preco_entrada + (stop_distance * risco_retorno)
                    
                    # Executar ordem
                    try:
                        abre_compra(cripto, qtd_cripto, preco_stop, preco_alvo)
                        estado_de_trade = EstadoDeTrade.COMPRADO
                        
                        print(f"\n🚀 ENTRADA EM COMPRA EXECUTADA!", flush=True)
                        print(f"📈 Preço Entrada: {preco_entrada:.2f}", flush=True)
                        print(f"🛑 Stop Loss: {preco_stop:.2f}", flush=True)
                        print(f"🎯 Take Profit: {preco_alvo:.2f}", flush=True)
                        print(f"📊 Score Final: {score_compra}/{score_maximo}", flush=True)
                        print("✅ Critérios atendidos:", flush=True)
                        for detalhe in detalhes_compra:
                            print(f"   {detalhe}", flush=True)
                        print('-' * 50, flush=True)
                        
                        # Configurar ordem parcial
                        abre_parcial_compra(cripto, qtd_cripto, preco_entrada)
                        
                    except Exception as e:
                        print(f'Erro ao executar compra: {e}', flush=True)
                
                # ===== ENTRADA EM VENDA =====
                elif score_venda >= score_minimo_entrada and score_venda > score_compra:
                    preco_entrada = df_principal['close'].iloc[-1]
                    
                    # Stop loss dinâmico
                    stop_distance = calcular_stop_dinamico(df_principal, 'venda', preco_entrada, atr_atual)
                    preco_stop = preco_entrada + stop_distance
                    
                    # Take profit baseado no R:R
                    preco_alvo = preco_entrada - (stop_distance * risco_retorno)
                    
                    # Executar ordem
                    try:
                        abre_venda(cripto, qtd_cripto, preco_stop, preco_alvo)
                        estado_de_trade = EstadoDeTrade.VENDIDO
                        
                        print(f"\n🔻 ENTRADA EM VENDA EXECUTADA!", flush=True)
                        print(f"📉 Preço Entrada: {preco_entrada:.2f}", flush=True)
                        print(f"🛑 Stop Loss: {preco_stop:.2f}", flush=True)
                        print(f"🎯 Take Profit: {preco_alvo:.2f}", flush=True)
                        print(f"📊 Score Final: {score_venda}/{score_maximo}", flush=True)
                        print("✅ Critérios atendidos:", flush=True)
                        for detalhe in detalhes_venda:
                            print(f"   {detalhe}", flush=True)
                        print('-' * 50, flush=True)
                        
                        # Configurar ordem parcial
                        abre_parcial_venda(cripto, qtd_cripto, preco_entrada)
                        
                    except Exception as e:
                        print(f'Erro ao executar venda: {e}', flush=True)
                
                else:
                    print(f"❌ Scores insuficientes para entrada (mín: {score_minimo_entrada})", flush=True)
                    if score_compra > 0:
                        print("   Critérios de compra:", flush=True)
                        for detalhe in detalhes_compra[:3]:  # Mostrar apenas os principais
                            print(f"   {detalhe}", flush=True)
                    if score_venda > 0:
                        print("   Critérios de venda:", flush=True)
                        for detalhe in detalhes_venda[:3]:  # Mostrar apenas os principais
                            print(f"   {detalhe}", flush=True)
        
        except Exception as e:
            print(f'Erro no loop principal: {e}', flush=True)
        
        # Aguardar próxima análise
        time.sleep(15)  # Análise a cada 15 segundos

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário", flush=True)
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}", flush=True)
        print("Reiniciando em 60 segundos...", flush=True)
        time.sleep(60)
        main()