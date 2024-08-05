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

## Setup Data Ingestion
* Run the following
```
python .\src\data_ingestion_script.py
```
