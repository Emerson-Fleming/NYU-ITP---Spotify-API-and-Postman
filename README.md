# NYU-ITP---Spotify-API-and-Postman
Documentation on Spotify API and Postman session I led at ITP Camp, NYU Tisch School of Arts

## Table of Contents
- [Features](#features)
- [Installation](#installation)

---

## Features

- Spotify Live Update App w/ QR Code (Written in Python)

## Installation

Step-by-step instructions on how to get the project up and running.

- Download node.js from site (https://nodejs.org/en/download)
- Download python3 and pip (https://www.python.org/downloads/)

```bash
# Clone the repository
git clone https://github.com/Emerson-Fleming/NYU-ITP---Spotify-API-and-Postman

# Navigate to the project directory
cd NYU-ITP---Spotify-API-and-Postman

# Python (python application)
- cd code/python
- source myenv/bin/activate
- python3 spotifypythonsimple.py

# JavaScript
- cd code/js
- npm init -y
- npm install node-fetch
- node spotifyTopTracks.js

# Postman
- Import Postman collection(s)
- In collection, fill required keys in the Authentication tab
- Authenticate token and go through OAuth process
- Use Spotify API (https://developer.spotify.com/documentation/web-api) to hit various endpoints within collection

