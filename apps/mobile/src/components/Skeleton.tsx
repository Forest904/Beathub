import React, { useEffect, useRef } from "react";
import { Animated, StyleProp, ViewStyle } from "react-native";

type SkeletonLength = number | `${number}%` | "auto";

interface SkeletonProps {
  width?: SkeletonLength;
  height?: number;
  borderRadius?: number;
  style?: StyleProp<ViewStyle>;
}

const Skeleton: React.FC<SkeletonProps> = ({
  width = "100%",
  height = 16,
  borderRadius = 12,
  style,
}) => {
  const opacity = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 0.9,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.4,
          duration: 700,
          useNativeDriver: true,
        }),
      ]),
    );
    animation.start();
    return () => {
      animation.stop();
    };
  }, [opacity]);

  const resolvedWidth: ViewStyle["width"] = width;

  return (
    <Animated.View
      style={[
        {
          width: resolvedWidth,
          height,
          borderRadius,
          backgroundColor: "#1f2937",
          opacity,
        },
        style,
      ]}
    />
  );
};

export default Skeleton;
