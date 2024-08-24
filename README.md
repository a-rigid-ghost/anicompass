# anicompass
App which suggests new Anime recommendations based on previous viewing history

## Setup Virtual Enviroment

* Install `python`, `pip` and `pipenv` if not already present locally.

* Run the following to install dependencies first
```
pipenv install
```
* Make sure to select the correct venv in VSCode using `Ctrl+Shift+P`
* Then execute the designated file
```
pipenv run python <file_name>.py
```
* For adding a new dependency make sure to use
```
pipenv install <dependency>
```
So that the `Pipfile` remains updated

To activate this project's virtualenv, run
``` 
pipenv shell
```

## Setup Data Ingestion
* Run the following
```
python .\src\data_ingestion_script.py
```

## Start Server
* Create `.env` file and add your MAL client ID
  * Details on how to create one: https://myanimelist.net/forum/?topicid=1973077
```
MAL_CLIENT_ID = <YOUR_MAL_CLIENT_ID>
```
* Start the Flask Server
```
python .\src\app.py
```
* Now you can hit the local endpoint
```
http://127.0.0.1:5000/recommendations/{YOUR_MAL_USERNAME}
```

## Response Format
```json
{
  "recommendationList": [
    {
      "english_title": "Attack on Titan",
      "favourites": 163844,
      "image_url": "https://cdn.myanimelist.net/images/anime/10/47347.jpg",
      "mal_id": "16498",
      "members": 3744541,
      "popularity": 1,
      "title": "Shingeki no Kyojin"
    },
    {
      "english_title": "No Game, No Life",
      "favourites": 47444,
      "image_url": "https://cdn.myanimelist.net/images/anime/1074/111944.jpg",
      "mal_id": "19815",
      "members": 2305805,
      "popularity": 16,
      "title": "No Game No Life"
    },
    ...
  ]
}
```

## Next Steps

You may want to deploy the [anicompass-frontend](https://github.com/a-rigid-ghost/anicompass-frontend) server for a visual exerience