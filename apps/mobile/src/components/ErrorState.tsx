import React from "react";
import { Text, View } from "react-native";

interface ErrorStateProps {
  title?: string;
  message?: string;
  action?: React.ReactNode;
}

const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message,
  action,
}) => (
  <View className="items-center justify-center px-6 py-12">
    <Text className="text-lg font-semibold text-rose-400">{title}</Text>
    {message ? <Text className="mt-2 text-center text-sm text-rose-200">{message}</Text> : null}
    {action ? <View className="mt-4">{action}</View> : null}
  </View>
);

export default ErrorState;
