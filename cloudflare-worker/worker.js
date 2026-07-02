/**
 * Cloudflare Worker - AI 助手 API 代理
 * 支持 SSE 流式响应
 *
 * 环境变量（在 Cloudflare Dashboard 配置）：
 * - DEEPSEEK_API_KEY: DeepSeek API 密钥
 */

export default {
    async fetch(request, env) {
        // CORS 预检
        if (request.method === 'OPTIONS') {
            return new Response(null, { headers: corsHeaders() });
        }

        // 只接受 POST /chat
        const url = new URL(request.url);
        if (request.method !== 'POST' || url.pathname !== '/chat') {
            return new Response(JSON.stringify({ error: 'Not Found' }), {
                status: 404,
                headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
            });
        }

        try {
            const body = await request.json();
            const { messages = [], context = '', stream = false } = body;

            // 构建系统 prompt
            const systemPrompt = `你是"每日早报"网站的 AI 助手。你的任务是帮助用户理解和分析当天的新闻。

以下是用户正在浏览的新闻内容：
---
${context.slice(0, 3000)}
---

请基于以上新闻内容回答用户问题。如果问题超出新闻范围，可以结合你的知识回答，但请注明。
回答请简洁、专业，使用中文。`;

            const apiBody = {
                model: 'deepseek-chat',
                messages: [
                    { role: 'system', content: systemPrompt },
                    ...messages.slice(-10),
                ],
                max_tokens: 500,
                temperature: 0.7,
                stream: stream,
            };

            const apiResponse = await fetch('https://api.deepseek.com/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${env.DEEPSEEK_API_KEY}`,
                },
                body: JSON.stringify(apiBody),
            });

            if (stream) {
                // SSE 流式转发
                return new Response(apiResponse.body, {
                    headers: {
                        ...corsHeaders(),
                        'Content-Type': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                    },
                });
            } else {
                // 非流式
                const data = await apiResponse.json();
                return new Response(JSON.stringify(data), {
                    headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
                });
            }
        } catch (e) {
            return new Response(JSON.stringify({ error: e.message }), {
                status: 500,
                headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
            });
        }
    },
};

function corsHeaders() {
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    };
}
