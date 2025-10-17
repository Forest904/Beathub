import React from "react";
import { Text, View } from "react-native";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  trailing?: React.ReactNode;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({ title, subtitle, trailing }) => (
  <View className="mb-3 flex-row items-center justify-between px-6">
    <View>
      <Text className="text-xl font-semibold text-slate-100">{title}</Text>
      {subtitle ? <Text className="text-sm text-slate-400">{subtitle}</Text> : null}
    </View>
    {trailing}
  </View>
);

export default SectionHeader;
