const { createApp } = Vue;

createApp({
    data() {
        return {
            // Main Performance Metrics
            totalProfit: +18.7,
            totalTrades: 423,
            winRate: 68.2,
            avgRR: 2.8,
            
            // Live Bots Data
            liveBots: [
                {
                    id: 1,
                    symbol: 'BTCUSDT',
                    status: 'online',
                    currentTrade: {
                        side: 'buy',
                        entry: '99,234',
                        pnl: +15.2
                    },
                    dailyPnl: +2.4,
                    winRate: 68
                },
                {
                    id: 2,
                    symbol: 'XRPUSDT',
                    status: 'online',
                    currentTrade: null,
                    dailyPnl: +0.8,
                    winRate: 62
                },
                {
                    id: 3,
                    symbol: 'SOLUSDT',
                    status: 'online',
                    currentTrade: {
                        side: 'sell',
                        entry: '200.45',
                        pnl: +42.3
                    },
                    dailyPnl: +5.1,
                    winRate: 64
                },
                {
                    id: 4,
                    symbol: 'PEPEUSDT',
                    status: 'offline',
                    currentTrade: null,
                    dailyPnl: 0.0,
                    winRate: 58
                }
            ],
            
            // ML Data from your actual reports
            mlData: {
                currentPrice: 113456,
                predictedPrice: 134567,
                direction: 'UP',
                confidence: 68.4,
                accuracy: 66.8,
                topFeatures: [
                    { name: 'RSI_lag_3', importance: 0.0696 },
                    { name: 'OBV', importance: 0.0434 },
                    { name: 'EMA_200', importance: 0.0319 },
                    { name: 'Resistance_50', importance: 0.0312 },
                    { name: 'Lower_Shadow', importance: 0.0252 }
                ]
            },
            
            // Strategy Performance Data
            strategies: [
                { id: 'scalping', name: 'BTC Scalping' },
                { id: 'momentum', name: 'Momentum Trading' },
                { id: 'reversal', name: 'Reversal Strategy' }
            ],
            activeStrategy: 'scalping',
            
            // Risk Management Metrics
            riskMetrics: {
                riskPerTrade: 1.0,
                currentRR: 2.8,
                maxDrawdown: 8.7,
                avgHoldTime: 3.2
            },
            
            // Analytics Tabs
            analyticsTabs: [
                { id: 'heatmap', label: 'Heatmap', icon: 'fas fa-th' },
                { id: 'correlation', label: 'Correlação', icon: 'fas fa-project-diagram' },
                { id: 'distribution', label: 'Distribuição', icon: 'fas fa-chart-area' }
            ],
            activeAnalytics: 'heatmap',
            
            // Chart instances
            charts: {}
        };
    },
    
    computed: {
        currentStrategy() {
            const strategies = {
                scalping: {
                    totalReturn: 18.7,
                    sharpeRatio: 1.87,
                    maxDrawdown: 8.7,
                    winRate: 68
                },
                momentum: {
                    totalReturn: 14.2,
                    sharpeRatio: 1.54,
                    maxDrawdown: 12.1,
                    winRate: 62
                },
                reversal: {
                    totalReturn: 22.3,
                    sharpeRatio: 2.12,
                    maxDrawdown: 6.3,
                    winRate: 74
                }
            };
            return strategies[this.activeStrategy] || strategies.scalping;
        }
    },
    
    mounted() {
        this.initializeCharts();
        this.loadRealTimeData();
        this.startRealTimeUpdates();
    },
    
    methods: {
        async loadRealTimeData() {
            try {
                // Load ML analysis data
                const mlResponse = await fetch('/api/ml-analysis');
                if (mlResponse.ok) {
                    const mlData = await mlResponse.json();
                    this.updateMLData(mlData);
                }
                
                // Load trading performance
                const performanceResponse = await fetch('/api/performance');
                if (performanceResponse.ok) {
                    const performance = await performanceResponse.json();
                    this.updatePerformanceData(performance);
                }
            } catch (error) {
                console.log('Using demo data - API endpoints not available');
                this.loadDemoData();
            }
        },
        
        loadDemoData() {
            // Simulate real-time data updates with demo data
            console.log('Loading demo data for presentation');
        },
        
        updateMLData(data) {
            if (data.best_model) {
                this.mlData.accuracy = (data.best_model.direction_accuracy * 100).toFixed(1);
            }
            if (data.prediction) {
                this.mlData.currentPrice = data.prediction.current_price;
                this.mlData.predictedPrice = data.prediction.predicted_price;
                this.mlData.direction = data.prediction.direction;
                this.mlData.confidence = (Math.abs(data.prediction.predicted_return) * 100).toFixed(1);
            }
            if (data.top_features) {
                this.mlData.topFeatures = data.top_features.slice(0, 5).map(f => ({
                    name: f.feature.replace(/_/g, ' ').toUpperCase(),
                    importance: f.importance
                }));
            }
        },
        
        updatePerformanceData(data) {
            // Update performance metrics from real data
            if (data.totalReturn) this.totalProfit = data.totalReturn;
            if (data.totalTrades) this.totalTrades = data.totalTrades;
            if (data.winRate) this.winRate = data.winRate;
            if (data.avgRR) this.avgRR = data.avgRR;
        },
        
        initializeCharts() {
            this.createHeroChart();
            this.createStrategyChart();
            this.createBacktestChart();
            this.createHeatmap();
            this.createCorrelationChart();
            this.createDistributionChart();
        },
        
        createHeroChart() {
            const ctx = document.getElementById('heroChart');
            if (!ctx) return;
            
            this.charts.hero = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: this.generateTimeLabels(30),
                    datasets: [{
                        label: 'Performance',
                        data: this.generatePerformanceData(30),
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            display: false
                        },
                        y: {
                            display: false
                        }
                    },
                    elements: {
                        line: {
                            borderWidth: 3
                        }
                    }
                }
            });
        },
        
        createStrategyChart() {
            const ctx = document.getElementById('strategyChart');
            if (!ctx) return;
            
            this.charts.strategy = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun'],
                    datasets: [{
                        label: 'Retorno Mensal (%)',
                        data: [12.5, 8.3, 15.7, 9.2, 18.4, 11.8],
                        backgroundColor: 'rgba(0, 212, 255, 0.6)',
                        borderColor: '#00d4ff',
                        borderWidth: 1,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#94a3b8'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            });
        },
        
        createBacktestChart() {
            const ctx = document.getElementById('backtestChart');
            if (!ctx) return;
            
            this.charts.backtest = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: this.generateTimeLabels(365),
                    datasets: [{
                        label: 'Equity Curve',
                        data: this.generateEquityCurve(365),
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#94a3b8'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#94a3b8',
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        },
        
        createHeatmap() {
            const data = this.generateHeatmapData();
            
            Plotly.newPlot('heatmapChart', [{
                z: data.z,
                x: data.x,
                y: data.y,
                type: 'heatmap',
                colorscale: 'RdYlBu',
                reversescale: true
            }], {
                title: 'Performance por Hora e Dia da Semana',
                xaxis: { title: 'Hora do Dia' },
                yaxis: { title: 'Dia da Semana' },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#ffffff' }
            });
        },
        
        createCorrelationChart() {
            const indicators = ['RSI', 'EMA_9', 'EMA_21', 'Volume', 'ATR'];
            const correlationMatrix = this.generateCorrelationMatrix(indicators);
            
            Plotly.newPlot('correlationChart', [{
                z: correlationMatrix,
                x: indicators,
                y: indicators,
                type: 'heatmap',
                colorscale: 'RdBu',
                reversescale: true
            }], {
                title: 'Matriz de Correlação dos Indicadores',
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#ffffff' }
            });
        },
        
        createDistributionChart() {
            const returns = this.generateReturnsDistribution();
            
            Plotly.newPlot('distributionChart', [{
                x: returns,
                type: 'histogram',
                nbinsx: 50,
                marker: {
                    color: 'rgba(0, 212, 255, 0.6)',
                    line: {
                        color: '#00d4ff',
                        width: 1
                    }
                }
            }], {
                title: 'Distribuição dos Retornos por Trade',
                xaxis: { title: 'Retorno (%)' },
                yaxis: { title: 'Frequência' },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#ffffff' }
            });
        },
        
        startRealTimeUpdates() {
            // Update live data every 30 seconds
            setInterval(() => {
                this.updateLiveBots();
                this.updateMLPrediction();
            }, 30000);
        },
        
        updateLiveBots() {
            // Simulate real-time bot updates
            this.liveBots.forEach(bot => {
                if (bot.status === 'online' && Math.random() > 0.7) {
                    if (bot.currentTrade) {
                        // Update PnL
                        const change = (Math.random() - 0.5) * 2;
                        bot.currentTrade.pnl += change;
                        bot.currentTrade.pnl = Math.round(bot.currentTrade.pnl * 100) / 100;
                    }
                    
                    // Update daily PnL
                    const dailyChange = (Math.random() - 0.5) * 0.5;
                    bot.dailyPnl += dailyChange;
                    bot.dailyPnl = Math.round(bot.dailyPnl * 100) / 100;
                }
            });
        },
        
        updateMLPrediction() {
            // Simulate ML prediction updates
            const change = (Math.random() - 0.5) * 1000;
            this.mlData.predictedPrice += change;
            this.mlData.predictedPrice = Math.round(this.mlData.predictedPrice * 100) / 100;
            
            this.mlData.direction = this.mlData.predictedPrice > this.mlData.currentPrice ? 'UP' : 'DOWN';
            
            const confidenceChange = (Math.random() - 0.5) * 10;
            this.mlData.confidence += confidenceChange;
            this.mlData.confidence = Math.max(0, Math.min(100, this.mlData.confidence));
            this.mlData.confidence = Math.round(this.mlData.confidence * 10) / 10;
        },
        
        // Data generation helpers
        generateTimeLabels(days) {
            const labels = [];
            const now = new Date();
            for (let i = days; i >= 0; i--) {
                const date = new Date(now);
                date.setDate(date.getDate() - i);
                labels.push(date.toLocaleDateString());
            }
            return labels;
        },
        
        generatePerformanceData(days) {
            const data = [];
            let value = 1000;
            for (let i = 0; i < days; i++) {
                const change = (Math.random() - 0.4) * 50;
                value += change;
                data.push(Math.round(value));
            }
            return data;
        },
        
        generateEquityCurve(days) {
            const data = [];
            let equity = 1000;
            for (let i = 0; i < days; i++) {
                const dailyReturn = (Math.random() - 0.45) * 0.05;
                equity *= (1 + dailyReturn);
                data.push(Math.round(equity));
            }
            return data;
        },
        
        generateHeatmapData() {
            const hours = Array.from({length: 24}, (_, i) => i);
            const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            const z = [];
            
            for (let day = 0; day < 7; day++) {
                const row = [];
                for (let hour = 0; hour < 24; hour++) {
                    // Simulate higher returns during trading hours
                    let performance = Math.random() * 2 - 1;
                    if (hour >= 8 && hour <= 16) {
                        performance += 0.5;
                    }
                    row.push(performance);
                }
                z.push(row);
            }
            
            return { x: hours, y: days, z: z };
        },
        
        generateCorrelationMatrix(indicators) {
            const matrix = [];
            for (let i = 0; i < indicators.length; i++) {
                const row = [];
                for (let j = 0; j < indicators.length; j++) {
                    if (i === j) {
                        row.push(1);
                    } else {
                        row.push((Math.random() - 0.5) * 2);
                    }
                }
                matrix.push(row);
            }
            return matrix;
        },
        
        generateReturnsDistribution() {
            const returns = [];
            for (let i = 0; i < 1000; i++) {
                // Generate normally distributed returns
                const u1 = Math.random();
                const u2 = Math.random();
                const z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
                returns.push(z0 * 2 + 0.5); // Mean 0.5%, std 2%
            }
            return returns;
        }
    },
    
    watch: {
        activeStrategy(newStrategy) {
            // Update strategy chart when strategy changes
            if (this.charts.strategy) {
                // Update chart data based on selected strategy
                this.updateStrategyChart(newStrategy);
            }
        },
        
        activeAnalytics(newTab) {
            // Recreate charts when analytics tab changes
            this.$nextTick(() => {
                if (newTab === 'heatmap') {
                    this.createHeatmap();
                } else if (newTab === 'correlation') {
                    this.createCorrelationChart();
                } else if (newTab === 'distribution') {
                    this.createDistributionChart();
                }
            });
        }
    }
}).mount('#app');