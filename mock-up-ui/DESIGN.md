---
name: Deep Intelligence System
colors:
  surface: '#121318'
  surface-dim: '#121318'
  surface-bright: '#39393f'
  surface-container-lowest: '#0d0e13'
  surface-container-low: '#1b1b21'
  surface-container: '#1f1f25'
  surface-container-high: '#29292f'
  surface-container-highest: '#34343a'
  on-surface: '#e3e1e9'
  on-surface-variant: '#c6c5d3'
  inverse-surface: '#e3e1e9'
  inverse-on-surface: '#303036'
  outline: '#8f909d'
  outline-variant: '#454651'
  surface-tint: '#bac3ff'
  primary: '#bac3ff'
  on-primary: '#15267b'
  primary-container: '#5c6bc0'
  on-primary-container: '#f8f6ff'
  inverse-primary: '#4858ab'
  secondary: '#c7c6c6'
  on-secondary: '#2f3131'
  secondary-container: '#484949'
  on-secondary-container: '#b8b8b8'
  tertiary: '#f6bd58'
  on-tertiary: '#432c00'
  tertiary-container: '#976900'
  on-tertiary-container: '#fff6ee'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dee0ff'
  primary-fixed-dim: '#bac3ff'
  on-primary-fixed: '#00105b'
  on-primary-fixed-variant: '#2f3f92'
  secondary-fixed: '#e3e2e2'
  secondary-fixed-dim: '#c7c6c6'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#464747'
  tertiary-fixed: '#ffdeac'
  tertiary-fixed-dim: '#f6bd58'
  on-tertiary-fixed: '#281900'
  on-tertiary-fixed-variant: '#5f4100'
  background: '#121318'
  on-background: '#e3e1e9'
  surface-variant: '#34343a'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  mono-sm:
    fontFamily: jetbrainsMono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  gutter: 12px
  margin: 16px
  drawer_width: 320px
---

## Brand & Style

The design system is engineered for the "power-user," prioritizing utility, information density, and technical precision. The brand personality is clinical, efficient, and authoritative, removing all decorative distractions to focus entirely on data synthesis and task management.

The visual style is a refined **Minimalism** with a **Corporate / Modern** influence, specifically tailored for high-performance workflows. It utilizes a deep-space dark mode to reduce eye strain during prolonged sessions. There are no illustrations or organic flourishes; instead, the system relies on strict alignment, clear hierarchy, and functional motion to guide the user. The aesthetic evokes a sense of professional mastery over complex information.

## Colors

The color palette is anchored in a true-dark `#0f0f0f` background to maximize contrast for the primary indigo accent. 

- **Primary:** Deep Indigo (`#5C6BC0`) is used for primary actions and active states.
- **Surface:** A slightly elevated `#1a1a1a` defines cards and containers.
- **Typography:** Pure white (`#ffffff`) is reserved for primary headings and critical data. Secondary text (`#a0a0a0`) provides visual quiet for metadata and labels.
- **Semantic Status:** Functional colors are used sparingly but strictly: Blue for activity (with an opacity-based pulse), Green for success, Red for errors, and Gray for pending states.
- **File Taxonomy:** Specific hues are assigned to note types (Indigo, Purple, Orange) to allow for instant visual categorization within dense lists.

## Typography

This design system uses **Inter** for all UI elements to ensure maximum legibility at small sizes. The typographic scale is intentionally compact to support high information density.

- **Headlines:** Use a tighter letter-spacing and semi-bold weights to anchor sections.
- **Body:** The default body size is 13px (`body-md`), optimized for reading long-form summaries without excessive scrolling.
- **Labels:** Small, uppercase labels with increased tracking are used for metadata headers and category tags.
- **Monospace:** For technical identifiers or file paths, **JetBrains Mono** is introduced as a secondary utility font.

## Layout & Spacing

The system follows a **4px base grid** to allow for "Dense" layouts. 

- **Grid Model:** A 12-column fluid grid is used for the main content area, while a fixed 320px right-side drawer handles settings and metadata.
- **Density:** Padding within cards and list items is kept to a minimum (`12px`) to maximize the amount of data visible on a single screen.
- **Breakpoints:** On desktop, the layout remains expanded. On tablet, the right drawer becomes an overlay. On mobile, the grid collapses to a single column and the drawer is hidden behind a bottom sheet or full-screen modal.
- **Gutters:** Tight 12px gutters provide just enough separation between functional blocks while maintaining a cohesive, "single-app" feel.

## Elevation & Depth

In this dark theme, depth is conveyed through **Tonal Layering** rather than heavy shadows.

- **Level 0 (Background):** `#0f0f0f` - The lowest layer for the main workspace.
- **Level 1 (Surfaces):** `#1a1a1a` - Cards, sidebars, and input containers.
- **Level 2 (Overlays):** `#242424` - Tooltips, dropdown menus, and the right-side settings drawer.
- **Outlines:** Subtle 1px borders using `#333333` are preferred over shadows to define boundaries in high-density areas. Shadows, if used for modals, should be tight, black, and have 0% spread to maintain the "clean edge" aesthetic.

## Shapes

The design system utilizes **Soft** roundedness (`4px` or `0.25rem`). This slight rounding softens the technical feel of the app without leaning into a "consumer" look. 

- **Small Components:** Checkboxes and small tags use a 2px radius.
- **Standard Components:** Buttons, inputs, and cards use the 4px base radius.
- **Large Components:** The right-side drawer and main container panels may use an 8px radius for internal corners to create a nested visual effect.

## Components

- **Buttons:** Primary buttons use the indigo background with white text. Ghost buttons (outline only) are preferred for secondary actions in settings.
- **Inputs:** High-density variants with 32px height. Labels should be placed above the input in `label-md` style. Focused states use a 1px indigo border.
- **Status Badges:** Small, pill-shaped containers with a background alpha of 15% of the status color and a solid 100% color dot for visibility.
- **Settings Drawer:** A fixed-position right sidebar. It uses a vertical stack of "Accordion" groups to manage the density of settings.
- **Lists:** Row heights are strictly 40px or 48px. Hover states use a subtle `#ffffff08` highlight.
- **Active Pulse:** For the "Active" status, an animation should oscillate the opacity of the blue status dot between 0.4 and 1.0.
- **File Type Icons:** Minimalist 16px geometric icons (Square for Main, Diamond for Atomic, Hexagon for MOC) using their respective assigned colors.