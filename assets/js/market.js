/**
 * 市场行情速览
 * 从 static/market-data.json 加载数据并渲染到侧边栏
 */
(function () {
    'use strict';

    const container = document.getElementById('marketQuotes');
    if (!container) return;

    async function loadMarketData() {
        try {
            const res = await fetch('/daily-news/market-data.json');
            if (!res.ok) return;
            const data = await res.json();
            renderMarket(data);
        } catch (e) {
            container.innerHTML = '<p style="font-size:12px;color:#999;">行情加载失败</p>';
        }
    }

    function renderMarket(data) {
        if (!data || !data.indices) {
            container.innerHTML = '<p style="font-size:12px;color:#999;">暂无数据</p>';
            return;
        }

        const html = data.indices.map(item => {
            const changeClass = item.change >= 0 ? 'up' : 'down';
            const changeStr = item.change >= 0
                ? `+${item.change.toFixed(2)}%`
                : `${item.change.toFixed(2)}%`;
            return `
                <div class="market-item">
                    <span class="name">${item.name}</span>
                    <span class="change ${changeClass}">${changeStr}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    loadMarketData();
})();
