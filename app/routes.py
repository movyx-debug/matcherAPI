import json
from flask import Response, render_template, request, abort
from functools import wraps
from app import app, API_KEY
from app.funtions import check_for_database_reload, get_BefundpreisInfo, get_cached_parameterListeTest, matchRating
from app.models import ProjektListeTest

def require_apikey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-KEY') and request.headers.get('X-API-KEY') == API_KEY:
            return view_function(*args, **kwargs)
        else:
            abort(401)  # Unauthorized access
    return decorated_function

@app.route('/')
@require_apikey
def index():
    # url = /?name=asdqwe&goae=4567
    name = request.args.get('name', default=None, type=str)
    goae = request.args.get('goae', default=None, type=str)
    result = matchRating(name, goae)

    json_data = json.dumps(result, ensure_ascii=False).encode('utf-8')
    
    # Erstellen der Response mit dem korrekten Content-Type und Charset
    response = Response(json_data, content_type="application/json; charset=utf-8")
    return response

@app.route('/befundpreis')
@require_apikey
def befundpreis():
    # url = /?parameterID=asdqwe&leistungen=4567

    parameterID = request.args.get('parameterID', default=None, type=int)
    leistungen = request.args.get('leistungen', default=None, type=float)

    result = get_BefundpreisInfo(parameterID, leistungen).to_json(orient='records')
    # Erstellen der Response mit dem korrekten Content-Type und Charset
    response = Response(result, content_type="application/json; charset=utf-8")
    
    return response

@app.route('/params')
@require_apikey
def params():
    check_for_database_reload()
    result = get_cached_parameterListeTest().to_json(orient='records')
    
    # Erstellen der Response mit dem korrekten Content-Type und Charset
    response = Response(result, content_type="application/json; charset=utf-8")
    return response
    
@app.route('/documentation')
def api_documentation():
    return render_template('api_documentation.html')


@app.route('/test')
def test():
    projekte = ProjektListeTest.query.all()

    for item in projekte:
        print(item.Standort)

    return "projekte"