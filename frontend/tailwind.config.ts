import type { Config } from "tailwindcss";

/** VEL-48: Tailwind v4 — theme tokens sourced from admin/design/v0.1/tokens.css */
const config: Config = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:          "var(--bg)",
        surface:     "var(--surface)",
        "surface-2": "var(--surface-2)",
        border:      "var(--border)",
        text:        "var(--text)",
        "text-muted":"var(--text-muted)",
        accent:      "var(--accent)",
        "accent-hover":"var(--accent-hover)",
        danger:      "var(--danger)",
        success:     "var(--success)",
        error:       "var(--error)",
        "input-bg":  "var(--input-bg)",
        "warning-bg":"var(--warning-bg)",
        "warning-border":"var(--warning-border)",
        "warning-text":"var(--warning-text)",
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm:      "calc(var(--radius) - 2px)",
        lg:      "calc(var(--radius) + 2px)",
        full:    "9999px",
      },
      fontFamily: {
        sans: ["var(--font)"],
        mono: ["var(--font-mono)"],
      },
      fontSize: {
        xs:  ["11.5px", { lineHeight: "1.5" }],
        sm:  ["12.5px", { lineHeight: "1.5" }],
        base:["14px",   { lineHeight: "1.5" }],
        lg:  ["16px",   { lineHeight: "1.5" }],
      },
      keyframes: {
        shimmer: {
          "0%":   { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition:  "400px 0" },
        },
        toastIn: {
          from: { opacity: "0", transform: "translateX(16px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        modalIn: {
          from: { opacity: "0", transform: "translate(-50%, -46%)" },
          to:   { opacity: "1", transform: "translate(-50%, -50%)" },
        },
        drawerIn: {
          from: { opacity: "0", transform: "translateX(20px)" },
          to:   { opacity: "1", transform: "translateX(0)"  },
        },
        spin: {
          to: { transform: "rotate(360deg)" },
        },
      },
      animation: {
        shimmer:  "shimmer 1.4s linear infinite",
        "toast-in": "toastIn .18s ease",
        "fade-in":  "fadeIn .15s ease",
        "modal-in": "modalIn .18s ease",
        "drawer-in":"drawerIn .2s ease",
        spin:       "spin .7s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
