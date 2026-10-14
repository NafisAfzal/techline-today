# UI and UX Specification

## Visual direction

Goal: editorial technology product, not a generic AI dashboard.

Avoid:
- endless purple gradients;
- glowing AI-orb imagery;
- large empty hero sections;
- excessive glassmorphism;
- five different card styles;
- long unbroken AI prose.

Recommended dark palette:
- background: `#0B0F14`
- raised surface: `#111821`
- secondary surface: `#17212C`
- primary text: `#F4F7FA`
- muted text: `#96A2B1`
- cyan accent: `#42D3FF`
- green/available: `#4ADE80`
- amber/attention: `#F5B942`
- coral/expiry/error: `#FF6B6B`

Use a light theme with equivalent contrast, not a simple color inversion.

Typography:
- neutral readable sans for body;
- slightly distinctive display face only for important headings if self-hosted/licensed;
- use system font stack by default to maximize speed and avoid font privacy/loading issues.

## Desktop layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Logo | AI Research APIs Freebies Chips Devices | Search  ☼   │
├──────────────────────────────────────────────────────────────┤
│ Updated 7:17 PM | 60-second briefing | Daily Weekly Monthly  │
├──────────────────────────────────────────────────────────────┤
│ Top story                    │ Quick signals / expiring APIs  │
│ 3 bullets + key chips        │ 3 compact modules              │
├──────────────────────────────────────────────────────────────┤
│ AI                           │ Dev & APIs                      │
│ compact cards                │ compact cards                  │
├──────────────────────────────────────────────────────────────┤
│ Chips / Devices / Research / Jobs pulse                      │
└──────────────────────────────────────────────────────────────┘
```

## Mobile layout

Mobile is not a compressed desktop page.

Order:
1. slim header + search;
2. horizontal category chips;
3. top five 60-second briefing;
4. compact category sections;
5. sticky bottom action only when useful, never permanent clutter.

Touch targets >= 44px where applicable. No hover-only functionality.

## Story card anatomy

```text
[AI] [Primary confirmed]                         18 min ago
Clear headline describing the event

• Key fact one
• Key fact two
• Key fact three

Why it matters: one concise sentence.

[128K ctx] [Free API] [2 sources]
Details      Original ↗
```

If no meaningful key number exists, do not invent chips.

## Detail interactions

- Details opens a dedicated route, not a huge modal on mobile.
- `Broader context` can be collapsible.
- sources expand into a clean list with publisher, title, date and source type.
- source links always open the original URL.
- show update history when a story materially changes.

## Search

Use Pagefind or a small static search index in V1.

Support:
- title and summary text;
- provider/model names;
- tags/categories;
- exact API/tool names;
- keyboard shortcut `/` or `Ctrl/Cmd + K`.

## Personal feed

V1 personalization should be transparent:
- selected categories pinned first;
- chronological/importance sort toggle;
- no opaque behavioral profiling;
- `Reset personalization` action.

## Accessibility

- semantic landmarks;
- visible focus state;
- full keyboard navigation;
- prefers-reduced-motion support;
- WCAG AA contrast minimum;
- no information conveyed by color alone;
- screen-reader labels for evidence and expiry badges.

## Motion

Use subtle 120-220ms transitions for:
- card expansion;
- filter changes;
- bookmark state;
- command palette.

No background particle systems or continuous animation.
