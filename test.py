import pandas as pd
import matplotlib.pyplot as plt

# Chargement des fichiers CSV en utilisant l'encodage latin1 et le séparateur ';'
df1 = pd.read_csv("data-1741631746373.csv", encoding="latin1", sep=";")
df2 = pd.read_csv("projets_engineer_feb_march.csv", encoding="latin1", sep=";")

# Affichage rapide pour vérification (optionnel)
print("Fichier 1:")
print(df1.head())
print("\nFichier 2:")
print(df2.head())

# Renommer les colonnes du deuxième fichier pour plus de clarté

# Pour le deuxième fichier, nous n'utiliserons que la date et le numéro de référence
df2 = df2[["date_publication", "num_reference"]]

# Convertir les dates en datetime
df1['date_publication'] = pd.to_datetime(df1['date_publication'])
df2['date_publication'] = pd.to_datetime(df2['date_publication'])

# --- 1. Taux de chevauchement global ---
# Extraire les ensembles de références de chaque fichier
refs1 = set(df1['num_reference'].unique())
refs2 = set(df2['num_reference'].unique())

# Intersection et union
intersection = refs1.intersection(refs2)
union = refs1.union(refs2)

taux_global = (len(intersection) / len(union)) * 100 if union else 0

print(f"Taux de chevauchement global: {taux_global:.2f}%")
print(f"Nombre de projets dans Fichier 1: {len(refs1)}")
print(f"Nombre de projets dans Fichier 2: {len(refs2)}")
print(f"Nombre de projets communs: {len(intersection)}")

# --- 2. Taux de chevauchement par semaine et graphique ---
# Pour regrouper par semaine, nous allons utiliser la date de publication et déterminer la semaine correspondante.
# Ici, nous allons choisir la date du lundi comme date de début de semaine.

# Créer une colonne "semaine" pour chaque DataFrame (on peut utiliser pd.Grouper ou dt.to_period('W'))
df1['semaine'] = df1['date_publication'].dt.to_period('W').apply(lambda r: r.start_time)
df2['semaine'] = df2['date_publication'].dt.to_period('W').apply(lambda r: r.start_time)

# Déterminer la plage de semaines à partir du 30 janvier
start_week = pd.to_datetime("2025-01-30")
end_week = max(df1['semaine'].max(), df2['semaine'].max())

# Créer un DataFrame pour stocker le taux par semaine
semaine_range = pd.date_range(start=start_week, end=end_week, freq='W-MON')
taux_semaine = []

for semaine in semaine_range:
    # Sélection des projets de la semaine dans chaque DataFrame
    refs1_semaine = set(df1.loc[df1['semaine'] == semaine, 'num_reference'])
    refs2_semaine = set(df2.loc[df2['semaine'] == semaine, 'num_reference'])
    
    # Union et intersection pour la semaine
    union_semaine = refs1_semaine.union(refs2_semaine)
    intersection_semaine = refs1_semaine.intersection(refs2_semaine)
    
    taux = (len(intersection_semaine) / len(union_semaine)) * 100 if union_semaine else 0
    taux_semaine.append(taux)

# Créer un DataFrame récapitulatif pour le graphique
df_taux = pd.DataFrame({
    "semaine": semaine_range,
    "taux_chevauchement": taux_semaine
})

print("\nTaux de chevauchement par semaine:")
print(df_taux)

# Création du graphique
plt.figure(figsize=(10, 6))
plt.plot(df_taux['semaine'], df_taux['taux_chevauchement'], marker='o')
plt.xlabel("Semaine (début)")
plt.ylabel("Taux de chevauchement (%)")
plt.title("Taux de chevauchement des projets par semaine")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()
