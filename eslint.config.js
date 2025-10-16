import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import jsxA11yPlugin from "eslint-plugin-jsx-a11y";
import importPlugin from "eslint-plugin-import";

const tsRules = tseslint.configs?.recommended?.rules ?? {};
const reactRules = reactPlugin.configs?.recommended?.rules ?? {};
const reactJsxRuntimeRules = reactPlugin.configs?.["jsx-runtime"]?.rules ?? {};
const hooksRules = reactHooksPlugin.configs?.recommended?.rules ?? {};
const a11yRules = jsxA11yPlugin.configs?.recommended?.rules ?? {};

export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/build/**",
      "**/.expo/**",
      "**/.turbo/**"
    ],
  },
  {
    files: ["**/*.{js,jsx,ts,tsx}", "*.cjs"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
      "jsx-a11y": jsxA11yPlugin,
      import: importPlugin,
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      ...tsRules,
      ...reactRules,
      ...reactJsxRuntimeRules,
      ...hooksRules,
      ...a11yRules,
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
      "react/prop-types": "off",
      "react/react-in-jsx-scope": "off",
      "react/jsx-uses-react": "off",
      "import/no-unresolved": "error",
      "import/order": [
        "warn",
        {
          groups: [["builtin", "external"], "internal", ["parent", "sibling", "index"]],
          "newlines-between": "always",
          alphabetize: {
            order: "asc",
            caseInsensitive: true,
          },
        },
      ],
    },
  },
];
