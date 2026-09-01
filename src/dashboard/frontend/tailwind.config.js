/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0b0d",
        surface: "#131417",
        border: "#1f2124",
        "border-hover": "#2d3035",
        accent: "#7ee787", // signal green
        "text-main": "#e6e6e6",
        "text-muted": "#8b8f94",
        "text-subtle": "#4a4d52",
        status: {
          success: "#7ee787",
          warning: "#e8b339",
          error: "#e5534b",
          info: "#6e9fe0",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["'IBM Plex Mono'", "Consolas", "Courier New", "monospace"],
      },
      borderRadius: {
        DEFAULT: "4px",
        sm: "2px",
        md: "4px",
        lg: "4px",
      },
      transitionDuration: {
        DEFAULT: "150ms",
        fast: "150ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};
