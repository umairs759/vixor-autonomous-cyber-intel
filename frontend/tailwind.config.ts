/** VIXOR — Tailwind CSS config with DESIGN.md tokens */

import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // DESIGN.md palette
        background: "#07090D",
        surface: "#0E131B",
        elevated: "#151C27",
        border: "#1F2937",
        text: "#E6EDF3",
        muted: "#8B98A9",
        primary: "#22D3EE",   // electric cyan
        accent: "#F5B83D",    // amber
        // Severity colors
        critical: "#F43F5E",
        high: "#F97316",
        medium: "#F5B83D",
        low: "#38BDF8",
        info: "#94A3B8",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      fontSize: {
        "12": ["0.75rem", { lineHeight: "1rem" }],
        "14": ["0.875rem", { lineHeight: "1.25rem" }],
        "16": ["1rem", { lineHeight: "1.5rem" }],
        "20": ["1.25rem", { lineHeight: "1.75rem" }],
        "28": ["1.75rem", { lineHeight: "2rem" }],
        "40": ["2.5rem", { lineHeight: "3rem" }],
      },
      borderRadius: {
        sm: "0.375rem",
        DEFAULT: "0.5rem",
        lg: "0.75rem",
        full: "9999px",
      },
      spacing: {
        "1": "0.25rem",
        "2": "0.5rem",
        "3": "0.75rem",
        "4": "1rem",
        "6": "1.5rem",
        "8": "2rem",
        "12": "3rem",
        "16": "4rem",
      },
    },
  },
  plugins: [],
}

export default config
