from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from funcoes_bybit import busca_velas, tem_trade_aberto, saldo_da_conta, quantidade_minima_para_operar, abre_compra, abre_venda, abre_parcial_venda, abre_parcial_compra, stop_breakeven_compra, stop_breakeven_venda
from utilidades import quantidade_cripto_para_operar
from ml_predictor import MLPredictor
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

# ===== CONFIGURAÇÕES =====
cripto = 'XRPUSDT'
tempo_grafico = '15'
qtd_velas_stop = 17
risco_retorno = 3.1
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2

# Multi-timeframe
tf_principal = '15'
tf_confirmacao = '60'

# Indicadores
rsi_periodo = 14
adx_periodo = 14
cci_periodo = 20
vwap_periodo = 20
volume_ma_periodo = 20

# Thresholds
rsi_oversold = 35
rsi_overbought = 65
adx_forte = 25
cci_extremo = 100
volume_threshold = 1.5

# ===== NOVO: CONFIGURAÇÕES CONTEXTUAIS E ML =====
# Sequências de velas
min_velas_sequencia = 5  # Mínimo de velas seguidas para considerar sequência
max_velas_sequencia_permitido = 7  # Não entrar se já tem muitas velas na mesma direção

# Machine Learning
ml_confidence_threshold = 40  # Confiança mínima do ML (0-100%)
ml_retrain_hours = 4  # Retreinar modelo a cada X horas

# Sistema de Score Aprimorado
score_tecnico_max = 10  # Score técnico (original)
score_ml_max = 3  # Score ML (novo)
score_contextual_max = 3  # Score contextual (novo)
score_total_max = 16  # Total possível
score_minimo_entrada = 10  # Mínimo para entrar (mais rigoroso)

print('=' * 60)
print('🤖 Bot Quantitativo com IA INTEGRADA - Iniciado')
print('=' * 60)
print(f'Cripto: {cripto}')
print(f'Timeframe Principal: {tf_principal}')
print(f'Timeframe Confirmação: {tf_confirmacao}')
print(f'Score Mínimo para Entrada: {score_minimo_entrada}/{score_total_max}')
print(f'ML Confidence Threshold: {ml_confidence_threshold}%')
print(f'Filtro de Sequências: máx {max_velas_sequencia_permitido} velas')
print('=' * 60)

# ===== INICIALIZAR ML PREDICTOR =====
ml_predictor = MLPredictor(forecast_horizon=1)
ultimo_treinamento_ml = None

# ===== INDICADORES QUANTITATIVOS =====
def calcular_atr(df, periodo=14):
    """Calcula Average True Range otimizado"""
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

def calcular_adx(df, periodo=14):
    """Calcula Average Directional Index"""
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
    """Calcula Commodity Channel Index"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(window=periodo).mean()
    mad = tp.rolling(window=periodo).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    df['CCI'] = (tp - sma_tp) / (0.015 * mad)
    return df

def calcular_vwap(df, periodo=20):
    """Calcula Volume Weighted Average Price"""
    df['vwap_num'] = (df['close'] * df['volume']).rolling(window=periodo).sum()
    df['vwap_den'] = df['volume'].rolling(window=periodo).sum()
    df['VWAP'] = df['vwap_num'] / df['vwap_den']
    return df

def calcular_momentum(df, periodo=10):
    """Calcula Momentum"""
    df['Momentum'] = df['close'] / df['close'].shift(periodo) * 100
    return df

def calcular_williams_r(df, periodo=14):
    """Calcula Williams %R"""
    highest_high = df['high'].rolling(window=periodo).max()
    lowest_low = df['low'].rolling(window=periodo).min()
    df['Williams_R'] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
    return df

# ===== NOVO: ANÁLISE CONTEXTUAL DE SEQUÊNCIAS =====
def analisar_sequencia_velas(df, lookback=10):
    """
    Analisa sequências de velas para detectar:
    - Sequências longas de velas verdes/vermelhas
    - Exaustão de movimento
    - Possíveis reversões

    Retorna: dict com análise contextual
    """
    if len(df) < lookback:
        return {
            'velas_verdes_seguidas': 0,
            'velas_vermelhas_seguidas': 0,
            'em_sequencia_longa': False,
            'tipo_sequencia': None,
            'possivel_reversao_alta': False,
            'possivel_reversao_baixa': False,
            'exaustao_detectada': False
        }

    # Últimas N velas
    df_recent = df.tail(lookback).copy()

    # Identificar velas verdes/vermelhas
    df_recent['is_green'] = (df_recent['close'] > df_recent['open']).astype(int)

    # Contar sequências
    velas_verdes_seguidas = 0
    velas_vermelhas_seguidas = 0

    # Contar da última vela para trás
    for i in range(len(df_recent) - 1, -1, -1):
        if df_recent['is_green'].iloc[i] == 1:
            if velas_vermelhas_seguidas > 0:
                break
            velas_verdes_seguidas += 1
        else:
            if velas_verdes_seguidas > 0:
                break
            velas_vermelhas_seguidas += 1

    # Detectar sequência longa
    em_sequencia_longa = max(velas_verdes_seguidas, velas_vermelhas_seguidas) >= min_velas_sequencia
    tipo_sequencia = 'VERDE' if velas_verdes_seguidas >= min_velas_sequencia else ('VERMELHA' if velas_vermelhas_seguidas >= min_velas_sequencia else None)

    # Detectar possível reversão
    ultima_vela = df.iloc[-1]
    penultima_vela = df.iloc[-2] if len(df) >= 2 else ultima_vela

    # Reversão de alta: muitas velas vermelhas + RSI oversold + última vela verde forte
    possivel_reversao_alta = (
        velas_vermelhas_seguidas >= min_velas_sequencia and
        ultima_vela['RSI'] < 40 and
        ultima_vela['close'] > ultima_vela['open'] and  # Última vela verde
        abs(ultima_vela['close'] - ultima_vela['open']) > abs(penultima_vela['close'] - penultima_vela['open'])  # Corpo maior
    )

    # Reversão de baixa: muitas velas verdes + RSI overbought + última vela vermelha forte
    possivel_reversao_baixa = (
        velas_verdes_seguidas >= min_velas_sequencia and
        ultima_vela['RSI'] > 60 and
        ultima_vela['close'] < ultima_vela['open'] and  # Última vela vermelha
        abs(ultima_vela['close'] - ultima_vela['open']) > abs(penultima_vela['close'] - penultima_vela['open'])  # Corpo maior
    )

    # Exaustão: sequência muito longa (risco de reversão)
    exaustao_detectada = max(velas_verdes_seguidas, velas_vermelhas_seguidas) > max_velas_sequencia_permitido

    return {
        'velas_verdes_seguidas': velas_verdes_seguidas,
        'velas_vermelhas_seguidas': velas_vermelhas_seguidas,
        'em_sequencia_longa': em_sequencia_longa,
        'tipo_sequencia': tipo_sequencia,
        'possivel_reversao_alta': possivel_reversao_alta,
        'possivel_reversao_baixa': possivel_reversao_baixa,
        'exaustao_detectada': exaustao_detectada
    }

# ===== NOVO: INTEGRAÇÃO ML =====
def treinar_ml_predictor(df_principal, force=False):
    """Treina o ML Predictor (ou retreina se passou tempo suficiente)"""
    global ultimo_treinamento_ml

    # Verificar se precisa retreinar
    agora = datetime.now()
    if ultimo_treinamento_ml is not None and not force:
        tempo_desde_ultimo = (agora - ultimo_treinamento_ml).total_seconds() / 3600
        if tempo_desde_ultimo < ml_retrain_hours:
            return False  # Não precisa retreinar ainda

    try:
        print("\n🧠 Treinando modelo ML...")

        # Preparar dados
        X_train, X_test, y_train, y_test = ml_predictor.prepare_data(df_principal)

        # Treinar modelos
        training_results = ml_predictor.train_models(X_train, y_train)

        # Avaliar modelos
        evaluation_results = ml_predictor.evaluate_models(X_test, y_test, training_results)

        # Obter melhor modelo
        best_model_name, best_result = ml_predictor.get_best_model(evaluation_results)

        if best_model_name:
            print(f"✓ Melhor modelo: {best_model_name} (R²: {best_result['r2']:.4f}, Dir Acc: {best_result['direction_accuracy']:.2%})")
            ultimo_treinamento_ml = agora
            return True
        else:
            print("✗ Nenhum modelo válido treinado")
            return False

    except Exception as e:
        print(f"⚠️ Erro ao treinar ML: {e}")
        return False

def obter_previsao_ml(df_principal, model_name='random_forest'):
    """Obtém previsão do ML para a próxima vela"""
    try:
        prediction = ml_predictor.predict_next_prices(df_principal, model_name)
        return prediction
    except Exception as e:
        print(f"⚠️ Erro ao obter previsão ML: {e}")
        return None

def sistema_score_contextual(analise_sequencia, df_principal, direcao='compra'):
    """
    Sistema de pontuação contextual baseado em sequências e padrões
    Retorna: score (0-3), detalhes
    """
    score = 0
    detalhes = []

    try:
        if direcao == 'compra':
            # +1: Possível reversão de alta detectada
            if analise_sequencia['possivel_reversao_alta']:
                score += 1
                detalhes.append(f"✓ Reversão de alta detectada ({analise_sequencia['velas_vermelhas_seguidas']} velas vermelhas)")

            # +1: Não está em sequência longa de velas verdes (evita comprar no topo)
            if analise_sequencia['velas_verdes_seguidas'] < max_velas_sequencia_permitido:
                score += 1
                detalhes.append("✓ Sem exaustão de alta")
            else:
                detalhes.append(f"✗ EXAUSTÃO: {analise_sequencia['velas_verdes_seguidas']} velas verdes seguidas")

            # +1: Estrutura favorável (não em sequência vermelha longa sem reversão)
            if not (analise_sequencia['velas_vermelhas_seguidas'] > max_velas_sequencia_permitido and not analise_sequencia['possivel_reversao_alta']):
                score += 1
                detalhes.append("✓ Estrutura de mercado favorável")

        else:  # venda
            # +1: Possível reversão de baixa detectada
            if analise_sequencia['possivel_reversao_baixa']:
                score += 1
                detalhes.append(f"✓ Reversão de baixa detectada ({analise_sequencia['velas_verdes_seguidas']} velas verdes)")

            # +1: Não está em sequência longa de velas vermelhas (evita vender no fundo)
            if analise_sequencia['velas_vermelhas_seguidas'] < max_velas_sequencia_permitido:
                score += 1
                detalhes.append("✓ Sem exaustão de baixa")
            else:
                detalhes.append(f"✗ EXAUSTÃO: {analise_sequencia['velas_vermelhas_seguidas']} velas vermelhas seguidas")

            # +1: Estrutura favorável (não em sequência verde longa sem reversão)
            if not (analise_sequencia['velas_verdes_seguidas'] > max_velas_sequencia_permitido and not analise_sequencia['possivel_reversao_baixa']):
                score += 1
                detalhes.append("✓ Estrutura de mercado favorável")

        return score, detalhes

    except Exception as e:
        print(f"Erro no score contextual: {e}")
        return 0, [f"Erro: {str(e)}"]

def sistema_score_ml(prediction, direcao='compra'):
    """
    Sistema de pontuação ML baseado na previsão
    Retorna: score (0-3), detalhes
    """
    if prediction is None:
        return 0, ["ML não disponível"]

    score = 0
    detalhes = []

    try:
        ml_direction = prediction['direction']
        ml_confidence = prediction['confidence']

        # Verificar se ML concorda com a direção
        if direcao == 'compra' and ml_direction == 'UP':
            # +1: ML concorda
            score += 1
            detalhes.append(f"✓ ML prevê ALTA")

            # +1: Confiança moderada (>40%)
            if ml_confidence >= ml_confidence_threshold:
                score += 1
                detalhes.append(f"✓ Confiança ML: {ml_confidence:.1f}%")

            # +1: Confiança alta (>60%)
            if ml_confidence >= 60:
                score += 1
                detalhes.append(f"✓ Alta confiança ML")
            else:
                detalhes.append(f"○ Confiança ML: {ml_confidence:.1f}%")

        elif direcao == 'venda' and ml_direction == 'DOWN':
            # +1: ML concorda
            score += 1
            detalhes.append(f"✓ ML prevê BAIXA")

            # +1: Confiança moderada (>40%)
            if ml_confidence >= ml_confidence_threshold:
                score += 1
                detalhes.append(f"✓ Confiança ML: {ml_confidence:.1f}%")

            # +1: Confiança alta (>60%)
            if ml_confidence >= 60:
                score += 1
                detalhes.append(f"✓ Alta confiança ML")
            else:
                detalhes.append(f"○ Confiança ML: {ml_confidence:.1f}%")
        else:
            detalhes.append(f"✗ ML discorda (prevê {ml_direction})")

        return score, detalhes

    except Exception as e:
        print(f"Erro no score ML: {e}")
        return 0, [f"Erro: {str(e)}"]

def buscar_dados_multi_timeframe(cripto, tf_principal, tf_confirmacao, emas):
    """Busca dados em múltiplos timeframes"""
    try:
        # Dados do timeframe principal
        df_principal = busca_velas(cripto, tf_principal, emas)

        # Dados do timeframe de confirmação
        resposta_confirmacao = cliente.get_kline(symbol=cripto, interval=tf_confirmacao, limit=200)
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
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_periodo).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_periodo).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        df['Volume_EMA_20'] = df['volume'].ewm(span=volume_ma_periodo, adjust=False).mean()

        # Indicadores avançados
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
    """Sistema de pontuação quantitativa técnica (0-10 pontos)"""
    score = 0
    detalhes_score = []

    if len(df_principal) < 50 or len(df_confirmacao) < 20:
        return 0, ["Dados insuficientes"]

    try:
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

            # 4. ADX confirmando força - 1 ponto
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

            # 8. Williams %R em zona favorável - 1 ponto
            if -80 <= ultima_vela['Williams_R'] <= -20:
                score += 1
                detalhes_score.append("✓ Williams %R favorável")

            # 9. Momentum positivo - 1 ponto
            if ultima_vela['Momentum'] > 100:
                score += 1
                detalhes_score.append("✓ Momentum positivo")

        else:  # venda
            # 1. Tendência de fundo - 2 pontos
            if (ultima_vela_conf[f'EMA_{ema_rapida}'] < ultima_vela_conf[f'EMA_{ema_lenta}'] and
                ultima_vela_conf[f'EMA_{ema_lenta}'] < ultima_vela_conf['EMA_200']):
                score += 2
                detalhes_score.append("✓ Tendência de baixa confirmada no TF maior")

            # 2. Alinhamento de EMAs - 1 ponto
            if (ultima_vela[f'EMA_{ema_rapida}'] < ultima_vela[f'EMA_{ema_lenta}'] and
                ultima_vela[f'EMA_{ema_lenta}'] < ultima_vela['EMA_200']):
                score += 1
                detalhes_score.append("✓ EMAs alinhadas para baixa")

            # 3. RSI em zona favorável - 1 ponto
            if 30 <= ultima_vela['RSI'] <= rsi_overbought:
                score += 1
                detalhes_score.append(f"✓ RSI favorável: {ultima_vela['RSI']:.1f}")

            # 4. ADX forte - 1 ponto
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

            # 8. Williams %R favorável - 1 ponto
            if -80 <= ultima_vela['Williams_R'] <= -20:
                score += 1
                detalhes_score.append("✓ Williams %R favorável")

            # 9. Momentum negativo - 1 ponto
            if ultima_vela['Momentum'] < 100:
                score += 1
                detalhes_score.append("✓ Momentum negativo")

        return score, detalhes_score

    except Exception as e:
        print(f'Erro no sistema de score: {e}', flush=True)
        return 0, [f"Erro: {str(e)}"]

def calcular_stop_dinamico(df, direcao, preco_entrada, atr_atual):
    """Calcula stop loss dinâmico"""
    try:
        stop_atr = atr_atual * 2.5

        if direcao == 'compra':
            low_recente = df['low'].tail(10).min()
            stop_sr = preco_entrada - low_recente
        else:
            high_recente = df['high'].tail(10).max()
            stop_sr = high_recente - preco_entrada

        williams_atual = df['Williams_R'].iloc[-1]
        if abs(williams_atual) > 80:
            stop_volatilidade = stop_atr * 1.5
        else:
            stop_volatilidade = stop_atr * 1.2

        stop_final = min(stop_atr, stop_sr, stop_volatilidade)
        stop_minimo = preco_entrada * 0.005
        stop_final = max(stop_final, stop_minimo)

        return stop_final

    except Exception as e:
        print(f'Erro ao calcular stop dinâmico: {e}', flush=True)
        return atr_atual * 2

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
    estado_de_trade, preco_entrada, preco_stop, preco_alvo = verificar_trade_aberto()
    print(f'Estado inicial: {estado_de_trade}')

    vela_fechou_trade = None
    ml_treinado = False

    while True:
        try:
            # Buscar dados multi-timeframe
            df_principal, df_confirmacao = buscar_dados_multi_timeframe(cripto, tf_principal, tf_confirmacao, emas)

            if df_principal is None or df_confirmacao is None:
                print('Erro ao buscar dados. Aguardando...', flush=True)
                time.sleep(30)
                continue

            # Calcular indicadores
            df_principal = calcular_indicadores_quantitativos(df_principal)

            if len(df_principal) < 50:
                print('Dados insuficientes. Aguardando...', flush=True)
                time.sleep(30)
                continue

            # Treinar ML se necessário (primeira vez ou retreino)
            if not ml_treinado or ultimo_treinamento_ml is None:
                ml_treinado = treinar_ml_predictor(df_principal, force=True)
            else:
                treinar_ml_predictor(df_principal, force=False)

            # ===== GESTÃO DE POSIÇÕES ABERTAS =====
            if estado_de_trade == EstadoDeTrade.COMPRADO:
                print('Posição COMPRADA - Monitorando saída...', flush=True)

                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto()
                preco_atual = df_principal['close'].iloc[-1]

                preco_parcial_compra = preco_entrada * 1.01
                stop_breakeven_compra(cripto, preco_entrada, preco_parcial_compra, estado_de_trade, preco_atual)

                if df_principal['high'].iloc[-1] >= preco_alvo_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🎯 ALVO ATINGIDO! Preço: {preco_alvo_atual:.2f}", flush=True)
                    print('-' * 60, flush=True)
                elif df_principal['low'].iloc[-1] <= preco_stop_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🛑 STOP LOSS! Preço: {preco_stop_atual:.2f}", flush=True)
                    print('-' * 60, flush=True)
                elif verificar_trade_aberto()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print('Trade fechado manualmente', flush=True)
                    print('-' * 60, flush=True)

            elif estado_de_trade == EstadoDeTrade.VENDIDO:
                print('Posição VENDIDA - Monitorando saída...', flush=True)

                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto()
                preco_atual = df_principal['close'].iloc[-1]

                preco_parcial_venda = preco_entrada * 0.99
                stop_breakeven_venda(cripto, preco_entrada, preco_parcial_venda, estado_de_trade, preco_atual)

                if df_principal['low'].iloc[-1] <= preco_alvo_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🎯 ALVO ATINGIDO! Preço: {preco_alvo_atual:.2f}", flush=True)
                    print('-' * 60, flush=True)
                elif df_principal['high'].iloc[-1] >= preco_stop_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🛑 STOP LOSS! Preço: {preco_stop_atual:.2f}", flush=True)
                    print('-' * 60, flush=True)
                elif verificar_trade_aberto()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print('Trade fechado manualmente', flush=True)
                    print('-' * 60, flush=True)

            # ===== BUSCA POR NOVAS ENTRADAS =====
            elif estado_de_trade == EstadoDeTrade.DE_FORA and df_principal['open_time'].iloc[-1] != vela_fechou_trade:
                print('\n' + '=' * 60)
                print('🔍 Analisando oportunidades de entrada...')
                print('=' * 60)

                # Obter dados para cálculos
                saldo = saldo_da_conta() * alavancagem
                qtidade_minima = quantidade_minima_para_operar(cripto)
                qtd_cripto = quantidade_cripto_para_operar(saldo, qtidade_minima, df_principal['close'].iloc[-1])
                atr_atual = df_principal['ATR'].iloc[-1]

                # === ANÁLISE CONTEXTUAL ===
                analise_sequencia = analisar_sequencia_velas(df_principal, lookback=15)

                print(f"\n📊 Análise de Sequências:")
                print(f"   Velas verdes seguidas: {analise_sequencia['velas_verdes_seguidas']}")
                print(f"   Velas vermelhas seguidas: {analise_sequencia['velas_vermelhas_seguidas']}")
                if analise_sequencia['em_sequencia_longa']:
                    print(f"   ⚠️  Sequência longa detectada: {analise_sequencia['tipo_sequencia']}")
                if analise_sequencia['possivel_reversao_alta']:
                    print(f"   🔄 Possível reversão de ALTA")
                if analise_sequencia['possivel_reversao_baixa']:
                    print(f"   🔄 Possível reversão de BAIXA")

                # === PREVISÃO ML ===
                prediction_ml = obter_previsao_ml(df_principal, 'random_forest') if ml_treinado else None

                if prediction_ml:
                    print(f"\n🧠 Previsão ML:")
                    print(f"   Direção: {prediction_ml['direction']}")
                    print(f"   Confiança: {prediction_ml['confidence']:.1f}%")
                    print(f"   Preço atual: ${prediction_ml['current_price']:.4f}")
                    print(f"   Preço previsto: ${prediction_ml['predicted_price']:.4f}")

                # === SCORING COMPLETO ===

                # COMPRA
                score_tecnico_compra, detalhes_tecnico_compra = sistema_score_quantitativo(df_principal, df_confirmacao, 'compra')
                score_contextual_compra, detalhes_contextual_compra = sistema_score_contextual(analise_sequencia, df_principal, 'compra')
                score_ml_compra, detalhes_ml_compra = sistema_score_ml(prediction_ml, 'compra') if prediction_ml else (0, ["ML não disponível"])

                score_total_compra = score_tecnico_compra + score_contextual_compra + score_ml_compra

                # VENDA
                score_tecnico_venda, detalhes_tecnico_venda = sistema_score_quantitativo(df_principal, df_confirmacao, 'venda')
                score_contextual_venda, detalhes_contextual_venda = sistema_score_contextual(analise_sequencia, df_principal, 'venda')
                score_ml_venda, detalhes_ml_venda = sistema_score_ml(prediction_ml, 'venda') if prediction_ml else (0, ["ML não disponível"])

                score_total_venda = score_tecnico_venda + score_contextual_venda + score_ml_venda

                # Exibir scores
                print(f"\n📊 SCORES DETALHADOS:")
                print(f"\n🟢 COMPRA:")
                print(f"   Técnico: {score_tecnico_compra}/{score_tecnico_max}")
                print(f"   Contextual: {score_contextual_compra}/{score_contextual_max}")
                print(f"   ML: {score_ml_compra}/{score_ml_max}")
                print(f"   TOTAL: {score_total_compra}/{score_total_max}")

                print(f"\n🔴 VENDA:")
                print(f"   Técnico: {score_tecnico_venda}/{score_tecnico_max}")
                print(f"   Contextual: {score_contextual_venda}/{score_contextual_max}")
                print(f"   ML: {score_ml_venda}/{score_ml_max}")
                print(f"   TOTAL: {score_total_venda}/{score_total_max}")

                # ===== ENTRADA EM COMPRA =====
                if score_total_compra >= score_minimo_entrada and score_total_compra > score_total_venda:
                    preco_entrada = df_principal['close'].iloc[-1]

                    stop_distance = calcular_stop_dinamico(df_principal, 'compra', preco_entrada, atr_atual)
                    preco_stop = preco_entrada - stop_distance
                    preco_alvo = preco_entrada + (stop_distance * risco_retorno)

                    try:
                        abre_compra(cripto, qtd_cripto, preco_stop, preco_alvo)
                        estado_de_trade = EstadoDeTrade.COMPRADO

                        print(f"\n{'=' * 60}")
                        print(f"🚀 ENTRADA EM COMPRA EXECUTADA!")
                        print(f"{'=' * 60}")
                        print(f"📈 Preço Entrada: {preco_entrada:.4f}")
                        print(f"🛑 Stop Loss: {preco_stop:.4f}")
                        print(f"🎯 Take Profit: {preco_alvo:.4f}")
                        print(f"📊 Score Total: {score_total_compra}/{score_total_max}")
                        print(f"\n✅ Critérios Técnicos ({score_tecnico_compra}/{score_tecnico_max}):")
                        for detalhe in detalhes_tecnico_compra:
                            print(f"   {detalhe}")
                        print(f"\n✅ Critérios Contextuais ({score_contextual_compra}/{score_contextual_max}):")
                        for detalhe in detalhes_contextual_compra:
                            print(f"   {detalhe}")
                        print(f"\n✅ Critérios ML ({score_ml_compra}/{score_ml_max}):")
                        for detalhe in detalhes_ml_compra:
                            print(f"   {detalhe}")
                        print('=' * 60)

                        abre_parcial_compra(cripto, qtd_cripto, preco_entrada)

                    except Exception as e:
                        print(f'Erro ao executar compra: {e}', flush=True)

                # ===== ENTRADA EM VENDA =====
                elif score_total_venda >= score_minimo_entrada and score_total_venda > score_total_compra:
                    preco_entrada = df_principal['close'].iloc[-1]

                    stop_distance = calcular_stop_dinamico(df_principal, 'venda', preco_entrada, atr_atual)
                    preco_stop = preco_entrada + stop_distance
                    preco_alvo = preco_entrada - (stop_distance * risco_retorno)

                    try:
                        abre_venda(cripto, qtd_cripto, preco_stop, preco_alvo)
                        estado_de_trade = EstadoDeTrade.VENDIDO

                        print(f"\n{'=' * 60}")
                        print(f"🔻 ENTRADA EM VENDA EXECUTADA!")
                        print(f"{'=' * 60}")
                        print(f"📉 Preço Entrada: {preco_entrada:.4f}")
                        print(f"🛑 Stop Loss: {preco_stop:.4f}")
                        print(f"🎯 Take Profit: {preco_alvo:.4f}")
                        print(f"📊 Score Total: {score_total_venda}/{score_total_max}")
                        print(f"\n✅ Critérios Técnicos ({score_tecnico_venda}/{score_tecnico_max}):")
                        for detalhe in detalhes_tecnico_venda:
                            print(f"   {detalhe}")
                        print(f"\n✅ Critérios Contextuais ({score_contextual_venda}/{score_contextual_max}):")
                        for detalhe in detalhes_contextual_venda:
                            print(f"   {detalhe}")
                        print(f"\n✅ Critérios ML ({score_ml_venda}/{score_ml_max}):")
                        for detalhe in detalhes_ml_venda:
                            print(f"   {detalhe}")
                        print('=' * 60)

                        abre_parcial_venda(cripto, qtd_cripto, preco_entrada)

                    except Exception as e:
                        print(f'Erro ao executar venda: {e}', flush=True)

                else:
                    print(f"\n❌ Scores insuficientes para entrada (mínimo: {score_minimo_entrada}/{score_total_max})")
                    print(f"   Compra: {score_total_compra} | Venda: {score_total_venda}")

        except Exception as e:
            print(f'Erro no loop principal: {e}', flush=True)

        # Aguardar próxima análise
        time.sleep(15)

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
