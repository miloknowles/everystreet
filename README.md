# :runner: Running Every Street (in Cambridge)

See the app [here](https://everystreet.run/).

![Cambridge street map](/static/cambridge.png)

## :runner: Getting Strava Access Tokens

First, you need to get an authentication code from Strava.

Put this URL in the browser:
```
https://www.strava.com/oauth/authorize?client_id=77280&response_type=code&redirect_uri=http://www.miloknowles.com&approval_prompt=force&scope=read_all,profile:read_all,activity:read_all
```

Notice that it requests several scopes of access, so that we can use the same token for every action needed. More info on scopes is [here](https://developers.strava.com/docs/authentication/).

```bash
# Copy the OAuth2 code into this POST request. You'll be able to execute the request once, and should get an access token in the JSON response.
curl -X POST https://www.strava.com/api/v3/oauth/token \
  -d client_id=77280 \
  -d client_secret=SOME_VALUE \
  -d code=SOME_VALUE \
  -d grant_type=authorization_code
```

Then you'll get a JSON response with a `refresh_token` and an `access_token`.

## :computer: AWS

### Checking on Docker Container
```bash
docker ps                   # See running containers.
docker logs container_name  # Check output from container.
```

### Auto-Delete Logs on EC2 Instance
```bash
# SSH into the server.
ssh -i /path/to/key.pem ec2-user@X.X.X.X

Once in the server, run:
sudo su # to become the superuser. 

# Confirm that there are no running crontabs with the command crontab -l.
# Use the command crontab -e to edit the crontab jobs and schedule. Paste in the following commands:
0 4 * * * truncate -s 0 /var/lib/docker/containers/**/*.log
0 12 * * * docker system prune -a -f
```

## :fire: Google Firebase

https://console.firebase.google.com/u/2/project/runningheatmap-a5864/overview

To encode a `serviceAccountKey.json` into a string:
```bash
openssl base64 -in .serviceAccountKey.json -out firebaseConfigBase64.txt -A
```

## :scroll: Cambridge GeoJson

I downloaded the shapefile from [here](https://www.cambridgema.gov/GIS/gisdatadictionary/Boundary/BOUNDARY_CityBoundary).

Convert using [this tool](http://ogre.adc4gis.com/), and make sure to specify `EPSG:4326` as the target SRS.

## :computer: Heroku

https://dashboard.heroku.com/apps/everystreet

```bash
# Run locally. This will load in the .env file variables.
heroku local

python app.py # If you want hot-reloading to work.

# Deploys to the remote app on Heroku.
git push heroku main

# Check the logs.
heroku logs --tail
```