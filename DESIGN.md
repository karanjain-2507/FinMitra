---
name: Sage Clarity Material
colors:
  surface: '#f6fbf1'
  surface-dim: '#d6dcd2'
  surface-bright: '#f6fbf1'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f5eb'
  surface-container: '#eaf0e6'
  surface-container-high: '#e4eae0'
  surface-container-highest: '#dfe4db'
  on-surface: '#171d17'
  on-surface-variant: '#434843'
  inverse-surface: '#2c322b'
  inverse-on-surface: '#edf2e9'
  outline: '#737873'
  outline-variant: '#c3c8c1'
  surface-tint: '#4f6354'
  primary: '#384b3d'
  on-primary: '#ffffff'
  primary-container: '#4f6354'
  on-primary-container: '#c8decb'
  inverse-primary: '#b6ccba'
  secondary: '#536254'
  on-secondary: '#ffffff'
  secondary-container: '#d6e7d5'
  on-secondary-container: '#59685a'
  tertiary: '#244c5a'
  on-tertiary: '#ffffff'
  tertiary-container: '#3d6473'
  on-tertiary-container: '#b7dff1'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e8d5'
  primary-fixed-dim: '#b6ccba'
  on-primary-fixed: '#0d1f14'
  on-primary-fixed-variant: '#384b3d'
  secondary-fixed: '#d6e7d5'
  secondary-fixed-dim: '#bacbba'
  on-secondary-fixed: '#111f14'
  on-secondary-fixed-variant: '#3c4a3d'
  tertiary-fixed: '#c0e9fa'
  tertiary-fixed-dim: '#a5cdde'
  on-tertiary-fixed: '#001f29'
  on-tertiary-fixed-variant: '#234c5a'
  background: '#f6fbf1'
  on-background: '#171d17'
  surface-variant: '#dfe4db'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 57px
    fontWeight: '400'
    lineHeight: 64px
    letterSpacing: -0.25px
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 44px
    fontWeight: '400'
    lineHeight: 52px
    letterSpacing: 0px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0.15px
  title-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.1px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0.5px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0.25px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.4px
  label-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.1px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.5px
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.5px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 1.5rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system delivers a calm, authoritative, and deeply reassuring utility experience for digital credit passports and financial health management. Guided by Google's Material 3 (Material You) expressive design philosophy, the visual identity rejects anxiety-inducing financial tropes—such as aggressive red alerts, cold neon gradients, and hyperactive dashboard metrics—in favor of deliberate tranquility, balance, and transparency.

The aesthetic leans on natural tones, organic warmth, and structural legibility. The interface feels native, tactile, and grounded, evoking the physical presence of a high-security paper passport paired with the effortless clarity of a modern Google Pixel system experience. Tactile interactions rely on tonal surface transitions rather than heavy drop shadows, providing clarity without visual noise.

## Colors

The palette is rooted in dynamic tonal relationships engineered for comfort and accessibility:

- **Primary (`#4F6354`)**: A deep, balanced sage green providing institutional trust without corporate rigidity.
- **On Primary (`#FFFFFF`)**: High-contrast pure white for prominent action text and iconography.
- **Primary Container (`#D2E8D6`)**: A soft pastel sage tint that serves as a gentle highlight for key active states, badge backgrounds, and primary metric cards.
- **On Primary Container (`#0C1F13`)**: Ultra-dark evergreen text providing crisp contrast on soft primary containers.
- **Surface Hierarchy**:
  - `Background`: `#FAFDF7` (warm organic off-white foundation)
  - `Surface`: `#FFFFFF`
  - `Surface Container Lowest`: `#FFFFFF`
  - `Surface Container Low`: `#F4F7F1`
  - `Surface Container`: `#EEF2EC`
  - `Surface Container High`: `#E8EDE6`
  - `Surface Container Highest`: `#E2E7E0`
- **Text & Stroke Hierarchy**:
  - `On Surface`: `#1A1C1A` (near-black with olive undertones)
  - `On Surface Variant`: `#5F635E` (secondary text and supporting data labels)
  - `Outline`: `#737971` (focused structural borders and active input frames)
  - `Outline Variant`: `#C2C8BF` (subtle separators and inactive card perimeters)
- **Functional Semantics**:
  - `Success`: `#2E7D32` (verified credentials, score improvements)
  - `Warning`: `#B7791F` (impending renewals, debt thresholds)
  - `Error`: `#BA1A1A` (delinquencies, critical verification blocks)

## Typography

The typography implements the standard Material 3 proportional scale using Plus Jakarta Sans for its modern geometry, humanist warmth, and balance at both display scale and dense data representations.

- **Display & Headline Roles**: Reserved for high-level passport statuses, score readouts (e.g., "780"), and primary page anchors. Mobile viewport variants keep headline scale constrained without awkward line wrapping.
- **Title Roles**: Applied to section markers, module groupings, and prominent list item headers within verification logs.
- **Body Roles**: Tuned for extended financial disclosures, scoring factor breakdowns, and account histories.
- **Label Roles**: Used strictly for interactive tags, credit badge indicators, pill buttons, and structural card meta-tags.

## Layout & Spacing

The layout is built on a responsive 4/8/12 column grid system adhering to Material 3 standard adaptive layout behaviors:

- **Compact (Mobile: 0 - 599px)**: 4 columns, 16px (`gutter`) column gaps, 16px (`margin`) outer screen margin. Single-column stacked cards dominate.
- **Medium (Tablet: 600 - 839px)**: 8 columns, 24px (`gutter-tablet`) column gaps, 32px (`margin-tablet`) outer margins. Supports side-by-side metric tiles and two-column data grids.
- **Expanded (Desktop: 840px+)**: 12 columns, 24px (`gutter-desktop`) column gaps, dynamic margins centered with a maximum content canvas of 1200px.

All component internal spacings and rhythm use the standard 4px/8px incremental scale (`space-xs` through `space-xl`) to preserve vertical cadence and clean grouping of sensitive financial credentials.

## Elevation & Depth

This design system avoids harsh dropshadows, glassmorphic blurs, and pseudo-3D bevels. Instead, elevation is achieved primarily through **tonal layering** and subtle ambient contact shadows:

- **Level 0 (Flat / Canvas)**: `Background` (`#FAFDF7`). Flat foundation for the whole screen.
- **Level 1 (Card Resting)**: `Surface Container Low` (`#F4F7F1`) or `Surface` (`#FFFFFF`) with a faint ambient shadow: `0px 1px 3px 1px rgba(26, 28, 26, 0.05), 0px 1px 2px 0px rgba(26, 28, 26, 0.08)`.
- **Level 2 (Cards / Modules Hovered or Grouped)**: `Surface Container` (`#EEF2EC`) with ambient shadow: `0px 2px 6px 2px rgba(26, 28, 26, 0.06), 0px 1px 2px 0px rgba(26, 28, 26, 0.08)`.
- **Level 3 (Modals, Bottom Sheets, Floating Action Cards)**: `Surface Container High` (`#E8EDE6`) with diffuse ambient shadow: `0px 4px 8px 3px rgba(26, 28, 26, 0.08), 0px 1px 3px 0px rgba(26, 28, 26, 0.12)`.

Separation between flat elements on identical tonal surfaces is maintained using hairline structural borders colored with `Outline Variant` (`#C2C8BF`).

## Shapes

The interface embraces the Material 3 expressive shape system to create approachable, touch-friendly touchpoints:

- **Full Pill (`9999px`)**: Standard buttons, action pills, filter chips, category markers, and search capsules.
- **Large Container Shapes (`28px`)**: Primary passport summary card, credit score dial container, verification hero banners.
- **Medium Container Shapes (`16px` to `20px`)**: Secondary insight cards, breakdown modules, bottom sheets, and dialogs.
- **Small Element Shapes (`8px` to `12px`)**: Form inputs, text entry fields, status indicator badges, and nested inline metric containers.

## Components

### Buttons
- **Filled Button (Primary Action)**: Full pill shape (`9999px`), `Primary` (`#4F6354`) background with `On Primary` (`#FFFFFF`) text and icons. No border. Height: 44px (mobile: 48px target).
- **Tonal Button**: Full pill shape, `Primary Container` (`#D2E8D6`) background with `On Primary Container` (`#0C1F13`) text. For secondary actions like "Download Statement" or "Share Passport."
- **Outlined Button**: Full pill shape, transparent background, 1px border of `Outline` (`#737971`), and `Primary` text.

### Chips
- **Filter & Assist Chips**: Full pill shape, 32px height. Resting state has `Surface Container Low` background with a 1px `Outline Variant` border. Selected state swaps to `Primary Container` background with zero border and an active leading checkmark.

### Cards & Passport Tiles
- **Passport Hero Container**: 28px border radius, filled with `Surface Container Low` (`#F4F7F1`), bordered with subtle 1px `Outline Variant`. Contains score meters, user verification badges, and primary status tags.
- **Insight Cards**: 16px border radius, `Surface` (`#FFFFFF`) fill, soft Level 1 elevation. Padding is strictly `space-lg` (24px).

### Input Fields
- **Outlined Text Field**: 12px border radius, 1px `Outline` (`#737971`) border in default state. Transitions to 2px `Primary` (`#4F6354`) on focus. Floating label adheres to Material 3 standard specs, resting in `On Surface Variant`.

### Lists & Activity Logs
- **Credit Event List Items**: Divided by 1px horizontal strokes of `Outline Variant` (`#C2C8BF`). Leading icon or badge is housed inside a 40px circle or squircle of `Surface Container High` (`#E8EDE6`).

### Checkboxes & Switches
- **Switch**: Pill track styled in `Surface Container Highest` (`#E2E7E0`) when inactive, and `Primary` (`#4F6354`) when active. Circular thumb scales up slightly on selection per M3 guidelines.
- **Checkbox**: 4px radius squircle with 2px stroke of `Outline`, turning solid `Primary` with white checkmark when checked.