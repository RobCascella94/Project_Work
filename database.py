from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session

# Connessione (da cambiare echo=False prima di consegnare)
DATABASE_URL = "sqlite:///db_banca.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})#check è per sqlite in modo da gestire più thread in app

#scoped_session assicura che ogni thread (o contesto) ottenga la propria Session isolata. In Flask questo impedisce che due richieste condividano la stessa sessione.
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()