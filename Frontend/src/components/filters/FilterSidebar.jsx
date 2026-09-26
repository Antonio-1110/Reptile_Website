import { useTranslation } from "react-i18next";
import IncludeExcludeFilter from "./IncludeExcludeFilter";
import MultiSelectFilter from "./MultiSelectFilter";
import RangeFilter from "./RangeFilter";
import CategorySwitch from "../ui/CategorySwitch";
import { LOCATION_KEYS } from "../../constants/locations";
import { EQUIPMENT_CATEGORIES, EQUIPMENT_CONDITIONS } from "../../constants/equipment";
import { MARKETPLACE_CATEGORIES } from "../../utils/marketplaceSearch";
import "./FilterSidebar.css";

// The switch at the top picks what the marketplace shows; the filters below follow it.
export default function FilterSidebar({ category, onCategoryChange, filters, setFilters }) {
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
  const equipmentTypeOptions = EQUIPMENT_CATEGORIES.map((value) => ({ value, label: t(`createListing.equipment.types.${value}`) }));
  const conditionOptions = EQUIPMENT_CONDITIONS.map((code) => ({ value: String(code), label: t(`createListing.equipment.conditions.${code}`) }));
  const isEquipment = category === "equipment";
  const range = (title, minKey, maxKey, props) => (
    <RangeFilter title={title} min={filters[minKey]} max={filters[maxKey]} onMinChange={(value) => updateFilter(minKey, value)} onMaxChange={(value) => updateFilter(maxKey, value)} {...props} />
  );
  return (
    <aside className="filter-sidebar">
      <div className="filter-sidebar-content">
        <h2>{t("filters.title")}</h2>
      <CategorySwitch
        className="filter-category"
        labelClassName="filter-category-label"
        label={t("filters.category")}
        options={MARKETPLACE_CATEGORIES.map((value) => ({ value, label: t(`filters.categories.${value}`) }))}
        value={category}
        onChange={onCategoryChange}
      />
      {isEquipment ? (
        <>
          <div className="filter-group">
            <MultiSelectFilter title="filters.equipmentType" options={equipmentTypeOptions} selectedValues={filters.equipmentTypes} onChange={(values) => updateFilter("equipmentTypes", values)} />
            <MultiSelectFilter title="filters.condition" options={conditionOptions} selectedValues={filters.conditions} onChange={(values) => updateFilter("conditions", values)} />
            <MultiSelectFilter title="filters.shipping" options={shippingOptions} selectedValues={filters.shippingMethods} onChange={(values) => updateFilter("shippingMethods", values)} />
          </div>
          <div className="filter-group">
            {range("filters.postedTime", "minPostedDays", "maxPostedDays", { rangeMin: 0, rangeMax: 365, step: 1 })}
            {range("filters.priceRange", "minPrice", "maxPrice", { rangeMin: 0, rangeMax: 1000000, step: 50, formatWithCommas: true })}
          </div>
        </>
      ) : (
        <>
          <div className="filter-group">
            <MultiSelectFilter title="filters.sex" options={sexOptions} selectedValues={filters.sex} onChange={(values) => updateFilter("sex", values)} />
            <MultiSelectFilter title="filters.lifeStage" options={lifeStageOptions} selectedValues={filters.lifeStages} onChange={(values) => updateFilter("lifeStages", values)} />
            <MultiSelectFilter title="filters.diet" options={dietOptions} selectedValues={filters.diets} onChange={(values) => updateFilter("diets", values)} />
            <MultiSelectFilter title="filters.shipping" options={shippingOptions} selectedValues={filters.shippingMethods} onChange={(values) => updateFilter("shippingMethods", values)} />
          </div>
          <div className="filter-group">
            {range("filters.ageRange", "minAgeYears", "maxAgeYears", { rangeMin: 0, rangeMax: 100, step: 0.1, allowDecimal: true })}
            {range("filters.weightRange", "minWeight", "maxWeight", { rangeMin: 0, rangeMax: 100000, step: 0.1, allowDecimal: true, formatWithCommas: true })}
            {range("filters.postedTime", "minPostedDays", "maxPostedDays", { rangeMin: 0, rangeMax: 365, step: 1 })}
            {range("filters.priceRange", "minPrice", "maxPrice", { rangeMin: 0, rangeMax: 1000000, step: 50, formatWithCommas: true })}
            {range("filters.size", "minSize", "maxSize", { rangeMin: 0, rangeMax: 300, step: 0.1, allowDecimal: true })}
          </div>
        </>
      )}
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