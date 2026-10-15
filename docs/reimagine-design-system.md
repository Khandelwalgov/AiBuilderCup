# Opportunity OS design exploration

## Direction A — Signal workspace (selected)

Public: full-width cool-white site, slim top navigation, oversized geometric sans headline, cobalt call to action and a horizontal interactive evidence-to-action preview. No internal sidebar. Workspace: midnight neutral navigation, cool-white canvas, compact context bar and action-first split views. Admin: operational queue rail, evidence comparison and explicit human decision controls. Cobalt is primary, restrained violet connects dependencies, coral marks attention. No cream, green, serif headings or oversized dark introductory banners.

## Direction B — Editorial instrument

Public: white stacked editorial sections with coral margins and large numbered source annotations. Workspace: horizontal tab navigation, narrow evidence rail and dense monochrome data sheets. Admin: full-screen document workbench. Distinct from Atlas, but the wide horizontal navigation is less resilient for Hindi and multiple subject contexts.

Select A for clear separation of public/workspace/admin, mobile adaptation and immediate recognizable actions. Preserve content fidelity, progressive disclosure and unknown states.

Implementation: replace styles.css/finale.css with token/base, shell, components and feature styles. Geometric system sans, body16px/support14px, Devanagari1.7line-height. Buttons44px minimum, visible focus, reduced motion. Evidence and shared dependency visuals use actual data; public preview explicitly illustrative. Two actual screenshot critique passes required.

## Implemented tokens and composition

`src/styles/index.css` composes tokens, base, shell, pages, intelligence and review. Both legacy stylesheets were removed. Primary cobalt #3155f5; midnight navigation #121a2b; cool-white canvas #f6f8fc; restrained violet #7757d5; coral #d96545. Teal appears only as a semantic satisfied-status indicator. System geometric sans avoids network font dependence; Hindi has its own readable line-height and reduced tracking. Native form and dialog semantics, focus outlines, reduced motion and responsive checklists remain functional.

## Actual visual review and refinement

Baseline: existing Atlas captures copied to `.live-validation/reimagine-before`; baseline was inspected. Two page-level directions are in `apps/web/tests/design-directions.html`, captured in `.live-validation/reimagine-design-directions.png` and visually inspected. The test-only concept board is excluded from production build.

Pass 1: viewed actual 1440px landing. New top navigation and horizontal illustrative action preview are distinct; headline tracking was too tight. Reduced tracking, collapsed mobile brand wording while retaining accessible brand name, and fixed the absolute breadcrumb's width-plus-offset overflow rather than hiding page overflow. Actual mobile EN/HI capture then passed.

Pass 2: viewed graph, family and admin desktop plus Hindi320 landing. Viewed Overview, Discover Hindi390, Detail desktop, Profile Hindi320, Business desktop and Settings Hindi390. Refined general heading tracking, removed repetitive zero-account summary values, reduced graph minimum height, and made opportunities inspectable buttons with related-action details. Fixed ResizeObserver resetting zoom on height changes. Admin's dark evidence reader, separate queue and collapsed operations distinguish review from the workspace. Narrow layouts retain readable forms and the complete checklist; graph canvas is intentionally replaced by that list on mobile.

Final EN/HI matrix: 1440, 1024, 390, 320 pixels for all ten required screens under `.live-validation/reimagine-after`. Fixture titles identify fictional opportunities; saved official capture copies are public-only evidence. Screens are visually inspected representatives, not merely file-existence checks. The matrix checks horizontal overflow automatically. Remaining visual limitations: system font appearance varies by OS, long original legal passages are dense, and user/source-authored free text remains original language.
