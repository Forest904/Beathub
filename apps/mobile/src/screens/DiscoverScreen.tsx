import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FlatList,
  RefreshControl,
  ScrollView,
  Text,
  View,
  Pressable,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

import {
  useDownloadHistoryQuery,
  usePopularArtistsQuery,
} from "@cd-collector/shared/react-query";
import type { DownloadItem } from "@cd-collector/shared/api";
import SectionHeader from "../components/SectionHeader";
import Skeleton from "../components/Skeleton";
import EmptyState from "../components/EmptyState";
import { useSnackbar } from "../providers/SnackbarProvider";
import type { RootStackParamList } from "../navigation/types";

type Navigation = NativeStackNavigationProp<RootStackParamList>;

const ARTIST_CARD_WIDTH = 132;

const DiscoverScreen: React.FC = () => {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation<Navigation>();
  const snackbar = useSnackbar();

  const [refreshing, setRefreshing] = useState(false);

  const popularQuery = usePopularArtistsQuery({ limit: 10 });
  const downloadsQuery = useDownloadHistoryQuery();

  useEffect(() => {
    if (popularQuery.error) {
      snackbar.showError("Could not load trending artists.");
    }
  }, [popularQuery.error, snackbar]);

  useEffect(() => {
    if (downloadsQuery.error) {
      snackbar.showError("Failed to load recent releases.");
    }
  }, [downloadsQuery.error, snackbar]);

  const onRefresh = useCallback(async () => {
    try {
      setRefreshing(true);
      await Promise.all([popularQuery.refetch(), downloadsQuery.refetch()]);
    } finally {
      setRefreshing(false);
    }
  }, [downloadsQuery, popularQuery]);

  const popularArtists = useMemo(
    () => popularQuery.data?.artists ?? [],
    [popularQuery.data?.artists],
  );

  const recentDownloads = useMemo(
    () => (downloadsQuery.data ?? []).slice(0, 8),
    [downloadsQuery.data],
  );

  const renderArtist = useCallback(
    ({ item }: { item: (typeof popularArtists)[number] }) => (
      <View
        className="mr-4 rounded-2xl bg-slate-900/80 p-3"
        style={{ width: ARTIST_CARD_WIDTH }}
      >
        {item.image ? (
          <Image
            source={{ uri: item.image }}
            style={{ width: "100%", height: 104, borderRadius: 16 }}
            cachePolicy="memory-disk"
            accessibilityLabel={item.name}
          />
        ) : (
          <View className="h-26 w-full items-center justify-center rounded-2xl bg-slate-800">
            <Text className="text-3xl font-semibold text-slate-200">
              {item.name.slice(0, 1).toUpperCase()}
            </Text>
          </View>
        )}
        <Text numberOfLines={2} className="mt-3 text-base font-medium text-slate-100">
          {item.name}
        </Text>
        <Text className="mt-1 text-xs text-slate-400">
          {item.followers_available ? `${item.followers.toLocaleString()} fans` : "Newcomer"}
        </Text>
      </View>
    ),
    [],
  );

  const renderRelease = useCallback(
    ({ item }: { item: DownloadItem }) => (
      <Pressable
        onPress={() => navigation.navigate("ReleaseDetail", { item })}
        className="mb-4 flex-row items-center rounded-2xl bg-slate-900/80 p-3"
      >
        {item.image_url ? (
          <Image
            source={{ uri: item.image_url }}
            style={{ width: 64, height: 64, borderRadius: 16 }}
            cachePolicy="memory-disk"
            accessibilityLabel={item.title || item.name}
          />
        ) : (
          <View className="h-16 w-16 items-center justify-center rounded-2xl bg-slate-800">
            <Text className="text-lg font-semibold text-slate-200">
              {(item.title || item.name).slice(0, 1).toUpperCase()}
            </Text>
          </View>
        )}
        <View className="ml-3 flex-1">
          <Text numberOfLines={1} className="text-base font-semibold text-slate-100">
            {item.title || item.name}
          </Text>
          <Text numberOfLines={1} className="text-sm text-slate-400">
            {item.artist || "Unknown artist"}
          </Text>
        </View>
      </Pressable>
    ),
    [navigation],
  );

  return (
    <ScrollView
      className="flex-1 bg-slate-950"
      contentContainerStyle={{
        paddingTop: insets.top + 24,
        paddingBottom: insets.bottom + 32,
      }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#38bdf8"
        />
      }
    >
      <View className="pt-6">
        <SectionHeader
          title="Trending Artists"
          subtitle="Fresh picks curated from Spotify activity"
        />
        {popularQuery.isLoading ? (
          <View className="flex-row px-6">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton
                key={index.toString()}
                height={150}
                width={ARTIST_CARD_WIDTH}
                style={{ marginRight: index === 3 ? 0 : 16 }}
              />
            ))}
          </View>
        ) : popularArtists.length > 0 ? (
          <FlatList
            data={popularArtists}
            horizontal
            keyExtractor={(item) => item.id}
            renderItem={renderArtist}
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ paddingHorizontal: 24 }}
          />
        ) : (
          <EmptyState
            title="No artists yet"
            description="Link Spotify searches or downloads to see curated artist highlights."
          />
        )}
      </View>

      <View className="mt-8">
        <SectionHeader
          title="Recent Releases"
          subtitle="Latest downloads across albums, playlists, and tracks"
        />
        {downloadsQuery.isLoading ? (
          <View className="px-6">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index.toString()} height={76} style={{ marginBottom: 16 }} />
            ))}
          </View>
        ) : recentDownloads.length > 0 ? (
          <View className="px-6">
            {recentDownloads.map((item) => (
              <View key={item.id} className="mb-2">
                {renderRelease({ item })}
              </View>
            ))}
          </View>
        ) : (
          <EmptyState
            title="No downloads yet"
            description="Start a download from the web app to populate this feed."
          />
        )}
      </View>
    </ScrollView>
  );
};

export default DiscoverScreen;
