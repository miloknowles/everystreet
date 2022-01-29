# Running Heatmap

## Installing Swagger Client

```bash
wget https://repo1.maven.org/maven2/io/swagger/swagger-codegen-cli/2.4.13/swagger-codegen-cli-2.4.13.jar -O swagger-codegen-cli.jar
java -jar swagger-codegen-cli.jar generate -i https://developers.strava.com/swagger/swagger.json -l python -o generated
cd generated && python setup.py install
```

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

{"token_type":"Bearer","expires_at":1643345126,"expires_in":18805,"refresh_token":"28abf4fb89dee2efc9cbd2441ab28471c576bb70","access_token":"8cea078f35c16461758c1131830baa82106c53df","athlete":{"id":98027359,"username":"everystreetincambridge","resource_state":2,"firstname":"Every Street In","lastname":"Cambridge","bio":"","city":"Cambridge","state":"Massachusetts","country":"United States","sex":null,"premium":false,"summit":false,"created_at":"2022-01-23T18:24:43Z","updated_at":"2022-01-27T22:26:38Z","badge_type_id":0,"weight":272.155,"profile_medium":"https://dgalywyr863hv.cloudfront.net/pictures/athletes/98027359/23187499/2/medium.jpg","profile":"https://dgalywyr863hv.cloudfront.net/pictures/athletes/98027359/23187499/2/large.jpg","friend":null,"follower":null}}
