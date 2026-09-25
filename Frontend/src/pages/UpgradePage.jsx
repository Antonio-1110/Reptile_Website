import "./UpgradePage.css";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getAccountPlans, getCurrentProfile } from "../api/listingsApi";
import { errorText, toErrorState } from "../utils/errorState";

// Plans in upgrade order, so anything after the current plan counts as an upgrade.
const PLAN_ORDER = ["hobbyist", "commercial", "commercial_paid"];

function currentPlanId(profile) {
  if (profile.account_type !== "commercial") return "hobbyist";
  return profile.is_paid_account ? "commercial_paid" : "commercial";
}

// Checkout is a placeholder until a payment provider is chosen; choosing a plan only explains that.
export default function UpgradePage() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState(null);
  const [plans, setPlans] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [chosenPlan, setChosenPlan] = useState(null);

  useEffect(() => {
    Promise.all([getCurrentProfile(), getAccountPlans()])
      .then(([loadedProfile, loadedPlans]) => {
        setProfile(loadedProfile);
        setPlans(loadedPlans);
      })
      .catch((error) => setLoadError(toErrorState(error, "upgrade.loadError")));
  }, []);

  const header = (
    <div className="upgrade-header">
      <div>
        <p className="upgrade-kicker">{t("navigation.account")}</p>
        <h1 className="upgrade-title">{t("upgrade.title")}</h1>
        <p className="upgrade-subtitle">{t("upgrade.subtitle")}</p>
      </div>
      <a href="/settings" className="upgrade-back">{t("upgrade.back")}</a>
    </div>
  );

  if (!profile || !plans) {
    return (
      <div className="upgrade-page">
        {header}
        {loadError
          ? <p role="alert" className="upgrade-error">{errorText(t, loadError)}</p>
          : <p className="upgrade-loading">{t("upgrade.loading")}</p>}
      </div>
    );
  }

  const currentIndex = PLAN_ORDER.indexOf(currentPlanId(profile));

  return (
    <div className="upgrade-page">
      {header}

      <div className="upgrade-plans">
        {plans.map((plan) => {
          const planIndex = PLAN_ORDER.indexOf(plan.id);
          const isCurrent = planIndex === currentIndex;
          const isUpgrade = planIndex > currentIndex;
          return (
            <section key={plan.id} className={`upgrade-plan${isCurrent ? " is-current" : ""}`}>
              <div className="upgrade-plan-top">
                <h2 className="upgrade-plan-name">{t(`upgrade.plans.${plan.id}.name`)}</h2>
                {isCurrent && <span className="upgrade-plan-badge">{t("upgrade.current")}</span>}
              </div>
              <p className="upgrade-plan-description">{t(`upgrade.plans.${plan.id}.description`)}</p>
              <ul className="upgrade-plan-features">
                <li>{t("upgrade.features.listings", { count: plan.max_post_count })}</li>
                <li>{t("upgrade.features.photos", { count: plan.max_images_per_post })}</li>
                <li>{t(plan.can_start_auction ? "upgrade.features.auctions" : "upgrade.features.noAuctions")}</li>
              </ul>
              {isUpgrade && (
                <button type="button" className="upgrade-plan-choose" onClick={() => setChosenPlan(plan.id)}>
                  {t("upgrade.choose")}
                </button>
              )}
            </section>
          );
        })}
      </div>

      {chosenPlan && (
        <div role="status" className="upgrade-checkout-placeholder">
          <p className="upgrade-checkout-title">
            {t("upgrade.checkout.title", { plan: t(`upgrade.plans.${chosenPlan}.name`) })}
          </p>
          <p>{t("upgrade.checkout.body")}</p>
        </div>
      )}
    </div>
  );
}
