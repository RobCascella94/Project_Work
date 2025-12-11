import random
import bcrypt, re
from sqlalchemy import Boolean, Column, DateTime, Numeric, Integer, String, ForeignKey, func
from sqlalchemy.orm import relationship, validates
from enum import Enum as PyEnum
from sqlalchemy import Enum as SqlEnum
from database import Base
from decimal import ROUND_HALF_UP, Decimal

class Utente(Base):
    __tablename__ = 'utenti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    codice_fiscale = Column(String, nullable=False)
    codice_titolare = Column(String, nullable=False, unique=True)
    pin_hash = Column(String, nullable=False)

    #chiave esterna
    lavoro_id = Column(Integer, ForeignKey('lavori.id'), nullable=True)

    #relazioni
    lavoro = relationship("Lavoro", back_populates="utenti") 
    conti = relationship("Conto", back_populates="utente", cascade="all, delete-orphan") 

    def __init__(self, nome, cognome, codice_fiscale, lavoro_id, session):
        self.nome = nome
        self.cognome = cognome
        self.codice_fiscale = codice_fiscale
        self.codice_titolare = self.genera_codice_titolare(session)
        self.lavoro_id = lavoro_id
        
    def genera_codice_titolare(self, session):
        while True:
            print(f"[OK] sono in genera codice")
            numero = random.randint(1, 999999)
            codice = f"CT{numero:06d}"
            print(f"[OK] sono in genera codice: {codice}")

            if not session.query(Utente).filter_by(codice_titolare=codice).first():
                return codice             

    def crea_pin(self, pin):
        if len(pin)<6: 
            raise ValueError("Il PIN deve essere di almeno 6 cifre.")
       
        if re.search(r"(\d)\1\1", pin): 
            raise ValueError("Il PIN da lei inserito contiene una cifra ripetuta tre volte di seguito.")
        
        pin_bytes = pin.encode('utf-8') 
        salt = bcrypt.gensalt()         
        pin_hash_bytes = bcrypt.hashpw(pin_bytes, salt)
        self.pin_hash = pin_hash_bytes.decode('utf-8')               
       

    def verifica_pin(self, pin_inserito):
        if not pin_inserito:
            raise ValueError("PIN vuoto: impossibile verificare.")
        
        pin_bytes = pin_inserito.encode('utf-8') #Ricontrolla automaticamente con lo stesso salt e serve per il main che controlla sia la stessa password e dovrebbe ritornare true se matchano
        db_hash_bytes = self.pin_hash.encode('utf-8')
        return bcrypt.checkpw(pin_bytes, db_hash_bytes)


class Lavoro(Base):
    __tablename__ = "lavori"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_lavoro = Column(String, nullable=False, unique=True)
    stipendio_mensile = Column(Numeric(10,2), nullable=False)

    #relazione
    utenti = relationship("Utente", back_populates="lavoro") #un lavoro può essere svolto da più utenti


class Conto(Base):
    __tablename__ = 'conti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    iban = Column(String, nullable=False, unique=True)
    data_creazione = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    #chiavi esterne
    utente_id = Column(Integer, ForeignKey('utenti.id'), nullable=False)

    #relazioni
    utente = relationship("Utente", back_populates="conti") #più conti possono appartenere ad un utente
    transazioni_effettuate = relationship("Transazione", foreign_keys="Transazione.conto_mittente_id", back_populates="conto_mittente")
    transazioni_ricevute = relationship("Transazione", foreign_keys="Transazione.conto_destinatario_id", back_populates="conto_destinatario")

    def __init__(self, utente_id, session):
        self.iban = self.genera_iban(session)
        self.utente_id = utente_id

    def genera_iban(self, session):
        #semplici codici banca e filiale fissi per semplicità 
        abi = "123"     #codice banca
        cab = "456"     #codice filiale

        while True:
            numero = random.randint(1, 999999)
            conto = f"{numero:06d}"
            iban = f"IT{abi}{cab}{conto}"

            if not session.query(Conto).filter_by(iban=iban).first():
                return iban


    @property #in questo modo posso usarlo come attributo
    def saldo_corrente(self):
        entrate = sum(t.importo for t in self.transazioni_ricevute)
        uscite = sum(t.importo for t in self.transazioni_effettuate)
        return entrate - uscite
    
    def verifica_importo(self,importo):
        importo = Decimal(importo)
        if importo <= 0:
            raise ValueError("L'importo non valido.")
        
    def verifica_saldo(self, importo):
        self.verifica_importo(importo)
        if self.saldo_corrente < importo:
            raise ValueError("Saldo insufficiente.")   

    def bonifico(self, destinazione, importo, descrizione):
        self.verifica_saldo(importo)

        trans = Transazione(
            importo=importo,
            tipo=TipoTransazione.BONIFICO,
            conto_mittente=self,
            conto_destinatario=destinazione,
            descrizione=descrizione,
        )

        return trans

    def prelievo(self, importo, descrizione="Prelievo da ATM"):
        self.verifica_saldo(importo)

        trans = Transazione(
            importo=importo,
            tipo=TipoTransazione.PRELIEVO,
            conto_mittente=self,
            conto_destinatario=None,
            descrizione=descrizione
        )

        return trans

    def deposito(self, importo, descrizione="Deposito da ATM"):
        self.verifica_importo(importo)
        
        trans = Transazione(
            importo=importo,
            tipo=TipoTransazione.DEPOSITO,
            conto_mittente=None,
            conto_destinatario=self,
            descrizione=descrizione
        )
        return trans
    
    def pagamento(self, esercente, importo, descrizione):
        self.verifica_saldo(importo)

        trans = Transazione(
            importo=importo,
            tipo=TipoTransazione.PAGAMENTO,
            conto_mittente=self,
            conto_destinatario=esercente,
            descrizione=descrizione
        )
        return trans


class TipoTransazione(PyEnum):
    BONIFICO = "Bonifico"  #richiede mittente e destinatario
    DEPOSITO = "Deposito"  #solo destinatario. da atm
    PRELIEVO = "Prelievo"  #solo mittente. da atm
    PAGAMENTO = "Pagamento" #come bonifico ma a un esercente
    BONUS = "Bonus"     #solo destinatario, da parte della banca


class Transazione(Base):
    __tablename__ = 'transazioni'
    id = Column(Integer, primary_key=True, autoincrement=True)
    importo = Column(Numeric(10,2), nullable=False)
    data = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    descrizione = Column(String, nullable=True)
    tipo = Column(SqlEnum(TipoTransazione, name="tipo_transazione"), nullable=False)

    #chiave esterna
    conto_mittente_id = Column(Integer, ForeignKey('conti.id'), nullable=True)
    conto_destinatario_id = Column(Integer, ForeignKey('conti.id'), nullable=True)

    #relazioni
    conto_mittente = relationship("Conto", foreign_keys=[conto_mittente_id], back_populates="transazioni_effettuate")
    conto_destinatario = relationship("Conto", foreign_keys=[conto_destinatario_id], back_populates="transazioni_ricevute")


    
