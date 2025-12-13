#lavori.py è stata creata solo per popolare la tabella lavori con dati iniziali.
from database import SessionLocal, engine, Base
from models import Lavoro


Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    print("Inserimento lavori...")

    lavori = [   
        {"nome_lavoro": "Medico", "stipendio_mensile": 2000.00},
        {"nome_lavoro": "Impiegato amministrativo", "stipendio_mensile": 1500.00},
        {"nome_lavoro": "Operaio", "stipendio_mensile": 1300.00},
        {"nome_lavoro": "Insegnante", "stipendio_mensile": 1400.00},
        {"nome_lavoro": "Programmatore", "stipendio_mensile": 1500.00},
        {"nome_lavoro": "Infermiere", "stipendio_mensile": 1600.00},
        {"nome_lavoro": "Cassiere", "stipendio_mensile": 1300.00},
        {"nome_lavoro": "Magazziniere", "stipendio_mensile": 1200.00},
        {"nome_lavoro": "Autista", "stipendio_mensile": 1700.00},
        {"nome_lavoro": "Disoccupato", "stipendio_mensile": 0.00},
    ]

    for lavoro in lavori:
        if not db.query(Lavoro).filter_by(nome_lavoro=lavoro["nome_lavoro"]).first():
            db.add(Lavoro(**lavoro))

    db.commit()
    print("✔️ Lavori inseriti.")
except Exception as e:
    db.rollback()
    print("❌ Errore:", e)

finally:
    db.close()