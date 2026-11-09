/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Light console: lavender page, white cards, near-black ink.
        // Token names are kept from the original dark theme (950 = page
        // background ... 100 = primary text), so every component re-themes
        // from here without touching its class names.
        surface: {
          950: "#EEF0F8", // page background
          900: "#F5F6FB", // inset panels, inputs
          800: "#FFFFFF", // cards
          700: "#E1E4EF", // borders, dividers
          600: "#CBD0E0", // stronger borders
          500: "#9AA1B8", // disabled/inactive
          400: "#666D85", // muted text
          300: "#474D63", // labels
          200: "#2C3145", // secondary text
          100: "#0E1020", // primary text
        },
        // The accent ("teal" kept as the token name): electric blue, the
        // "protected / calm" state.
        teal: {
          300: "#2A44D6",
          400: "#3350F5",
          500: "#3B5BFD",
          600: "#2440E0",
        },
        // Reserved ONLY for actual threat states — functional, not decorative.
        danger: {
          400: "#D92D2D",
          500: "#EF4444",
          600: "#C81E1E",
        },
        amber: {
          400: "#B86E00",
          500: "#F59E0B",
        },
        // Landing page / hero.
        ink: "#05060D",
        electric: {
          300: "#8FA2FF",
          400: "#6B83FF",
          500: "#3B5BFD",
          600: "#2236F0",
          700: "#1A22B8",
        },
      },
      fontFamily: {
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.045em",
      },
      boxShadow: {
        card: "0 1px 2px rgba(14,16,32,0.04), 0 8px 24px -12px rgba(14,16,32,0.10)",
        glow: "0 10px 40px -10px rgba(59,91,253,0.55)",
      },
    },
  },
  plugins: [],
};
