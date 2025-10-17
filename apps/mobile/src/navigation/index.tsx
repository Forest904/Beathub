import React from "react";
import { useColorScheme } from "react-native";
import { NavigationContainer, DarkTheme, DefaultTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { enableScreens } from "react-native-screens";

import DiscoverScreen from "../screens/DiscoverScreen";
import ReleasesScreen from "../screens/ReleasesScreen";
import PlaylistsScreen from "../screens/PlaylistsScreen";
import DownloadQueueScreen from "../screens/DownloadQueueScreen";
import PlaylistDetailScreen from "../screens/PlaylistDetailScreen";
import ReleaseDetailScreen from "../screens/ReleaseDetailScreen";
import type { RootStackParamList, TabsParamList } from "./types";

enableScreens(true);

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabsParamList>();

const tabIconMap: Record<
  keyof TabsParamList,
  { focused: React.ComponentProps<typeof Ionicons>["name"]; default: React.ComponentProps<typeof Ionicons>["name"] }
> = {
  Discover: { focused: "planet", default: "planet-outline" },
  Releases: { focused: "albums", default: "albums-outline" },
  Playlists: { focused: "list", default: "list-outline" },
  DownloadQueue: { focused: "download", default: "download-outline" },
};

const TabsNavigator = () => (
  <Tab.Navigator
    screenOptions={({ route }) => ({
      headerShown: false,
      tabBarActiveTintColor: "#38bdf8",
      tabBarInactiveTintColor: "#94a3b8",
      tabBarStyle: {
        backgroundColor: "#0f172a",
        borderTopColor: "rgba(148, 163, 184, 0.2)",
      },
      tabBarIcon: ({ color, focused, size }) => {
        const iconSet = tabIconMap[route.name as keyof TabsParamList];
        const iconName = focused ? iconSet.focused : iconSet.default;
        return <Ionicons name={iconName} size={size} color={color} />;
      },
    })}
  >
    <Tab.Screen name="Discover" component={DiscoverScreen} />
    <Tab.Screen name="Releases" component={ReleasesScreen} options={{ title: "Releases" }} />
    <Tab.Screen name="Playlists" component={PlaylistsScreen} />
    <Tab.Screen name="DownloadQueue" component={DownloadQueueScreen} options={{ title: "Download Queue" }} />
  </Tab.Navigator>
);

const Navigation = () => {
  const scheme = useColorScheme();

  return (
    <NavigationContainer theme={scheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: "#0f172a" },
          headerTintColor: "#f8fafc",
          contentStyle: { backgroundColor: "#0f172a" },
        }}
      >
        <Stack.Screen
          name="MainTabs"
          component={TabsNavigator}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="PlaylistDetail"
          component={PlaylistDetailScreen}
          options={({ route }) => ({
            title: route.params.title ?? "Playlist",
          })}
        />
        <Stack.Screen
          name="ReleaseDetail"
          component={ReleaseDetailScreen}
          options={({ route }) => ({
            title: route.params.item.title || route.params.item.name || "Release",
          })}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default Navigation;
