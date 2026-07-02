/**
 * 搜索功能 - 基于 MiniSearch v7.1.1 的纯前端全文检索
 * 中文使用 bigram（相邻双字组合）分词，避免单字匹配导致的误召回
 */
(function () {
    'use strict';

    let searchIndex = null;
    let miniSearch = null;

    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const searchResults = document.getElementById('searchResults');

    /**
     * 中文 bigram 分词函数
     * 中文字符提取相邻双字组合（bigram），英文按空格保留完整 token
     * 例如："美团推出" → ["美团", "团推", "推出"]
     * 这样搜索"美团"时只会匹配包含"美团"的文本，不会匹配"美联储"
     */
    function chineseTokenize(text) {
        var tokens = [];
        var current = '';      // 当前英文 token 缓冲
        var chineseChars = []; // 当前连续中文字符缓冲

        function flushChinese() {
            if (chineseChars.length === 1) {
                // 单个中文字也要作为 token（否则单字搜索无法匹配）
                tokens.push(chineseChars[0]);
            } else if (chineseChars.length >= 2) {
                // 生成所有相邻 bigram
                for (var j = 0; j < chineseChars.length - 1; j++) {
                    tokens.push(chineseChars[j] + chineseChars[j + 1]);
                }
            }
            chineseChars = [];
        }

        for (var i = 0; i < text.length; i++) {
            var ch = text[i];
            if (/[\u4e00-\u9fff]/.test(ch)) {
                // 遇到中文字，先清空英文缓冲
                if (current) { tokens.push(current); current = ''; }
                chineseChars.push(ch);
            } else if (/\s/.test(ch)) {
                // 空白符：清空所有缓冲
                if (current) { tokens.push(current); current = ''; }
                flushChinese();
            } else {
                // 英文/数字/符号
                flushChinese();
                current += ch;
            }
        }
        // 清空尾部缓冲
        if (current) tokens.push(current);
        flushChinese();

        return tokens;
    }

    // 加载搜索索引
    async function loadIndex() {
        try {
            const res = await fetch('/daily-news/search-index.json');
            if (!res.ok) return;
            searchIndex = await res.json();

            // 初始化 MiniSearch
            if (typeof MiniSearch !== 'undefined') {
                miniSearch = new MiniSearch({
                    fields: ['title', 'summary'],
                    storeFields: ['title', 'summary', 'date', 'category', 'source', 'source_url'],
                    tokenize: chineseTokenize,
                    searchOptions: {
                        boost: { title: 2 },
                        fuzzy: false,
                        prefix: true,
                        tokenize: chineseTokenize
                    }
                });
                miniSearch.addAll(searchIndex);
                console.log('MiniSearch 索引加载完成，共 ' + searchIndex.length + ' 条');
            } else {
                console.warn('MiniSearch CDN 未加载，降级为字符串匹配');
            }
        } catch (e) {
            console.warn('搜索索引加载失败:', e);
        }
    }

    // 根据日期生成对应的新闻页链接
    function getDatePageUrl(dateStr) {
        if (!dateStr) return null;
        var parts = dateStr.split('-');
        if (parts.length !== 3) return null;
        return '/daily-news/daily/' + parts[0] + '/' + parts[1] + '/' + dateStr + '/';
    }

    // 执行搜索
    function doSearch() {
        var query = searchInput.value.trim();
        if (!query) {
            searchResults.style.display = 'none';
            return;
        }

        var results = [];

        if (miniSearch) {
            results = miniSearch.search(query, { limit: 20 });
        } else if (searchIndex) {
            // 降级：简单字符串匹配
            var lowerQuery = query.toLowerCase();
            results = searchIndex.filter(function (item) {
                return item.title.toLowerCase().includes(lowerQuery) ||
                    (item.summary && item.summary.toLowerCase().includes(lowerQuery));
            }).slice(0, 20);
        }

        renderResults(results);
    }

    // 清除搜索结果
    function clearSearch() {
        searchInput.value = '';
        searchResults.style.display = 'none';
    }

    // 渲染搜索结果
    function renderResults(results) {
        if (results.length === 0) {
            searchResults.innerHTML =
                '<div class="search-results-header">' +
                '<span>未找到相关新闻</span>' +
                '<button class="back-btn" id="backToNews">✕ 关闭搜索</button>' +
                '</div>';
            searchResults.style.display = 'block';
            document.getElementById('backToNews').addEventListener('click', clearSearch);
            return;
        }

        var header =
            '<div class="search-results-header">' +
            '<span>找到 ' + results.length + ' 条相关新闻</span>' +
            '<button class="back-btn" id="backToNews">✕ 关闭搜索</button>' +
            '</div>';

        var items = results.map(function (item) {
            var dateUrl = getDatePageUrl(item.date);
            var dateLink = dateUrl
                ? '<a href="' + dateUrl + '" class="result-date-link">' + item.date + '</a>'
                : (item.date || '');

            return '<div class="result-item">' +
                '<div class="result-title">' +
                '<a href="' + (item.source_url || '#') + '">' + item.title + '</a>' +
                '</div>' +
                '<div class="result-meta">' +
                '📅 ' + dateLink + ' · ' + (item.source || '') + ' · ' + getCategoryLabel(item.category) +
                '</div>' +
                (item.summary ? '<div style="font-size:13px;color:#8c8c8c;margin-top:4px;">' + item.summary + '</div>' : '') +
                '</div>';
        }).join('');

        searchResults.innerHTML = header + items;
        searchResults.style.display = 'block';

        document.getElementById('backToNews').addEventListener('click', clearSearch);
    }

    function getCategoryLabel(cat) {
        var map = { internet: '🌐 互联网与商业', ai: '🤖 AI前沿', finance: '💰 金融市场' };
        return map[cat] || cat || '';
    }

    // 事件绑定
    if (searchBtn) searchBtn.addEventListener('click', doSearch);
    if (searchInput) {
        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') doSearch();
        });
    }

    // 页面加载后初始化
    loadIndex();
})();
