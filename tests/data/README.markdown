# Data for Tests

### Adding a New Artist

    mkdir Tiësto 
    curl "http://api.bandsintown.com/artists/Tiësto/events.json?api_version=2.0&app_id=YOUR_APP_ID" > Tiësto/upcoming.json
    curl "http://api.bandsintown.com/artists/Tiësto.json?api_version=2.0&app_id=YOUR_APP_ID" > Tiësto/artist.json
    curl "https://www.bandsintown.com/a/30843" > Tiësto/artist.html
