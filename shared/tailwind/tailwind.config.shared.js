/**
 * Platform Shared Tailwind Config (ADR-049)
 *
 * Maps semantic color names to CSS Custom Properties defined in pui-tokens.css.
 * Each app uses this as a Tailwind preset:
 *
 *   // tailwind.config.js
 *   const shared = require("../platform/shared/tailwind/tailwind.config.shared");
 *   module.exports = { presets: [shared], content: ["./templates/**/*.html"] };
 *
 * Result: `bg-primary` compiles to `background-color: var(--pui-primary)`.
 */

module.exports = {
  theme: {
    extend: {
      colors: {
        primary:         "var(--pui-primary)",
        "primary-hover": "var(--pui-primary-hover)",
        surface:         "var(--pui-surface)",
        "surface-alt":   "var(--pui-surface-alt)",
        success:         "var(--pui-success)",
        danger:          "var(--pui-danger)",
        warning:         "var(--pui-warning)",
        foreground:      "var(--pui-foreground)",
        muted:           "var(--pui-muted)",
        border:          "var(--pui-border)",
        "border-strong": "var(--pui-border-strong)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      borderRadius: {
        DEFAULT: "var(--pui-radius-md)",
        sm: "var(--pui-radius-sm)",
        lg: "var(--pui-radius-lg)",
      },
      boxShadow: {
        sm: "var(--pui-shadow-sm)",
        md: "var(--pui-shadow-md)",
        lg: "var(--pui-shadow-lg)",
      },
    },
  },
};
