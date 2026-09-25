import { useTranslation } from "react-i18next";
import IncludeExcludeFilter from "./IncludeExcludeFilter";
import MultiSelectFilter from "./MultiSelectFilter";
import RangeFilter from "./RangeFilter";
import { LOCATION_KEYS } from "../../constants/locations";
import "./FilterSidebar.css";

export default function FilterSidebar({ filters, setFilters }) {
  const { t } = useTranslation();
  const updateFilter = (key, value) => {
    setFilters((currentFilters) => ({ ...currentFilters, [key]: value }));
  };

  const sexOptions = [
    { value: "1.0", label: t("filters.male") },
    { value: "0.1", label: t("filters.female") },
    { value: "unsexed", label: t("filters.unconfirmed") }
  ];
  const lifeStageOptions = [
    ...["hatchling", "juvenile", "subAdult", "adult"].map((value) => ({ value, label: t(`createListing.lifeStages.${value}`) })),
  ];
  const dietOptions = ["live", "frozenThawed", "pellets"].map((value) => ({ value, label: t(`createListing.diets.${value}`) }));
  const shippingOptions = ["localPickup", "shipping"].map((value) => ({ value, label: t(`createListing.shipping.${value}`) }));
  const locationOptions = LOCATION_KEYS.map((key) => ({ value: key, label: t(`locations.${key}`) }));
  return (
    <aside className="filter-sidebar">
      <div className="filter-sidebar-content">
        <h2>{t("filters.title")}</h2>
      <div className="filter-group">
        <MultiSelectFilter title="filters.sex" options={sexOptions} selectedValues={filters.sex} onChange={(values) => updateFilter("sex", values)} />
        <MultiSelectFilter title="filters.lifeStage" options={lifeStageOptions} selectedValues={filters.lifeStages} onChange={(values) => updateFilter("lifeStages", values)} />
        <MultiSelectFilter title="filters.diet" options={dietOptions} selectedValues={filters.diets} onChange={(values) => updateFilter("diets", values)} />
        <MultiSelectFilter title="filters.shipping" options={shippingOptions} selectedValues={filters.shippingMethods} onChange={(values) => updateFilter("shippingMethods", values)} />
      </div>
      <div className="filter-group">
        <RangeFilter title="filters.ageRange" min={filters.minAgeYears} max={filters.maxAgeYears} rangeMin={0} rangeMax={100} step={0.1} allowDecimal onMinChange={(value) => updateFilter("minAgeYears", value)} onMaxChange={(value) => updateFilter("maxAgeYears", value)} />
        <RangeFilter title="filters.weightRange" min={filters.minWeight} max={filters.maxWeight} rangeMin={0} rangeMax={100000} step={0.1} allowDecimal formatWithCommas onMinChange={(value) => updateFilter("minWeight", value)} onMaxChange={(value) => updateFilter("maxWeight", value)} />
        <RangeFilter title="filters.postedTime" min={filters.minPostedDays} max={filters.maxPostedDays} rangeMin={0} rangeMax={365} step={1} onMinChange={(value) => updateFilter("minPostedDays", value)} onMaxChange={(value) => updateFilter("maxPostedDays", value)} />
        <RangeFilter title="filters.priceRange" min={filters.minPrice} max={filters.maxPrice} rangeMin={0} rangeMax={1000000} step={50} formatWithCommas onMinChange={(value) => updateFilter("minPrice", value)} onMaxChange={(value) => updateFilter("maxPrice", value)} />
        <RangeFilter title="filters.size" min={filters.minSize} max={filters.maxSize} rangeMin={0} rangeMax={300} step={0.1} allowDecimal onMinChange={(value) => updateFilter("minSize", value)} onMaxChange={(value) => updateFilter("maxSize", value)} />
      </div>
      <IncludeExcludeFilter
        title="filters.location"
        includeLabel={t("filters.chooseLocations")}
        options={locationOptions}
        selectedValues={filters.locations}
        onSelectionChange={(values, include) => setFilters((currentFilters) => ({
          ...currentFilters,
          locations: values,
          includeLocations: include,
        }))}
      />
      </div>
    </aside>
  );
}