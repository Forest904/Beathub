# TODO


## Artist Best-Of Playlist
- [x] Place a single `AlbumCard` on the artist page, to the right of the artist info in the same row.
- [x] Make the album conver the artist image.
- [x] Make the album title "The Best Of XXX "
- [x] Populate the card with the most popular N tracks for that artist (fit to CD duration).
- [x] Make the card clickable and behave like any other album/playlist.

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
- [ ] Create a fixed bottom player bar  component with play, pause, and skip controls.
- [ ] Display the player bar whenever a song is playing and hide it when playback stops.

## CD Burning Audit
- [x] Ensure burn order matches the preview order using `disc_number` and `track_number` from metadata.
- [x] Log start and end time of each burn session.
- [x] Log each track written, including success/failure status and file path.
- [x] Include error codes and messages for any failed burns in the log.
- [ ] Audit the CD Burning pipeline for possible break points.

## Steps for onine publication 

## Steps for .exe packaging

## Steps for telegram bot
