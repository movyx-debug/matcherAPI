import json
from flask import Response, render_template, request, abort
from functools import wraps
from app import app, API_KEY, db
from app.funtions import check_for_database_reload, finde_vier_zahlen, get_BefundpreisInfo, get_cached_parameterListeTest, matchRating
from app.models import ProjektListeTest, ProjektAuftraggeber, ProjektAnbieter, ParameterListeTest, ParameterMaterial, ProjektBefundpreiseTest

def require_apikey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-KEY') and request.headers.get('X-API-KEY') == API_KEY:
            return view_function(*args, **kwargs)
        else:
            abort(401)  # Unauthorized access
    return decorated_function

@app.route('/documentation')
def api_documentation():
    return render_template('api_documentation.html')

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

@app.route('/projekte')
@require_apikey
def projekte():
    projekte = ProjektListeTest.query.all()
    projekte_liste = [projekt.to_dict() for projekt in projekte]
    return (projekte_liste)

@app.route('/materials')
@require_apikey
def materials():
    materials = ParameterMaterial.query.all()
    materials_liste = [material.to_dict() for material in materials]
    return (materials_liste)

@app.route('/anbieter')
@require_apikey
def anbieter():
    anbieter = ProjektAnbieter.query.all()
    anbieter_liste = [anbieter.to_dict() for anbieter in anbieter]
    return (anbieter_liste)

@app.route('/auftraggeber')
@require_apikey
def auftraggeber():
    auftraggeber = ProjektAuftraggeber.query.all()
    auftraggeber_liste = [auftraggeber.to_dict() for auftraggeber in auftraggeber]
    return (auftraggeber_liste)

@app.route('/createParam', methods=['POST'])
@require_apikey
def createParam():
    name = request.form.get('Name')
    # Überprüfung, ob der Parameter bereits existiert
    existierender_parameter = ParameterListeTest.query.filter_by(Name=name).first()
    if existierender_parameter:
        return ({"meldung": "Parameter existiert bereits"}), 400
    
    material_name = request.form.get('Material')
    goae = request.form.get('goae')
    punkte = request.form.get('Punkte')
    goae_single = finde_vier_zahlen(goae)

    hauptparameter_name = request.form.get('Hauptparameter')
    synonyme_name = request.form.get('Synonyme')
    parameterzusatz = request.form.get('Hauptparameter')

    # Suche die Material_ID zum Material_Namen
    material = ParameterMaterial.query.filter_by(Material=material_name).first()
    if material is None:
        return ({"meldung": "Material nicht in der Datenbank vorhanden"}), 400
    
    material_id = material.ID

    #Erstelle neues ParameterListe Objekt
    neuer_parameter = ParameterListeTest(
        Name = name,
        Synonyme = synonyme_name,
        MaterialID = material_id,
        goae = goae,
        Punkte = punkte,
        goaeSingle = goae_single,
        Hauptparameter = hauptparameter_name,
        Parameterzusatz = parameterzusatz
    )

    db.session.ad(neuer_parameter)
    db.session.commit()

    return ({"meldung": "Parameter erfolgreich hinzugefügt", "Paramter": name}), 201

@app.route('/createProjekt', methods=['POST'])
@require_apikey
def projekt_hinzufuegen():

    auftrags_id = request.form.get('AuftragsID')
    angebotsdatum = request.form.get('Angebotsdatum')
    auftraggeber_name = request.form.get('Auftraggeber') # ID needed
    anbieter_name = request.form.get('Anbieter') # ID needed
    standort = request.form.get('Standort')
    bemerkung = request.form.get('Bemerkung')

    # Überprüfe, ob auftraggeber_name und anbieter_name nicht leer oder None sind
    if not auftraggeber_name:
        return ({"fehler": "Auftraggeber darf nicht leer sein"}), 400
    if not anbieter_name:
        return ({"fehler": "Anbieter darf nicht leer sein"}), 400

    # Überprüfen ob Auftraggeber und/oder Anbieter bereits existieren

    # Überprüfe den Auftraggeber
    auftraggeber = ProjektAuftraggeber.query.filter_by(Auftraggeber=auftraggeber_name).first()
    if auftraggeber is None:
        auftraggeber = ProjektAuftraggeber(Auftraggeber=auftraggeber_name)
        db.session.add(auftraggeber)
        db.session.commit()
    auftraggeber_id = auftraggeber.ID

    # Überprüfe den Anbieter
    anbieter = ProjektAnbieter.query.filter_by(Anbieter=anbieter_name).first()
    if anbieter is None:
        anbieter = ProjektAnbieter(Anbieter=anbieter_name)
        db.session.add(anbieter)
        db.session.commit()
    anbieter_id = anbieter.ID

    # Erstelle ein neues ProjektListeTest Objekt
    neues_projekt = ProjektListeTest(
        AuftragsID=auftrags_id,
        AuftraggeberID=auftraggeber_id,
        Angebotsdatum=angebotsdatum,
        AnbieterID=anbieter_id,
        Standort=standort,
        Bemerkung=bemerkung,
    )
    
    # Füge das neue Projekt zur Datenbank hinzu
    db.session.add(neues_projekt)
    db.session.commit()

    return ({"meldung": "Projekt erfolgreich hinzugefügt", "projekt": neues_projekt.to_dict()}), 201

@app.route('/createBefundpreise', methods=['POST'])
@require_apikey
def befundpreise_hinzufuegen():

    # erforderliche JSON-Struktur:
    #{
    #    "ProjektID" : "w",
    #    
    #    "Data": [
    #        {"parameterID": "x", "Leistungen" : int, "PpBReagenz": "y", "PpBKontrollen": "z"},
    #        {"parameterID": "x", "Leistungen" : int, "PpBReagenz": "y", "PpBKontrollen": "z"},
    #        {"parameterID": "x", "Leistungen" : int, "PpBReagenz": "y", "PpBKontrollen": "z"},
    #    ]
    #}


    daten = request.get_json()
    
    # Überprüfe, ob JSON-Daten vorhanden sind
    if not daten:
        return ({"fehler": "Keine Daten gesendet."}), 400
    
    # Überprüfe, ob Projekt vorhanden ist
    
    projekt_id = daten.get('ProjektID')
    projekt = ProjektListeTest.query.filter_by(ID=projekt_id).first()
    if projekt is None:
        return ({"fehler, Projekt mit der angegebenen ID existiert nicht": projekt_id}), 400
    
    anbieter_id = projekt.AnbieterID

    check_for_database_reload()
    parameterIDs = get_cached_parameterListeTest()["ID"].tolist()

    for eintrag in daten.get('Data', []):
        # Überprüfe, ob ParameterID in der Datenbank existiert
        if isinstance(eintrag.get('parameterID'), int):
            if int(eintrag.get('parameterID')) not in parameterIDs:
                return ({"fehler, Parameter mit der angegebenen ID existiert nicht": eintrag.get('parameterID')}), 400
        
        neuer_befundpreis = ProjektBefundpreiseTest(
            ProjektID=projekt_id,
            ParameterID=eintrag.get('parameterID'),
            AnbieterID=anbieter_id, 
            Leistungen=eintrag.get('Leistungen'),
            PpBReagenz=eintrag.get('PpBReagenz'),
            PpBKontrollen=eintrag.get('PpBKontrollen'),
        )
        db.session.add(neuer_befundpreis)

    try:
        db.session.commit()
        return ({"meldung": "Daten erfolgreich gespeichert"}), 201
    except Exception as e:
        db.session.rollback()
        return ({"fehler": "Daten konnten nicht gespeichert werden", "details": str(e)}), 500
