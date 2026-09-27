import "./PasswordRules.css";
import { useTranslation } from "react-i18next";
import { PASSWORD_MIN_LENGTH, passwordRuleStates } from "../../constants/passwordRules";

// The password rules under a new-password field, ticked off as the person types. Shown up front rather
// than only after a rejected attempt; the server still has the final say. Point the input's
// aria-describedby at `id`.
export default function PasswordRules({ id, password }) {
  const { t } = useTranslation();
  return (
    <div id={id} className="password-rules">
      <p>{t("passwordRules.heading")}</p>
      <ul>
        {passwordRuleStates(password).map(({ key, met }) => (
          <li key={key} className={met ? "is-met" : undefined}>
            <span aria-hidden="true">{met ? "✓" : "•"}</span>
            {t(`passwordRules.${key}`, { count: PASSWORD_MIN_LENGTH })}
            {password && <span className="password-rules-sr"> ({t(met ? "passwordRules.met" : "passwordRules.notMet")})</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
