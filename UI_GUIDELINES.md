# NSC UI Guidelines

## Official visual baseline
- Dashboard V3 is the official visual baseline for the UI.
- All pages must be harmonized against Dashboard V3.

## Versioning
- Semantic versioning must be used: MAJOR.MINOR.PATCH
- MAJOR = structural or UX overhaul
- MINOR = new page or major page harmonization
- PATCH = visual fixes, wording fixes, small UI corrections

## Current baseline
- Dashboard premium baseline: UI v3.0.0
- Control Room harmonization target: UI v3.1.0

## Layout rules
- Premium autonomous panels must not be wrapped inside SectionCard
- Simple informational blocks may use SectionCard
- Avoid double framing, duplicate headers, and nested premium wrappers

## Unified components
- StatusBadge is the single source of truth for badge rendering
- UiKit or other wrappers must delegate to StatusBadge

## Language
- Target language is English-only across the UI
- Avoid mixed wording such as Bonds / Obligations or Defensive Equities / Actions Défensives

## Naming targets
- Offensive Equities
- Defensive Equities
- Bonds
- Precious Metals
- Long Term
- Options US
