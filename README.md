# iTunes Feed Grabber
A simple script to parse iTunes and iTunesU podcasts and generate an RSS XML feed. At the moment only audio podcasts are supported.

## Run it in Google App Engine
Grabber can also be hosted on [Google App Engine](https://cloud.google.com/appengine/) (see `app.yml` and `server.py`):

```bash
# From the project root
appcfg.py -A YOUR_PROJECT_ID update .
```

Now you can convert as follows:

```bash
# By URL
wget http://YOUR_PROJECT_ID.appspot.com/generate?target=itunes.apple.com/us/itunes-u/psychology-audio/id341652042
# OR by ID
wget http://YOUR_PROJECT_ID.appspot.com/generate?target=341652042
```

## Disclaimer
***This script is provided without any warranty and only for educational purposes. By using this script you might violate iTunes terms of use. In such case you and only you are responsible for the consequences!***
