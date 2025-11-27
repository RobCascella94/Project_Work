from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from models import Transazione, TipoTransazione


def crea_transazione(importo, descrizione, tipo, conto_mittente=None, conto_destinatario=None):
    return Transazione(
        importo=Decimal(importo),
        descrizione=descrizione,
        tipo=tipo,
        conto_mittente_id=conto_mittente.id if conto_mittente else None,
        conto_destinatario_id=conto_destinatario.id if conto_destinatario else None
    )


def crea_deposito(importo, descrizione, conto_destinatario):
    return crea_transazione(
        importo=importo,
        descrizione=descrizione,
        tipo=TipoTransazione.DEPOSITO,
        conto_destinatario=conto_destinatario
    )

def crea_prelievo(importo, descrizione, conto_mittente):
    return crea_transazione(
        importo=importo,
        descrizione=descrizione,
        tipo=TipoTransazione.PRELIEVO,
        conto_mittente=conto_mittente
    )

def crea_pagamento(importo, descrizione, conto_mittente, conto_destinatario):
    return crea_transazione(
        importo=importo,
        descrizione=descrizione,
        tipo=TipoTransazione.PAGAMENTO,
        conto_mittente=conto_mittente,
        conto_destinatario=conto_destinatario
    )

def crea_bonifico(importo, descrizione, conto_mittente, conto_destinatario):
    return crea_transazione(
        importo=importo,
        descrizione=descrizione,
        tipo=TipoTransazione.BONIFICO,
        conto_mittente=conto_mittente,
        conto_destinatario=conto_destinatario
    )


def esegui_transazione_su_conti(db, transazione, conto_mittente=None, conto_destinatario=None):
    try:
        # Applica gli effetti al conto mittente
        if conto_mittente:
            conto_mittente.applica_transazione(transazione)
            db.add(conto_mittente)

        # Applica gli effetti al conto destinatario
        if conto_destinatario:
            conto_destinatario.applica_transazione(transazione)
            db.add(conto_destinatario)

        db.add(transazione)
        db.commit()

        # Refresh per ottenere saldi aggiornati
        if conto_mittente:
            db.refresh(conto_mittente)
        if conto_destinatario:
            db.refresh(conto_destinatario)

        return {
            "saldo_mittente": conto_mittente.saldo if conto_mittente else None,
            "saldo_destinatario": conto_destinatario.saldo if conto_destinatario else None,
        }

    except Exception as e:
        db.rollback()
        raise e
