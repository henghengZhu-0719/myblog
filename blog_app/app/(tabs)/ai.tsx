import { useState, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, SafeAreaView, KeyboardAvoidingView, Platform,
} from 'react-native';
import api from '../../lib/api';
import { PRIMARY, BG, GRAY, BORDER } from '../../lib/colors';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef<FlatList>(null);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    const assistantMsg: Message = { id: Date.now().toString() + 'a', role: 'assistant', content: '' };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    try {
      const res = await api.post('/ai/chat', { message: text }, { responseType: 'text' });
      setMessages((prev) =>
        prev.map((m) => m.id === assistantMsg.id ? { ...m, content: res.data } : m)
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) => m.id === assistantMsg.id ? { ...m, content: '请求失败，请重试' } : m)
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.title}>AI 助手</Text>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          contentContainerStyle={s.list}
          onContentSizeChange={() => listRef.current?.scrollToEnd()}
          renderItem={({ item }) => (
            <View style={[s.bubble, item.role === 'user' ? s.userBubble : s.aiBubble]}>
              <Text style={[s.bubbleText, item.role === 'user' && s.userText]}>
                {item.content || (loading ? '...' : '')}
              </Text>
            </View>
          )}
          ListEmptyComponent={<Text style={s.empty}>开始和 AI 对话吧</Text>}
        />
        <View style={s.inputRow}>
          <TextInput
            style={s.input}
            placeholder="输入消息..."
            value={input}
            onChangeText={setInput}
            onSubmitEditing={send}
            returnKeyType="send"
          />
          <TouchableOpacity style={s.sendBtn} onPress={send} disabled={loading}>
            <Text style={s.sendText}>发送</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: BG },
  header: { padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: BORDER },
  title: { fontSize: 20, fontWeight: 'bold', color: '#333' },
  list: { padding: 16, paddingBottom: 8 },
  bubble: { maxWidth: '80%', borderRadius: 16, padding: 12, marginBottom: 10 },
  aiBubble: { backgroundColor: '#fff', alignSelf: 'flex-start' },
  userBubble: { backgroundColor: PRIMARY, alignSelf: 'flex-end' },
  bubbleText: { fontSize: 15, color: '#333', lineHeight: 22 },
  userText: { color: '#fff' },
  empty: { textAlign: 'center', color: GRAY, marginTop: 60, fontSize: 16 },
  inputRow: { flexDirection: 'row', padding: 12, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: BORDER, gap: 8 },
  input: { flex: 1, borderWidth: 1, borderColor: BORDER, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 8, fontSize: 15 },
  sendBtn: { backgroundColor: PRIMARY, borderRadius: 20, paddingHorizontal: 18, justifyContent: 'center' },
  sendText: { color: '#fff', fontWeight: 'bold' },
});
