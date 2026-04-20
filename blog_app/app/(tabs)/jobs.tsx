import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Linking,
} from 'react-native';
import api from '../lib/api';
import { PRIMARY, BG, GRAY, BORDER } from '../lib/colors';

interface Job {
  id: number;
  title: string;
  company: string;
  salary?: string;
  location?: string;
  url?: string;
  date: string;
}

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [crawling, setCrawling] = useState(false);

  const fetchJobs = async () => {
    try {
      const res = await api.get('/jobs');
      setJobs(res.data);
    } catch {}
  };

  useEffect(() => { fetchJobs(); }, []);

  const triggerCrawl = async () => {
    setCrawling(true);
    try {
      await api.post('/actions/crawl');
      // poll result
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const res = await api.get('/actions/crawl/result');
          if (res.data?.status === 'done' || attempts > 10) {
            clearInterval(poll);
            fetchJobs();
            setCrawling(false);
          }
        } catch {
          if (attempts > 10) { clearInterval(poll); setCrawling(false); }
        }
      }, 3000);
    } catch {
      setCrawling(false);
    }
  };

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.title}>职位</Text>
        <TouchableOpacity style={s.crawlBtn} onPress={triggerCrawl} disabled={crawling}>
          {crawling ? <ActivityIndicator color="#fff" size="small" /> : <Text style={s.crawlText}>抓取</Text>}
        </TouchableOpacity>
      </View>
      <FlatList
        data={jobs}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={s.list}
        renderItem={({ item }) => (
          <TouchableOpacity style={s.card} onPress={() => item.url && Linking.openURL(item.url)}>
            <Text style={s.jobTitle} numberOfLines={1}>{item.title}</Text>
            <Text style={s.company}>{item.company}</Text>
            <View style={s.row}>
              {item.salary && <Text style={s.salary}>{item.salary}</Text>}
              {item.location && <Text style={s.location}>{item.location}</Text>}
            </View>
            <Text style={s.date}>{item.date}</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={s.empty}>暂无职位，点击抓取</Text>}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: BG },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: BORDER },
  title: { fontSize: 20, fontWeight: 'bold', color: '#333' },
  crawlBtn: { backgroundColor: PRIMARY, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 6 },
  crawlText: { color: '#fff', fontWeight: 'bold' },
  list: { padding: 12 },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10 },
  jobTitle: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 4 },
  company: { fontSize: 14, color: '#555', marginBottom: 6 },
  row: { flexDirection: 'row', gap: 12, marginBottom: 4 },
  salary: { fontSize: 14, color: PRIMARY, fontWeight: '600' },
  location: { fontSize: 13, color: GRAY },
  date: { fontSize: 12, color: GRAY },
  empty: { textAlign: 'center', color: GRAY, marginTop: 60, fontSize: 16 },
});
