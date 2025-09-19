# TODO

## Lyrics Component Delivery
- [ ] Design and build a lyrics display component that opens when the user clicks the green "Lyrics" icon.
- [ ] Add loading, error, and "not found" states (render a red badge when lyrics are missing).
- [ ] Connect the component to existing lyrics retrieval APIs.
- [ ] Show clear fallback messaging when lyrics cannot be retrieved.

## UI Fixes
- [ ] Keep the selected album's `TrackListRich` visible during burning progress.
- [ ] Move the "don't change page while burning" message to the top of the page, make it visually prominent, and hide it when burning completes.
- [ ] Add an "In Use" `StatusPill` to the device card while the device is actively burning.
- [ ] In Burn Preview:
  - [ ] Make song titles red instead of showing a "Missing" badge.
  - [ ] Remove Explicit, ISRC, and Popularity columns.

## Artist Best-Of Playlist
- [ ] Place a single `AlbumCard` on the artist page, to the right of the artist info in the same row.
- [ ] Populate the card with the top N tracks for that artist (fit to CD duration).
- [ ] Make the card clickable and behave like any other album/playlist.

## Artist Discovery Enhancements
- [ ] Add pagination with forward/back buttons and current page number at the bottom of the page.
- [ ] Create a `searchFilters` component to filter artists.
- [ ] Reset pagination to page 1 when filters are updated.

## Header Restyle
- [ ] Remove the gradient background and CD icon.
- [ ] Replace "CD Collector" text with a funnier, more engaging name.

## Missing Tracks Bug
- [x] Fix burn preview logic to correctly match tracks with "(feat XXX)" in filenames, including these patterns:
  - `Eyes Closed (feat. J Balvin).mp3`
  - `Imagine Dragons - Eyes Closed (feat. J Balvin).mp3`

## Make Your Compilation Feature
- [ ] Add a "Make Your Own CD Remix" button on the DiscoverArtists page.
- [ ] Create a `Compilation` sidebar component that opens when the button is clicked.
- [ ] Allow users to add/remove songs while browsing artists (cart-like experience).
- [ ] Prompt for a compilation name on first click and allow editing later.
- [ ] At the bottom of the Compilation component have a direct download button working same as the others.

## Song Previews
- [ ] Retrieve 10-second song previews during artist discovery (e.g., via Spotipy if available).
- [ ] Add a quick-play button to preview tracks inline.

## Song Player Feature
- [ ] Add a play button between track number and title in `TrackListRich` on the Download page after album download completes.
- [ ] Create a fixed bottom player bar with play, pause, and skip controls.
- [ ] Display the player bar whenever a song is playing and hide it when playback stops.

## CD Burning Audit
- [ ] Log start and end time of each burn session.
- [ ] Log each track written, including success/failure status and file path.
- [ ] Include error codes and messages for any failed burns.
- [ ] Audit the CD Burning pipeline for possible break points.

## Steps for onine publication 

## Steps for .exe packaging

## Steps for telegram bot
