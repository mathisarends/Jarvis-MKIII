/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      maxWidth: {
        "8xl": "88rem", // 1408px
        "9xl": "96rem", // 1536px
        "10xl": "104rem", // 1664px
        "11xl": "112rem", // 1792px
        "12xl": "120rem", // 1920px
        "13xl": "128rem", // 2048px
        "14xl": "136rem", // 2176px
      },
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
      },
    },
  },
  plugins: [],
};
