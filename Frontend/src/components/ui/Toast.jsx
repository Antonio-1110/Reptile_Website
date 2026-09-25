import './Toast.css';
import { useTranslation } from 'react-i18next';

export default function Toast({ message, tone = 'success', onDismiss }) {
  const { t } = useTranslation();
  return (
    <div role="status" className={`toast toast--${tone}`}>
      <span className="toast-message">{message}</span>
      <button type="button" onClick={onDismiss} aria-label={t('common.dismiss')} className="toast-dismiss">
        ×
      </button>
    </div>
  );
}
