import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";

type SnackbarKind = "info" | "error";

interface SnackbarOptions {
  type?: SnackbarKind;
  duration?: number;
}

interface SnackbarContextValue {
  show: (message: string, options?: SnackbarOptions) => void;
  showError: (message: string, options?: Omit<SnackbarOptions, "type">) => void;
  dismiss: () => void;
}

const SnackbarContext = createContext<SnackbarContextValue>({
  show: () => undefined,
  showError: () => undefined,
  dismiss: () => undefined,
});

const DEFAULT_DURATION = 4000;

export const SnackbarProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [visible, setVisible] = useState(false);
  const [message, setMessage] = useState("");
  const [kind, setKind] = useState<SnackbarKind>("info");
  const translateY = useRef(new Animated.Value(80)).current;
  const hideTimeout = useRef<NodeJS.Timeout | null>(null);

  const clearTimer = useCallback(() => {
    if (hideTimeout.current) {
      clearTimeout(hideTimeout.current);
      hideTimeout.current = null;
    }
  }, []);

  const animateTo = useCallback(
    (toValue: number, onComplete?: () => void) => {
      Animated.timing(translateY, {
        toValue,
        duration: 250,
        easing: Easing.out(Easing.ease),
        useNativeDriver: true,
      }).start(({ finished }) => {
        if (finished && onComplete) {
          onComplete();
        }
      });
    },
    [translateY],
  );

  const hide = useCallback(() => {
    animateTo(80, () => {
      setVisible(false);
      setMessage("");
    });
  }, [animateTo]);

  const show = useCallback(
    (text: string, options?: SnackbarOptions) => {
      if (!text) {
        return;
      }
      clearTimer();
      setMessage(text);
      setKind(options?.type ?? "info");
      setVisible(true);
      animateTo(0);
      const duration = options?.duration ?? DEFAULT_DURATION;
      if (duration > 0) {
        hideTimeout.current = setTimeout(() => {
          hide();
        }, duration);
      }
    },
    [animateTo, clearTimer, hide],
  );

  const showError = useCallback(
    (text: string, options?: Omit<SnackbarOptions, "type">) => {
      show(text, { ...options, type: "error" });
    },
    [show],
  );

  const dismiss = useCallback(() => {
    clearTimer();
    hide();
  }, [clearTimer, hide]);

  const contextValue = useMemo(
    () => ({
      show,
      showError,
      dismiss,
    }),
    [dismiss, show, showError],
  );

  return (
    <SnackbarContext.Provider value={contextValue}>
      {children}
      <View pointerEvents="none" style={styles.absolute}>
        {visible ? (
          <Animated.View
            style={[
              styles.snackbar,
              kind === "error" ? styles.error : styles.info,
              { transform: [{ translateY }] },
            ]}
          >
            <Text style={styles.text}>{message}</Text>
          </Animated.View>
        ) : null}
      </View>
    </SnackbarContext.Provider>
  );
};

export const useSnackbar = () => useContext(SnackbarContext);

const styles = StyleSheet.create({
  absolute: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 24,
    alignItems: "center",
    paddingHorizontal: 16,
  },
  snackbar: {
    minWidth: "40%",
    maxWidth: "90%",
    borderRadius: 12,
    paddingHorizontal: 18,
    paddingVertical: 14,
    shadowColor: "#000",
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 8,
  },
  info: {
    backgroundColor: "#1e293b",
  },
  error: {
    backgroundColor: "#b91c1c",
  },
  text: {
    color: "#f8fafc",
    fontSize: 15,
    fontWeight: "500",
  },
});
