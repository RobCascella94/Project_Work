from sqlalchemy.exc import IntegrityError
from decimal import Decimal
import random
from models import Conto, Utente




def genera_iban(db_da_passare):
    #semplici codici banca e filiale fissi per semplicità 
    abi = "123"     #codice banca
    cab = "456"     #codice filiale

    while True:
        numero = random.randint(1, 999999)
        conto = f"{numero:06d}"
        iban = f"IT{abi}{cab}{conto}"

        exists = db_da_passare.query(Conto).filter_by(iban=iban).first()
        if not exists:
            return iban


def crea_nuovo_conto_utente(db_da_passare, utente_da_passare):
  ''' #idea di bonus al primo conto aperto
    saldo_iniziale = Decimal("0.00")
    if len(utente_da_passare.conti) == 0:
        saldo_iniziale = Decimal("100.00")

    while True:
        try:
            nuovo_conto = Conto(
                iban = genera_iban(db_da_passare),
                saldo = saldo_iniziale,
                utente = utente_da_passare
            )
            db_da_passare.add(nuovo_conto)
            return nuovo_conto
        
        except IntegrityError:
            db_da_passare.rollback()
            continue'''