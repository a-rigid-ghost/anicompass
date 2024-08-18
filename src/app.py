from generate_anime_rec import RecFactory
from models import Anime

from flask import Flask,jsonify,request
from dataclasses import asdict

app = Flask(__name__) 

@app.route('/recommendations/<username>', methods = ['GET']) 
def ReturnJSON(username): 
	if(request.method == 'GET'):
		recFactory = RecFactory(username=username)
		anime_obj_list: list[Anime] = recFactory.generate_anime_recommendations(topk=10)
		anime_dict_list = [asdict(anime) for anime in anime_obj_list]
		data = { 
			"recommendationList" : anime_dict_list, 
		}
		response = jsonify(data)
		response.headers.add("Access-Control-Allow-Origin", "*")
		return response

if __name__=='__main__': 
	app.run(debug=True)
