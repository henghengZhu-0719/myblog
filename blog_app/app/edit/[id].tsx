import { useEffect, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ScrollView, SafeAreaView, ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import api from '../../lib/api';
import { PRIMARY, BORDER, GRAY } from '../../lib/colors';

export default function ArticleEdit() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const router = useRouter();

  useEffect(() => {
    api.get(`/articles/${id}`).then((res) => {
      setTitle(res.data.title);
      setContent(res.data.content);
    }).finally(() => setFetching(false));
  }, [id]);

  const handleSave = async () => {
    if (!title || !content) return Alert.alert('请填写标题和内容');
    setLoading(true);
    try {
      await api.put(`/articles/${id}`, { title, content });
      router.back();
    } catch {
      Alert.alert('保存失败');
    } finally {
      setLoading(false);
    }
  };

  if (fetching) return <ActivityIndicator style={{ flex: 1 }} color={PRIMARY} />;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.topBar}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={s.back}>← 返回</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleSave} disabled={loading}>
          <Text style={s.save}>{loading ? '保存中...' : '保存'}</Text>
        </TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={s.scroll}>
        <TextInput style={s.titleInput} placeholder="标题" value={title} onChangeText={setTitle} />
        <TextInput
          style={s.textarea}
          placeholder="内容"
          value={content}
          onChangeText={setContent}
          multiline
          textAlignVertical="top"
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: BORDER },
  back: { fontSize: 16, color: GRAY },
  save: { fontSize: 16, color: PRIMARY, fontWeight: 'bold' },
  scroll: { padding: 20 },
  titleInput: { fontSize: 20, fontWeight: 'bold', borderBottomWidth: 1, borderBottomColor: BORDER, paddingBottom: 12, marginBottom: 16 },
  textarea: { fontSize: 16, color: '#444', lineHeight: 26, minHeight: 400 },
});
