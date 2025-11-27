from database import Base, SessionLocal, engine
from models import Utente, Lavoro, Conto
from servizi_banca import crea_transazione, crea_deposito, crea_prelievo, crea_pagamento, crea_bonifico, esegui_transazione_su_conti, genera_codice_titolare, genera_iban, crea_nuovo_conto_utente
from decimal import Decimal


def main():

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # -------------------------------------------------
        # 1) CREAZIONE UTENTE + LAVORO
        # -------------------------------------------------
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

        utente = Utente(
            nome="Mario",
            cognome="Rossi",
            codice_fiscale="RSSMRA80A01H501Z",
            codice_titolare=genera_codice_titolare(db),
            lavoro_id=db.query(Lavoro).filter_by(nome_lavoro="Impiegato amministrativo").first().id
        )
        utente.crea_pin("123456")
        

        db.add(utente)
        db.commit()
        db.refresh(utente)
        print("✔️ Utente creato:", utente.codice_titolare)
        # -------------------------------------------------
        # 2) CREAZIONE CONTI
        # -------------------------------------------------
        conto1 = crea_nuovo_conto_utente(db, utente)
        conto2 = crea_nuovo_conto_utente(db, utente)

        db.add_all([conto1, conto2])
        db.commit()
        db.refresh(conto1)
        db.refresh(conto2)

        # -------------------------------------------------
        # 3) STIPENDIO → DEPOSITO
        # -------------------------------------------------
        stipendio = crea_deposito(db.query(Lavoro).filter_by(nome_lavoro="Impiegato amministrativo").first().stipendio_mensile, "Stipendio mensile", conto1)

        esegui_transazione_su_conti(db, transazione=stipendio, conto_destinatario=conto1)

        # -------------------------------------------------
        # 4) PRELIEVO ATM
        # -------------------------------------------------
        prelievo = crea_prelievo("100.00", "Prelievo Bancomat", conto1)

        esegui_transazione_su_conti(db, transazione=prelievo, conto_mittente=conto1)

        # -------------------------------------------------
        # 5) BONIFICO TRA CONTI
        # -------------------------------------------------
        bonifico = crea_bonifico("250.00", "Pagamento affitto", conto1, conto2)

        saldi = esegui_transazione_su_conti(db, transazione=bonifico, conto_mittente=conto1, conto_destinatario=conto2)

        # -------------------------------------------------
        # 6) RISULTATI FINALI
        # -------------------------------------------------
        print("\n----- RISULTATI FINALI -----")
        print("Conto 1:", conto1.iban, " → Saldo:", saldi["saldo_mittente"])
        print("Conto 2:", conto2.iban, " → Saldo:", saldi["saldo_destinatario"])

        print("\nTransazioni conto 1:")
        # Unisci transazioni effettuate e ricevute per mostrare tutti i movimenti
        transazioni_conto1 = list(conto1.transazioni_effettuate) + list(conto1.transazioni_ricevute)
        # Ordina per data (dal più vecchio al più recente)
        transazioni_conto1 = sorted(transazioni_conto1, key=lambda x: x.data)
        for t in transazioni_conto1:
            print(f"[{t.tipo.value.upper()}] {t.importo}€ - {t.descrizione}")

        print("\nTransazioni conto 2:")
        transazioni_conto2 = list(conto2.transazioni_effettuate) + list(conto2.transazioni_ricevute)
        transazioni_conto2 = sorted(transazioni_conto2, key=lambda x: x.data)
        for t in transazioni_conto2:
            print(f"[{t.tipo.value.upper()}] {t.importo}€ - {t.descrizione}")

    except Exception as e:
        print("❌ ERRORE:", e)

    finally:
        db.close()


if __name__ == "__main__":
    main()