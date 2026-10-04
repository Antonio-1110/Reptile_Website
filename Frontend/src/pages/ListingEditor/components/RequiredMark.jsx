import "./ListingFormSection.css";

// Hidden from screen readers: the inputs carry `required`, which they announce already.
export default function RequiredMark() {
  return <span className="listing-form-required" aria-hidden="true">*</span>;
}
