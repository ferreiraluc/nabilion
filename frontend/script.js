const { createApp } = Vue;

createApp({
    data() {
        return {
            totalBots: 8,
            supportedPairs: 15,
            backtestingAccuracy: 87,
            riskManagement: 2.5,
            activeTab: 'performance',
            chartTabs: [
                { id: 'performance', label: 'Performance', icon: 'fas fa-chart-line' },
                { id: 'trades', label: 'Trades', icon: 'fas fa-exchange-alt' },
                { id: 'risk', label: 'Risco', icon: 'fas fa-shield-alt' }
            ],
            tradingBots: [
                {
                    id: 1,
                    name: 'XRP Live',
                    symbol: 'XRPUSDT',
                    timeframe: '1H',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'online'
                },
                {
                    id: 2,
                    name: 'Scalping BTC',
                    symbol: 'BTCUSDT',
                    timeframe: '15M',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'online'
                },
                {
                    id: 3,
                    name: 'Trading XRP',
                    symbol: 'XRPUSDT',
                    timeframe: '30M',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'online'
                },
                {
                    id: 4,
                    name: '1000PEPE Scalping',
                    symbol: 'PEPEUSDT',
                    timeframe: '1H',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'online'
                },
                {
                    id: 5,
                    name: 'Solana Scalp',
                    symbol: 'SOLUSDT',
                    timeframe: '15M',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'online'
                },
                {
                    id: 6,
                    name: 'Quantum Trading',
                    symbol: 'BTCUSDT',
                    timeframe: '1H',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'online'
                },
                {
                    id: 7,
                    name: 'Reverse Trading',
                    symbol: 'BTCUSDT',
                    timeframe: '30M',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'offline'
                },
                {
                    id: 8,
                    name: 'NEWT Scalping',
                    symbol: 'NEWTUSDT',
                    timeframe: '15M',
                    leverage: 1,
                    ema_fast: 9,
                    ema_slow: 21,
                    status: 'offline'
                }
            ]
        }
    },
    mounted() {
        this.initChart();
        this.animateStats();
    },
    watch: {
        activeTab() {
            this.updateChart();
        }
    },
    methods: {
        initChart() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            
            this.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul'],
                    datasets: [{
                        label: 'Performance (%)',
                        data: [5.2, 8.7, 12.1, 15.8, 18.9, 22.3, 28.7],
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
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
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#b0b0b0'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#b0b0b0'
                            }
                        }
                    }
                }
            });
        },
        updateChart() {
            const datasets = {
                performance: {
                    label: 'Performance (%)',
                    data: [5.2, 8.7, 12.1, 15.8, 18.9, 22.3, 28.7],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)'
                },
                trades: {
                    label: 'Trades Executados',
                    data: [45, 52, 61, 73, 68, 79, 84],
                    borderColor: '#4ecdc4',
                    backgroundColor: 'rgba(78, 205, 196, 0.1)'
                },
                risk: {
                    label: 'Score de Risco',
                    data: [2.1, 1.8, 2.3, 1.9, 2.0, 1.7, 1.6],
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)'
                }
            };
            
            this.chart.data.datasets[0] = {
                ...datasets[this.activeTab],
                borderWidth: 3,
                fill: true,
                tension: 0.4
            };
            this.chart.update();
        },
        animateStats() {
            // Animate stat values on load
            setTimeout(() => {
                const statCards = document.querySelectorAll('.stat-card');
                statCards.forEach((card, index) => {
                    setTimeout(() => {
                        card.style.transform = 'translateY(0)';
                        card.style.opacity = '1';
                    }, index * 100);
                });
            }, 300);
        }
    }
}).mount('#app');