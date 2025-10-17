import React from "react";
import { Text, View } from "react-native";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon }) => (
  <View className="items-center justify-center px-6 py-12">
    {icon}
    <Text className="mt-2 text-lg font-semibold text-slate-200">{title}</Text>
    {description ? <Text className="mt-1 text-center text-sm text-slate-400">{description}</Text> : null}
  </View>
);

export default EmptyState;
