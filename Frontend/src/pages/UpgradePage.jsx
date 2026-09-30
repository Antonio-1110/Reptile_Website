import "./UpgradePage.css";
import { useEffect, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { getAccountPlans, getCurrentProfile } from "../api/listingsApi";
import { errorText, toErrorState } from "../utils/errorState";
import BackLink from "../components/ui/BackLink";
import { formatDate, formatMoney, formatPercent } from "../utils/auctionFormat";
import { SUPPORT_EMAIL } from "../constants/site";
import useFeature from "../hooks/useFeature";

// Plans in upgrade order, so anything after the current plan counts as an upgrade.
const PLAN_ORDER = ["hobbyist", "commercial", "commercial_paid"];

// The marketplace fee on auction sales comes from the API (a share such as "0.05"); 0 is advertised as free.
function auctionFeeText(t, language, rate) {
  if (!Number(rate)) return t("upgrade.features.auctionFeeFree");
  return t("upgrade.features.auctionFee", { percent: formatPercent(rate, language) });
}

function priceText(t, language, plan) {
  if (!Number(plan.monthly_price)) return t("upgrade.price.free");
  return t("upgrade.price.monthly", { price: formatMoney(plan.monthly_price, plan.currency, language) });
}

function currentPlanId(profile) {
  if (profile.account_type !== "commercial") return "hobbyist";
  return profile.is_paid_account ? "commercial_paid" : "commercial";
}

// There's no online checkout yet: staff change plans by hand (in the admin) for sellers who email
// support, so choosing a plan explains how to ask.
export default function UpgradePage() {
  const { t, i18n } = useTranslation();
  const auctionsOn = useFeature("auctions");
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
      <BackLink to="/settings">{t("upgrade.back")}</BackLink>
      <p className="upgrade-kicker">{t("navigation.account")}</p>
      <h1 className="upgrade-title">{t("upgrade.title")}</h1>
      <p className="upgrade-subtitle">{t(auctionsOn ? "upgrade.subtitle" : "upgrade.subtitleNoAuctions")}</p>
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

      {auctionsOn && profile.launch_offer_ends_at && (
        <p className="upgrade-launch-offer">
          {t("upgrade.launchOffer", {
            date: formatDate(new Date(profile.launch_offer_ends_at), i18n.language),
          })}
        </p>
      )}

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
              <p className="upgrade-plan-price">{priceText(t, i18n.language, plan)}</p>
              <p className="upgrade-plan-description">
                {/* Plans whose description mentions auctions have a version without them. */}
                {t(auctionsOn ? `upgrade.plans.${plan.id}.description` : [`upgrade.plans.${plan.id}.descriptionNoAuctions`, `upgrade.plans.${plan.id}.description`])}
              </p>
              <ul className="upgrade-plan-features">
                <li>{t("upgrade.features.listings", { count: plan.max_post_count })}</li>
                <li>{t("upgrade.features.photos", { count: plan.max_images_per_post })}</li>
                {auctionsOn && <li>{t(plan.can_start_auction ? "upgrade.features.auctions" : "upgrade.features.noAuctions")}</li>}
                {auctionsOn && plan.can_start_auction && <li>{auctionFeeText(t, i18n.language, plan.auction_fee_rate)}</li>}
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
          <p>{t("upgrade.checkout.body", { username: profile.username })}</p>
          <p className="upgrade-checkout-email">
            <Trans
              i18nKey="upgrade.checkout.email"
              values={{ email: SUPPORT_EMAIL }}
              components={{
                email: <a href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
                  t("upgrade.checkout.subject", { plan: t(`upgrade.plans.${chosenPlan}.name`), username: profile.username }),
                )}`} />,
              }}
            />
          </p>
        </div>
      )}
    </div>
  );
}
