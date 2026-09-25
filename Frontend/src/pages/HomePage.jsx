import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import ListingCard from "../components/listings/ListingCard";
import ListingGrid from "../components/listings/ListingGrid";
import { getListingsPage } from "../api/listingsApi";
import coverImage from "../assets/cover.jpg";
import "./HomePage.css";

const pickFeaturedListings = (listings) => [...listings].sort(() => Math.random() - 0.5).slice(0, 6);

export default function HomePage() {
  const { t } = useTranslation();
  const [listings, setListings] = useState([]);
  const [featuredListings, setFeaturedListings] = useState([]);
  const [visibleCount, setVisibleCount] = useState(1);
  const featuredGridRef = useRef(null);

  useEffect(() => {
    // Featured cards are drawn from the newest page only, so the home page stays a single small request.
    getListingsPage().then(({ results: loadedListings }) => {
      setListings(loadedListings);
      setFeaturedListings(pickFeaturedListings(loadedListings));
    });
  }, []);

  useEffect(() => {
    const updateVisibleCount = () => {
      const gridWidth = featuredGridRef.current?.clientWidth || 0;
      const minimumCardWidth = 280;
      const gap = 16;
      const fittingCount = Math.floor((gridWidth + gap) / (minimumCardWidth + gap));
      setVisibleCount(Math.max(1, Math.min(6, fittingCount)));
    };

    updateVisibleCount();
    const observer = new ResizeObserver(updateVisibleCount);
    if (featuredGridRef.current) observer.observe(featuredGridRef.current);
    return () => observer.disconnect();
  }, []);

  const refreshFeatured = () => setFeaturedListings(pickFeaturedListings(listings));
  return (
    <div className="home-page">
      <section className="home-hero">
        <div className="home-hero-inner">
          <div>
            <p className="home-kicker">{t("home.kicker")}</p>
            <h1>{t("home.heading")}</h1>
            <p>{t("home.intro")}</p>
            <div className="home-hero-actions">
              <a href="/marketplace" className="home-primary-action">{t("home.browse")}</a>
              <a href="/postinput" className="home-secondary-action">{t("home.sell")}</a>
            </div>
          </div>
          <img className="home-hero-mark" src={coverImage} alt={t("home.coverAlt")} />
        </div>
      </section>
      <section className="home-featured">
        <div className="home-featured-inner">
          <div className="home-featured-heading">
            <div>
              <h2>{t("home.featuredHeading")}</h2>
              <p>{t("home.featuredIntro")}</p>
            </div>
            <button type="button" className="home-refresh" onClick={refreshFeatured}>{t("home.refresh")}</button>
          </div>
          <ListingGrid ref={featuredGridRef} variant="featured">
            {featuredListings.slice(0, visibleCount).map((animal) => <ListingCard key={animal.id} animal={animal} />)}
          </ListingGrid>
        </div>
      </section>
      <section className="home-story">
        <div className="home-story-inner">
          <p className="home-kicker">{t("home.storyKicker")}</p>
          <h2>{t("home.storyHeading")}</h2>
          <p>{t("home.storyBody")}</p>
        </div>
      </section>
    </div>
  );
}
