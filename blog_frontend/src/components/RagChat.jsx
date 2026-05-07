import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BookOpen, Search, FileText, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react';

function RagChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showRefs, setShowRefs] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const toggleShowRefs = (msgIdx) => {
    setShowRefs(prev => ({ ...prev, [msgIdx]: !prev[msgIdx] }));
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    setMessages(prev => [...prev, { role: 'ai', content: '', events: [] }]);

    try {
      const response = await fetch('/api/rag/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ message: userMessage })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let aiText = '';
      let buffer = '';

      const updateAnswer = () => {
        setMessages(prev => {
          const newMsgs = [...prev];
          const last = newMsgs[newMsgs.length - 1];
          last.content = aiText;
          return newMsgs;
        });
      };

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
            if (dataStr === '[DONE]') continue;

            try {
              const data = JSON.parse(dataStr);

              if (data.type === 'rewrite') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const last = { ...newMsgs[newMsgs.length - 1] };
                  last.events = [...(last.events || []), {
                    type: 'rewrite',
                    dense_query: data.dense_query,
                    sparse_query: data.sparse_query
                  }];
                  newMsgs[newMsgs.length - 1] = last;
                  return newMsgs;
                });
              } else if (data.type === 'retrieve') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const last = { ...newMsgs[newMsgs.length - 1] };
                  last.events = [...(last.events || []), {
                    type: 'retrieve',
                    total: data.total,
                    chunks: data.chunks
                  }];
                  newMsgs[newMsgs.length - 1] = last;
                  return newMsgs;
                });
              } else if (data.type === 'build_prompt') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const last = { ...newMsgs[newMsgs.length - 1] };
                  last.events = [...(last.events || []), { type: 'build_prompt' }];
                  newMsgs[newMsgs.length - 1] = last;
                  return newMsgs;
                });
              } else if (data.type === 'text' && data.content) {
                aiText += data.content;
                updateAnswer();
              } else if (data.type === 'done') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const last = { ...newMsgs[newMsgs.length - 1] };
                  last.events = [...(last.events || []), { type: 'done' }];
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
    } catch (error) {
      console.error('RAG Chat error:', error);
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
      <h2 style={{ marginTop: 0, borderBottom: '1px solid #eee', paddingBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <BookOpen size={22} /> 知识库问答
      </h2>

      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', marginTop: '20px' }}>
            基于博客知识库回答你的问题
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
                  {msg.events && msg.events.map((evt, ei) => {
                    if (evt.type === 'rewrite') {
                      return (
                        <div key={ei} style={{
                          display: 'flex', alignItems: 'flex-start', gap: '8px', padding: '8px 12px',
                          marginBottom: '4px', borderRadius: '6px', fontSize: '13px',
                          backgroundColor: '#e8f4fd', color: '#0c5460',
                          border: '1px solid #b8daff', flexDirection: 'column'
                        }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
                            <Search size={14} /> 问题重写
                          </span>
                          <div style={{ paddingLeft: '18px', lineHeight: 1.6 }}>
                            <div><span style={{ opacity: 0.7 }}>语义查询:</span> {evt.dense_query}</div>
                            <div><span style={{ opacity: 0.7 }}>关键词查询:</span> {evt.sparse_query}</div>
                          </div>
                        </div>
                      );
                    }
                    if (evt.type === 'retrieve') {
                      return (
                        <div key={ei} style={{
                          display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px',
                          marginBottom: '4px', borderRadius: '6px', fontSize: '13px',
                          backgroundColor: '#d4edda', color: '#155724',
                          border: '1px solid #c3e6cb'
                        }}>
                          <FileText size={14} /> 检索到 {evt.total} 条相关文档
                        </div>
                      );
                    }
                    if (evt.type === 'build_prompt') {
                      return (
                        <div key={ei} style={{
                          display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px',
                          marginBottom: '4px', borderRadius: '6px', fontSize: '13px',
                          backgroundColor: '#fff3cd', color: '#856404',
                          border: '1px solid #ffeeba'
                        }}>
                          <MessageSquare size={14} /> 构建回答中...
                        </div>
                      );
                    }
                    return null;
                  })}
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
                  {msg.events && (() => {
                    const hasDone = msg.events.some(e => e.type === 'done');
                    const retrieveEvent = msg.events.find(e => e.type === 'retrieve');
                    if (!hasDone || !retrieveEvent || !retrieveEvent.chunks || retrieveEvent.chunks.length === 0) return null;
                    const isOpen = showRefs[idx];
                    return (
                      <div style={{
                        marginTop: '10px',
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        overflow: 'hidden',
                        backgroundColor: '#fafafa'
                      }}>
                        <div
                          onClick={() => toggleShowRefs(idx)}
                          style={{
                            padding: '8px 14px',
                            fontSize: '13px',
                            fontWeight: 600,
                            color: '#555',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            userSelect: 'none'
                          }}
                        >
                          {isOpen ? <ChevronUp size={14} color="#666" /> : <ChevronDown size={14} color="#666" />}
                          <BookOpen size={14} /> 参考文献（{retrieveEvent.chunks.length} 条）
                        </div>
                        {isOpen && (
                          <div>
                            {retrieveEvent.chunks.map((chunk, ci) => {
                              const headings = (chunk.headings || []).join(' > ');
                              const scorePct = chunk.score != null ? (chunk.score * 100).toFixed(1) : null;
                              const preview = (chunk.content || '').slice(0, 120);
                              return (
                                <div key={ci} style={{
                                  padding: '6px 14px 6px 28px',
                                  borderTop: ci > 0 ? '1px solid #eee' : '1px solid #e0e0e0',
                                  fontSize: '13px',
                                  lineHeight: 1.6
                                }}>
                                  <div style={{ fontWeight: 600, color: '#333' }}>
                                    【文档{ci + 1}】
                                    <span style={{ fontWeight: 400, color: '#666', marginLeft: '4px' }}>
                                      {chunk.source_file || '未知来源'}
                                    </span>
                                    {scorePct && (
                                      <span style={{
                                        marginLeft: '8px',
                                        fontSize: '11px',
                                        color: '#999',
                                        backgroundColor: '#eee',
                                        padding: '1px 6px',
                                        borderRadius: '3px'
                                      }}>
                                        相关度 {scorePct}%
                                      </span>
                                    )}
                                  </div>
                                  {headings && (
                                    <div style={{ color: '#888', fontSize: '12px', marginTop: '2px' }}>
                                      {headings}
                                    </div>
                                  )}
                                  <div style={{ color: '#999', marginTop: '2px', wordBreak: 'break-all' }}>
                                    {preview}{chunk.content && chunk.content.length > 120 ? '...' : ''}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })()}
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
          placeholder="基于知识库提问..."
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

export default RagChat;