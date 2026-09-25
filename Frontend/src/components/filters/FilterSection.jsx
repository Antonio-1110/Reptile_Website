import { useTranslation } from "react-i18next";
import "./FilterSection.css";

// Shared chrome (heading + controls row) for every section in the filter sidebar.
export default function FilterSection({ title, children }) {
  const { t } = useTranslation();

  return (
    <section className="filter-section">
      <h4>{t(title)}</h4>
      <div className="filter-controls">{children}</div>
    </section>
  );
}
