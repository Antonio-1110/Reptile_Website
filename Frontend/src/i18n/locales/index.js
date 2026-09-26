// Each file in en/ and zh/ is one top-level section of the translations, named after the file
// (en/favorites.js → t("favorites.…")). A feature adds its own file instead of editing a shared
// one, so branches built in parallel don't conflict here. New files are picked up automatically.
const bySection = (modules) => Object.fromEntries(
  Object.entries(modules).map(([path, module]) => [path.match(/([^/]+)\.js$/)[1], module.default]),
);

export const en = bySection(import.meta.glob("./en/*.js", { eager: true }));
export const zh = bySection(import.meta.glob("./zh/*.js", { eager: true }));
