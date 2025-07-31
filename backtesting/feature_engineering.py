#!/usr/bin/env python3
"""
Feature Engineering Pipeline para Trading Quantitativo
Cria features avançadas baseadas nos indicadores existentes do sistema
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import ta
from funcoes_bybit import busca_velas
from typing import List, Tuple, Dict
import warnings
warnings.filterwarnings('ignore')

class FeatureEngineer:
    """Pipeline de Feature Engineering para dados de trading"""
    
    def __init__(self, lookback_periods: List[int] = [5, 10, 20, 50]):
        self.lookback_periods = lookback_periods
        self.scaler = RobustScaler()
        self.feature_names = []
        
    def create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features baseadas em preços"""
        df_features = df.copy()
        
        # Returns em diferentes períodos
        for period in self.lookback_periods:
            df_features[f'return_{period}'] = df['close'].pct_change(period)
            df_features[f'log_return_{period}'] = np.log(df['close'] / df['close'].shift(period))
            
        # Volatilidade realizada
        for period in self.lookback_periods:
            df_features[f'volatility_{period}'] = df['close'].pct_change().rolling(period).std()
            
        # Price position dentro de ranges
        for period in self.lookback_periods:
            high_roll = df['high'].rolling(period).max()
            low_roll = df['low'].rolling(period).min()
            df_features[f'price_position_{period}'] = (df['close'] - low_roll) / (high_roll - low_roll)
            
        # RSI divergence
        if 'RSI' in df.columns:
            df_features['rsi_ma_5'] = df['RSI'].rolling(5).mean()
            df_features['rsi_ma_14'] = df['RSI'].rolling(14).mean()
            df_features['rsi_divergence'] = df['RSI'] - df_features['rsi_ma_14']
        
        return df_features
    
    def create_ema_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features baseadas nas EMAs existentes"""
        df_features = df.copy()
        
        # Assume que temos EMA_9, EMA_21, EMA_200 do sistema original
        ema_cols = [col for col in df.columns if col.startswith('EMA_')]
        
        if len(ema_cols) >= 2:
            # EMA crossover signals
            ema_fast = ema_cols[0]  # EMA menor
            ema_slow = ema_cols[1]  # EMA maior
            
            df_features['ema_ratio'] = df[ema_fast] / df[ema_slow]
            df_features['ema_distance'] = (df[ema_fast] - df[ema_slow]) / df['close']
            df_features['price_above_ema_fast'] = (df['close'] > df[ema_fast]).astype(int)
            df_features['price_above_ema_slow'] = (df['close'] > df[ema_slow]).astype(int)
            
            # EMA slope (momentum)
            for ema_col in ema_cols:
                df_features[f'{ema_col}_slope_5'] = df[ema_col].diff(5) / 5
                df_features[f'{ema_col}_slope_10'] = df[ema_col].diff(10) / 10
                
            # Distance from EMAs
            for ema_col in ema_cols:
                df_features[f'distance_from_{ema_col}'] = (df['close'] - df[ema_col]) / df['close']
        
        return df_features
    
    def create_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features baseadas em volume"""
        df_features = df.copy()
        
        # Volume ratios
        if 'Volume_EMA_20' in df.columns:
            df_features['volume_ratio'] = df['volume'] / df['Volume_EMA_20']
            df_features['volume_above_avg'] = (df['volume'] > df['Volume_EMA_20']).astype(int)
        
        # Volume-Price Analysis
        for period in [5, 10, 20]:
            df_features[f'volume_sma_{period}'] = df['volume'].rolling(period).mean()
            df_features[f'volume_ratio_{period}'] = df['volume'] / df_features[f'volume_sma_{period}']
            
        # Price-Volume Trend
        df_features['pvt'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1) * df['volume']).cumsum()
        
        # On-Balance Volume
        df_features['obv'] = (df['volume'] * np.where(df['close'] > df['close'].shift(1), 1, 
                                                    np.where(df['close'] < df['close'].shift(1), -1, 0))).cumsum()
        
        return df_features
    
    def create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features técnicas avançadas usando biblioteca ta"""
        df_features = df.copy()
        
        try:
            # Bollinger Bands
            df_features['bb_upper'] = ta.bollinger_hband(df['close'])
            df_features['bb_lower'] = ta.bollinger_lband(df['close'])
            df_features['bb_middle'] = ta.bollinger_mavg(df['close'])
            df_features['bb_width'] = (df_features['bb_upper'] - df_features['bb_lower']) / df_features['bb_middle']
            df_features['bb_position'] = (df['close'] - df_features['bb_lower']) / (df_features['bb_upper'] - df_features['bb_lower'])
        except:
            # Manual Bollinger Bands if ta functions don't work
            period = 20
            rolling_mean = df['close'].rolling(period).mean()
            rolling_std = df['close'].rolling(period).std()
            df_features['bb_upper'] = rolling_mean + (rolling_std * 2)
            df_features['bb_lower'] = rolling_mean - (rolling_std * 2)
            df_features['bb_middle'] = rolling_mean
            df_features['bb_width'] = (df_features['bb_upper'] - df_features['bb_lower']) / df_features['bb_middle']
            df_features['bb_position'] = (df['close'] - df_features['bb_lower']) / (df_features['bb_upper'] - df_features['bb_lower'])
        
        try:
            # MACD
            df_features['macd'] = ta.macd(df['close'])
            df_features['macd_signal'] = ta.macd_signal(df['close'])
            df_features['macd_histogram'] = ta.macd_diff(df['close'])
        except:
            # Manual MACD
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            df_features['macd'] = ema_12 - ema_26
            df_features['macd_signal'] = df_features['macd'].ewm(span=9).mean()
            df_features['macd_histogram'] = df_features['macd'] - df_features['macd_signal']
        
        try:
            # Stochastic
            df_features['stoch_k'] = ta.stoch(df['high'], df['low'], df['close'])
            df_features['stoch_d'] = ta.stoch_signal(df['high'], df['low'], df['close'])
        except:
            # Manual Stochastic
            period = 14
            low_min = df['low'].rolling(period).min()
            high_max = df['high'].rolling(period).max()
            df_features['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
            df_features['stoch_d'] = df_features['stoch_k'].rolling(3).mean()
        
        try:
            # ATR
            df_features['atr'] = ta.atr(df['high'], df['low'], df['close'])
        except:
            # Manual ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            df_features['atr'] = true_range.rolling(14).mean()
        
        df_features['atr_ratio'] = df_features['atr'] / df['close']
        
        try:
            # Williams %R
            df_features['williams_r'] = ta.wr(df['high'], df['low'], df['close'])
        except:
            # Manual Williams %R
            period = 14
            high_max = df['high'].rolling(period).max()
            low_min = df['low'].rolling(period).min()
            df_features['williams_r'] = -100 * (high_max - df['close']) / (high_max - low_min)
        
        try:
            # CCI
            df_features['cci'] = ta.cci(df['high'], df['low'], df['close'])
        except:
            # Manual CCI
            period = 20
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = typical_price.rolling(period).mean()
            mad = typical_price.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())))
            df_features['cci'] = (typical_price - sma_tp) / (0.015 * mad)
        
        return df_features
    
    def create_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features baseadas em padrões de candles"""
        df_features = df.copy()
        
        # Tamanho do corpo da vela
        df_features['body_size'] = abs(df['close'] - df['open']) / df['close']
        
        # Tamanho das sombras
        df_features['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df_features['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # Tipo da vela
        df_features['is_green'] = (df['close'] > df['open']).astype(int)
        df_features['is_doji'] = (abs(df['close'] - df['open']) / df['close'] < 0.001).astype(int)
        
        # Gaps
        df_features['gap_up'] = (df['low'] > df['high'].shift(1)).astype(int)
        df_features['gap_down'] = (df['high'] < df['low'].shift(1)).astype(int)
        
        # Sequências de velas
        for period in [3, 5, 7]:
            df_features[f'green_streak_{period}'] = df_features['is_green'].rolling(period).sum()
            df_features[f'red_streak_{period}'] = (1 - df_features['is_green']).rolling(period).sum()
        
        return df_features
    
    def create_market_structure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features de estrutura de mercado"""
        df_features = df.copy()
        
        # Higher Highs / Lower Lows
        for period in [10, 20, 50]:
            df_features[f'hh_{period}'] = (df['high'] > df['high'].rolling(period).max().shift(1)).astype(int)
            df_features[f'll_{period}'] = (df['low'] < df['low'].rolling(period).min().shift(1)).astype(int)
            df_features[f'hl_{period}'] = (df['low'] > df['low'].rolling(period).min().shift(1)).astype(int)
            df_features[f'lh_{period}'] = (df['high'] < df['high'].rolling(period).max().shift(1)).astype(int)
        
        # Support/Resistance levels (simplified)
        for period in [20, 50]:
            df_features[f'resistance_{period}'] = df['high'].rolling(period).max()
            df_features[f'support_{period}'] = df['low'].rolling(period).min()
            df_features[f'distance_to_resistance_{period}'] = (df_features[f'resistance_{period}'] - df['close']) / df['close']
            df_features[f'distance_to_support_{period}'] = (df['close'] - df_features[f'support_{period}']) / df['close']
        
        return df_features
    
    def create_lag_features(self, df: pd.DataFrame, target_col: str = 'close') -> pd.DataFrame:
        """Cria features de lag (valores passados)"""
        df_features = df.copy()
        
        # Lags do preço
        for lag in [1, 2, 3, 5, 10]:
            df_features[f'{target_col}_lag_{lag}'] = df[target_col].shift(lag)
            
        # Lags dos indicadores principais
        key_indicators = ['RSI', 'volume_ratio'] + [col for col in df.columns if col.startswith('EMA_')]
        
        for indicator in key_indicators:
            if indicator in df.columns:
                for lag in [1, 2, 3]:
                    df_features[f'{indicator}_lag_{lag}'] = df[indicator].shift(lag)
        
        return df_features
    
    def create_target_variable(self, df: pd.DataFrame, forecast_horizon: int = 1) -> pd.DataFrame:
        """Cria variável target para predição"""
        df_target = df.copy()
        
        # Target: retorno futuro
        df_target['target_return'] = df['close'].pct_change(forecast_horizon).shift(-forecast_horizon)
        
        # Target: direção do movimento (classificação)
        df_target['target_direction'] = (df_target['target_return'] > 0).astype(int)
        
        # Target: preço futuro
        df_target['target_price'] = df['close'].shift(-forecast_horizon)
        
        return df_target
    
    def engineer_all_features(self, df: pd.DataFrame, forecast_horizon: int = 1) -> pd.DataFrame:
        """Pipeline completo de feature engineering"""
        print("Iniciando feature engineering...")
        
        # Aplicar todas as transformações
        df_engineered = self.create_price_features(df)
        print("✓ Price features criadas")
        
        df_engineered = self.create_ema_features(df_engineered)
        print("✓ EMA features criadas")
        
        df_engineered = self.create_volume_features(df_engineered)
        print("✓ Volume features criadas")
        
        df_engineered = self.create_technical_features(df_engineered)
        print("✓ Technical features criadas")
        
        df_engineered = self.create_pattern_features(df_engineered)
        print("✓ Pattern features criadas")
        
        df_engineered = self.create_market_structure_features(df_engineered)
        print("✓ Market structure features criadas")
        
        df_engineered = self.create_lag_features(df_engineered)
        print("✓ Lag features criadas")
        
        df_engineered = self.create_target_variable(df_engineered, forecast_horizon)
        print("✓ Target variables criadas")
        
        # Remover linhas com NaN
        df_clean = df_engineered.dropna()
        
        # Salvar nomes das features
        self.feature_names = [col for col in df_clean.columns if col not in ['target_return', 'target_direction', 'target_price', 'open_time']]
        
        print(f"Feature engineering concluído: {len(self.feature_names)} features criadas")
        print(f"Dataset shape: {df_clean.shape}")
        
        return df_clean
    
    def get_feature_importance(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """Calcula importância das features usando Random Forest"""
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance_df

def teste_feature_engineering():
    """Teste do pipeline de feature engineering"""
    print("=== Teste do Feature Engineering Pipeline ===")
    
    # Carregar dados de exemplo
    try:
        df = busca_velas('BTCUSDT', '60', [9, 21])
        print(f"Dados carregados: {df.shape}")
        
        # Aplicar feature engineering
        engineer = FeatureEngineer()
        df_features = engineer.engineer_all_features(df, forecast_horizon=1)
        
        print(f"\nTop 20 features mais importantes:")
        X = df_features[engineer.feature_names]
        y = df_features['target_return']
        
        importance = engineer.get_feature_importance(X, y)
        print(importance.head(20))
        
        # Estatísticas básicas
        print(f"\nEstatísticas do dataset:")
        print(f"- Total de samples: {len(df_features)}")
        print(f"- Total de features: {len(engineer.feature_names)}")
        print(f"- Target mean: {y.mean():.6f}")
        print(f"- Target std: {y.std():.6f}")
        
        return df_features, engineer
        
    except Exception as e:
        print(f"Erro no teste: {e}")
        return None, None

if __name__ == "__main__":
    df_features, engineer = teste_feature_engineering()