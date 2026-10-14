# Dependency license review

The sole owner Nafis Afzal confirmed original-code ownership and authorized MIT; the 2026 LICENSE is now present. MIT suits this owner-controlled project source: it is simple, widely reusable and appropriate for this static portal/pipeline. Apache-2.0 is an alternative when an explicit patent grant and its related conditions are desired. Neither choice licenses news, screenshots, branding or dependencies belonging to others. The owner grant is in LICENSE, separately from this dependency assessment.

The frozen pnpm and uv locks identify the installed tree. This pass collected **475 Node license records and 31 Python distributions** from installed package metadata. Registry metadata is useful inventory, not a legal opinion or proof that every packaged file has identical terms. The full-tree metadata review is retained in ignored audit evidence.

| Distribution | License/obligation observed | Handling |
|---|---|---|
| React, react-dom, scheduler | MIT; preserve copyright and permission notice with substantial copies | Exact installed license text accompanies static assets |
| Astro runtime, React integration, internal helpers | MIT | Included in static software notices |
| Pagefind reader/search runtime | MIT; package also includes a vscode-ripgrep notice | Packaged license directory included in notices; tool/platform executable stays outside public Git/static output |
| Tailwind generated styles | MIT | Packaged notice retained conservatively |
| http-cache-semantics local patch | BSD-2-Clause | Original packaged notice retained alongside the public patch |
| axe tooling / lightningcss / certifi | MPL-2.0 metadata in development/build/Python dependencies | Package source/venvs/node_modules not redistributed; modifications or binary redistribution require file-level/source-offer review |
| Sharp platform library | Apache-2.0/LGPL-3.0-or-later metadata | Native build/dry-run tooling is excluded from the site and public tree; do not bundle a virtual environment or dependency binary without separate notice/source/relinking review |
| Other transitive tools | Predominantly MIT/Apache/ISC/BSD; individual terms remain applicable | Frozen install fetches original packages; review licenses when dependencies or delivered code change |

`pnpm notices:generate` regenerates [the committed notice file](../apps/web/public/third-party-notices.txt) from nine installed packages, including nested packaged notices. Every `pnpm build` checks that it is current. The static bundle carries the same file. This addresses the confirmed missing-notice finding; it is not a source-ownership clearance or a claim to have independently audited every upstream author/contribution.

The owner states there are no co-owners; this is an independently developed project. No conflicting incorporated-code license was identified. Keep package notices intact, and investigate any later identified employment/client/university or copied-asset obligation before distributing affected material. Reassess native/runtime/WASM distribution whenever architecture or dependencies change.
