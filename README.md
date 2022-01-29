# Running Heatmap

## Getting Access Tokens

First, you need to get an authentication code from Strava.

Put this URL in the browser:
```
https://www.strava.com/oauth/authorize?client_id=77280&response_type=code&redirect_uri=http://www.miloknowles.com&approval_prompt=force&scope=read_all,profile:read_all,activity:read_all
```

Notice that it requests several scopes of access, so that we can use the same token for every action needed. More info on scopes is (https://developers.strava.com/docs/authentication/)[here].

```bash
# Copy the OAuth2 code into this POST request. You'll be able to execute the request once, and should get an access token in the JSON response.
curl -X POST https://www.strava.com/api/v3/oauth/token \
  -d client_id=77280 \
  -d client_secret=2c396c1e3d793afc2537bbb1cba8a4e1da1015ae \
  -d code=6c10d2019ec3c7bea68b08ba8db85758a9fa3960 \
  -d grant_type=authorization_code
```

Then you'll get a JSON response with a `refresh_token` and an `access_token`.

## Heroku

```bash
# Run locally. This will load in the .env file variables.
heroku local

# Deploys to the remote app on Heroku.
git push heroku main
```
