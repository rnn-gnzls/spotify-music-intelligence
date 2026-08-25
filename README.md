# Spotify Music Intelligence

A data analytics-focused music intelligence platform that analyzes Spotify data to discover patterns in artist, track, albums, listening behavior, and audio characteristics.

>  **Status:** Complete — Audio Characteristics section is working, however, I can't analyze every song listened because I need to download it locally since I don't have any permission from Spotify to directly analyze songs from it.

---

## Project Overview

**Spotify Music Intelligence** is a data-driven analytics project designed to explore Spotify music data and answer questions about music popularity, streaming performance, artist consistency, and audio characteristics.

The project combines **Python + Flask + PostgreSQL + SQL + Spotify API + HTML/JavaScript + Tailwind + Chart.js** to build an end-to-end data pipeline.

---

## Project Architecture

```text
                  SPOTIFY MUSIC INTELLIGENCE
                              │
               ┌──────────────┴──────────────┐
               │                             │
               │                      Spotify Web API
        Python / Pandas                      │
               │                     Spotify OAuth 2.0
               │                             │
         Data Cleaning                   User Data
               │                             │
               └──────────────┬──────────────┘
                              ▼
                          PostgreSQL
                              │
                              ▼
                       SQL / SQLAlchemy
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
              Flask Backend       Analytics Logic
                    │                   │
                    └─────────┬─────────┘
                              ▼
                          JSON APIs
                              │
                              ▼
                      HTML / JavaScript
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
           Chart.js                    Tailwind CSS
                │
                ▼
        Interactive Dashboard