from decimal import Decimal
from models import Transazione, TipoTransazione
from .servizio_transazioni import crea_transazione, crea_deposito, crea_prelievo, crea_pagamento, crea_bonifico, esegui_transazione_su_conti

'''
def esegui_bonifico(db, conto_mittente, conto_destinatario, importo, descrizione):

    try:
        # 1) Transazione uscita sul mittente
        transazione_uscita = crea_transazione_uscita(
            importo=Decimal(importo),
            descrizione=descrizione,
            mittente_iban=conto_mittente.iban,
            destinatario_iban=conto_destinatario.iban
        )
        conto_mittente.applica_transazione(transazione_uscita)

        # 2) Transazione entrata sul destinatario
        transazione_entrata = crea_transazione_entrata(
            importo=Decimal(importo),
            descrizione=descrizione,
            mittente_iban=conto_mittente.iban,
            destinatario_iban=conto_destinatario.iban
        )
        conto_destinatario.applica_transazione(transazione_entrata)

        # salviamo tutto in una sola transazione DB
        db.add_all([conto_mittente, conto_destinatario, transazione_uscita, transazione_entrata])
        db.commit()

        db.refresh(conto_mittente)
        db.refresh(conto_destinatario)

        return conto_mittente.saldo, conto_destinatario.saldo

    except Exception as e:
        db.rollback()
        raise e
'''