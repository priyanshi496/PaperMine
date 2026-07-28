---
name: PaperMine Professional
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#0058be'
  on-secondary: '#ffffff'
  secondary-container: '#2170e4'
  on-secondary-container: '#fefcff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002113'
  on-tertiary-container: '#009668'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  sidebar-width: 260px
  sidebar-collapsed: 64px
  container-max: 1600px
  gutter: 1rem
  margin-page: 2rem
  density-xs: 0.25rem
  density-sm: 0.5rem
  density-md: 0.75rem
  density-lg: 1rem
---

## Brand & Style
The design system evolves into a high-density, professional environment tailored for financial intelligence and complex data analysis. The brand personality is authoritative, precise, and systematic. 

The aesthetic follows a **Corporate / Modern** style with a focus on functional efficiency. It prioritizes information density over white space, utilizing sharp lines and subtle tonal shifts to organize complex datasets. The goal is to evoke a sense of "quiet power"—a tool that remains unobtrusive while providing deep analytical clarity for expert users.

## Colors
The palette is anchored by the primary **#0f172a (Slate 950)**, used for structural navigation and high-contrast text. 

- **Primary:** Used for the sidebar, primary buttons, and heavy headings to ground the interface.
- **Secondary:** A bright blue used for interactive states, focus indicators, and data highlights.
- **Tertiary:** A refined emerald green specifically reserved for positive financial indicators and "success" states.
- **Neutral:** A range of cool grays (Slate 50–200) define the background layers and borders, ensuring the canvas feels technical and clean.

## Typography
This design system utilizes **Inter** for all UI elements to ensure maximum legibility and a neutral, systematic feel. A secondary monospace font, **JetBrains Mono**, is introduced for labels, financial figures, and data points to provide a technical "ticker" aesthetic.

The scale is tighter than a standard consumer app to accommodate high-density dashboards. "Body-md" (14px) is the workhorse for most interface text, while labels are reduced to 11px–12px for metadata and utility information.

## Layout & Spacing
The layout uses a **persistent sidebar navigation** on the left, which can be collapsed to an icon-only view to maximize horizontal space for data tables. 

The content area follows a **12-column fluid grid** for dashboard widgets, but switches to a fixed-width container for text-heavy reports. 
- **Density:** We use a tight 4px-based grid. 
- **Breakpoints:** Desktop (1440px+), Laptop (1024px-1439px), and Tablet (768px-1023px). For the financial intelligence focus, mobile views are secondary and emphasize summary cards over full tables.

## Elevation & Depth
In this design system, depth is communicated through **Tonal Layers** rather than heavy shadows. 

- **Level 0 (Background):** Slate 50 (#f8fafc).
- **Level 1 (Card/Container):** White (#ffffff) with a 1px Slate 200 border. No shadow.
- **Level 2 (Active/Hover):** White with a very soft, high-diffusion shadow (0 4px 12px rgba(15, 23, 42, 0.05)).
- **Overlays (Modals):** Stronger Slate 900 tint on the backdrop with a crisp white surface to ensure focus.

This "Flat-Plus" approach ensures the UI feels like a single, cohesive instrument rather than a collection of floating pieces.

## Shapes
The shape language is disciplined and "Soft" (0.25rem). This subtle rounding takes the edge off a dense technical UI without appearing overly consumer-friendly or playful. 

- **Small elements (Inputs, Buttons):** 4px radius.
- **Large elements (Cards, Modals):** 8px radius.
- **Status Pills:** Fully rounded (pill-shaped) to distinguish them from interactive buttons.

## Components
- **Buttons:** Primary buttons are Slate 950 with white text. Secondary buttons use a Slate 200 border. Use small padding (8px 16px) to maintain density.
- **Data Tables:** The core of the system. Use "Body-sm" for cell content. Row headers are semi-bold. Zebra striping is used for readability in large datasets (Slate 50).
- **Sidebar:** Slate 950 background. Active items use a Secondary Blue left-accent border (2px) and a subtle ghost-white background.
- **Input Fields:** 1px Slate 300 border, turning Blue 500 on focus. Labels should be "Label-sm" positioned above the field.
- **Data Visualizations:** Use a custom 6-color palette based on the Primary and Secondary colors. Chart lines are 2px thick. Tooltips use the dark Slate 950 background to pop against light charts.
- **Status Chips:** Small, condensed labels with light backgrounds (e.g., Green 50 background with Green 700 text) for at-a-glance status reading.