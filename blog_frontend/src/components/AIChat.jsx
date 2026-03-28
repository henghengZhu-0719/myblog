import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function AIChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    // 占位一条 AI 回复
    setMessages(prev => [...prev, { role: 'ai', content: '' }]);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}` // 如果需要的话
        },
        body: JSON.stringify({ message: userMessage })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let aiReply = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value, { stream: true });
        // chunkText 可能是多个 SSE 事件组合，用 \n\n 分割
        const lines = chunkText.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') {
              continue;
            }
            try {
              const data = JSON.parse(dataStr);
              if (data.text) {
                aiReply += data.text;
                // 更新最后一条消息的内容
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = aiReply;
                  return newMsgs;
                });
              } else if (data.error) {
                console.error('Server error:', data.error);
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content += `\n[错误: ${data.error}]`;
                  return newMsgs;
                });
              }
            } catch (err) {
              console.error('Failed to parse SSE data:', err, dataStr);
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const newMsgs = [...prev];
        // 移除刚才占位的空消息，替换为错误消息
        newMsgs.pop();
        return [...newMsgs, { role: 'error', content: '请求失败，请稍后重试。' }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '80vh' }}>
      <h2 style={{ marginTop: 0, borderBottom: '1px solid #eee', paddingBottom: '10px' }}>AI 助手 (MiniMax)</h2>
      
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', marginTop: '20px' }}>
            有什么我可以帮你的吗？
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div 
              key={idx} 
              style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%',
                backgroundColor: msg.role === 'user' ? '#007bff' : (msg.role === 'error' ? '#f8d7da' : '#f1f1f1'),
                color: msg.role === 'user' ? 'white' : (msg.role === 'error' ? '#721c24' : '#333'),
                padding: '10px 15px',
                borderRadius: '8px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
              }}
            >
              {msg.role === 'user' ? (
                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              ) : (
                <div className="markdown-content" style={{ margin: 0 }}>
                  <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div style={{ alignSelf: 'flex-start', backgroundColor: '#f1f1f1', padding: '10px 15px', borderRadius: '8px', color: '#666' }}>
            正在思考...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '10px', marginTop: '15px', borderTop: '1px solid #eee', paddingTop: '15px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你的问题..."
          style={{ margin: 0, flex: 1 }}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()} style={{ width: 'auto', margin: 0, padding: '0 20px' }}>
          发送
        </button>
      </form>
    </div>
  );
}

export default AIChat;
