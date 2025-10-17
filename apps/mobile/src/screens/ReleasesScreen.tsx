import React, { useCallback, useEffect } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { Image } from "expo-image";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

import { useDownloadHistoryQuery } from "@cd-collector/shared/react-query";
import type { DownloadItem } from "@cd-collector/shared/api";
import Skeleton from "../components/Skeleton";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { useSnackbar } from "../providers/SnackbarProvider";
import type { RootStackParamList } from "../navigation/types";

type Navigation = NativeStackNavigationProp<RootStackParamList>;

const renderSkeletonRow = (index: number) => <Skeleton key={index.toString()} height={78} style={{ marginBottom: 16 }} />;

const ReleasesScreen: React.FC = () => {
  const navigation = useNavigation<Navigation>();
  const snackbar = useSnackbar();
  const insets = useSafeAreaInsets();
  const query = useDownloadHistoryQuery();

  useEffect(() => {
    if (query.error) {
      snackbar.showError("Unable to load releases right now.");
    }
  }, [query.error, snackbar]);

  const onRefresh = useCallback(async () => {
    try {
      await query.refetch();
    } catch {
      /* errors surfaced via snackbar */
    }
  }, [query]);

  const renderItem = useCallback(
    ({ item }: { item: DownloadItem }) => (
      <Pressable
        onPress={() => navigation.navigate("ReleaseDetail", { item })}
        className="mb-4 flex-row items-center rounded-3xl bg-slate-900/85 p-4"
      >
        {item.image_url ? (
          <Image
            source={{ uri: item.image_url }}
            style={{ width: 72, height: 72, borderRadius: 18 }}
            cachePolicy="memory-disk"
            accessibilityLabel={item.title || item.name}
          />
        ) : (
          <View className="h-18 w-18 items-center justify-center rounded-3xl bg-slate-800">
            <Text className="text-xl font-semibold text-slate-200">
              {(item.title || item.name).slice(0, 1).toUpperCase()}
            </Text>
          </View>
        )}
        <View className="ml-4 flex-1">
          <Text numberOfLines={1} className="text-lg font-semibold text-slate-100">
            {item.title || item.name}
          </Text>
          <Text numberOfLines={1} className="text-sm text-slate-400">
            {item.artist || "Unknown artist"}
          </Text>
        </View>
        <View className="items-end">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {item.item_type}
          </Text>
          {item.local_path ? (
            <Text className="mt-1 text-xs text-emerald-400">Downloaded</Text>
          ) : (
            <Text className="mt-1 text-xs text-slate-500">Queued</Text>
          )}
        </View>
      </Pressable>
    ),
    [navigation],
  );

  return (
    <View className="flex-1 bg-slate-950">
      <FlatList
        data={query.data ?? []}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderItem}
        contentContainerStyle={{
          paddingHorizontal: 24,
          paddingTop: insets.top + 16,
          paddingBottom: insets.bottom + 32,
        }}
        refreshControl={
          <RefreshControl
            refreshing={query.isFetching}
            onRefresh={onRefresh}
            tintColor="#38bdf8"
          />
        }
        ListEmptyComponent={
          query.isLoading ? (
            <View>
              {Array.from({ length: 6 }).map((_, index) => renderSkeletonRow(index))}
            </View>
          ) : query.error ? (
            <ErrorState
              message={(query.error as Error).message}
              action={
                <Pressable
                  className="rounded-full bg-sky-500 px-4 py-2"
                  onPress={() => query.refetch()}
                >
                  <Text className="text-sm font-semibold text-white">Retry</Text>
                </Pressable>
              }
            />
          ) : (
            <EmptyState
              title="Library is empty"
              description="Start a download from the Discover tab or from the web app to populate your catalog."
            />
          )
        }
      />
    </View>
  );
};

export default ReleasesScreen;
