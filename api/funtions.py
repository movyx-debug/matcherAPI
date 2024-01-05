import numpy as np
from api import engine
import pandas as pd
import re

# Dataframe beinhaltet alle Parameter aus der Datenbank
def get_ParameterListeTest():
    ParameterListeTest = pd.read_sql("SELECT `parameterListeTest`.*, parameterMaterial.Material FROM `parameterListeTest` JOIN parameterMaterial ON parameterListeTest.MaterialID = parameterMaterial.ID", con=engine)
    return ParameterListeTest
# Dataframe beinhaltet alle Direktmatchstrings und die zugeörige ID aus der Datenbank
def get_ParameterMatrix():
    ParameterMatrix = pd.read_sql("SELECT * from parameterMatrix", con=engine)
    return ParameterMatrix

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

def bewerte_treffer(string, substring):
    if substring not in string:
        return 0  # Keine Punkte, wenn keine Übereinstimmung

    länge_treffer = len(substring)
    länge_gesamt_string = len(string)

    # Berechnen der Punktzahl, wobei 1 erreicht wird, wenn der gesamte String dem Substring entspricht
    treffer_punkte = länge_treffer / länge_gesamt_string

    return treffer_punkte


    # Beispiel bewerte Treffer:

    # Testen der Funktion mit verschiedenen Strings
    strings = ["ing", "ving", "loving", "caving sol", "Abcehthaingok für, hallo adsasdasdassdsad"]
    substring = "ing"

    # Bewertung jedes Ausdrucks
    bewertungen = {string: bewerte_treffer(string, substring) for string in strings}

    #{'ing': 1.0, 'ving': 0.75, 'loving': 0.5, 'caving sol': 0.3, 'Abcehthaingok für, hallo adsasdasdassdsad': 0.07317073170731707}

    #bewerte_treffer("loving", "ing")

    #0.5

    
def matchRating(name, goae):

    score_Df = get_ParameterListeTest()
    directmatchDF = get_ParameterMatrix()

    goae_single = finde_vier_zahlen(goae)
    parameter = säubere_parameter(name)

    goae_matches_result = score_Df[score_Df["goaeSingle"] == goae_single]
    if not goae_matches_result.empty:
        goae_matches = goae_matches_result['ID'].values
    else:
        goae_matches = None

    direct_match_result = directmatchDF[directmatchDF["DirektMatch"] == parameter["direct_match_string"]]
    if not direct_match_result.empty:
        direct_match = direct_match_result['ParameterID'].values[0]
    else:
        direct_match = None
    
    #Punktesystem per hit
    alpha_scale=1
    beta_scale=1
    gamma_scale=0.5
    delta_scale=0.1
    epsilon_scale=0.1

    #Score-df
    score_Df["ratingscore_alpha_mainName"] = 0
    score_Df["ratingscore_beta_synonym"] = 0
    score_Df["ratingscore_gamma_goae"] = 0
    score_Df["ratingscore_delta_nameAddon"] = 0
    score_Df["ratingscore_epsilon_material"] = 0

    score_Df["TotalRatingOhneMat"] = 0
    score_Df["TotalRating"] = 0


    for index in range(0, len(score_Df)):
        #Defining searchable Strings from Database:

        displayName = score_Df.at[index,"Name"]

        clean_displayNameLower = (re.sub('[^a-zA-Z0-9<>ßäöü]+', ';', displayName)).lower().strip()
        clean_displayNameLower_list = re.split(';', clean_displayNameLower)

        #1 alpha
        mainName = score_Df.at[index,"Hauptparameter2"].lower() # singleString

        #2 beta
        synonyms_list = score_Df.at[index,"Synonyme2"].lower().split(",") # List of Strings
        
        for value in [""]:
            while value in synonyms_list:
                synonyms_list.remove(value)

        synonyms = " ".join(synonyms_list)

        #4 delta
        nameAddons_list = score_Df.at[index,"Parameterzusatz"].lower().split(",") # List of Strings
        for value in [""]:
            while value in nameAddons_list:
                nameAddons_list.remove(value)

        nameAddons = " ".join(nameAddons_list)

        #5 epsilon
        material = score_Df.at[index,"Material"].lower() # singleString

        #Start Matchrating:

        # look for namestrings (alpha, beta, delta)
        alphaPoints = 0
        betaPoints = 0
        deltaPoints = 0

        for namestring in parameter["name_strings"]:
            
            alphaPoints = alphaPoints + bewerte_treffer(mainName, namestring)*alpha_scale

            synonym_scores=[0]
            for synonym in synonyms_list:
                synonym_score = bewerte_treffer(synonym, namestring)
                synonym_scores.append(synonym_score)

            betaPoints = betaPoints + max(synonym_scores)*beta_scale

            deltaPoints = deltaPoints + bewerte_treffer(nameAddons, namestring)*delta_scale

            if betaPoints != 0 and (1 - alphaPoints/betaPoints) < 0.8:
 
                betaPoints = 0 # wenn akzeptable Treffer für MainName und Synonyme gefunden werden, bewerte nur die Treffer für MainName

        epsilonPoints = 0
        # Überprüfen, ob die Liste leer ist, bevor die For-Schleife beginnt
        if parameter["material_strings"]:

            for materialstring in parameter["material_strings"]:

                epsilonPoints = epsilonPoints + bewerte_treffer(material, materialstring)*epsilon_scale
        
        else:
            if "im" not in clean_displayNameLower_list and "liquor" not in clean_displayNameLower_list and "urin" not in clean_displayNameLower_list:
                epsilonPoints = epsilon_scale



        score_Df.at[index, "ratingscore_alpha_mainName"] = alphaPoints
        score_Df.at[index, "ratingscore_beta_synonym"] = betaPoints
        score_Df.at[index, "ratingscore_gamma_goae"] = 0
        score_Df.at[index, "ratingscore_delta_nameAddon"] = deltaPoints
        score_Df.at[index, "ratingscore_epsilon_material"] = epsilonPoints

        score_Df.at[index, "TotalRatingOhneMat"] = alphaPoints + betaPoints + deltaPoints
        score_Df.at[index, "TotalRating"] = alphaPoints + betaPoints + deltaPoints + epsilonPoints

    if goae_matches is not None:
        for parameterID in goae_matches:
            score_Df.loc[score_Df['ID'] == parameterID, 'ratingscore_gamma_goae'] = gamma_scale
        
    score_Df["TotalRatingOhneGOAE"] = score_Df["ratingscore_alpha_mainName"] + score_Df["ratingscore_beta_synonym"] + score_Df["ratingscore_delta_nameAddon"] + score_Df["ratingscore_epsilon_material"]

    score_Df["TotalRating"] = score_Df["ratingscore_alpha_mainName"] + score_Df["ratingscore_beta_synonym"] + score_Df["ratingscore_delta_nameAddon"] + score_Df["ratingscore_epsilon_material"] + score_Df["ratingscore_gamma_goae"]


    score_Df_sorted=score_Df.sort_values(by="TotalRating", ascending=False)
    score_Df_sorted = score_Df_sorted.reset_index(drop=True)
    pd.set_option('display.max_columns', None)  # Keine Begrenzung für Spalten


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


        ratingInfo["ScoreDetail"] = ratingInfoDetail
        ratingInfos.append(ratingInfo)

    json["output"]["ratingInfos"] = ratingInfos
    

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