#!/usr/bin/env python3
"""
Quantitative Analyzer - Sistema Principal de Análise Quantitativa
Integra feature engineering, ML predictions e visualizações
"""

import pandas as pd
import numpy as np
from datetime import datetime
from feature_engineering import FeatureEngineer
from ml_predictor import MLPredictor
from chart_predictor import ChartPredictor
from funcoes_bybit import busca_velas
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

class QuantitativeAnalyzer:
    """Sistema principal de análise quantitativa para trading"""
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.ml_predictor = MLPredictor()
        self.chart_predictor = ChartPredictor()
        self.analysis_history = []
    
    def analyze_symbol(self, symbol: str, timeframe: str = '60', 
                      emas: List[int] = [9, 21], 
                      save_charts: bool = True) -> Dict:
        """Análise completa de um símbolo"""
        
        print(f"\n{'='*50}")
        print(f"ANÁLISE QUANTITATIVA - {symbol}")
        print(f"Timeframe: {timeframe}m | EMAs: {emas}")
        print(f"{'='*50}")
        
        try:
            # 1. Carregar dados
            print("📊 Carregando dados...")
            df = busca_velas(symbol, timeframe, emas)
            
            # 2. Feature Engineering
            print("🔧 Executando feature engineering...")
            df_features = self.feature_engineer.engineer_all_features(df)
            
            # 3. ML Analysis
            print("🤖 Executando análise ML...")
            ml_results = self.ml_predictor.run_complete_analysis(symbol, timeframe, emas)
            
            # 4. Gerar relatório
            analysis_report = self._generate_analysis_report(
                symbol, df, df_features, ml_results
            )
            
            # 5. Criar visualizações (opcional)
            charts = None
            if save_charts:
                print("📈 Criando visualizações...")
                dashboard = self.chart_predictor.create_comprehensive_dashboard(
                    symbol, timeframe, emas
                )
                if dashboard and dashboard.get('charts'):
                    # Salvar charts
                    saved_files = self.chart_predictor.save_charts_html(
                        dashboard['charts'], symbol, f"charts/{symbol}/"
                    )
                    analysis_report['chart_files'] = saved_files
            
            # 6. Salvar na história
            analysis_result = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'timeframe': timeframe,
                'report': analysis_report,
                'charts': charts
            }
            
            self.analysis_history.append(analysis_result)
            
            # 7. Exibir resumo
            self._print_analysis_summary(analysis_report)
            
            return analysis_result
            
        except Exception as e:
            error_msg = f"Erro na análise de {symbol}: {str(e)}"
            print(f"❌ {error_msg}")
            return {'error': error_msg}
    
    def _generate_analysis_report(self, symbol: str, df: pd.DataFrame, 
                                df_features: pd.DataFrame, ml_results: Dict) -> Dict:
        """Gera relatório completo da análise"""
        
        current_price = df['close'].iloc[-1]
        
        # Estatísticas básicas
        price_stats = {
            'current_price': current_price,
            'price_change_24h': (df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24] * 100,
            'volatility_24h': df['close'].pct_change().tail(24).std() * 100,
            'volume_24h': df['volume'].tail(24).sum(),
            'rsi_current': df['RSI'].iloc[-1],
        }
        
        # Features mais importantes
        feature_analysis = {
            'total_features': len(self.feature_engineer.feature_names),
            'top_features': ml_results.get('feature_importance', pd.DataFrame()).head(10).to_dict('records') if ml_results.get('feature_importance') is not None else [],
            'data_quality': {
                'samples': len(df_features),
                'missing_ratio': df_features.isnull().sum().sum() / (len(df_features) * len(df_features.columns)),
                'feature_correlation': self._calculate_feature_correlation(df_features)
            }
        }
        
        # Análise ML
        ml_analysis = {
            'best_model': ml_results.get('best_model', 'N/A'),
            'model_performance': ml_results.get('model_performance', {}),
            'next_prediction': ml_results.get('next_prediction', {}),
            'model_comparison': ml_results.get('all_results', {})
        }
        
        # Análise técnica avançada
        technical_analysis = self._advanced_technical_analysis(df, df_features)
        
        # Score geral
        overall_score = self._calculate_overall_score(price_stats, ml_analysis, technical_analysis)
        
        report = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'price_stats': price_stats,
            'feature_analysis': feature_analysis,
            'ml_analysis': ml_analysis,
            'technical_analysis': technical_analysis,
            'overall_score': overall_score,
            'recommendation': self._generate_recommendation(overall_score, ml_analysis)
        }
        
        return report
    
    def _calculate_feature_correlation(self, df_features: pd.DataFrame) -> Dict:
        """Calcula correlações entre features principais"""
        
        key_features = ['RSI', 'volume_ratio', 'bb_position', 'macd', 'atr_ratio']
        available_features = [f for f in key_features if f in df_features.columns]
        
        if len(available_features) < 2:
            return {}
        
        corr_matrix = df_features[available_features].corr()
        
        return {
            'high_correlations': [],
            'avg_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
        }
    
    def _advanced_technical_analysis(self, df: pd.DataFrame, df_features: pd.DataFrame) -> Dict:
        """Análise técnica avançada"""
        
        analysis = {}
        
        # Trend Analysis
        ema_cols = [col for col in df.columns if col.startswith('EMA_')]
        if len(ema_cols) >= 2:
            ema_fast = df[ema_cols[0]].iloc[-1]
            ema_slow = df[ema_cols[1]].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            trend_strength = abs(ema_fast - ema_slow) / current_price * 100
            trend_direction = 'BULLISH' if ema_fast > ema_slow else 'BEARISH'
            
            analysis['trend'] = {
                'direction': trend_direction,
                'strength': trend_strength,
                'price_above_ema_fast': current_price > ema_fast,
                'price_above_ema_slow': current_price > ema_slow
            }
        
        # Support/Resistance
        if 'support_20' in df_features.columns and 'resistance_20' in df_features.columns:
            support = df_features['support_20'].iloc[-1]
            resistance = df_features['resistance_20'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            analysis['support_resistance'] = {
                'support_level': support,
                'resistance_level': resistance,
                'distance_to_support': (current_price - support) / current_price * 100,
                'distance_to_resistance': (resistance - current_price) / current_price * 100
            }
        
        # Volume Analysis
        if 'volume_ratio' in df_features.columns:
            current_volume_ratio = df_features['volume_ratio'].iloc[-1]
            avg_volume_ratio = df_features['volume_ratio'].tail(20).mean()
            
            analysis['volume'] = {
                'current_ratio': current_volume_ratio,
                'average_ratio': avg_volume_ratio,
                'volume_spike': current_volume_ratio > avg_volume_ratio * 1.5
            }
        
        # Volatility Analysis
        if 'atr_ratio' in df_features.columns:
            current_atr = df_features['atr_ratio'].iloc[-1]
            avg_atr = df_features['atr_ratio'].tail(20).mean()
            
            analysis['volatility'] = {
                'current_atr_ratio': current_atr,
                'average_atr_ratio': avg_atr,
                'volatility_regime': 'HIGH' if current_atr > avg_atr * 1.2 else 'LOW'
            }
        
        return analysis
    
    def _calculate_overall_score(self, price_stats: Dict, ml_analysis: Dict, 
                               technical_analysis: Dict) -> Dict:
        """Calcula score geral da análise"""
        
        scores = {}
        
        # ML Score (baseado na performance do modelo)
        model_perf = ml_analysis.get('model_performance', {})
        r2_score = model_perf.get('r2', 0)
        direction_acc = model_perf.get('direction_accuracy', 0.5)
        
        ml_score = (max(r2_score, 0) * 50) + (direction_acc * 50)
        scores['ml_score'] = min(ml_score, 100)
        
        # Technical Score
        tech_score = 50  # Base score
        
        # Trend bonus/penalty
        trend_info = technical_analysis.get('trend', {})
        if trend_info:
            trend_strength = trend_info.get('strength', 0)
            tech_score += min(trend_strength * 2, 20)
        
        # Volume bonus
        volume_info = technical_analysis.get('volume', {})
        if volume_info and volume_info.get('volume_spike', False):
            tech_score += 10
        
        scores['technical_score'] = min(tech_score, 100)
        
        # Overall Score (média ponderada)
        overall = (scores['ml_score'] * 0.6) + (scores['technical_score'] * 0.4)
        scores['overall'] = overall
        
        return scores
    
    def _generate_recommendation(self, scores: Dict, ml_analysis: Dict) -> Dict:
        """Gera recomendação baseada na análise"""
        
        overall_score = scores.get('overall', 0)
        prediction = ml_analysis.get('next_prediction', {})
        
        if overall_score >= 70:
            action = 'STRONG_BUY' if prediction.get('direction') == 'UP' else 'STRONG_SELL'
            confidence = 'HIGH'
        elif overall_score >= 50:
            action = 'BUY' if prediction.get('direction') == 'UP' else 'SELL'
            confidence = 'MEDIUM'
        else:
            action = 'HOLD'
            confidence = 'LOW'
        
        return {
            'action': action,
            'confidence': confidence,
            'score': overall_score,
            'reasoning': f"Based on ML score: {scores.get('ml_score', 0):.1f}, Technical score: {scores.get('technical_score', 0):.1f}"
        }
    
    def _print_analysis_summary(self, report: Dict):
        """Imprime resumo da análise"""
        
        print(f"\n📋 RESUMO DA ANÁLISE")
        print(f"{'='*30}")
        
        # Preço atual
        price_stats = report['price_stats']
        print(f"💰 Preço Atual: ${price_stats['current_price']:,.2f}")
        print(f"📈 Variação 24h: {price_stats['price_change_24h']:+.2f}%")
        print(f"📊 RSI: {price_stats['rsi_current']:.1f}")
        
        # ML Analysis
        ml_analysis = report['ml_analysis']
        best_model = ml_analysis['best_model']
        model_perf = ml_analysis['model_performance']
        prediction = ml_analysis['next_prediction']
        
        print(f"\n🤖 ANÁLISE ML")
        print(f"Melhor Modelo: {best_model}")
        print(f"R² Score: {model_perf.get('r2', 0):.4f}")
        print(f"Acurácia Direcional: {model_perf.get('direction_accuracy', 0):.1%}")
        print(f"Predição: {prediction.get('direction', 'N/A')} ({prediction.get('confidence', 0):.1f}% confiança)")
        
        # Recommendation
        recommendation = report['recommendation']
        print(f"\n🎯 RECOMENDAÇÃO")
        print(f"Ação: {recommendation['action']}")
        print(f"Confiança: {recommendation['confidence']}")
        print(f"Score Geral: {recommendation['score']:.1f}/100")
        
        # Top Features
        feature_analysis = report['feature_analysis']
        top_features = feature_analysis['top_features']
        if top_features:
            print(f"\n🔝 TOP 5 FEATURES")
            for i, feature in enumerate(top_features[:5], 1):
                print(f"{i}. {feature['feature']}: {feature['importance']:.4f}")
    
    def analyze_multiple_symbols(self, symbols: List[str], 
                                timeframe: str = '60', 
                                emas: List[int] = [9, 21]) -> List[Dict]:
        """Analisa múltiplos símbolos"""
        
        results = []
        
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}...")
            result = self.analyze_symbol(symbol, timeframe, emas, save_charts=False)
            results.append(result)
        
        # Ranking por score
        valid_results = [r for r in results if 'error' not in r]
        ranking = sorted(valid_results, 
                        key=lambda x: x['report']['overall_score']['overall'], 
                        reverse=True)
        
        print(f"\n🏆 RANKING DOS SÍMBOLOS")
        print(f"{'='*40}")
        for i, result in enumerate(ranking[:10], 1):
            report = result['report']
            symbol = report['symbol']
            score = report['overall_score']['overall']
            recommendation = report['recommendation']['action']
            
            print(f"{i:2d}. {symbol:10s} | Score: {score:5.1f} | {recommendation}")
        
        return results

def teste_sistema_completo():
    """Teste do sistema completo"""
    
    analyzer = QuantitativeAnalyzer()
    
    # Teste com um símbolo
    print("Testando análise individual...")
    result = analyzer.analyze_symbol('BTCUSDT', '60', [9, 21])
    
    # Teste com múltiplos símbolos
    print("\n\nTestando análise múltipla...")
    symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
    results = analyzer.analyze_multiple_symbols(symbols, '60', [9, 21])
    
    return analyzer, results

if __name__ == "__main__":
    analyzer, results = teste_sistema_completo()