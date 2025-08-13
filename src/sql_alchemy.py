from sqlalchemy import create_engine, Column, Integer, DateTime, Boolean, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

Base = declarative_base()

class AoInfos(Base):
    __tablename__ = "ao_infos"
    numero = Column(String(250), primary_key=True)
    num_reference = Column(Text(),primary_key=True)
    type_avis = Column(Text())
    status = Column(Text())
    titre = Column(Text())
    organisation = Column(Text())
    description = Column(Text())
    classifications = Column(Text())
    categorie = Column(Text())
    delai_reception = Column(Text())
    date_publication = Column(Text())
    nature_contrat = Column(Text())
    date_limite = Column(Text())
    region = Column(Text())
    #LLM
    is_pertinent = Column(Boolean, nullable=True)
    motif_pertinence = Column(Text(), nullable=True)
    motif_exclusion = Column(Text(), nullable=True)
    discipline = Column(Text(), nullable=True)
    date_analyse = Column(DateTime, nullable=True)
    pourcentage_pertinence = Column(Text(), nullable=True)


    def get_engine(db_url):
        return create_engine(db_url)
    
    def create_tables(engine):
        return Base.metadata.create_all(engine)
    
    def get_session(engine):
        Session = sessionmaker(bind=engine)
        return Session()
    