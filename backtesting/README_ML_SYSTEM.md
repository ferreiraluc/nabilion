# Sistema ML de Trading Quantitativo

## 📋 Visão Geral

Sistema completo de análise quantitativa e predição de preços para trading de criptomoedas usando Machine Learning, construído sobre a infraestrutura existente do projeto.

## 🏗️ Arquitetura do Sistema

### Módulos Principais

1. **`feature_engineering.py`** - Pipeline de Feature Engineering
2. **`ml_predictor.py`** - Sistema de Predição ML
3. **`chart_predictor.py`** - Visualizações Avançadas
4. **`quantitative_analyzer.py`** - Análise Quantitativa Completa
5. **`main_ml_analysis.py`** - Sistema Principal Integrado

## 🔧 Features Criadas (138 total)

### 1. Price Features
- Retornos em múltiplos períodos (5, 10, 20, 50)
- Log returns
- Volatilidade realizada
- Posição do preço em ranges
- Divergência RSI

### 2. EMA Features
- Ratios entre EMAs
- Distâncias das EMAs
- Slopes (momentum) das EMAs
- Sinais de crossover

### 3. Volume Features
- Ratios de volume
- On-Balance Volume (OBV)
- Price-Volume Trend (PVT)
- Volume médias móveis

### 4. Technical Indicators
- Bollinger Bands (posição, largura)
- MACD (line, signal, histogram)
- Stochastic Oscillator
- Average True Range (ATR)
- Williams %R
- Commodity Channel Index (CCI)

### 5. Candlestick Patterns
- Tamanho do corpo
- Sombras (upper/lower)
- Tipos de vela (green/red/doji)
- Gaps (up/down)
- Sequências de velas

### 6. Market Structure
- Higher Highs / Lower Lows
- Support/Resistance levels
- Distâncias para suporte/resistência

### 7. Lag Features
- Valores históricos de preços e indicadores
- Lags de 1, 2, 3, 5, 10 períodos

## 🤖 Modelos ML Implementados

1. **Random Forest** ⭐ (Melhor performance)
2. **Gradient Boosting**
3. **Linear Regression**
4. **Ridge Regression**
5. **Lasso Regression**
6. **Support Vector Regression (SVR)**

## 📊 Métricas de Avaliação

- **R² Score**: Coefficient of determination
- **Mean Absolute Error (MAE)**
- **Direction Accuracy**: Precisão na predição da direção
- **Cross-Validation**: 5-fold CV para validação

## 🎯 Resultados Típicos

```
🏆 Melhor Modelo: RANDOM_FOREST
📈 R² Score: 0.0018
📊 MAE: 0.002360
🎯 Acurácia Direcional: 51.6%

🔮 PREDIÇÃO PRÓXIMO PERÍODO
💰 Preço Atual: $117,849.90
🎯 Preço Predito: $117,754.95
📊 Direção: 📉 DOWN
🎲 Confiança: 0.1%
📈 Retorno Esperado: -0.0806%
```

## 🔝 Features Mais Importantes

1. **RSI_lag_3** - RSI de 3 períodos atrás
2. **obv** - On-Balance Volume
3. **EMA_200** - EMA de 200 períodos
4. **distance_to_resistance_50** - Distância para resistência
5. **lower_shadow** - Sombra inferior da vela
6. **price_position_5** - Posição do preço no range de 5 períodos
7. **volume** - Volume atual
8. **rsi_divergence** - Divergência do RSI
9. **turnover** - Volume em USDT
10. **close_lag_10** - Preço de fechamento de 10 períodos atrás

## 🚀 Como Usar

### Análise Individual
```python
from main_ml_analysis import TradingMLSystem

system = TradingMLSystem()
result = system.analyze_crypto('BTCUSDT', '60', [9, 21])
```

### Análise Múltipla
```python
symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
results = system.analyze_multiple_cryptos(symbols, '60')
```

### Teste Rápido
```python
python test_ml_system.py
```

### Sistema Completo
```python
python main_ml_analysis.py
```

## 📁 Estrutura de Arquivos

```
backtesting/
├── feature_engineering.py      # Pipeline de features
├── ml_predictor.py             # Modelos ML
├── chart_predictor.py          # Visualizações
├── quantitative_analyzer.py    # Análise completa
├── main_ml_analysis.py         # Sistema principal
├── test_ml_system.py          # Teste rápido
├── reports/                   # Relatórios salvos
└── charts/                    # Gráficos gerados
```

## 🎨 Visualizações Disponíveis

1. **Candlestick com Predições** - Gráfico principal com velas e predições ML
2. **Feature Importance** - Ranking das features mais importantes
3. **Model Comparison** - Comparação de performance dos modelos
4. **Prediction Analysis** - Distribuições e análise de resíduos
5. **Signal Heatmap** - Força dos sinais por horário/dia

## 📈 Integração com Sistema Existente

O sistema ML se integra perfeitamente com:

- **`funcoes_bybit.py`** - Para buscar dados da exchange
- **`estado_trade.py`** - Estados de trading
- **`indicadores_osciladores.py`** - RSI existente
- **EMA calculations** - EMAs já calculadas no sistema
- **Volume analysis** - Volume EMA existente

## ⚙️ Dependências Principais

- **scikit-learn** - Algoritmos ML
- **pandas/numpy** - Manipulação de dados
- **ta** - Indicadores técnicos
- **plotly** - Visualizações interativas
- **scipy** - Computação científica

## 🔍 Monitoramento e Logs

O sistema inclui logs detalhados:
- ✓ Features criadas com sucesso
- ✓ Modelos treinados e avaliados
- ✓ Predições geradas
- ✓ Relatórios salvos

## 📝 Relatórios Salvos

Relatórios JSON são salvos em `reports/` contendo:
- Informações dos dados
- Performance dos modelos
- Predições
- Top features importantes
- Timestamps completos

## 🎛️ Configurações

### Parâmetros Principais
- **forecast_horizon**: Horizonte de predição (padrão: 1)
- **lookback_periods**: Períodos para features [5, 10, 20, 50]
- **timeframe**: Timeframe das velas ('60' = 1 hora)
- **emas**: EMAs utilizadas [9, 21]

### Modelos ML
- **Random Forest**: n_estimators=100, max_depth=10
- **Gradient Boosting**: n_estimators=100, learning_rate=0.1
- **Ridge/Lasso**: Alpha otimizado
- **SVR**: RBF kernel, C=100

## 🚨 Considerações Importantes

1. **Performance**: Modelos apresentam R² baixo (normal para dados financeiros)
2. **Direction Accuracy**: ~51.6% (ligeiramente melhor que chance)
3. **Overfitting**: Sistema usa cross-validation e split temporal
4. **Features**: 138 features podem gerar overfitting - feature selection recomendada
5. **Tempo Real**: Sistema preparado para integração com live trading

## 🔄 Próximas Melhorias

1. **Feature Selection** - Reduzir dimensionalidade
2. **Ensemble Models** - Combinar modelos
3. **Deep Learning** - LSTM/GRU para séries temporais
4. **Real-time Streaming** - Predições em tempo real
5. **Backtesting Integration** - Integrar com sistema de backtesting
6. **Risk Management** - Incorporar gestão de risco
7. **Multi-timeframe** - Análise multi-timeframe

## 📞 Suporte

Sistema desenvolvido seguindo as convenções do projeto existente e integrado com a arquitetura atual de trading.

**Arquivos principais para debugging:**
- `test_ml_system.py` - Teste rápido
- `main_ml_analysis.py` - Sistema completo
- Logs detalhados em cada módulo

---

**Status**: ✅ Sistema Completo e Funcional
**Testado**: ✅ BTC, ETH, XRP
**Integração**: ✅ Com sistema existente