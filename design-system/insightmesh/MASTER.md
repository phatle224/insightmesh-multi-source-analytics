# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/insightmesh/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** InsightMesh
**Generated:** 2026-09-18 20:00:20
**Category:** Analytics Dashboard
**Design Dials:** Variance 4/10 (Balanced / Modern) | Motion 3/10 (Subtle) | Density 8/10 (Dense / Dashboard)

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#1E40AF` | `--color-primary` |
| On Primary | `#FFFFFF` | `--color-on-primary` |
| Secondary | `#3B82F6` | `--color-secondary` |
| On Secondary | `#000000` | `--color-on-secondary` |
| Accent/CTA | `#D97706` | `--color-accent` |
| On Accent/CTA | `#000000` | `--color-on-accent` |
| Background | `#F8FAFC` | `--color-background` |
| Foreground | `#1E3A8A` | `--color-foreground` |
| Card | `#FFFFFF` | `--color-card` |
| Card Foreground | `#1E3A8A` | `--color-card-foreground` |
| Muted | `#E9EEF6` | `--color-muted` |
| Muted Foreground | `#475569` | `--color-muted-foreground` |
| Border | `#DBEAFE` | `--color-border` |
| Destructive | `#DC2626` | `--color-destructive` |
| On Destructive | `#FFFFFF` | `--color-on-destructive` |
| Ring | `#1E40AF` | `--color-ring` |

**Color Notes:** Blue data + amber highlights [Accent adjusted from #F59E0B]

### Typography

- **Heading Font:** Fira Sans
- **Body Font:** Fira Sans
- **Code/Data Font:** Fira Code (PostgreSQL/MySQL SQL, identifiers, tabular numeric values)
- **Mood:** dashboard, data, analytics, code, technical, precise
- **Google Fonts:** [Fira Code + Fira Sans](https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

*Density: 8/10 — Dense / Dashboard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `2px` / `0.125rem` | Tight gaps |
| `--space-sm` | `4px` / `0.25rem` | Icon gaps, inline spacing |
| `--space-md` | `8px` / `0.5rem` | Standard padding |
| `--space-lg` | `12px` / `0.75rem` | Section padding |
| `--space-xl` | `16px` / `1rem` | Large gaps |
| `--space-2xl` | `24px` / `1.5rem` | Section margins |
| `--space-3xl` | `32px` / `2rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: var(--color-accent);
  color: var(--color-on-accent);
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: background-color 200ms ease, box-shadow 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  filter: brightness(0.94);
  box-shadow: var(--shadow-sm);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: background-color 200ms ease, color 200ms ease, box-shadow 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: var(--color-card);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: box-shadow 200ms ease, border-color 200ms ease;
}

.card:hover {
  box-shadow: var(--shadow-lg);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.input:focus {
  border-color: var(--color-primary);
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-ring) 20%, transparent);
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Data-Dense Dashboard

**Keywords:** Multiple charts/widgets, data tables, KPI cards, minimal padding, grid layout, space-efficient, maximum data visibility

**Best For:** Business intelligence dashboards, financial analytics, enterprise reporting, operational dashboards, data warehousing

**Key Effects:** Hover tooltips, chart zoom on click, row highlighting on hover, smooth filter animations, data loading spinners

### Page Pattern

**Pattern Name:** Analytics Workspace

- **Navigation:** Persistent sidebar on large screens; accessible compact navigation on smaller screens.
- **Primary action:** Ask/Run query, with one clear primary CTA per screen.
- **Content order:** Active datasource → question/input → runtime status → generated query → verified table → compatible visualization → dashboard action.
- **Dashboard behavior:** Prefer dense, scannable grids with explicit loading, empty, stale, and error states.

---

## Motion

**Scroll Reveal** (Subtle) — Trigger: scroll (viewport enter) | Duration: 300-400ms | Easing: `power1.out`

```js
gsap.from(el, { opacity: 0, y: 12, duration: 0.35, ease: 'power1.out', scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none reverse' } });
```

**Framework notes:** Requires the ScrollTrigger plugin registered once via gsap.registerPlugin(ScrollTrigger); Use matchMedia('(prefers-reduced-motion: reduce)') to skip non-essential motion and render the final state immediately

- ✅ Keep the y offset small (8-16px) so it reads as a fade, not a slide
- ❌ Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default without a no-JS fallback
- ⚡ toggleActions 'play none none reverse' avoids re-triggering on every scroll direction change

---

## Anti-Patterns (Do NOT Use)

- ❌ Ornate design
- ❌ No filtering

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use one consistent SVG icon family; Phosphor is the default recommendation.
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from one consistent SVG icon set (Phosphor preferred)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
