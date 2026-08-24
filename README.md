# Spotify Music Intelligence

A data analytics-focused music intelligence platform that analyzes Spotify data to discover patterns in artist, track, genre, popularity, streaming performance, and audio characteristics.

>  **Status:** In Development — Backend foundation is nearly complete. Analytics, dashboards, and frontend components are being developed iteratively.

---

## Project Overview

**Spotify Music Intelligence** is a data-driven analytics project designed to explore Spotify music data and answer questions about music popularity, streaming performance, artist consistency, and audio characteristics.

The project combines **Python, PostgreSQL, SQL, Excel, Tableau, and Flask** to build an end-to-end data pipeline from raw CSV data to analysis and visualization.

## Key Questions

The analysis focuses on questions such as:

- Do highly energetic songs receive more streams?
- Which artists consistently produce popular tracks?
- How has music popularity changed over time?
- Are certain genres associated with higher streaming performance?
- How do audio features relate to popularity and streams?

---

## Project Architecture

```text
                SPOTIFY MUSIC INTELLIGENCE

                           CSV
                            │
                            ▼
                    Python / Pandas
                            │
                     Data Cleaning
                            │
                            ▼
                       PostgreSQL
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
            SQL           Excel         Tableau
                            │              │
                            └──────┬───────┘
                                   ▼
                            Analysis /
                            Dashboard
                                   │
                                   ▼
                            Flask Frontend