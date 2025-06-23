
# Nabilion Quantum

Sistema completo de **Trading Automático**, **Backtesting** e **Análise Quantitativa** em Python.

---

## Estrutura do Projeto

```
nabilion/
├── backtesting_teste.py
├── data_loader.py
├── estado_trade.py
├── funcoes_bybit.py
├── indicadores_osciladores.py
├── live_trading_scalp.py
├── padroes_velas.py
├── utilidades.py
├── requirements.txt
└── .env
```

---

## Descrição

**Nabilion** é uma arquitetura modular para automação de trades em criptomoedas na **Bybit**, com foco em:

- Trading em tempo real (Live Trading)
- Backtesting offline com histórico de candles
- Indicadores técnicos customizados (EMA, RSI, ATR, etc)
- Análise de padrões de velas (Price Action)
- Controle de estado de operação
- Proteções de risco (Stop Loss, Stop Gain, Breakeven, etc)
-  Suporte a futuras integrações com Machine Learning e Banco de Dados PostgreSQL

---

## Funcionalidades Principais

| Módulo                     | Descrição                                                                                   |
|----------------------------|---------------------------------------------------------------------------------------------|
| **live_trading_scalp.py**  | Robô principal de execução de ordens ao vivo com gerenciamento de posição e risco          |
| **backtesting_teste.py**   | Teste offline das estratégias utilizando velas salvas em JSON                              |
| **funcoes_bybit.py**       | Funções de integração com a API da Bybit (consultas, ordens, etc)                          |
| **estado_trade.py**        | Enum e controle de estado da operação (Aberto, Fechado, etc)                               |
| **indicadores_osciladores.py** | Cálculo de indicadores técnicos como RSI, ATR, etc                                        |
| **padroes_velas.py**       | Reconhecimento de padrões de velas (Doji, Engolfo, etc)                                     |
| **data_loader.py**         | Leitura, salvamento e manipulação de dados históricos de velas (JSON)                      |
| **utilidades.py**          | Funções auxiliares como cálculo de quantidade, ajuste de horários e filtros                |

---

## ️ Instalação

### Pré-requisitos:

- Python 3.10 ou superior
- Conta na **Bybit** com API Keys geradas

### Instale as dependências:

```bash
pip install -r requirements.txt
```

### Configuração do `.env`:

Crie um arquivo `.env` na raiz com suas credenciais:

```
BYBIT_API_KEY=YOUR_API_KEY
BYBIT_API_SECRET=YOUR_API_SECRET
```

---

##  Como Executar

### Live Trading:

```bash
python live_trading_scalp.py
```

### Backtesting:

Certifique-se de ter os dados de candles salvos (ex: `BTCUSDT_1m.json`):

```bash
python backtesting_teste.py
```

---

## ️ Customização de Estratégia

Todas as regras de entrada/saída, filtros de tendência, cálculo de tamanho de posição e controles de risco estão centralizados nas funções dentro de:

- `funcoes_bybit.py`
- `estado_trade.py`
- `indicadores_osciladores.py`
- `padroes_velas.py`

>️  **Importante:** Caso queira adicionar mais filtros ou indicadores (ex: VWAP, Bollinger Bands), siga o padrão das funções existentes.

---

##  Exemplos de Indicadores Suportados

- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- ATR (Average True Range)
- Padrões de Velas (Doji, Engolfo, Martelo, etc)

---

##  Exemplo de Lógica de Trade

- Filtragem por EMAs de 9 e 21 períodos
- Confirmação por RSI
- Controle de Stop Loss baseado em múltiplos de ATR
- Stop Gain parcial (ex: 5% do lucro realizado com ajuste de Breakeven)
- Gestão de risco com alavancagem configurável

---

##  Futuras Melhorias Planejadas

- {} Integração com Banco de Dados PostgreSQL
- {}Dashboard web com Flask ou FastAPI
- {} Otimização de estratégias via Machine Learning
- {} Backtester mais robusto com multi-thread e análises de desempenho
- {} Exportação automática de relatórios de performance

---

##  Problemas Conhecidos

-  Algumas exceções da API Bybit podem interromper a execução (ex: perda de conexão, limites de API)
- Necessário melhorar o controle de erros nas funções de ordem
- Falta de sincronização de horário pode gerar erros de execução (solução parcial em `utilidades.py`)

---

---

## 📋 Licença

Distribuído sob a Licença MIT. Veja o arquivo [LICENSE](https://github.com/ferreiraluc/nabilion/blob/main/LICENSE) para mais detalhes.

---