import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

console.log("MAIN LOADED - build timestamp", new Date().toISOString());
console.log("VITE_API_URL =", import.meta.env.VITE_API_URL);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

console.log("Render call finished");
