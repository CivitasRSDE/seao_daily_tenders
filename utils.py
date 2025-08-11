import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
import json


def extract_ao_details(driver, link):
    driver.get(link)
    time.sleep(5)
    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
    ao_details = []
    for row in rows:
        try:
            status = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
            avis_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a")
            avis = avis_element.text.strip()
            avis_link = avis_element.get_attribute("href")
            title = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) .row:nth-of-type(2) span").text.strip()
            organization = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) .row:nth-of-type(3) span").text.strip()
            publication_date = row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text.strip()
            closing_date = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
            ao_details.append({
                "Statut": status,
                "Avis": avis,
                "Avis_Link": avis_link,
                "Title": title,
                "Organization": organization,
                "Publication_Date": publication_date,
                "Closing_Date": closing_date
            })
        except Exception as e:
            print(f"Error processing row: {e}")
            continue

    return ao_details

def get_clickable_numbers(driver):
    EXCLUDED_SUBCATEGORIES = {
        "Alimentation",
        "Ameublement",
        "Communication, détection et fibres optiques",
        "Constructions préfabriquées",
        "Préparation alimentaire et équipement de service",
        "Marine",
        "Cosmétiques et articles de toilette",
        "Moteurs, turbines, composants et accessoires connexes",
        "Armement",
        "Matériel de climatisation et de réfrigération",
        "Publications, formulaires et articles en papier",
        "Machinerie et outils",
        "Équipement de transport et pièces de rechange",
        "Papeterie et fournitures de bureau",
        "Véhicules spéciaux",
        "Matériaux de construction",
        "Produits et spécialités chimiques",
        "Équipement de lutte contre l’incendie, de sécurité et de protection",
        "Instruments scientifiques",
        "Fourniture et équipement médicaux et produits pharmaceutiques",
        "Équipement industriel",
        "Textiles et vêtements",
        "Vente de biens immeubles",
        "Vente de biens meubles"
        "Produits électriques et électroniques",
        "Produits finis"
    }
    links = []
    try:
        sections = driver.find_elements(By.CSS_SELECTOR, "div.container")
        for section in sections:
            try:
                main_category = section.find_element(By.CSS_SELECTOR, "h2").text.strip()
            except Exception:
                main_category = "Unknown"
            tables = section.find_elements(By.CSS_SELECTOR, "table.table-accueil")
            for table in tables:
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                for row in rows:
                    try:
                        columns = row.find_elements(By.CSS_SELECTOR, "td.enteteCentre.col-2")
                        if len(columns) < 2:
                            continue
                        
                        avis_du_jour = columns[0]
                        total = columns[1]

                        AV_link = avis_du_jour.find_element(By.CSS_SELECTOR, 'a').get_attribute("href") if avis_du_jour.find_elements(By.CSS_SELECTOR, "a") else None
                        total_link = total.find_element(By.CSS_SELECTOR, 'a').get_attribute("href") if total.find_elements(By.CSS_SELECTOR, "a") else None
                        
                        sub_category = row.find_element(By.CSS_SELECTOR, "td.enteteGauche").text.strip()
                        if sub_category in EXCLUDED_SUBCATEGORIES:
                            continue

                        links.append({
                            "sub_category": sub_category,
                            "avis_du_jour_url": AV_link,
                            "Nombre_avis_du_jour": avis_du_jour.text.strip(),
                            "total_url": total_link,
                            "Nombre_total_url": total.text.strip()
                        })

                    except Exception as e:
                        logging.error(f"Error processing row: {e}")
                        continue

    except Exception as e:
        logging.error(f"Error getting clickable numbers: {e}")
    
    return pd.DataFrame(links)

def filter_dataset(data_frame : pd.DataFrame):
    EXCLUDED = {
        "Alimentation",
        "Ameublement",
        "Communication, détection et fibres optiques",
        "Constructions préfabriquées",
        "Préparation alimentaire et équipement de service",
        "Marine",
        "Cosmétiques et articles de toilette",
        "Moteurs, turbines, composants et accessoires connexes",
        "Armement",
        "Matériaux de construction",
        "Matériel de climatisation et de réfrigération",
        "Publications, formulaires et articles en papier",
        "Machinerie et outils",
        "Équipement de transport et pièces de rechange",
        "Papeterie et fournitures de bureau",
        "Véhicules spéciaux",
        "Produits et spécialités chimiques",
        "Équipement de lutte contre l’incendie, de sécurité et de protection",
        "Instruments scientifiques",
        "Fourniture et équipement médicaux et produits pharmaceutiques",
        "Équipement industriel",
        "Textiles et vêtements",
        "Vente de biens immeubles",
        "Vente de biens meubles"
        "Produits électriques et électroniques",
        "Produits finis"
    }
    return data_frame[data_frame["avis_du_jour_url"].notnull() & ~data_frame["sub_category"].isin(EXCLUDED)]

def extract_ao_info(driver, ao_list, sub_category):
    all_ao_details = []
    for ao in ao_list: 
        try:
            driver.get(ao["Avis_Link"])
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, 'form.avis.resume.description.descriptionHtml.anchor'))
            )
            time.sleep(5)
            
            ao_details = {
                "sub_category": sub_category,
                "Numéro": ao["Avis"],
                "Titre": ao["Title"],
                "Organisation": ao["Organization"]
            }
            card = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'card'))
            )
            #card = driver.find_element(By.CLASS_NAME, 'card')
            rows = card.find_elements(By.CLASS_NAME, "row")
            for row in rows:
                dt_element = row.find_element(By.TAG_NAME, "dt").text.strip(':')
                dd_element = row.find_element(By.TAG_NAME, "dd").text
                ao_details[dt_element] = dd_element

            desc_section = driver.find_element(By.ID, 'form.avis.resume.description.descriptionHtml.anchor')
            ao_details["Description"] = desc_section.find_element(
                By.XPATH, './following-sibling::div[@class="resume-texte-enrichi"]').text.strip()

            try:
                class_section = driver.find_element(By.ID, 'form.avis.resume.categorie.unspsc.unspsc.anchor')
                dl = class_section.find_element(By.XPATH, './following-sibling::dl')
                classifications = []
                category = None
                for item in dl.find_elements(By.CLASS_NAME, "g-0.row"):
                    label = item.find_element(By.CLASS_NAME, 'col-title').text.strip()
                    value = item.find_element(By.CLASS_NAME, 'col-content').text.strip()
                    if label == "Classifications":
                        classifications.append(value)
                    elif label == "Catégorie":
                        category = value
                ao_details["Classifications"] = ', '.join(classifications)
                ao_details["Catégorie"] = category
            except NoSuchElementException:
                ao_details["Classifications"] = None
                ao_details["Catégorie"] = None

            info_fields = {
                'Délai pour la réception des offres': 'form.avis.resume.information.dateLimiteReceptionOffre',
                'Date de publication': 'form.avis.resume.information.datePublicationUtc',
                'Nature du contrat': 'form.avis.resume.information.natureContrat',
                'Date limite de réception des offres': 'form.avis.resume.information.limiteReceptionOffre',
                'Région': 'form.avis.resume.information.regionsLivraison'
            }
            
            for field, field_id in info_fields.items():
                try:
                    element = driver.find_element(By.ID, field_id)
                    ao_details[field] = element.find_element(By.CLASS_NAME, 'col-content').text.strip()
                except NoSuchElementException:
                    ao_details[field] = None

            all_ao_details.append(ao_details)
            
        except Exception as e:
            print(f"Error processing {ao['Avis']}: {str(e)}")
            continue

    return all_ao_details

def analyze_project(prompt_template, model, project):
    print(f"Analyzing {project['Numéro']}")
    try:
        cleaned_project = {
            k.strip(':'): v 
            for k, v in project.items()
            if k in [
                'Numéro', 'Titre', 'Organisation', 'Description',
                'Catégorie', 'Classifications', 'Région'
            ]
        }
        response = model.generate_content(prompt_template.format(**cleaned_project))
        response_text = "".join(part.text for part in response.parts)
        json_str = response_text.replace('```json', '').replace('```', '').strip()
        result = json.loads(json_str)

        return {
            'pertinent': result.get('pertinent', False),
            'motifPertinence': result.get('motifPertinence', ''),
            'motifExclusion': result.get('motifExclusion', ''),
            'disciplinePrincipale': result.get('disciplinePrincipale', ''),
            'pourcentage_pertinence': result.get('pourcentage_pertinence')
        }

    except Exception as e:
        print(f"Erreur d'analyse: {str(e)}")
        return {
            'pertinent': False,
            'motifPertinence': '',
            'motifExclusion': 'Erreur technique lors de l\'analyse',
            'disciplinePrincipale': '',
            'pourcentage_pertinence' : ''
        }
    
    