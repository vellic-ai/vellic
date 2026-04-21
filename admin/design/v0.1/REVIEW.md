# Design Gate Checklist — VEL v0.1

How to review each screen before merge. UX/UI Designer must sign off per VEL-48.

---

## How to use

1. Open the SPA at `/__/design` alongside the reference at `admin/design/v0.1/index.html`
2. Walk through each checklist below for the screen under review
3. Paste the filled-in checklist as a PR comment and mark each item ✅ or ❌
4. All items must be ✅ for the screen to pass the design gate

---

## Global (every screen)

- [ ] Dark background is `#0f1117` (`--bg`) — not black, not grey
- [ ] Surface cards use `#1a1d27` (`--surface`) with `1px solid #2e3347` border
- [ ] Body text is `#e8eaf0`, muted text `#7b82a0`
- [ ] Accent colour is `#6c63ff` for CTAs and focus rings
- [ ] Border radius is `8px` everywhere (buttons, inputs, cards, modals, badges)
- [ ] Font is system-sans at `14px / 1.5`; monospace where specified
- [ ] Focus ring: `box-shadow: 0 0 0 3px rgba(108,99,255,.18)` + `border-color: #6c63ff`
- [ ] Scrollbar: slim (`10px`), thumb `#2a2f44`, hover `#3a4058`
- [ ] Transitions on hover/focus: `120ms ease` for `background` and `border-color`

---

## Button

| Variant  | Background       | Border            | Text        | Hover bg   |
|----------|-----------------|-------------------|-------------|------------|
| default  | `#22263a`       | `#2e3347`         | `#e8eaf0`  | `#2a2f44`  |
| primary  | `#6c63ff`       | `#6c63ff`         | `#fff`     | `#7c74ff`  |
| danger   | transparent     | `rgba(255,77,109,.35)` | `#ff4d6d` | `rgba(255,77,109,.08)` |
| ghost    | transparent     | transparent       | `#7b82a0`  | `#22263a`  |

- [ ] Height: `sm=26px` / `default=32px` / `lg=38px`
- [ ] Disabled state: `opacity: 0.45`, cursor `not-allowed`

---

## Input / Textarea / Select

- [ ] Background: `#12141e` (`--input-bg`)
- [ ] Border: `1px solid #2e3347`; focus → `#6c63ff` + focus ring
- [ ] Height: `34px` for input/select; textarea min `88px`, resizable vertically
- [ ] Placeholder: `#4a5072`
- [ ] Error state: border `#ef4444`
- [ ] Label: `12.5px`, `#7b82a0`, `font-weight: 500`, `margin-bottom: 6px`
- [ ] Hint text: `12px`, `#7b82a0`
- [ ] Error text: `12px`, `#ef4444`

---

## Card

- [ ] Background: `#1a1d27`, border `1px solid #2e3347`, radius `8px`
- [ ] Inner padding: `20px`

---

## Badge

| Variant  | Text         | Border                    | Background            |
|----------|-------------|---------------------------|-----------------------|
| default  | `#7b82a0`   | `#2e3347`                 | `#22263a`             |
| success  | `#22c55e`   | `rgba(34,197,94,.3)`      | `rgba(34,197,94,.08)` |
| error    | `#ef4444`   | `rgba(239,68,68,.3)`      | `rgba(239,68,68,.08)` |
| warning  | `#f0a05a`   | `#c87941`                 | `#2a1f10`             |
| info     | `#8ea3ff`   | `rgba(108,99,255,.35)`    | `rgba(108,99,255,.1)` |

- [ ] Height: `20px`, pill radius, `11.5px` font, `font-weight: 500`

---

## Table

- [ ] Header: sticky, `#1a1d27` bg, `#7b82a0` text, `11.5px`, uppercase, `0.04em` tracking
- [ ] Row height: ~`48px` (12px top+bottom padding)
- [ ] Even rows: `rgba(34,38,58,.35)` tint
- [ ] Row hover: `#22263a`
- [ ] Failed row: `box-shadow: inset 2px 0 0 #ef4444`
- [ ] Outer wrapper: border `1px solid #2e3347`, radius `8px`, overflow hidden

---

## Dialog (Modal)

- [ ] Overlay: `rgba(5,6,12,.6)`, full-screen, fade-in `0.15s`
- [ ] Width: `min(460px, calc(100vw - 32px))`, centered
- [ ] Background: `#1a1d27`, border `1px solid #2e3347`, radius `8px`
- [ ] Shadow: `0 20px 60px rgba(0,0,0,.5)`
- [ ] Header padding: `18px 20px`, border-bottom
- [ ] Body padding: `20px`
- [ ] Footer padding: `14px 20px`, border-top, right-aligned actions
- [ ] Entrance animation: translateY from `-46%` to `-50%` + fade, `0.18s`

---

## Toast

- [ ] Position: `top: 16px; right: 16px`, fixed, z-index ≥ 100
- [ ] Width: `min(360px, …)`; min-width `260px`
- [ ] Background: `#1a1d27`, border `1px solid #2e3347`, radius `8px`
- [ ] Shadow: `0 6px 18px rgba(0,0,0,.35)`
- [ ] Left accent border `3px`: success `#22c55e`, error `#ef4444`, info `#6c63ff`
- [ ] Entrance: slide in from right `16px`, fade in, `0.18s ease`

---

## Skeleton / Shimmer

- [ ] Colors: `#22263a` → `#2a2f44` → `#22263a`, `800px` wide gradient
- [ ] Animation: `1.4s linear infinite`
- [ ] Radius: `6px`

---

## Screen-specific checklists

Expand per screen in [VEL-50] PR reviews. One table row per screen:

| Screen       | Global | Buttons | Inputs | Cards | Table | Badges | Dialog | Toast | Sign-off |
|-------------|--------|---------|--------|-------|-------|--------|--------|-------|----------|
| Login        |        |         |        |       |       |        |        |       |          |
| Onboarding   |        |         |        |       |       |        |        |       |          |
| Dashboard    |        |         |        |       |       |        |        |       |          |
| Deliveries   |        |         |        |       |       |        |        |       |          |
| Jobs         |        |         |        |       |       |        |        |       |          |
| LLM Settings |        |         |        |       |       |        |        |       |          |
| Repos        |        |         |        |       |       |        |        |       |          |
| Webhook      |        |         |        |       |       |        |        |       |          |
