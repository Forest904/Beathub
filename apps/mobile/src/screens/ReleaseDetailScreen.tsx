import React, { useCallback } from "react";
import { Linking, ScrollView, Text, View, Pressable } from "react-native";
import { RouteProp, useRoute } from "@react-navigation/native";
import { Image } from "expo-image";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { RootStackParamList } from "../navigation/types";

type ReleaseDetailRoute = RouteProp<RootStackParamList, "ReleaseDetail">;

const InfoRow: React.FC<{ label: string; value?: string | null }> = ({ label, value }) =>
  value ? (
    <View className="mb-3">
      <Text className="text-xs uppercase tracking-wide text-slate-500">{label}</Text>
      <Text className="mt-1 text-base text-slate-100">{value}</Text>
    </View>
  ) : null;

const ReleaseDetailScreen: React.FC = () => {
  const { params } = useRoute<ReleaseDetailRoute>();
  const item = params.item;
  const insets = useSafeAreaInsets();

  const openInSpotify = useCallback(() => {
    if (item.spotify_url) {
      Linking.openURL(item.spotify_url).catch(() => {
        // swallow errors; users can try again
      });
    }
  }, [item.spotify_url]);

  return (
    <ScrollView
      className="flex-1 bg-slate-950"
      contentContainerStyle={{
        paddingHorizontal: 24,
        paddingTop: insets.top + 24,
        paddingBottom: insets.bottom + 32,
      }}
    >
      <View className="items-center">
        {item.image_url ? (
          <Image
            source={{ uri: item.image_url }}
            style={{ width: 220, height: 220, borderRadius: 28 }}
            cachePolicy="memory-disk"
            accessibilityLabel={item.title || item.name}
          />
        ) : (
          <View className="h-56 w-56 items-center justify-center rounded-3xl bg-slate-800">
            <Text className="text-4xl font-semibold text-slate-200">
              {(item.title || item.name).slice(0, 1).toUpperCase()}
            </Text>
          </View>
        )}
        <Text className="mt-6 text-2xl font-semibold text-slate-100">
          {item.title || item.name}
        </Text>
        <Text className="mt-2 text-base text-slate-400">
          {item.artist || "Unknown artist"}
        </Text>
      </View>

      <View className="mt-8">
        <InfoRow label="Item Type" value={item.item_type} />
        <InfoRow label="Spotify ID" value={item.spotify_id || undefined} />
        <InfoRow label="Local Path" value={item.local_path || undefined} />
        <InfoRow label="Spotify URL" value={item.spotify_url || undefined} />
      </View>

      {item.spotify_url ? (
        <Pressable
          onPress={openInSpotify}
          className="mt-8 items-center justify-center rounded-full bg-sky-500 px-6 py-3"
        >
          <Text className="text-sm font-semibold uppercase tracking-wide text-white">
            Open in Spotify
          </Text>
        </Pressable>
      ) : null}
    </ScrollView>
  );
};

export default ReleaseDetailScreen;
