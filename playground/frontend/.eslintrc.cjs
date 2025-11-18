module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },
  settings: {
    react: {
      version: "detect",
    },
  },
  plugins: [
    "@typescript-eslint",
    "react",
    "react-hooks",
    "testing-library",
    "jsx-a11y",
    "storybook",
  ],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:testing-library/react",
    "plugin:storybook/recommended",
    "plugin:@typescript-eslint/stylistic",
    "prettier",
  ],
  rules: {
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
  "react-hooks/exhaustive-deps": "warn",
  "react-hooks/rules-of-hooks": "error",
  "react-hooks/purity": "off",
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/consistent-type-definitions": "off",
    "@typescript-eslint/array-type": "off",
    "@typescript-eslint/no-explicit-any": "off",
    "testing-library/prefer-screen-queries": "off",
    "storybook/no-renderer-packages": "off",
  },
  overrides: [
    {
      files: ["src/**/*.test.{ts,tsx}", "src/**/*.spec.{ts,tsx}"],
      rules: {
        "react/jsx-no-bind": "off",
      },
    },
  ],
};
