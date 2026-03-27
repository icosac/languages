/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./core/templates/**/*.html",
    "./core/**/*.py"
  ],
  theme: {
    extend: {
      colors: {
        surface: "#f9f9fb",
        "surface-container-low": "#f2f4f7",
        "surface-container-lowest": "#ffffff",
        "surface-container-high": "#e4e9ee",
        primary: "#496177",
        "primary-dim": "#3d556a",
        "primary-container": "#cce5ff",
        "on-primary-container": "#153046",
        "on-surface": "#2d3338",
        "on-surface-variant": "#61707d",
        "outline-variant": "#acb3b8",
        muted: "#dbe2e8"
      },
      fontFamily: {
        display: ["Manrope", "sans-serif"],
        body: ["Manrope", "sans-serif"],
        label: ["Inter", "sans-serif"]
      },
      boxShadow: {
        soft: "0 20px 40px rgba(45, 51, 56, 0.06)"
      },
      borderRadius: {
        panel: "1rem",
        card: "1.25rem"
      },
      backgroundImage: {
        "primary-gradient": "linear-gradient(120deg, #496177 0%, #3d556a 100%)"
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem"
      }
    }
  },
  plugins: []
};
