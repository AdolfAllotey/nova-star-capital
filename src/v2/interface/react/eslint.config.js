import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import babelParser from "@babel/eslint-parser";

export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "**/*.backup.*",
      "**/*_min.*",
      "src/App.backup.jsx",
      "src/App_min.jsx",
    ],
  },

  js.configs.recommended,

  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
        babelOptions: {
          plugins: ["@babel/plugin-syntax-jsx"],
        },
},
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // React Hooks rules
      ...reactHooks.configs.recommended.rules,

      // Vite/React refresh
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],

      // Make preprod lint non-blocking
      "no-empty": "warn",
      "no-constant-binary-expression": "warn",

      // Keep warnings only for unused
      "no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^(React|_)",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },
];
