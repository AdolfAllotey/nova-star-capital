// src/config/features.js
// Feature flags UI (source unique côté front)

export const FEATURES = {
  // crypto modules
  CRYPTO_ICO: true, // API /ico/* encore 404 en PREPROD

  // Briquets futures (V3/V4)
  BRICK_OFFENSIVE: false,
  BRICK_DEFENSIVE: false,
  BRICK_LT: false,
  BRICK_OPTIONS: false,

  // Options d'affichage
  SHOW_COMING_SOON_ITEMS: true, // si false => on cache les items "coming soon"
};
