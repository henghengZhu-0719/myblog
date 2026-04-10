import { Tabs } from 'expo-router';
import { PRIMARY } from '../../lib/colors';
import { Text } from 'react-native';

function Icon({ label }: { label: string }) {
  return <Text style={{ fontSize: 20 }}>{label}</Text>;
}

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ tabBarActiveTintColor: PRIMARY, headerShown: false }}>
      <Tabs.Screen
        name="index"
        options={{ title: '首页', tabBarIcon: () => <Icon label="🏠" /> }}
      />
      <Tabs.Screen
        name="publish"
        options={{ title: '发布', tabBarIcon: () => <Icon label="✏️" /> }}
      />
      <Tabs.Screen
        name="bills"
        options={{ title: '账单', tabBarIcon: () => <Icon label="💰" /> }}
      />
      <Tabs.Screen
        name="jobs"
        options={{ title: '职位', tabBarIcon: () => <Icon label="💼" /> }}
      />
      <Tabs.Screen
        name="ai"
        options={{ title: 'AI', tabBarIcon: () => <Icon label="🤖" /> }}
      />
    </Tabs>
  );
}
