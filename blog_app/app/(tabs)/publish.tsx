import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ScrollView, SafeAreaView, Image,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import api from '../lib/api';
import { PRIMARY, BORDER, GRAY } from '../lib/colors';

export default function Publish() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [cover, setCover] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.8 });
    if (!result.canceled) setCover(result.assets[0].uri);
  };

  const handlePublish = async () => {
    if (!title || !content) return Alert.alert('请填写标题和内容');
    setLoading(true);
    try {
      await api.post('/articles', { title, content, cover_image: cover || undefined });
      Alert.alert('发布成功', '', [{ text: '确定', onPress: () => { router.replace('/(tabs)/'); setTitle(''); setContent(''); setCover(''); } }]);
    } catch {
      Alert.alert('发布失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={s.container}>
      <ScrollView contentContainerStyle={s.scroll}>
        <Text style={s.heading}>发布文章</Text>
        <TextInput style={s.input} placeholder="标题" value={title} onChangeText={setTitle} />
        <TouchableOpacity style={s.coverBtn} onPress={pickImage}>
          {cover ? <Image source={{ uri: cover }} style={s.coverImg} /> : <Text style={s.coverText}>+ 添加封面图</Text>}
        </TouchableOpacity>
        <TextInput
          style={[s.input, s.textarea]}
          placeholder="写点什么..."
          value={content}
          onChangeText={setContent}
          multiline
          textAlignVertical="top"
        />
        <TouchableOpacity style={s.btn} onPress={handlePublish} disabled={loading}>
          <Text style={s.btnText}>{loading ? '发布中...' : '发布'}</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 20 },
  heading: { fontSize: 22, fontWeight: 'bold', marginBottom: 20, color: '#333' },
  input: { borderWidth: 1, borderColor: BORDER, borderRadius: 8, padding: 12, fontSize: 16, marginBottom: 14 },
  textarea: { height: 240, marginBottom: 14 },
  coverBtn: { borderWidth: 1, borderColor: BORDER, borderRadius: 8, height: 120, justifyContent: 'center', alignItems: 'center', marginBottom: 14, overflow: 'hidden' },
  coverImg: { width: '100%', height: '100%', resizeMode: 'cover' },
  coverText: { color: GRAY, fontSize: 15 },
  btn: { backgroundColor: PRIMARY, borderRadius: 8, padding: 14, alignItems: 'center' },
  btnText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
