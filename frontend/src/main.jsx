import { createRoot } from "react-dom/client";
import BrandList from "./BrandList.jsx";

// Django renders <div id="brand-list-root"> plus a json_script with the industry options.
const root = document.getElementById("brand-list-root");
if (root) {
  const el = document.getElementById("brand-list-industries");
  const industries = el ? JSON.parse(el.textContent) : [];
  createRoot(root).render(
    <BrandList
      industries={industries}
      apiBase={root.dataset.api || "/api/brands/"}
    />,
  );
}
