import json
from flask import Response, jsonify, request
import numpy as np
from api import app
from api.funtions import get_ParameterListeTest, matchRating

@app.route('/')
def index():
    # url = /?name=asdqwe&goae=4567
    name = request.args.get('name', default=None, type=str)
    goae = request.args.get('goae', default=None, type=str)
    result = matchRating(name, goae)

    

    json_data = json.dumps(result, ensure_ascii=False).encode('utf-8')
    
    # Erstellen der Response mit dem korrekten Content-Type und Charset
    response = Response(json_data, content_type="application/json; charset=utf-8")
    return response
    