import { useId } from "react";
import { useTranslation } from "react-i18next";
import "./FilterSection.css";

// Shared chrome (heading + controls row) for every section in the filter sidebar.
// The controls are a labelled group, so a screen reader announces "Sex, group" before "Male, toggle".
export default function FilterSection({ title, children }) {
  const { t } = useTranslation();
  const headingId = useId();

  return (
    <section className="filter-section">
      <h4 id={headingId}>{t(title)}</h4>
      <div className="filter-controls" role="group" aria-labelledby={headingId}>{children}</div>
    </section>
  );
}
