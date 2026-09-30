# 91.3 Ayclt FM — IPTV / Plex / Jellyfin

Official IPTV playlist and XMLTV EPG project for **91.3 Ayclt FM**.

This repository provides channel metadata, live HLS streams, a rolling XMLTV programme guide, and JSON EPG data designed for IPTV players and media servers such as **Jellyfin** and **Plex**.

## Channels

| Channel | Number | Guide ID |
|---|---:|---|
| 91.3 Ayclt FM | 1 | `913AycltFM` |
| 91.3 Ayclt FM HD2 | 1.2 | `913AycltFMHD2` |
| 91.3 Ayclt FM HD3 | 1.3 | `913AycltFMHD3` |
| 91.3 Ayclt FM Live Studio Cam | 1.4 | `913AycltFMLiveStudioCam` |
| 91.3 Ayclt FM Mobile Studio Cam | 1.5 | `913AycltFMMobileStudioCam` |

## Playlist

The IPTV playlist is:

`https://raw.githubusercontent.com/913AycltFM/91.3-Ayclt-FM-TV/refs/heads/main/91.3_Ayclt_FM_radio_playlist.m3u`

The playlist is linked to this XMLTV guide:

`https://raw.githubusercontent.com/913AycltFM/91.3-Ayclt-FM-TV/refs/heads/main/91.3_Ayclt_FM_radio_guide.xml`

## EPG

The main XMLTV guide is:

`91.3_Ayclt_FM_radio_guide.xml`

A JSON version is also generated:

`epg.json`

The EPG is generated from the 91.3 Ayclt FM AzuraCast schedule and maintains a **7-day rolling guide**.

Timezone:

**America/Chicago (Central Time)**

## LIVE indicator

Live DJ/streamer programmes are marked in the XMLTV guide with:

`<live />`

The generator also keeps:

`<category lang="en">LIVE</category>`

The `<live />` element is important for Jellyfin because Jellyfin's XMLTV parser uses it to set the programme's live state.

### LIVE rules

- Current live DJ/streamer: LIVE
- Future live DJ/streamer: LIVE metadata
- Past live DJ/streamer: LIVE metadata
- Regular scheduled programme: no LIVE
- Filler programme: no LIVE
- HD2/HD3: LIVE only while a live DJ/streamer is currently airing
- Live Studio Cam follows the main FM live-DJ schedule
- Mobile Studio Cam follows the same main FM live-DJ schedule.

The XMLTV file provides the live metadata. The actual visual LIVE badge is rendered by the IPTV/Jellyfin client.

## Automatic updates

GitHub Actions regenerates the EPG every **5 minutes**.

Workflow:

`.github/workflows/update-epg.yml`

Schedule:

`*/5 * * * *`

The workflow:

1. Fetches the AzuraCast schedule.
2. Builds the 7-day rolling EPG.
3. Adds scheduled programmes and filler blocks.
4. Applies LIVE metadata to DJ/streamer programmes.
5. Validates the XMLTV file.
6. Updates `91.3_Ayclt_FM_radio_guide.xml` and `epg.json` when changes are detected.

The generator is:

`generate_epg.py`

## Jellyfin setup

In Jellyfin, add the IPTV playlist as an **M3U tuner**.

Use this playlist URL:

`https://raw.githubusercontent.com/913AycltFM/91.3-Ayclt-FM-TV/main/91.3_Ayclt_FM_radio_playlist.m3u`

For guide data, configure the XMLTV provider with:

`https://raw.githubusercontent.com/913AycltFM/91.3-Ayclt-FM-TV/main/91.3_Ayclt_FM_radio_guide.xml`

After adding or changing the guide provider, refresh the Live TV guide data in Jellyfin.

## Repository files

| File | Purpose |
|---|---|
| `91.3_Ayclt_FM_radio_playlist.m3u` | IPTV M3U playlist |
| `91.3_Ayclt_FM_radio_guide.xml` | XMLTV EPG for IPTV/Jellyfin/Plex |
| `epg.json` | JSON EPG data |
| `generate_epg.py` | EPG generator |
| `.github/workflows/update-epg.yml` | 5-minute automatic updater |

## Data source

Programme schedules are retrieved from the station's AzuraCast installation:

`https://radio.913aycltfm.com`

The repository-generated files are intended to remain compatible with the station's IPTV and Live TV services.

## Notes

The XMLTV standard does not define a universal graphical LIVE box. This project supplies LIVE metadata for compatible clients:

- `<live/>` for clients that support the XMLTV live marker.
- `<category lang="en">LIVE</category>` for clients that use programme categories.
- `<sub-title lang="en">LIVE</sub-title>` for clients that expose programme subtitles.

The programme title is kept clean without a `[LIVE]` prefix. Jellyfin Web/Desktop can render its own LIVE indicator from the guide data. Android/iPhone clients may not expose the graphical badge because their native guide UI handles LIVE metadata differently.

Because the XMLTV and JSON files are generated automatically, manual edits to those generated files may be replaced by the next EPG update.

## Repository

GitHub repository:

`https://github.com/913AycltFM/91.3-Ayclt-FM-TV`

## License

This repository is provided for the operation and distribution of 91.3 Ayclt FM IPTV/EPG metadata and station streams. Refer to the repository owner for licensing and redistribution terms.
