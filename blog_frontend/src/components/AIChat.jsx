import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function AIChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [userId, setUserId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 获取当前登录用户的 user_id，用于与后端会话关联
  useEffect(() => {
    const username = localStorage.getItem('username');
    const token = localStorage.getItem('token');
    if (!username || !token) return;
    const controller = new AbortController();
    (async () => {
      try {
        const res = await fetch(`/api/users/by-username/${encodeURIComponent(username)}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          signal: controller.signal
        });
        if (res.ok) {
          const data = await res.json();
          if (data.user_id) {
            setUserId(data.user_id);
          }
        }
      } catch (_) {
        // 忽略获取失败，后续请求仍可不带 user_id
      }
    })();
    return () => controller.abort();
  }, []);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    setMessages(prev => [...prev, { role: 'ai', content: '', events: [] }]);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ message: userMessage, user_id: userId })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let aiText = '';
      let buffer = '';

      const updateEvents = () => {
        setMessages(prev => {
          const newMsgs = [...prev];
          const last = newMsgs[newMsgs.length - 1];
          last.content = aiText;
          return newMsgs;
        });
      };

      const updateTextLoop = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            const line = part.trim();
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '[DONE]') {
                continue;
              }
              try {
                const data = JSON.parse(dataStr);
                if (data.type === 'text' && data.content) {
                  aiText += data.content;
                  updateEvents();
                } else if (data.type === 'tool_start') {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const last = { ...newMsgs[newMsgs.length - 1] };
                    last.events = [...(last.events || []), { type: 'tool_start', tool: data.tool }];
                    newMsgs[newMsgs.length - 1] = last;
                    return newMsgs;
                  });
                } else if (data.type === 'tool_end') {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const last = { ...newMsgs[newMsgs.length - 1] };
                    last.events = [...(last.events || []), { type: 'tool_end', tool: data.tool }];
                    newMsgs[newMsgs.length - 1] = last;
                    return newMsgs;
                  });
                }
              } catch (err) {
                console.error('Failed to parse SSE data:', err, dataStr);
              }
            }
          }
        }
      };

      await updateTextLoop();
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs.pop();
        return [...newMsgs, { role: 'error', content: '请求失败，请稍后重试。' }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '80vh' }}>
      <h2 style={{ marginTop: 0, borderBottom: '1px solid #eee', paddingBottom: '10px' }}>AI 智能助手</h2>
      
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', marginTop: '20px' }}>
            有什么我可以帮你的吗？
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx}>
              {msg.role === 'user' ? (
                <div style={{
                  alignSelf: 'flex-end',
                  maxWidth: '80%',
                  backgroundColor: '#007bff',
                  color: 'white',
                  padding: '10px 15px',
                  borderRadius: '8px',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                  whiteSpace: 'pre-wrap',
                  marginLeft: 'auto',
                  marginBottom: '8px'
                }}>
                  {msg.content}
                </div>
              ) : msg.role === 'error' ? (
                <div style={{
                  alignSelf: 'flex-start',
                  maxWidth: '80%',
                  backgroundColor: '#f8d7da',
                  color: '#721c24',
                  padding: '10px 15px',
                  borderRadius: '8px',
                  marginBottom: '8px'
                }}>
                  {msg.content}
                </div>
              ) : (
                <div style={{ alignSelf: 'flex-start', maxWidth: '80%', marginBottom: '8px' }}>
                  {msg.events && msg.events.map((evt, ei) => (
                    <div key={ei} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 12px',
                      marginBottom: '4px',
                      borderRadius: '6px',
                      fontSize: '13px',
                      backgroundColor: evt.type === 'tool_start' ? '#fff3cd' : '#d1ecf1',
                      color: evt.type === 'tool_start' ? '#856404' : '#0c5460',
                      border: `1px solid ${evt.type === 'tool_start' ? '#ffc107' : '#17a2b8'}`
                    }}>
                      <span>{evt.type === 'tool_start' ? '🔧' : '✅'}</span>
                      <span>{evt.type === 'tool_start' ? `正在执行: ${evt.tool}` : `完成: ${evt.tool}`}</span>
                    </div>
                  ))}
                  {msg.content && (
                    <div style={{
                      backgroundColor: '#f1f1f1',
                      color: '#333',
                      padding: '10px 15px',
                      borderRadius: '8px',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                      marginTop: msg.events && msg.events.length > 0 ? '8px' : 0
                    }}>
                      <div className="markdown-content" style={{ margin: 0 }}>
                        <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                      </div>
                    </div>
                  )}
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
