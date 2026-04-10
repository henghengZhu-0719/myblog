import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, Image,
  StyleSheet, RefreshControl, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import api from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { PRIMARY, BG, GRAY, BORDER } from '../../lib/colors';

interface Article {
  id: number;
  title: string;
  cover_image?: string;
  view_count: number;
  created_at: string;
  author: { username: string };
}

export default function ArticleList() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { user, logout } = useAuth();
  const router = useRouter();

  const load = useCallback(async (p = 1, reset = false) => {
    try {
      const res = await api.get(`/users/${user?.username}/articles`, { params: { page: p, size: 10 } });
      const data: Article[] = res.data.items ?? res.data;
      if (reset) setArticles(data);
      else setArticles((prev) => [...prev, ...data]);
      setHasMore(data.length === 10);
      setPage(p);
    } catch {}
  }, [user]);

  useEffect(() => { load(1, true); }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load(1, true);
    setRefreshing(false);
  };

  const onEndReached = () => {
    if (hasMore) load(page + 1);
  };

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.logo}>我的文章</Text>
        <TouchableOpacity onPress={logout}>
          <Text style={s.logout}>退出</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        data={articles}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={s.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={PRIMARY} />}
        onEndReached={onEndReached}
        onEndReachedThreshold={0.3}
        renderItem={({ item }) => (
          <TouchableOpacity style={s.card} onPress={() => router.push(`/article/${item.id}`)}>
            {item.cover_image && <Image source={{ uri: item.cover_image }} style={s.cover} />}
            <View style={s.cardBody}>
              <Text style={s.cardTitle} numberOfLines={2}>{item.title}</Text>
              <Text style={s.cardMeta}>👁 {item.view_count} · {item.created_at?.slice(0, 10)}</Text>
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={s.empty}>暂无文章</Text>}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: BG },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: BORDER },
  logo: { fontSize: 20, fontWeight: 'bold', color: PRIMARY },
  logout: { color: GRAY, fontSize: 14 },
  list: { padding: 12 },
  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  cover: { width: '100%', height: 160, resizeMode: 'cover' },
  cardBody: { padding: 12 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 6 },
  cardMeta: { fontSize: 12, color: GRAY },
  empty: { textAlign: 'center', color: GRAY, marginTop: 60, fontSize: 16 },
});
