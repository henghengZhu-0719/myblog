import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  SafeAreaView, Alert, Image,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import api from '../../lib/api';
import { PRIMARY, BG, GRAY, BORDER } from '../../lib/colors';

interface Bill {
  id: number;
  amount: number;
  category: string;
  description: string;
  date: string;
}

export default function Bills() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchBills = async () => {
    try {
      const res = await api.get('/bills');
      setBills(res.data);
    } catch {}
  };

  useEffect(() => { fetchBills(); }, []);

  const pickAndAnalyze = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 });
    if (result.canceled) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', { uri: result.assets[0].uri, name: 'bill.jpg', type: 'image/jpeg' } as any);
      const res = await api.post('/actions/bill', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      const items = res.data;
      await api.post('/bills', { items });
      fetchBills();
      Alert.alert('识别成功', `已添加 ${items.length} 条账单`);
    } catch {
      Alert.alert('识别失败');
    } finally {
      setLoading(false);
    }
  };

  const total = bills.reduce((sum, b) => sum + b.amount, 0);

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.title}>账单</Text>
        <Text style={s.total}>总计: ¥{total.toFixed(2)}</Text>
      </View>
      <FlatList
        data={bills}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={s.list}
        renderItem={({ item }) => (
          <View style={s.card}>
            <View style={s.cardLeft}>
              <Text style={s.category}>{item.category}</Text>
              <Text style={s.desc} numberOfLines={1}>{item.description}</Text>
              <Text style={s.date}>{item.date}</Text>
            </View>
            <Text style={s.amount}>¥{item.amount.toFixed(2)}</Text>
          </View>
        )}
        ListEmptyComponent={<Text style={s.empty}>暂无账单</Text>}
      />
      <TouchableOpacity style={s.fab} onPress={pickAndAnalyze} disabled={loading}>
        <Text style={s.fabText}>{loading ? '识别中...' : '📷 拍照识别'}</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: BG },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: BORDER },
  title: { fontSize: 20, fontWeight: 'bold', color: '#333' },
  total: { fontSize: 16, color: PRIMARY, fontWeight: '600' },
  list: { padding: 12, paddingBottom: 80 },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardLeft: { flex: 1 },
  category: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 2 },
  desc: { fontSize: 13, color: GRAY, marginBottom: 2 },
  date: { fontSize: 12, color: GRAY },
  amount: { fontSize: 18, fontWeight: 'bold', color: PRIMARY },
  empty: { textAlign: 'center', color: GRAY, marginTop: 60, fontSize: 16 },
  fab: { position: 'absolute', bottom: 24, alignSelf: 'center', backgroundColor: PRIMARY, borderRadius: 24, paddingHorizontal: 24, paddingVertical: 12 },
  fabText: { color: '#fff', fontSize: 15, fontWeight: 'bold' },
});
