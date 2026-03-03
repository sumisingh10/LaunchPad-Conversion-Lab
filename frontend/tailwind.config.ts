import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#102133",
        mist: "#f4f7fb",
        accent: "#0f766e",
        warm: "#f59e0b"
      }
    }
  },
  plugins: []
};

export default config;
