import React, { useCallback, useEffect, useMemo, useState } from "react";
import { AppState, AppStateStatus, ScrollView, Text, View } from "react-native";
import { useIsFocused } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useDownloadProgressSnapshotQuery } from "@cd-collector/shared/react-query";
import type { DownloadProgressSnapshot } from "@cd-collector/shared/api";
import EmptyState from "../components/EmptyState";
import Skeleton from "../components/Skeleton";
import { useSnackbar } from "../providers/SnackbarProvider";

interface QueueEntry {
  key: string;
  name: string;
  status: string | null;
  progress: number;
  updatedAt: number;
  errorMessage?: string | null;
  severity?: string | null;
}

const INITIAL_OVERALL = {
  total: 0,
  completed: 0,
  progress: 0,
  status: "Idle",
};

const normalizeKey = (payload: DownloadProgressSnapshot) =>
  (payload.song_id as string) ||
  (payload.spotify_url as string) ||
  (payload.song_display_name as string) ||
  (payload.song_name as string) ||
  null;

const DownloadQueueScreen: React.FC = () => {
  const [overall, setOverall] = useState(INITIAL_OVERALL);
  const [entries, setEntries] = useState<Record<string, QueueEntry>>({});
  const [order, setOrder] = useState<string[]>([]);
  const [hasActiveDownload, setHasActiveDownload] = useState(false);
  const [isForeground, setIsForeground] = useState(true);
  const snackbar = useSnackbar();
  const isFocused = useIsFocused();
  const insets = useSafeAreaInsets();

  const progressQuery = useDownloadProgressSnapshotQuery({
    enabled: isFocused && isForeground,
    refetchIntervalMs: 4000,
  });

  useEffect(() => {
    if (progressQuery.error) {
      snackbar.showError("Unable to refresh download progress.");
    }
  }, [progressQuery.error, snackbar]);

  useEffect(() => {
    const handler = (state: AppStateStatus) => {
      setIsForeground(state === "active");
    };
    const subscription = AppState.addEventListener("change", handler);
    return () => subscription.remove();
  }, []);

  const processSnapshot = useCallback(
    (snapshot: DownloadProgressSnapshot | null | undefined) => {
      if (!snapshot) {
        setOverall((prev) => ({ ...prev, status: "Idle" }));
        setHasActiveDownload(false);
        return;
      }

      setOverall((prev) => {
        const total =
          typeof snapshot.overall_total === "number" ? snapshot.overall_total : prev.total;
        const completed =
          typeof snapshot.overall_completed === "number"
            ? snapshot.overall_completed
            : prev.completed;
        const progressValue =
          typeof snapshot.overall_progress === "number"
            ? snapshot.overall_progress
            : total > 0
            ? Math.round((completed / total) * 100)
            : prev.progress;
        return {
          total,
          completed,
          progress: Math.max(0, Math.min(100, progressValue)),
          status: (snapshot.status as string) || prev.status,
        };
      });

      const key = normalizeKey(snapshot);
      if (key) {
        const now = Date.now();
        const status = (snapshot.song_status as string) || (snapshot.status as string) || null;
        const statusLower = (status || "").toLowerCase();
        const rawProgress = snapshot.song_progress ?? snapshot.progress ?? 0;
        const normalizedProgress = Math.max(
          0,
          Math.min(100, Math.round(Number(rawProgress) || 0)),
        );
        const isComplete =
          normalizedProgress >= 100 ||
          statusLower.includes("complete") ||
          statusLower.includes("done");

        if (isComplete) {
          setEntries((prev) => {
            if (!prev[key]) {
              return prev;
              }
            const next = { ...prev };
            delete next[key];
            return next;
          });
          setOrder((prev) => prev.filter((itemKey) => itemKey !== key));
        } else {
          const entry: QueueEntry = {
            key,
            name:
              (snapshot.song_display_name as string) ||
              (snapshot.song_name as string) ||
              key,
            status,
            progress: normalizedProgress,
            updatedAt: now,
            errorMessage:
              (snapshot.error_message as string) || (snapshot.errorMessage as string) || null,
            severity: (snapshot.severity as string) || null,
          };
          setEntries((prev) => ({ ...prev, [key]: entry }));
          setOrder((prev) => (prev.includes(key) ? prev : [...prev, key]));
        }
      }

      const statusText = (snapshot.status as string)?.toLowerCase() ?? "";
      const phase = (snapshot.phase as string)?.toLowerCase() ?? "";
      const completed =
        statusText.includes("complete") || phase.includes("complete") || snapshot.status === "Complete";
      setHasActiveDownload(!completed && (snapshot.overall_total ?? 0) > 0);
      if (completed) {
        setEntries({});
        setOrder([]);
      }
    },
    [],
  );

  useEffect(() => {
    processSnapshot(progressQuery.data);
  }, [processSnapshot, progressQuery.data]);

  const orderedEntries = useMemo(
    () =>
      order
        .map((key) => entries[key])
        .filter((entry): entry is QueueEntry => Boolean(entry))
        .sort((a, b) => a.updatedAt - b.updatedAt),
    [entries, order],
  );

  return (
    <ScrollView
      className="flex-1 bg-slate-950"
      contentContainerStyle={{
        paddingHorizontal: 24,
        paddingTop: insets.top + 24,
        paddingBottom: insets.bottom + 48,
      }}
    >
      <View className="rounded-3xl bg-slate-900/85 p-5">
        <Text className="text-sm uppercase tracking-wide text-slate-400">
          Overall Progress
        </Text>
        <Text className="mt-3 text-3xl font-semibold text-slate-100">
          {overall.completed} / {overall.total}
        </Text>
        <View className="mt-4 h-3 w-full rounded-full bg-slate-800">
          <View
            className="h-3 rounded-full bg-sky-500"
            style={{ width: `${overall.progress}%` }}
          />
        </View>
        <Text className="mt-3 text-sm text-slate-400">
          {progressQuery.isFetching ? "Updating…" : overall.status}
        </Text>
      </View>

      <Text className="mt-10 mb-4 text-lg font-semibold text-slate-100">
        Active downloads
      </Text>

      {progressQuery.isLoading ? (
        <View>
          <Skeleton height={70} style={{ marginBottom: 16 }} />
          <Skeleton height={70} />
        </View>
      ) : orderedEntries.length > 0 ? (
        orderedEntries.map((entry) => (
          <View key={entry.key} className="mb-4 rounded-3xl bg-slate-900/70 p-4">
            <View className="flex-row items-center justify-between">
              <Text numberOfLines={1} className="text-base font-semibold text-slate-100">
                {entry.name}
              </Text>
              <Text className="text-xs text-slate-400">{entry.progress}%</Text>
            </View>
            <View className="mt-3 h-2 w-full rounded-full bg-slate-800">
              <View
                className="h-2 rounded-full bg-emerald-500"
                style={{ width: `${entry.progress}%` }}
              />
            </View>
            {entry.status ? (
              <Text
                className={`mt-3 text-xs ${
                  entry.severity === "error"
                    ? "text-rose-400"
                    : "text-slate-400"
                }`}
              >
                {entry.status}
              </Text>
            ) : null}
            {entry.errorMessage && entry.errorMessage !== entry.status ? (
              <Text className="mt-2 text-xs text-rose-400">{entry.errorMessage}</Text>
            ) : null}
          </View>
        ))
      ) : hasActiveDownload ? (
        <Text className="text-sm text-slate-400">
          Download in progress. Waiting for next update…
        </Text>
      ) : (
        <EmptyState
          title="Queue is idle"
          description="Start a new download from Discover or the web console to see live updates here."
        />
      )}
    </ScrollView>
  );
};

export default DownloadQueueScreen;
