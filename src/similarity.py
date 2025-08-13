import pandas as pd
import os
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sql_alchemy import AoInfos, Base
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


engine = create_engine("postgresql://postgres:Wac3212013%40@localhost:5432/seaodb")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

query = """
    SELECT numero, titre, organisation, classifications, categorie 
    FROM public.ao_infos 
    WHERE is_pertinent 
    AND date_publication BETWEEN '2025-03-15' AND '2025-03-27'
"""

with engine.connect() as connection:
    df = pd.read_sql(query, connection)
print(df.columns)
soumissions= pd.read_excel("docs\soumissions_civitas.xlsx")
print(soumissions.columns)


df["texte"] = (
    df["titre"].fillna("") + " " +
    df["organisation"].fillna("") + " " +
    df["classifications"].fillna("") + " " +
    df["categorie"].fillna("")
)

soumissions["texte"] = (
    soumissions["titre"].fillna("") + " " +
    soumissions["organisation"].fillna("") + " " +
    soumissions["classifications"].fillna("") + " " +
    soumissions["categorie"].fillna(""))
    
corpus = pd.concat([df["texte"], soumissions["texte"]], ignore_index=True)

vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
vectorizer.fit(corpus)

tfidf_df1 = vectorizer.transform(df["texte"])
tfidf_df2 = vectorizer.transform(soumissions["texte"])

similarity_matrix = cosine_similarity(tfidf_df1, tfidf_df2)

import numpy as np

best_match_indices = similarity_matrix.argmax(axis=1)

best_match_scores = similarity_matrix.max(axis=1)

df["best_match_in_df2"] = soumissions["titre"].iloc[best_match_indices].values
df["similarity_score"] = best_match_scores

df.to_excel("similarity1.xlsx", index=False)
