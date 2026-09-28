import './LegalPage.css';
import { Trans, useTranslation } from 'react-i18next';
import { LEGAL_UPDATED, SUPPORT_EMAIL } from '../../constants/site';

// `doc` is "privacy" or "terms"; the text lives in the legal section of the locale files.
export default function LegalPage({ doc }) {
  const { t, i18n } = useTranslation();
  const sections = t(`legal.${doc}.sections`, { returnObjects: true });
  const updated = new Intl.DateTimeFormat(i18n.language === 'zh' ? 'zh-TW' : 'en', { dateStyle: 'long' })
    .format(new Date(`${LEGAL_UPDATED}T00:00:00`));

  return (
    <main className="legal-page">
      <article className="legal-inner">
        <h1>{t(`legal.${doc}.title`)}</h1>
        <p className="legal-updated">{t('legal.lastUpdated', { date: updated })}</p>
        <p>{t(`legal.${doc}.intro`)}</p>
        {Array.isArray(sections) && sections.map((section) => (
          <section key={section.heading}>
            <h2>{section.heading}</h2>
            {section.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            {section.items && (
              <ul>
                {section.items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            )}
          </section>
        ))}
        <p className="legal-contact">
          <Trans
            i18nKey="legal.contact"
            values={{ email: SUPPORT_EMAIL }}
            components={{ email: <a href={`mailto:${SUPPORT_EMAIL}`} /> }}
          />
        </p>
      </article>
    </main>
  );
}
