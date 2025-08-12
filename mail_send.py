import smtplib 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy import and_, create_engine
import os
from dotenv import load_dotenv
import pandas as pd
import urllib.parse
load_dotenv()


def encode_numero(numero):
    encoded = urllib.parse.quote(numero)
    return str(encoded)

def get_yesterday_ao(db_url):
    yesterday = str(datetime.now().date() - timedelta(days=1))
    # yesterday = str(datetime.now().date())
    engine = create_engine(db_url)
#     query = f"""
#             SELECT * FROM ao_infos
#             WHERE date_publication BETWEEN '2025-08-07' AND '2025-08-10'  
#             AND is_pertinent = true 
#             ORDER BY pourcentage_pertinence DESC
#   """
    query = f"""
          SELECT * FROM ao_infos
          WHERE date_publication = '{yesterday}' AND is_pertinent = true
          ORDER BY pourcentage_pertinence DESC
"""
    
    df = pd.read_sql(query, engine)
    return df

def format_tender_email(row):
    html_template = f"""
    <div style="margin-bottom: 20px; background-color: #f5f5f5; padding: 15px; border-radius: 5px; width: 100%; box-sizing: border-box;">
        <h3>
        No d'avis : 
        <a href="https://seao.gouv.qc.ca/avis-resultat-recherche?flTxtAllWrds={encode_numero(row['numero'])}&isSimpleSearch=true" 
           target="_blank" 
           style="text-decoration: none; color: #007bff;">
            {row['numero']} / {row['num_reference']}
        </a>
    </h3>

    <div>
            <p style="font-family: 'Aptos', sans-serif;"><strong>Donneur d'ouvrage :</strong><br>
            {row['organisation']}</p>
            
            <table style="width: 100%; border-collapse: collapse; font-family: 'Aptos', sans-serif;">
                <tr>
                    <td style="padding: 8px; background-color: #fff; width: 30%;"><strong>Titre :</strong></td>
                    <td style="padding: 8px; background-color: #fff;">{row['titre']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; width: 30%;"><strong>Catégorie :</strong></td>
                    <td style="padding: 8px;">{row['categorie']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #fff; width: 30%;"><strong>Type de l'avis :</strong></td>
                    <td style="padding: 8px; background-color: #fff;">{row['type_avis']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; width: 30%;"><strong>Discipline :</strong></td>
                    <td style="padding: 8px;">{row['discipline']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #fff; width: 30%;"><strong>Région :</strong></td>
                    <td style="padding: 8px; background-color: #fff;">{row['region']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; width: 30%;"><strong>Date limite :</strong></td>
                    <td style="padding: 8px;">{row['date_limite']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; width: 30%;"><strong>Motif de pertinence :</strong></td>
                    <td style="padding: 8px;">{row['motif_pertinence']}</td>
                </tr>
            </table>
        </div>
    </div>
    """
    return html_template

def send_outlook_email(sender_email, sender_password, recipient_email, df_tenders):
    #smtp_server = "smtp.gmail.com"
    smtp_server = "smtp.office365.com"
    smtp_port = 587
    grouped = df_tenders.groupby("discipline", sort=True) 
    discipline_html = []
    for discipline_name, discipline in grouped:
        discipline_html.append(f"""
            <div style="margin: 30px 0 10px 0; padding: 10px; background-color: #e9ecef; border-radius: 5px;">
                <h2 style="color: #2c3e50; margin: 0;">{discipline_name}</h2>
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
        """)

        discipline_html.extend([format_tender_email(row) for _, row in discipline.iterrows()])
        discipline_html.append("</div>")

    html_content = f"""
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Aptos:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{ 
                font-family: 'Aptos', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .logo-container {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo {{
                max-width: 300px;
                height: auto;
            }}
            h2 {{
                font-family: 'Aptos', sans-serif;
                font-weight: 700;
            }}
            p {{
                font-family: 'Aptos', sans-serif;
            }}
        </style>
    </head>
    <body>
        <div class="logo-container">
        <img src="https://afg.quebec/wp-content/uploads/2022/11/logoCivitas-1.png" alt="Logo" class="logo">
        </div>
        <h2>Nombre total d'appels d'offres : {len(df_tenders)}</h2>
        {''.join(discipline_html)}
    </body>
    </html>
    """
    msg = MIMEMultipart('alternative')
    # msg['Subject'] = f'Veille des marchés publics entre 2025-08-07 et 2025-08-10'
    msg['Subject'] = f'Veille des marchés publics en date du {(datetime.now().date() - timedelta(days=1))}'
    # msg['Subject'] = f'Veille des marchés publics en date du {(datetime.now().strftime("%Y-%m-%d"))}'
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        print("Email sent successfully")
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise
    
    finally:
        if 'server' in locals():
            server.quit()

def main():
    try:
        #db_url = "postgresql://postgres:Wac3212013%40@localhost:5432/seaodb"
        db_url = "postgresql://seao_user:Wac321@localhost:5432/seao_db"
        df_tenders = get_yesterday_ao(db_url)
        
        if len(df_tenders) == 0:
            print("No tenders found for yesterday")
            return
        
        send_outlook_email(
            sender_email=os.getenv('OUTLOOK_EMAIL'),
            sender_password=os.getenv('OUTLOOK_PASSWORD'),
            recipient_email=os.getenv('RECIPIENT_EMAIL'),
            df_tenders=df_tenders
        )
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

main()
