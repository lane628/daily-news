/**
 * AI 助手聊天功能
 * 通过 Cloudflare Worker 代理调用 DeepSeek API
 * 支持 SSE 流式响应
 */
(function () {
    'use strict';

    // === 配置 ===
    var WORKER_URL = 'https://your-worker.your-subdomain.workers.dev/chat';

    // === DOM 元素 ===
    var chatBubble = document.getElementById('chatBubble');
    var chatWindow = document.getElementById('chatWindow');
    var chatClose = document.getElementById('chatClose');
    var chatMessages = document.getElementById('chatMessages');
    var chatInput = document.getElementById('chatInput');
    var chatSend = document.getElementById('chatSend');
    var shortcutBtns = document.querySelectorAll('.shortcut-btn');

    var conversationHistory = [];

    // === 切换聊天窗口 ===
    if (chatBubble) {
        chatBubble.addEventListener('click', function () {
            var isVisible = chatWindow.style.display !== 'none';
            chatWindow.style.display = isVisible ? 'none' : 'flex';
            chatBubble.style.display = isVisible ? 'block' : 'none';
        });
    }

    if (chatClose) {
        chatClose.addEventListener('click', function () {
            chatWindow.style.display = 'none';
            chatBubble.style.display = 'block';
        });
    }

    // === 发送消息（SSE 流式） ===
    async function sendMessage(userMsg) {
        if (!userMsg.trim()) return;

        // 显示用户消息
        appendMessage('user', userMsg);
        chatInput.value = '';

        // 收集当前页面新闻作为上下文
        var newsContext = getPageNewsContext();
        conversationHistory.push({ role: 'user', content: userMsg });

        // 创建空的 assistant 消息
        var msgEl = appendMessage('assistant', '');

        try {
            var response = await fetch(WORKER_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: conversationHistory,
                    context: newsContext,
                    stream: true
                })
            });

            if (!response.ok) throw new Error('请求失败');

            // SSE 流式读取
            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var fullText = '';
            var buffer = '';

            while (true) {
                var result = await reader.read();
                if (result.done) break;

                buffer += decoder.decode(result.value, { stream: true });

                // 解析 SSE 数据
                var lines = buffer.split('\n');
                buffer = lines.pop() || '';  // 保留不完整的行

                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i].trim();
                    if (line.startsWith('data: ')) {
                        var data = line.slice(6);
                        if (data === '[DONE]') continue;

                        try {
                            var parsed = JSON.parse(data);
                            var delta = parsed.choices && parsed.choices[0] &&
                                parsed.choices[0].delta && parsed.choices[0].delta.content;
                            if (delta) {
                                fullText += delta;
                                msgEl.textContent = fullText;
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }
            }

            if (!fullText) {
                msgEl.textContent = '抱歉，我暂时无法回答。';
            }
            conversationHistory.push({ role: 'assistant', content: fullText });

        } catch (e) {
            msgEl.textContent = '网络错误，请稍后再试。';
            console.error('Chat error:', e);
        }
    }

    // === 辅助函数 ===
    function appendMessage(role, content) {
        var div = document.createElement('div');
        div.className = 'chat-msg ' + role;
        div.textContent = content;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return div;
    }

    function getPageNewsContext() {
        var newsEl = document.querySelector('.daily-news');
        if (!newsEl) return '';
        return newsEl.innerText.slice(0, 3000);
    }

    // === 事件绑定 ===
    if (chatSend) chatSend.addEventListener('click', function () { sendMessage(chatInput.value); });
    if (chatInput) {
        chatInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') sendMessage(chatInput.value);
        });
    }

    // 快捷按钮
    shortcutBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var prompt = this.dataset.prompt;
            if (prompt) sendMessage(prompt);
        });
    });
})();
