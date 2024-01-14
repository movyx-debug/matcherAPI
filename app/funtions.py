from datetime import datetime
import numpy as np
from app import engine
import pandas as pd
import re
import difflib
import time
from functools import lru_cache
from sqlalchemy import text

# Dataframe beinhaltet alle Parameter aus der Datenbank
def get_ParameterListeTest():
    ParameterListeTest = pd.read_sql("SELECT `parameterListeTest`.*, parameterMaterial.Material FROM `parameterListeTest` JOIN parameterMaterial ON parameterListeTest.MaterialID = parameterMaterial.ID", con=engine)
    return ParameterListeTest
# Dataframe beinhaltet alle Direktmatchstrings und die zugeörige ID aus der Datenbank
def get_ParameterMatrix():
    ParameterMatrix = pd.read_sql("SELECT * from parameterMatrix", con=engine)
    return ParameterMatrix

# Dataframe beinhaltet alle Befundpreise aus der Datenbank
def get_Befundpreise():
    Befundpreise = pd.read_sql(text("""
    SELECT
        pb.ID,
        pb.ParameterID,
        pb.PpBReagenz,
        pb.PpBKontrollen,
        pb.AnbieterID,
        pl.AuftraggeberID,
        pb.GeraeteID,
        pl.Angebotsdatum,
        pb.Leistungen
    FROM
        projektBefundpreise pb
    JOIN
        projektListe pl ON pb.ProjektID = pl.ID
    """), con=engine)
    return Befundpreise

#caching der Datenbankabfragen --> wird neugeladen wenn "is_data_updated() True ergibt"
@lru_cache(maxsize=None)
def get_cached_parameterListeTest():
    return get_ParameterListeTest()

@lru_cache(maxsize=None)
def get_cached_parameterMatrix():
    return get_ParameterMatrix()

def is_data_updated():
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT UPDATE_TIME
            FROM   information_schema.tables
            WHERE  TABLE_SCHEMA = 'ubcdata'
            AND    TABLE_NAME = 'parameterListeTest';
        """))
        update_time = result.fetchone()[0]
        if update_time is not None:
            last_update_time = load_last_check_timestamp()
            if update_time > last_update_time:
                save_last_check_timestamp(update_time)                
                return update_time > last_update_time
            
            else:
                return False
            
        else:
            return False

def save_last_check_timestamp(timestamp):
    with open("timestamp.txt", "w") as file:
        file.write(str(timestamp))

def load_last_check_timestamp():
    try:
        with open("timestamp.txt", "r") as file:
            return datetime.fromisoformat(file.read())
    except FileNotFoundError:
        return datetime.fromisoformat("2023-04-05T15:42:00.123456")
    
def check_for_database_reload():
    if is_data_updated():
        get_cached_parameterListeTest.cache_clear()  # Cache leeren
        get_cached_parameterMatrix.cache_clear()  # Cache leeren

        get_cached_parameterListeTest()
        get_cached_parameterMatrix()

def finde_vier_zahlen(s):
    if s == None:
        return None
    # Regulärer Ausdruck, der nach vier aufeinanderfolgenden Ziffern sucht
    match = re.search(r'\d{4}', s)
    if match:
        return int(match.group())
    else:
        return None
    
def säubere_parameter(name, hasMaterialInItsName=False):
    # Funktion identifiziert die "name_strings" und "material_strings" und erstellt das Dictionairy parameter
    parameter = {
         "name_strings": [],
         "material_strings": [],
         "direct_match_string" : ""
    }

    if name == None:
        return parameter

    # Stringlänge (wird bewertet um zu entscheiden ob es sich tatsächlich um Materialnagaben handelt. Z.B. "S" für Serum könnte auch für "S-100" stehen)
    parameternamenlänge = len(name)

    # Umwandeln des Parameternamens in einzelne Strings innerhalb einer Liste
    clean_parameter = (re.sub('[^a-zA-Z0-9<>ßäöü]+', ';', name)).lower().strip()
    clean_parameter_as_list = re.split(';', clean_parameter)
    for value in ["", "im", "i", "und"]:
        while value in clean_parameter_as_list:
            clean_parameter_as_list.remove(value)

    direct_match_string = (re.sub('[^a-zA-Z0-9<>ßÄäÖöÜü]+', '', name)).lower()

    # Definition von gängigen Ausdrücken für Untersuchungsmaterialien in Laboren
    materials = [
        "urin", "u", "sammelurin", "su",
        "serum", "s",
        "plasma", 
        "liquor", "li",
        "edta", "edtablut",
        "blut", "vollblut",
        "punktat", "p",
        "citrat", "citratblut",
        "speichel",
        "stuhl",
        "fruchtwasser"
    ]

    # Definition des des Dictionairy für Parameternamen
    parameter = {
         "name_strings": [],
         "material_strings": []
    }

    name_strings=[]
    material_strings=[]
    for string in clean_parameter_as_list:
        # Im Standardfall wird geschaut ob die Länge des Paramternamens größer als 4 (bei kurzen Parameternamen kann es zu falschen Zuordnungen kommen)
        # Alternativ kann der User explizit angeben, ob ein Untersuchungsmaterial im Parameternamen aufgeführt ist
        if string in materials and parameternamenlänge>4 or string in materials and hasMaterialInItsName:
            material_strings.append(string)
        else:
            name_strings.append(string)        
    
    parameter["name_strings"] = name_strings
    parameter["material_strings"] = material_strings
    parameter["direct_match_string"] = direct_match_string

    return parameter

def ratcliff_obershelp_similarity(str1, str2):
    if str1 is None or str2 is None:
        return 0
    # gibt die Stringähnlichkeit wieder (MaxValue = 1)
    # kommt dann zum Einsatz wenn für mehrere Parameter ein identischer RatingScore vorliegt --> gibt finale Einschätzung welcher Parameter am ähnlichsten ist
    return difflib.SequenceMatcher(None, str1, str2).ratio()

def separate_integers_and_others(list1, list2):
    # Hilfsfunktion zu identifizierung von "Integern" im gesuchten Parameternamen. Separiert die Strings in 2 Listen.
    list1_onlyInt = [item for item in list1 if item.isdigit()]
    list2_onlyInt = [item for item in list2 if item.isdigit()]
    list1_noInt = [item for item in list1 if not item.isdigit()]
    list2_noInt = [item for item in list2 if not item.isdigit()]

    return list1_onlyInt, list1_noInt, list2_onlyInt, list2_noInt

def get_norm_factor(items):
    # Hilfsfunktion da der Normierungsfaktor (Divisor) nicht null sein darf, wenn z.B. kein Element in der Liste vorliegt.
    if len(items) == 0:
        return 1
    else:
        return len(items)

def is_integer_string(s):
        return s.isdigit()

def compare_integer_strings(list1, list2):
    # Überprüfen, ob eine der Listen leer ist
    if not list1 or not list2:
        return False

    # Filtern der Listen, um nur Integer-Strings zu behalten
    filtered_list1 = [item for item in list1 if is_integer_string(item)]
    filtered_list2 = [item for item in list2 if is_integer_string(item)]

    # Überprüfen, ob die gefilterte erste Liste leer ist
    if not filtered_list1:
        return False

    # Überprüfen, ob alle Elemente der gefilterten ersten Liste in der gefilterten zweiten Liste in der gleichen Reihenfolge erscheinen
    # Integer-Strings werden abweichend von den restlichen Strings anders bewertet. Nur falls die Zahlenreihenfolge im gesuchten und im Datebank-String vorliegt werden RatingPunkte erzielt.
    iter_filtered_list2 = iter(filtered_list2)
    return all(item in iter_filtered_list2 for item in filtered_list1)

def rateHit(userStringList, databaseStringList, scaleForIntegers = 0.3):
    #Hauptfunktion
    #Funktion zur Bewertung der Übereinstimmung der vorhandenen Parameterstrings zwischen 2 Listen

    userStringList_Integers, userStringList_Others, databaseStringList_Integers, databaseStringList_Others = separate_integers_and_others(userStringList, databaseStringList)

    normFactorUser_others = get_norm_factor(userStringList_Others)
    normFactorDatabase_others = get_norm_factor(databaseStringList_Others)

    #Normierungsfaktor entspricht immer der maximalen Elemente-anzahl innerhalb des Vergleichs
    normFactor = max([normFactorUser_others, normFactorDatabase_others])

    points=0


    # Rating zwischen allen Substrings (Datenbank vs. Userinput) die NICHT IntegerStrings darstellen
    for databaseString in databaseStringList_Others:

        for userString in userStringList_Others:

            if userString in databaseString:
                
                länge_treffer = len(userString)
                länge_gesamt_string = len(databaseString)
                treffer_punkte = länge_treffer / länge_gesamt_string

                points = points + treffer_punkte 

    if userStringList_Integers:
        #Falls im UserInput separierte Integer vorliegen, wird der normFactor um 1 erhöht, da nun ein einzelner zusätzlicher Abgleich dieser Integer mit der Datenbank stattfindet
        normFactor = normFactor + 1
    
        if compare_integer_strings(userStringList_Integers, databaseStringList_Integers) == True:
            #überprüft ob die gleiche Integerreihenfolge gemäß Userinput auch in der Datenbank vorliegt
            points = points + scaleForIntegers
                    
    return points / normFactor

    
def matchRating(name, goae):

    start_time = time.time()

    check_for_database_reload()

    # Abruf benötigter Informationen aus der UBCDatenbank
    df = get_cached_parameterListeTest() # alle Parameter und alle Infos
    score_Df = df.copy()
    directmatchDF = get_cached_parameterMatrix() # alle Directmatchstrings

    goae_single = finde_vier_zahlen(goae) # separiere GOÄ (4-stellig) von restlichen ggf. vorliegenden Zeichen
    parameter = säubere_parameter(name) # identifiziere name- und material-Strings und directMatchString

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Zeit Datenbankabfrage: {execution_time} Sekunden")

    # GOÄ-Matches
    goae_matches_result = score_Df[score_Df["goaeSingle"] == goae_single]
    if not goae_matches_result.empty:
        goae_matches = goae_matches_result['ID'].values
    else:
        goae_matches = None

    #Direct-Match

    direct_match_result = directmatchDF[directmatchDF["DirektMatch"] == parameter["direct_match_string"]]
    if not direct_match_result.empty:
        direct_match = direct_match_result['ParameterID'].values[0]
    else:
        direct_match = None
    
    #Punktesystem (Scale)
        
    alpha_scale=1
    beta_scale=1
    gamma_scale=0.5 
    delta_scale=0.1
    epsilon_scale=0.1

    #Im Dataframe (enthält alle Informationen aus der UBC Datenbank) werden Spalten für das MatchRating erzeugt:
    score_Df["ratingscore_alpha_mainName"] = 0.0
    score_Df["ratingscore_beta_synonym"] = 0.0
    score_Df["ratingscore_gamma_goae"] = 0.0
    score_Df["ratingscore_delta_nameAddon"] = 0.0
    score_Df["ratingscore_epsilon_material"] = 0.0

    score_Df["TotalRatingOhneMat"] = 0.0
    score_Df["TotalRating"] = 0.0

    score_Df["RatcliffSimilarity"] = 0.0

    # Loop durch die gesamte Datenbank:


    start_time = time.time()
    


    for index in range(0, len(score_Df)):
    #--------------------Präparation-----------------------

        #1 alpha (Strings für mainName)
        mainName = score_Df.at[index,"Hauptparameter2"].lower() # singleString
        clean_mainNameLower = (re.sub('[^a-zA-Z0-9<>ßäöü]+', ';', mainName)).lower().strip()
        clean_mainNameLower_list = re.split(';', clean_mainNameLower)

        for value in [""]:
            while value in clean_mainNameLower_list:
                clean_mainNameLower_list.remove(value)

        #2 beta (Strings für Synonyme)
        synonyms_list = score_Df.at[index,"Synonyme2"].lower().split(",") # List of synonyms
        for value in [""]:
            while value in synonyms_list:
                synonyms_list.remove(value)
        clean_synonym_lower_substring_list=[]
        for syn in synonyms_list:
            clean_synonym_substring = (re.sub('[^a-zA-Z0-9<>ßäöü]+', ';', syn)).lower().strip()
            clean_synonym_substring_list = re.split(';', clean_synonym_substring)
            clean_synonym_lower_substring_list.append(clean_synonym_substring_list) # lists in list
        for value in [""]:
            while value in clean_synonym_lower_substring_list:
                clean_synonym_lower_substring_list.remove(value)


        #4 delta (Strings für ParameterAddon)
        nameAddons_list = score_Df.at[index,"Parameterzusatz"].lower().split(",") # List of Strings
        for value in [""]:
            while value in nameAddons_list:
                nameAddons_list.remove(value)


        #5 epsilon (Strings für Material)
        material = score_Df.at[index,"Material"].lower() # singleString
        clean_materialLower = (re.sub('[^a-zA-Z0-9<>ßäöü]+', ';', material)).lower().strip()
        clean_materialLower_list = re.split(';', clean_materialLower)
        for value in [""]:
            while value in clean_materialLower_list:
                clean_materialLower_list.remove(value)

        #Relevant für String-Similairity
        displayName = score_Df.at[index,"Name"] 
        clean_displayNameLower = (re.sub('[^a-zA-Z0-9<>ßäöü]+', ';', displayName)).lower().strip()
        clean_displayNameLower_list = re.split(';', clean_displayNameLower)        

        synonyms_list_displayName = []
        for synonym in synonyms_list:
            if "im" not in clean_displayNameLower_list and "liquor" not in clean_displayNameLower_list and "urin" not in clean_displayNameLower_list:
                synonym_displayName = synonym + " " + score_Df.at[index,"Parameterzusatz"]
            else:
                synonym_displayName = synonym + " " + score_Df.at[index,"Parameterzusatz"] + " " + score_Df.at[index,"Material"]

            synonyms_list_displayName.append(synonym_displayName)

    #--------------------Matching-----------------------

        alphaPoints = 0 #mainName
        betaPoints = 0 #Synonyms
        deltaPoints = 0 #NameAddon
        epsilonPoints = 0 #Material

        #alphaPoints (Vergleich der UserInputStrings mit dem MainName aus Datenbank)
        alphaPoints = rateHit(parameter["name_strings"], clean_mainNameLower_list, scaleForIntegers=0.3)*alpha_scale

        #betaPoints (Vergleich der UserInputStrings mit mehreren Synonymen aus Datenbank --> Bester Punktwert für spezifisches Synonym wird herangezogen)
        synonym_scores=[0]
        for synonyms in clean_synonym_lower_substring_list:
            synonym_score = rateHit(parameter["name_strings"], synonyms, scaleForIntegers=0.3)*beta_scale
            synonym_scores.append(synonym_score)
        betaPoints = max(synonym_scores)

        #alpha+betaPoints (es wird lediglich die max. Punktzahl (MainName vs. Synonyms) gewertet)
        alphaAndBetaPoints = [alphaPoints, betaPoints]
        max_index = alphaAndBetaPoints.index(max(alphaAndBetaPoints))
        if max_index == 0:
            betaPoints = 0
        else:
            alphaPoints = 0

        #deltaPoints (Vergleich der UserInputStrings mit dem NameAddon aus Datenbank --> alle Parameter bekommen Punkte gemäß delta_scale)
        #Lediglich wenn ein ParameterAddon in der Datenbank vorliegt und dieses nicht gemäß UserInput gehitted wird, werden 0 Punkte vergeben
        deltaPoints = delta_scale
        if len(nameAddons_list) != 0 and rateHit(parameter["name_strings"], nameAddons_list, scaleForIntegers=0.3) == 0:
            deltaPoints = 0

        #epsilonPoints (Vergleich der UserInputStrings mit dem Material aus Datenbank)

        # Überprüfen, ob die Liste leer ist (ob eine MaterialAngabe vom User existiert), bevor die For-Schleife beginnt
        if parameter["material_strings"]:
            epsilonPoints = rateHit(parameter["material_strings"], clean_materialLower_list, scaleForIntegers=0.3)*epsilon_scale
        #Falls keine Materialangabe vorliegt, werden jene Parameter aus der Datenbank mit Punkten bewertet die dem "StandardMaterial" entsprechen, wo i.d.R. eine Materialangabe überflüssig ist
        else:
            if "im" not in clean_displayNameLower_list and "liquor" not in clean_displayNameLower_list and "urin" not in clean_displayNameLower_list:
                epsilonPoints = epsilon_scale

        #StringSimilairity
        namesForStringCompare = synonyms_list_displayName
        namesForStringCompare.append(displayName)
        ratcliffScores = [ratcliff_obershelp_similarity(name, displayDatabaseString) for displayDatabaseString in namesForStringCompare]
        ratcliffScore = max(ratcliffScores)

    #--------------------Finale Scores-----------------------
    #SetRatings im Dataframe:
        score_Df.at[index, "ratingscore_alpha_mainName"] = alphaPoints
        score_Df.at[index, "ratingscore_beta_synonym"] = betaPoints
        score_Df.at[index, "ratingscore_gamma_goae"] = 0
        score_Df.at[index, "ratingscore_delta_nameAddon"] = deltaPoints
        score_Df.at[index, "ratingscore_epsilon_material"] = epsilonPoints
        score_Df.at[index, "RatcliffSimilarity"] = ratcliffScore

    if goae_matches is not None:
        for parameterID in goae_matches:
            score_Df.loc[score_Df['ID'] == parameterID, 'ratingscore_gamma_goae'] = gamma_scale
    
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Zeit Loop Params: {execution_time} Sekunden")

    #Kalkulation von Gesamtpunkten (Summen aus den Detailratings)
    score_Df["TotalRatingOhneGOAE"] = score_Df["ratingscore_alpha_mainName"] + score_Df["ratingscore_beta_synonym"] + score_Df["ratingscore_delta_nameAddon"] + score_Df["ratingscore_epsilon_material"]
    score_Df["TotalRating"] = score_Df["ratingscore_alpha_mainName"] + score_Df["ratingscore_beta_synonym"] + score_Df["ratingscore_delta_nameAddon"] + score_Df["ratingscore_epsilon_material"] + score_Df["ratingscore_gamma_goae"]

    #--------------------Sorting-----------------------
    #Sortieren des Dataframes nach (1) TotalRating & (2) RatcliffSimilarity
    score_Df_sorted=score_Df.sort_values(by=["TotalRating", "RatcliffSimilarity"], ascending=False)
    score_Df_sorted = score_Df_sorted.reset_index(drop=True)

    #--------------------Return/output-----------------------
    #Grundgerüst für return/output
    json = {
        "input" : {
            "name" : None,
            "goae" : None
        },
        "output" : {
            "directMatchID" : None,
            "directMatchDisplayName" : None,
            "ratingInfos" : None
        }
    }

    #Filling:
    json["input"]["name"] = name
    json["input"]["goae"] = goae
    json["output"]["directMatchID"] = direct_match

    if direct_match is not None:
        json["output"]["directMatchDisplayName"] = score_Df_sorted.loc[score_Df_sorted['ID'] == direct_match, 'Name'].iloc[0]
    else:
        json["output"]["directMatchDisplayName"] = None
    
    ratingInfos=[]
    for i in range(0, 10):
        parameterID = score_Df_sorted.at[i, "ID"]
        parameterDisplayName = score_Df_sorted.at[i, "Name"]
        parameterDisplayGoae = score_Df_sorted.at[i, "goae"]

        ratingInfo = {}
        ratingInfo["parameterID"] = parameterID
        ratingInfo["DisplayName"] = parameterDisplayName
        ratingInfo["parameterDisplayGoae"] = parameterDisplayGoae
        ratingInfo["correctMatchPropability"] = "InWork"
        ratingInfo["ratingScoreTotal"] = score_Df_sorted.at[i, "TotalRating"]
        ratingInfo["ratingScoreWithoutGoae"] = score_Df_sorted.at[i, "TotalRatingOhneGOAE"]

        ratingInfoDetail = {}
        ratingInfoDetail["ratingscore_alpha_mainName"] = score_Df_sorted.at[i, "ratingscore_alpha_mainName"]
        ratingInfoDetail["ratingscore_beta_synonym"] = score_Df_sorted.at[i, "ratingscore_beta_synonym"]
        ratingInfoDetail["ratingscore_gamma_goae"] = score_Df_sorted.at[i, "ratingscore_gamma_goae"]
        ratingInfoDetail["ratingscore_delta_nameAddon"] = score_Df_sorted.at[i, "ratingscore_delta_nameAddon"]
        ratingInfoDetail["ratingscore_epsilon_material"] = score_Df_sorted.at[i, "ratingscore_epsilon_material"]
        ratingInfoDetail["RatcliffSimilarity"] = score_Df_sorted.at[i, "RatcliffSimilarity"]

        ratingInfo["ScoreDetail"] = ratingInfoDetail
        ratingInfos.append(ratingInfo)

    json["output"]["ratingInfos"] = ratingInfos
    
    #converting type64 to INT
    def convert_int64(obj):
        if isinstance(obj, dict):
            return {k: convert_int64(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_int64(v) for v in obj]
        elif isinstance(obj, np.int64):
            return int(obj)
        else:
            return obj

    converted_json = convert_int64(json)
    
    return converted_json