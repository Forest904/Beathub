# TODO

## Legacy CLI Cleanup
1. Inventory every CLI-related module or script (e.g., `cli/`, `scripts/`, or `__main__` blocks) and document current consumers in the README.
2. Remove unused entry points and helper functions after confirming they are not referenced by the application, tests, or deployment scripts.
3. Update dependency lists to drop packages that were only required by the legacy CLI and validate the application still installs cleanly.

## Architecture Review
1. Map the current package structure and data flow between core services to highlight tight coupling or circular dependencies.
2. Identify modules that mix concerns (e.g., business logic, persistence, external API handling) and propose separation or abstraction layers.
3. Record the top three structural risks blocking scalability or maintainability and recommend actionable refactors.

## CD Burning Feature Audit
1. Perform a code review of `src/cd_burning_service.py` and related modules, capturing bugs, unclear logic, and missing error handling.
2. Reproduce current CD burning flows end-to-end, logging failures and performance bottlenecks.
3. Draft a refactor plan covering data validation, dependency boundaries, and improved status reporting.

## Frontend Cleanup
1. Identify unused components, styles, and assets; remove them while keeping a changelog for QA.
2. Standardize component structure (naming, props, hooks) and align with the design system guidelines.
3. Resolve lint warnings and type-checking errors to enforce a stable baseline.

## Spotify Metadata Performance
1. Profile existing Spotify metadata retrieval to measure latency per track and per batch.
2. Replace static artist lists with dynamic queries that pull the "Popular Artists" endpoint or equivalent high-relevance source.
3. Implement caching or request batching so repeated metadata lookups stay under the defined SLA.

## Test Suite Expansion
1. Review unit, integration, and end-to-end coverage to flag critical paths lacking automated tests.
2. Update brittle tests affected by recent refactors, ensuring fixtures and mocks reflect the current architecture.
3. Add regression tests for newly identified edge cases, prioritising the CD burning flow and Spotify integration.

## Lyrics Component Delivery
1. Design a frontend component that displays lyrics when the user clicks the green "lyrics acquired" icon, with loading and error states defined.
2. Wire the component to existing lyrics retrieval APIs, including fallback messaging when lyrics are unavailable.
3. Add UI tests (or storybook stories) confirming the component renders, toggles visibility, and handles long lyrics gracefully.

## High-Level Follow-Ups
1. Schedule a cross-team review to align backend, frontend, and devops priorities for the next milestone.
2. Document the refactor and testing roadmap in the project wiki so stakeholders can track progress.
3. Re-evaluate resource allocation once the above tasks start, ensuring owners and timelines are confirmed.
