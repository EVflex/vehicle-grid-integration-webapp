// Dev-only proxy: the browser calls the API same-origin (avoids CORS), and the
// dev server forwards those paths to the real VGI API. In production the app
// uses the absolute VUE_APP_API_URL from .env.production instead.
module.exports = {
  devServer: {
    proxy: {
      "^/(get-options|lv-network|lv-network-defaults|network-topology|simulate)": {
        target: process.env.VGI_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  }
};
