import json 
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import json
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
prompt_template  = """
Tu es un assistant spécialisé qui agit au nom de Groupe Civitas, une entreprise québécoise possédant plusieurs succursales (Beauharnois, Granby, Laval, Longueuil, Montréal, Mirabel, Québec, St-Césaire, Terrebonne). 

## CONTEXTE ENTREPRISE

Groupe Civitas intervient dans les domaines suivants :

1) GÉOMATIQUE ET ARPENTAGE
   - Acquisition de données (photogrammétrie, lidar, lasergrammétrie, drones, etc.)
   - Traitement et modélisation 3D (BIM, jumeaux numériques, etc.)
   - Arpentage foncier (plan d'implantation, piquetage, bornage, subdivision, lotissement)
   - Arpentage de construction (levés topographiques, implantation, calculs volumétriques, relevés “tel que construit”)
   - Certificats de localisation (étude des empiètements, servitudes, conformité réglementaire)

2) INFRASTRUCTURES URBAINES ET GÉNIE ROUTIER
   - Développement ou réhabilitation de réseaux routiers et d’infrastructures urbaines
   - Production d’eau potable, réseaux d’égout, drainage, réfection de voirie, parcs, terrains sportifs
   - Services : études d’avant-project, conception, plans et devis, préparation d’appels d’offres, surveillance, gestion de la construction

3) TRANSPORT ET CIRCULATION
   - Études de circulation, plan de transport, plan de maintien de la circulation
   - Sécurité routière, mobilité active et durable

4) AMÉNAGEMENT DU TERRITOIRE
   - Aménagement d’espaces publics (milieu urbain ou rural)
   - Études conceptuelles, plans et devis, surveillance, gestion de la construction
   - Vision de développement durable

5) INGÉNIERIE DU BÂTIMENT
   - projects résidentiels, industriels, commerciaux, institutionnels
   - Conception et design, études d’avant-project, plans, devis, gestion de la construction
   - Inspection (façades Loi 122, stationnements étagés, normes ASTM E2018-24)
   - Fonds de prévoyance (Loi 16), carnet d’entretien

Bien que nous ayons des succursales dans plusieurs villes, nous devons faire attention à la localisation des appels d’offres selon notre stratégie et nos ressources.

---

## RÈGLES DE FILTRAGE

1) **Catégories visées**  
   - Approvisionnements, Autres, Services (et sous-catégories) sur SEAO  
   - En particulier : “Services d’architecture et d’ingénierie” (pour l’ingénierie) et “Services de communication, de photographie, de cartographie” (pour l’arpentage)  
   - Parfois aussi “Indéterminé” ou “Entretien, réparation, modification, réfection et installation…” etc.

2) **Pour l’ingénierie**  
   - Intérêt pour : études d’avant-project, plans et devis, surveillance, ingénierie, génie civil, structure, mécanique, électricité  
   - Exclure si c’est uniquement de l’architecture (sauf mention explicite d’équipe d’ingénieurs)  
   - Exclure si c’est uniquement de l’architecture de paysage (sauf si ingénierie jointe)  
   - Exclure contrôle qualité des matériaux, suivi environnement des sols, études géotechniques (pour laboratoires)  
   - Exclure spécifiquement les structures MTMD (ponts, viaducs)  
   - Inclure les projects de construction/réfection d’infrastructures municipales, chaussées, routes, éclairage, parcs, stationnements, bassins de rétention, aqueducs, égouts, etc.  
   - Exclure tout appel d’offres mentionnant “audit”

3) **Pour l’arpentage**  
   - Mots-clés : cartographie, topographie, Lidar, imagerie numérique, relevés, photos aériennes, levés laser aéroportés  
   - Sinon, même logique d’examen de la description et de la localisation

4) **Localisation**  
   - De manière générale, on **exclut** l’est de la Ville de Québec, le Saguenay, l’Abitibi-Témiscamingue, La Tuque, etc. (sauf si nous décidons de couvrir ces régions)
   - Dans le doute, on peut demander plus de détails

---

## DONNÉES DE L’APPEL D’OFFRES

Voici les informations sur l’appel d’offres à évaluer :

«
**Numéro** : {Numéro}
**Titre** : {Titre}
**Organisation** : {Organisation}
**Description** : {Description}
**Catégorie** : {Catégorie}
**Classifications** : {Classifications}
**Région de livraison** : {Région}
»

Analyse ces données selon le **contexte de l’entreprise** (Groupe Civitas) et les **règles** ci-dessus.

---

## INSTRUCTION DE SORTIE

Tu dois répondre **uniquement** sous la forme d’un objet JSON avec les champs suivants :

```json
{{
  "pertinent": true or false,
  "motifPertinence": "raison(s) si pertinent",
  "motifExclusion": "raison(s) si exclu",
  "disciplinePrincipale": "ex: ingénierie, arpentage, géomatique, aménagment du térroire, ingénieurie du batiment....."
}}

"""

GEMINI_API = os.getenv("GEMINI_API")
genai.configure(api_key=GEMINI_API)
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(model_name="gemini-1.5-flash",generation_config=generation_config,)


def analyze_project(project):
    try:
        cleaned_project = {k.strip(':'): v for k, v in project.items()}
        response = model.generate_content(prompt_template.format(**cleaned_project))
        response_text = ""
        for part in response.parts:
            response_text += part.text
        json_str = response_text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"Erreur sur le projet {project.get('Numéro', '')}: {str(e)}")
        return {
            "pertinent": False,
            "motifExclusion": "Erreur technique",
            "disciplinePrincipale": "erreur"
        }
    

project = {
        "Numéro": "SP-241030",
        "Numéro de référence": "20041923",
        "Type de l’avis": "Avis d’appel d’offres",
        "Statut": "Publié",
        "Titre": "Fourniture de services professionnels pour les plans, devis et surveillance des travaux - Réaménagement terrain de baseball",
        "Organisation": "Société du Parc Jean-Drapeau",
        "Description": "la ville de Montréal demande des soumissions pour des services professionnels pour la conception des plans et devis ainsi que la surveillance des travaux de réaménagement du terrain de baseball du centre sportif ",
        "Classifications": "81201500 - Services d'architectes",
        "Catégorie": "S3 - Services d’architecture et d’ingénierie",
        "Délai pour la réception des offres": "1 mois 2 jour(s) 5 heure(s) 20 minute(s) 25 seconde(s)",
        "Date de publication": "2025-01-22 09:58:41 Heure légale du Québec",
        "Nature du contrat": "Services professionnels",
        "Date limite de réception des offres": "2025-02-24 Avant 14:00 Heure légale du Québec",
        "Région": "Montréal"
    }


result = analyze_project(project)
result['source'] = {
        'numero': project.get('Numéro', ''),
        'titre': project.get('Titre', ''),
        'Date de publication': project.get('Date de publication', '')
    }

print(result)








# with open("analyses_projects_gemini.json", 'r', encoding='utf-8') as f : 
#     data = json.load(f)


# for result in data:
#     if result["pertinent"] : 
#         print(f"{result['source']}\n {result['motifPertinence']}")
#         print("\n")


