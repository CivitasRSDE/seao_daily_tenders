import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import json
import os
from datetime import datetime
import datetime as dt
import tempfile
from utils import (
    extract_ao_details,
    get_clickable_numbers,
    filter_dataset,
    extract_ao_info,
    analyze_project,
)
import google.generativeai as genai
from sql_alchemy import AoInfos, Base
load_dotenv()

# engine = create_engine("postgresql://seao_user:wac321@localhost:5432/seao_db")
# engine = create_engine("postgresql://postgres:Wac3212013%40@localhost:5432/seaodb")
engine = create_engine(os.getenv('DB_URL'))
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

os.environ["GRPC_DNS_RESOLVER"] = "native"
base_url = "https://seao.gouv.qc.ca/toutes-categories"

logging.basicConfig(
    filename="web_scraping.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

prompt_template = """
Tu es un assistant spécialisé qui agit au nom de Groupe Civitas, une entreprise québécoise possédant plusieurs succursales (Beauharnois, Granby, Laval, Longueuil, Montréal, Mirabel, Québec, St-Césaire, Terrebonne). 

## CONTEXTE ENTREPRISE

Groupe Civitas intervient dans les domaines suivants :

1) GÉOMATIQUE ET ARPENTAGE
   - Acquisition de données (photogrammétrie, lidar, lasergrammétrie, drones, etc.)
   - Traitement et modélisation 3D (BIM, jumeaux numériques, etc.)
   - Arpentage foncier (plan d'implantation, piquetage, bornage, subdivision, lotissement)
   - Arpentage de construction (levés topographiques, implantation, calculs volumétriques, relevés “tel que construit”,Mesurage du déplacement de structures (monitoring))
   - Certificats de localisation (étude des empiètements, servitudes, conformité réglementaire)

2) SERVICES EN INFRASTRUCTURES URBAINES ET GÉNIE ROUTIER
   - Développement ou réhabilitation de réseaux routiers et d’infrastructures urbaines
   - Production d’eau potable, réseaux d’égout, drainage, réfection de voirie, parcs, terrains sportifs
   - Services : études d’avant-projet, conception, plans et devis, préparation d’appels d’offres, surveillance, gestion de la construction

3) SERVICES EN TRANSPORT ET CIRCULATION
   - Études de circulation, plan de transport, plan de maintien de la circulation
   - Sécurité routière, mobilité active et durable

4) SERVICES EN AMÉNAGEMENT DU TERRITOIRE
   - Aménagement d’espaces publics (milieu urbain ou rural)
   - Études conceptuelles, plans et devis, surveillance, gestion de la construction
   - Vision de développement durable

5) SERVICES EN INGÉNIERIE DU BÂTIMENT
   - Services exclusivement liés à l'expertise technique 
   - services en génie du bâtiment  : Études d'avant-projet, Études conceptuelles, Conception et design, Préparation des plans et des devis, Préparation des documents d'appels d'offres, Surveillance des travaux,Gestion de la construction
   - services en inspection commerciale : vérifications d'état de propriété en conformité (ASTM E2018-24), Un relevé des déficiences,Une estimation budgétaire
   - Projets résidentiels, industriels, commerciaux, institutionnels
   - Conception et design, études d’avant-projet, plans, devis, gestion de la construction
   - Inspection (façades Loi 122, stationnements étagés, normes ASTM E2018-24)
   - Fonds de prévoyance (Loi 16), carnet d’entretien
   - Exclure explicitement :
     * Toute implication dans l'exécution des travaux
     * Les projets purement constructifs sans besoin d'études préalables
     * Les appels mentionnant "entrepreneur général", "fourniture et installation", "réalisation des travaux"

Bien que nous ayons des succursales dans plusieurs villes, nous devons faire attention à la localisation des appels d’offres selon notre stratégie et nos ressources.

---

## RÈGLES DE FILTRAGE

1) **Catégories visées**  
   - Approvisionnements, Autres, Services (et sous-catégories) sur SEAO  
   - En particulier : “Services d’architecture et d’ingénierie” (pour l’ingénierie) et “Services de communication, de photographie, de cartographie” (pour l’arpentage)  
   - Parfois aussi “Indéterminé” ou “Entretien, réparation, modification, réfection et installation…” etc.

2) **Pour l’ingénierie**
   - La mention d’un ingénieur ou de tout titre professionnel parmi les représentants du donneur d’ouvrage (municipalité, ministère, etc.) ne signifie pas que l’appel d’offres recherche des services professionnels d’ingénierie. 
   - Il faut obligatoirement trouver dans la description une demande explicite de conception, d’études d’avant-projet, de plans et devis, ou de surveillance de travaux spécialisée pour être jugé pertinent. Si l’appel d’offres vise un entrepreneur pour la réalisation de travaux de construction, il doit être exclu
   - Exclure tout appel d'offres dont la nature du contrat est « Travaux de construction » et dont la description ne contient aucun indicateur explicite d'une demande de services professionnels (par exemple : « services professionnels », « plans et devis », « études d’avant-projet », « études préliminaires », « conception », « surveillance de travaux », « ingénieur », « bureau d'études »). Autrement dit, si l’appel d'offres concerne principalement la réhabilitation, la transformation ou le réaménagement de bâtiments par l'exécution de travaux sans solliciter clairement des services de conception, d’études ou de surveillance spécialisés, alors il doit être exclu.
   - Exclure tous les appels d’offres où la mission demandée se limite uniquement à l’exécution des travaux (construction, pavage, réfection, remplacement, installation d’équipements).
   - Exclure tous les appels d’offres portant sur l’exploitation, la gestion ou l’entretien des infrastructures (stations d’épuration, usines de traitement, réseaux d’égouts, etc.), sauf s’ils incluent explicitement des services professionnels d’ingénierie liés à la conception, aux études ou à la surveillance des travaux. Ajouter les mots-clés "exploitation", "opération", "gestion", "maintenance", "entretien" aux critères d’exclusion lorsqu’ils sont associés à des infrastructures existantes.
   - Un appel d’offres est jugé pertinent uniquement s'il mentionne explicitement des services professionnels d’ingénierie tels que :Études préliminaires, études d’avant-projet, Conception et élaboration des plans et devis, 
   - Inclure les appels mentionnant des services professionnels de surveillance des travaux, de suivi de chantier et de conformité aux normes.
   - Exclure tout appel d'offres dont l'objet principal est la réfection, la rénovation ou la conception d'installations ou de structures où la prestation requise relève exclusivement du domaine de l'architecture (même si une composante d’ingénierie est mentionnée de façon marginale). Ce type de mandat ne correspond pas à notre champ d'expertise qui se concentre sur les services d'ingénierie, d'arpentage ou de géomatique.
   - Exclure un appel d’offres s'il contient l’un des termes suivants sans mention d’ingénierie ou de surveillance spécialisée : "Travaux de réfection", "réhabilitation", "reconstruction", "construction", "réaménagement", "rénovation", "remplacement", "installation", "pavage", "asphaltage", "terrains de sport", "signalisation", "infrastructures routières", "égouts", "conduites d’eau", "remise en état", "excavation".
   - Seule exception : Si ces termes sont accompagnés d’une demande pour des services professionnels (conception, plans et devis, surveillance spécialisée).
   - Si l’appel d’offres mentionne la surveillance des travaux, la pertinence doit être élevée (70 % ou plus), à condition que la localisation soit acceptable.
   - Intérêt pour : études d’avant-projet, plans et devis, surveillance, ingénierie, génie civil, structure, mécanique, électricité  
   - Exclure tous les appels d’offres portant principalement sur l’analyse de stabilité des digues, barrages ou infrastructures hydrauliques, ainsi que sur l’ingénierie géotechnique ou hydraulique, sauf si ces projets incluent explicitement des services liés aux infrastructures municipales, au génie civil urbain ou à l’arpentage.
   - Exclure tous les appels d’offres portant principalement sur la gestion de projets de construction sans implication directe dans la conception, les études, les plans et devis ou la surveillance spécialisée des travaux. La gestion administrative des projets d’infrastructure, y compris les programmes de maintien d’actifs, ne relève pas des services professionnels d’ingénierie ciblés par Groupe Civitas.
   - Exclure si c’est uniquement de l’architecture (sauf mention explicite d’équipe d’ingénieurs)  
   - Exclure si c’est uniquement de l’architecture de paysage (sauf si ingénierie jointe)
   - Exclure tout appel d’offres portant sur des infrastructures de traitement ou de distribution d’eau (usines ou stations d’épuration, filtres, réservoirs, conduites), même s’ils requièrent des plans et devis ou de la surveillance, car ce domaine ne fait pas partie de notre expertise.  
   - Exclure contrôle qualité des matériaux, suivi environnement des sols, études géotechniques (pour laboratoires)  
   - Exclure tout appel d’offres portant sur les structures MTMD (ponts, viaducs, tunnels, murs de soutènement, échangeurs d’autoroutes, etc.), même s’ils requièrent des plans et devis ou des études préliminaires, car ces ouvrages ne relèvent pas de notre expertise.
   - Exclure tout appel d’offres qui requiert un mandataire multi-disciplinaire (architecture de paysage, urbanisme, design urbain, loisirs, etc.) pour la préparation d’un plan stratégique ou d’un plan directeur, et qui exige la présentation de projets similaires (ex. « deux projets réalisés dans les 10 dernières années »).
   - Exclure tout appel d'offres de services professionnels en ingénierie dont l'objet principal concerne des spécialités en télécommunications, électronique, audiovisuel ou scénique, car ces domaines ne relèvent pas de notre expertise.
   - Exclure tout avis de qualification dont l’objet principal est de constituer une banque de prestataires de services en architecture (même si des services connexes en ingénierie sont mentionnés), car cela ne correspond pas à notre champ d’expertise.
   - Exclure tout appel d’offres en ingénierie dont l’objet principal consiste en la mise à niveau, le remplacement ou la maintenance d’équipements électriques (ex. sous-stations, inverseurs) sans demande explicite de services de conception, d’études d’avant-projet ou de surveillance spécialisée. Ce type de mandat ne relève pas de notre champ d’expertise
   -Exclure tout appel d’offres de conception-construction (design-build) où le mandataire doit également réaliser ou gérer l’exécution des travaux. Groupe Civitas n’assume pas la responsabilité globale du projet (conception et construction) et intervient uniquement comme fournisseur de services professionnels d’ingénierie ou d’arpentage.
   - Exclure tout appel d’offres dont la participation est restreinte aux seuls soumissionnaires préqualifiés (2e étape ou étape subséquente d’un appel d’offres en plusieurs phases). Puisque Groupe Civitas n’a pas déjà été qualifié, il n’est pas admissible à soumissionner et cet appel d’offres ne peut pas être pertinent.
   -Exclure tout appel d’offres portant principalement sur des services de laboratoire, de contrôle qualitatif, d’essais de matériaux (essais en laboratoire, contrôle d’enrobés, béton, granulats, etc.) sans demande explicite de conception, de plans et devis, ou de surveillance spécialisée pour la mise en œuvre.
   - En d’autres termes, s’il ne s’agit que de contrôler la qualité des matériaux, de réaliser des essais (géotechniques, environnementaux, de compaction, etc.), et qu’aucun service de conception ou de surveillance d’ingénierie n’est demandé, alors l’appel d’offres est non pertinent pour Groupe Civitas.
   - Exclure tout appel d’offres ou d’intérêt visant la recherche de promoteurs, développeurs ou investisseurs pour un projet d’aménagement (ex. parc solaire, énergie renouvelable, réutilisation de site industriel), sans demande explicite de services professionnels d’ingénierie (conception, plans et devis, surveillance spécialisée) ou d’arpentage. L’absence d’une sollicitation directe d’ingénieurs ou d’arpenteurs signifie que ce n’est pas pertinent pour Groupe Civitas.  
   - Exclure les projets axés principalement sur l’installation, la réparation ou la maintenance d’équipements mécaniques ou électriques (p. ex. remplacement de thermostats, travaux de régulation automatique, pose d’appareils spécialisés) qui ne comportent pas de services professionnels significatifs (conception, ingénierie, plans et devis).
   - Inclure les projets de construction/réfection d’infrastructures municipales, chaussées, routes, éclairage, parcs, stationnements, bassins de rétention, aqueducs, égouts, etc.  
   - Exclure tout appel d’offres mentionnant uniquement des audits financiers, de performance, environnementaux ou tout autre audit sans lien avec nos services d’ingénierie ou d’arpentage.
    - Cependant, si l’appel d’offres mentionne un audit de sécurité, un audit en santé et sécurité au travail (SST) ou un audit en signalisation pouvant inclure des services professionnels d’ingénierie (études, plans, surveillance, conception), il peut être jugé pertinent.
   - Exclure les projets qui concernent exclusivement la construction ou la réfection (p. ex. terrains de sport, pistes cyclables, etc.) sans mention explicite de services professionnels (études d’avant-projet, plans et devis, surveillance, ingénierie). 
   - Autrement dit, s’il n’y a aucune indication que nous pourrions fournir un service d’ingénierie (conception, plans et devis, surveillance, gestion de la construction), l’appel d’offres doit être écarté.

3) **Pour l’arpentage** 
   - Exclure tout appel d’offres où la mission principale consiste en un inventaire, une analyse ou une étude patrimoniale, de conservation culturelle ou de promotion du patrimoine, sans aucune mention explicite de services professionnels d’ingénierie, d’arpentage ou de géomatique (comme la conception de plans, la surveillance de travaux, etc.). 
   - **Inclure** les appels d’offres liés à l’acquisition et l’utilisation de **drones RGB** pour la cartographie, l’arpentage et la modélisation 3D
   - Inclure les appels d’offres liés à l’acquisition et l’utilisation de drones RGB (excluant les capteurs multispectraux, hyperspectraux et thermiques) pour la cartographie, l’arpentage et la modélisation 3D.
   - **Exclure automatiquement** tout appel d’offres où la mission principale concerne le **traitement d’images satellitaires, la télédétection spatiale ou la cartographie basée sur des données satellites.**  
   - **Exclure** les appels d’offres relatifs uniquement à l’achat d’équipements ou de matériel scientifique (capteurs, caméras hyperspectrales, spectromètres, etc.), sauf s’ils incluent des services professionnels d’arpentage, de géomatique ou d’ingénierie.
   - **Exclure** les offres qui concernent exclusivement l’acquisition de capteurs de télédétection sans mention d’analyse ou de traitement des données par des services professionnels.
   - Mots-clés : cartographie, topographie, Lidar, imagerie numérique, relevés, photos aériennes, levés laser aéroportés  
   - Sinon, même logique d’examen de la description et de la localisation

4) **Localisation**
   - On prend les appels d'offres s'ils se trouvent sur la ville de quebec et les villes avoisinate mais pas trop loin non plus  
   - De manière générale, on **exclut** l’est lointain de la Ville de Québec, Bas-Saint-Laurent, Rimouski, La Pocatière, le Saguenay, l’Abitibi-Témiscamingue, La Tuque, etc. (sauf si nous décidons de couvrir ces régions par exemple pour les projets d'arpentage)


5) ** Pour SERVICES EN INGÉNIERIE DU BÂTIMENT**
   - **Exclure immédiatement** tout appel d’offres où l’objet principal concerne des **travaux de construction, de réparation ou de maintenance** et non une prestation de **services professionnels**.  
   - **Si la mission principale concerne des travaux, l’appel d’offres est exclu, même si une petite partie mentionne une inspection.**


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
**Région** : {Région}
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
  "disciplinePrincipale": "Choisit une discipline de cette liste [Arpentage, Géomatique, Ingénierie, Science du bâtiment]",
  "pourcentage_pertinence" : du 0 à 100 retourne le pourcentage de pertinene en se basant sur les informations de l'appel d'offre
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

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)


def run(driver):
    try:
        logging.info("Starting the web scraping process.")
        avis_du_jour_data = get_clickable_numbers(driver)
        print(avis_du_jour_data)
        logging.info("Retrieved clickable numbers.")
        avis_du_jour_data_filtered = filter_dataset(avis_du_jour_data)
        existing_entries = session.query(
        AoInfos.numero, 
        AoInfos.num_reference
        ).all()
        existing_pairs = {(str(a.numero), str(a.num_reference)) for a in existing_entries}
        #existing_numeros = {ao.numero for ao in session.query(AoInfos.numero).all()}
        # existing_numeros_ref = {
        #     ao.num_reference for ao in session.query(AoInfos.num_reference).all()
        # }
        new_enteries = []
        for _, row in avis_du_jour_data_filtered.iterrows():
            sub_category = row["sub_category"]
            url = row["avis_du_jour_url"]
            basic_ao_list = extract_ao_details(driver, url)
            detailed_ao_list = extract_ao_info(driver, basic_ao_list, sub_category)
            for ao in detailed_ao_list:
                num = ao.get("Numéro", "").strip()
                ref = ao.get("Numéro de référence", "").strip()
                if not num and not ref:
                    logging.warning(f"Entry missing both identifiers, skipping")
                    continue
                if (num,ref) not in existing_pairs:
                    new_enteries.append(ao)
        logging.info(f"Found {len(new_enteries)} new_enteries")
        if new_enteries:
            for entry in new_enteries:
                ao_entry = AoInfos(
                    numero=entry.get("Numéro", ""),
                    num_reference=entry.get("Numéro de référence", ""),
                    type_avis=entry.get("Type de l’avis", ""),
                    status=entry.get("Statut", ""),
                    titre=entry.get("Titre", ""),
                    organisation=entry.get("Organisation", ""),
                    description=entry.get("Description", ""),
                    classifications=entry.get("Classifications", ""),
                    categorie=entry.get("Catégorie", ""),
                    delai_reception=entry.get("Délai pour la réception des offres", ""),
                    date_publication=entry.get("Date de publication", "")[:10],
                    nature_contrat=entry.get("Nature du contrat", ""),
                    date_limite=entry.get("Date limite de réception des offres", "")[
                        :10
                    ],
                    region=entry.get("Région", ""),
                )
                session.add(ao_entry)
                session.commit()            
            logging.info("New entries have been added to the database.")
        for entry in new_enteries:
            try:
                result = analyze_project(prompt_template, model, entry)
                session.query(AoInfos).filter_by(numero=entry.get("Numéro")).update(
                    {
                        "is_pertinent": result.get("pertinent", False),
                        "motif_pertinence": result.get("motifPertinence", ""),
                        "motif_exclusion": result.get("motifExclusion", ""),
                        "discipline": result.get("disciplinePrincipale", ""),
                        "date_analyse": dt.datetime.now(),
                        "pourcentage_pertinence": result.get("pourcentage_pertinence"),
                    }
                )
                session.commit()
                logging.info(f"Analysis successful for entry {entry.get('Numéro')}.")
                time.sleep(25)
            except Exception as e:
                logging.error(f"Erreur d'analyse pour {entry.get('Numéro')}: {str(e)}")
                session.rollback()
    finally:
        session.close()
        driver.quit()
        logging.info("Web scraping process finished and driver closed.")


options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument(
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
)
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
profile_dir = tempfile.mkdtemp()
options.add_argument(f"--user-data-dir={profile_dir}")
driver = webdriver.Chrome(service=Service(), options=options)
driver.get(base_url)
time.sleep(5)

if __name__ == "__main__":
    run(driver)



