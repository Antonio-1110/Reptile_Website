import { useTranslation } from 'react-i18next';

// Keys of Account.contact_details() on the backend, in display order.
const CONTACT_FIELDS = ['name', 'email', 'phone', 'line', 'instagram', 'facebook'];

// A person's contact details as "Label: value" lines (the buyer's own, or the other side of a sale).
export default function ContactLines({ contact }) {
  const { t } = useTranslation();
  return (
    <dl className="action-panel-lines">
      {CONTACT_FIELDS.filter((field) => contact?.[field]).map((field) => (
        <div key={field}>
          <dt>{t(`listingDetail.contactFields.${field}`)}</dt>
          <dd>{contact[field]}</dd>
        </div>
      ))}
    </dl>
  );
}
