const fs = require("fs");
const path = require("path");
const { getDefaultConfig } = require("@expo/metro-config");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "..", "..");
const pnpmVirtualStore = path.join(workspaceRoot, "node_modules", ".pnpm");

function resolveFromPnpmStore(pkgName) {
  if (!fs.existsSync(pnpmVirtualStore)) {
    return path.join(workspaceRoot, "node_modules", pkgName);
  }

  const match = fs
    .readdirSync(pnpmVirtualStore)
    .find((entry) => entry.startsWith(`${pkgName}@`));

  if (!match) {
    return path.join(workspaceRoot, "node_modules", pkgName);
  }

  return path.join(pnpmVirtualStore, match, "node_modules", pkgName);
}

const config = getDefaultConfig(projectRoot);

config.watchFolders = [workspaceRoot];
config.resolver.unstable_enableSymlinks = true;
config.resolver.nodeModulesPaths = [
  path.join(projectRoot, "node_modules"),
  path.join(workspaceRoot, "node_modules"),
];
config.resolver.disableHierarchicalLookup = false;
config.resolver.extraNodeModules = {
  ...config.resolver.extraNodeModules,
  "@cd-collector/shared": path.join(
    workspaceRoot,
    "packages",
    "shared",
    "dist"
  ),
  "expo-modules-core": resolveFromPnpmStore("expo-modules-core"),
  "react-native-css-interop": resolveFromPnpmStore("react-native-css-interop"),
  "react-native-css-interop/jsx-runtime": path.join(
    resolveFromPnpmStore("react-native-css-interop"),
    "jsx-runtime"
  ),
};

module.exports = config;
