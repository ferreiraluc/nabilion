#!/usr/bin/env python3
"""
ML Predictor para Trading Quantitativo
Sistema de predição de preços usando múltiplos algoritmos de machine learning
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.svm import SVR
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from feature_engineering import FeatureEngineer
from funcoes_bybit import busca_velas
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class MLPredictor:
    """Sistema de predição usando Machine Learning"""
    
    def __init__(self, forecast_horizon: int = 1):
        self.forecast_horizon = forecast_horizon
        self.models = {}
        self.scalers = {}
        self.feature_engineer = FeatureEngineer()
        self.feature_importance = {}
        self.predictions_history = []
        
        # Configurar modelos
        self._setup_models()
    
    def _setup_models(self):
        """Configura os modelos de ML"""
        self.models = {
            'random_forest': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            ),
            'gradient_boosting': GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            'linear_regression': LinearRegression(),
            'ridge': Ridge(alpha=1.0),
            'lasso': Lasso(alpha=0.1),
            'svr': SVR(kernel='rbf', C=100, gamma=0.1)
        }
        
        # Scalers para cada modelo
        for model_name in self.models:
            self.scalers[model_name] = RobustScaler()
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Prepara dados para treinamento"""
        print("Preparando dados...")
        
        # Feature engineering
        df_features = self.feature_engineer.engineer_all_features(df, self.forecast_horizon)
        
        # Separar features e target
        feature_columns = self.feature_engineer.feature_names
        X = df_features[feature_columns]
        y = df_features['target_return']
        
        # Split temporal (80% treino, 20% teste)
        split_index = int(len(X) * 0.8)
        X_train = X.iloc[:split_index]
        X_test = X.iloc[split_index:]
        y_train = y.iloc[:split_index]
        y_test = y.iloc[split_index:]
        
        print(f"Dados preparados: {X_train.shape[0]} amostras de treino, {X_test.shape[0]} amostras de teste")
        
        return X_train, X_test, y_train, y_test
    
    def train_models(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Dict]:
        """Treina todos os modelos"""
        print("Treinando modelos...")
        results = {}
        
        for model_name, model in self.models.items():
            print(f"Treinando {model_name}...")
            
            try:
                # Escalar dados
                X_scaled = self.scalers[model_name].fit_transform(X_train)
                
                # Treinar modelo
                model.fit(X_scaled, y_train)
                
                # Cross-validation
                cv_scores = cross_val_score(model, X_scaled, y_train, cv=5, scoring='r2')
                
                # Feature importance (se disponível)
                feature_importance = None
                if hasattr(model, 'feature_importances_'):
                    importance_df = pd.DataFrame({
                        'feature': X_train.columns,
                        'importance': model.feature_importances_
                    }).sort_values('importance', ascending=False)
                    self.feature_importance[model_name] = importance_df
                    feature_importance = importance_df.head(10)
                
                results[model_name] = {
                    'model': model,
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'feature_importance': feature_importance
                }
                
                print(f"✓ {model_name}: CV R² = {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")
                
            except Exception as e:
                print(f"✗ Erro ao treinar {model_name}: {e}")
                results[model_name] = {'model': None, 'error': str(e)}
        
        return results
    
    def evaluate_models(self, X_test: pd.DataFrame, y_test: pd.Series, 
                       training_results: Dict) -> Dict[str, Dict]:
        """Avalia modelos no conjunto de teste"""
        print("\nAvaliando modelos...")
        evaluation_results = {}
        
        for model_name, result in training_results.items():
            if result['model'] is None:
                continue
                
            try:
                model = result['model']
                
                # Escalar dados de teste
                X_scaled = self.scalers[model_name].transform(X_test)
                
                # Predição
                y_pred = model.predict(X_scaled)
                
                # Métricas
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                # Acurácia direcional
                direction_accuracy = np.mean((np.sign(y_test) == np.sign(y_pred)))
                
                evaluation_results[model_name] = {
                    'mse': mse,
                    'mae': mae,
                    'r2': r2,
                    'direction_accuracy': direction_accuracy,
                    'predictions': y_pred,
                    'cv_score': result.get('cv_mean', 0)
                }
                
                print(f"{model_name}:")
                print(f"  R² Score: {r2:.4f}")
                print(f"  MAE: {mae:.6f}")
                print(f"  Direction Accuracy: {direction_accuracy:.4f}")
                
            except Exception as e:
                print(f"Erro ao avaliar {model_name}: {e}")
        
        return evaluation_results
    
    def create_ensemble_model(self, training_results: Dict) -> Optional[VotingRegressor]:
        """Cria modelo ensemble com os melhores modelos"""
        # Selecionar modelos com CV score > 0
        good_models = [(name, result['model']) 
                      for name, result in training_results.items() 
                      if result['model'] is not None and result.get('cv_mean', -1) > 0]
        
        if len(good_models) < 2:
            print("Poucos modelos válidos para ensemble")
            return None
        
        ensemble = VotingRegressor(good_models)
        print(f"Ensemble criado com {len(good_models)} modelos")
        
        return ensemble
    
    def get_best_model(self, evaluation_results: Dict) -> Tuple[Optional[str], Optional[Dict]]:
        """Retorna o melhor modelo baseado no R² score"""
        if not evaluation_results:
            return None, None
        
        best_model_name = max(evaluation_results.keys(), 
                             key=lambda x: evaluation_results[x]['r2'])
        
        return best_model_name, evaluation_results[best_model_name]
    
    def predict_next_prices(self, df: pd.DataFrame, model_name: str = 'random_forest') -> Dict:
        """Prediz próximos preços usando modelo treinado"""
        if model_name not in self.models:
            raise ValueError(f"Modelo {model_name} não encontrado")
        
        # Preparar últimas features
        df_features = self.feature_engineer.engineer_all_features(df, self.forecast_horizon)
        latest_features = df_features[self.feature_engineer.feature_names].iloc[-1:].dropna()
        
        if latest_features.empty:
            return {'error': 'Não foi possível extrair features dos dados'}
        
        # Escalar e predizer
        model = self.models[model_name]
        scaler = self.scalers[model_name]
        
        X_scaled = scaler.transform(latest_features)
        predicted_return = model.predict(X_scaled)[0]
        
        # Converter para preço
        current_price = df['close'].iloc[-1]
        predicted_price = current_price * (1 + predicted_return)
        
        # Probabilidade/confiança da direção
        direction = 'UP' if predicted_return > 0 else 'DOWN'
        confidence = abs(predicted_return) * 100  # Simples: maior mudança = maior confiança
        
        result = {
            'current_price': current_price,
            'predicted_return': predicted_return,
            'predicted_price': predicted_price,
            'direction': direction,
            'confidence': min(confidence, 100),  # Cap em 100%
            'model_used': model_name
        }
        
        self.predictions_history.append(result)
        
        return result
    
    def create_prediction_chart(self, df: pd.DataFrame, predictions: pd.Series, 
                              actual: pd.Series) -> go.Figure:
        """Cria gráfico comparando predições vs valores reais"""
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=['Preços: Real vs Predito', 'Retornos: Real vs Predito'],
            vertical_spacing=0.1
        )
        
        # Preparar dados
        dates = df['open_time'].iloc[-len(predictions):]
        current_prices = df['close'].iloc[-len(predictions):]
        predicted_prices = current_prices * (1 + predictions)
        actual_prices = current_prices * (1 + actual)
        
        # Gráfico de preços
        fig.add_trace(
            go.Scatter(x=dates, y=actual_prices, name='Preço Real', 
                      line=dict(color='blue')),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=predicted_prices, name='Preço Predito', 
                      line=dict(color='red', dash='dash')),
            row=1, col=1
        )
        
        # Gráfico de retornos
        fig.add_trace(
            go.Scatter(x=dates, y=actual, name='Retorno Real', 
                      line=dict(color='blue')),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=predictions, name='Retorno Predito', 
                      line=dict(color='red', dash='dash')),
            row=2, col=1
        )
        
        fig.update_layout(
            title='Análise de Predições ML',
            height=800
        )
        
        return fig
    
    def run_complete_analysis(self, symbol: str, timeframe: str = '60', 
                            emas: List[int] = [9, 21]) -> Dict:
        """Executa análise completa de ML"""
        print(f"=== Análise ML Completa para {symbol} ===")
        
        try:
            # Carregar dados
            df = busca_velas(symbol, timeframe, emas)
            print(f"Dados carregados: {len(df)} velas")
            
            # Preparar dados
            X_train, X_test, y_train, y_test = self.prepare_data(df)
            
            # Treinar modelos
            training_results = self.train_models(X_train, y_train)
            
            # Avaliar modelos
            evaluation_results = self.evaluate_models(X_test, y_test, training_results)
            
            # Melhor modelo
            best_model_name, best_result = self.get_best_model(evaluation_results)
            
            if best_model_name is None or best_result is None:
                return {'error': 'Nenhum modelo válido foi treinado com sucesso'}
            
            # Predição próximo período
            next_prediction = self.predict_next_prices(df, best_model_name)
            
            # Feature importance do melhor modelo
            feature_importance = self.feature_importance.get(best_model_name)
            
            results = {
                'symbol': symbol,
                'best_model': best_model_name,
                'model_performance': best_result,
                'next_prediction': next_prediction,
                'feature_importance': feature_importance,
                'all_results': evaluation_results,
                'data_shape': df.shape
            }
            
            print(f"\n=== Resumo ===")
            print(f"Melhor modelo: {best_model_name}")
            print(f"R² Score: {best_result['r2']:.4f}")
            print(f"Predição próxima: {next_prediction['direction']} ({next_prediction['confidence']:.1f}% confiança)")
            print(f"Preço atual: ${next_prediction['current_price']:.4f}")
            print(f"Preço predito: ${next_prediction['predicted_price']:.4f}")
            
            return results
            
        except Exception as e:
            print(f"Erro na análise: {e}")
            return {'error': str(e)}

def teste_ml_predictor():
    """Teste do sistema de predição ML"""
    predictor = MLPredictor(forecast_horizon=1)
    results = predictor.run_complete_analysis('BTCUSDT', '60', [9, 21])
    
    if 'error' not in results:
        print("\n=== Top 10 Features Mais Importantes ===")
        if results['feature_importance'] is not None:
            print(results['feature_importance'].head(10))
    
    return results

if __name__ == "__main__":
    results = teste_ml_predictor()