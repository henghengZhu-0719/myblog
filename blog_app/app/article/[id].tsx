import { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, SafeAreaView,
  TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import api from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { PRIMARY, GRAY, BORDER } from '../../lib/colors';

interface Article {
  id: number;
  title: string;
  content: string;
  view_count: number;
  created_at: string;
  author: { id: number; username: string };
}

export default function ArticleDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [article, setArticle] = useState<Article | null>(null);
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    api.get(`/articles/${id}`).then((res) => setArticle(res.data)).catch(() => {});
  }, [id]);

  const handleDelete = () => {
    Alert.alert('确认删除', '删除后不可恢复', [
      { text: '取消', style: 'cancel' },
      {
        text: '删除', style: 'destructive', onPress: async () => {
          await api.delete(`/articles/${id}`);
          router.back();
        },
      },
    ]);
  };

  if (!article) return <ActivityIndicator style={{ flex: 1 }} color={PRIMARY} />;

  const isOwner = user?.id === article.author.id;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.topBar}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={s.back}>← 返回</Text>
        </TouchableOpacity>
        {isOwner && (
          <View style={s.actions}>
            <TouchableOpacity onPress={() => router.push(`/edit/${id}`)}>
              <Text style={s.edit}>编辑</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={handleDelete}>
              <Text style={s.delete}>删除</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
      <ScrollView contentContainerStyle={s.scroll}>
        <Text style={s.title}>{article.title}</Text>
        <Text style={s.meta}>{article.author.username} · 👁 {article.view_count} · {article.created_at?.slice(0, 10)}</Text>
        <Text style={s.content}>{article.content}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: BORDER },
  back: { fontSize: 16, color: PRIMARY },
  actions: { flexDirection: 'row', gap: 16 },
  edit: { color: PRIMARY, fontSize: 15 },
  delete: { color: '#e53e3e', fontSize: 15 },
  scroll: { padding: 20 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#333', marginBottom: 10 },
  meta: { fontSize: 13, color: GRAY, marginBottom: 20 },
  content: { fontSize: 16, color: '#444', lineHeight: 26 },
});
