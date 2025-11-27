import random
import bcrypt, re
from sqlalchemy import Column, DateTime, Numeric, Integer, String, ForeignKey, func
from sqlalchemy.orm import relationship, validates
from enum import Enum as PyEnum
from sqlalchemy import Enum as SqlEnum
from database import Base
from decimal import Decimal

class Utente(Base):
    __tablename__ = 'utenti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    codice_fiscale = Column(String, nullable=False)
    codice_titolare = Column(String, nullable=False, unique=True)
    pin_hash = Column(String, nullable=False)

    lavoro_id = Column(Integer, ForeignKey('lavori.id'), nullable=True)
    lavoro = relationship("Lavoro", back_populates="utenti") 
    conti = relationship("Conto", back_populates="utente", cascade="all, delete-orphan") 

    def __init__(self, nome, cognome, codice_fiscale, lavoro_id):
        self.nome = nome
        self.cognome = cognome
        self.codice_fiscale = codice_fiscale
        self.codice_titolare = self.genera_codice_titolare()
        self.lavoro_id = lavoro_id
        
    def genera_codice_titolare(self):
        while True:
            numero = random.randint(1, 999999)
            codice = f"CT{numero:06d}"

            if not self.query.filter_by(codice_titolare=codice).first():
                self.codice_titolare = codice
                

    def crea_pin(self, pin):
        if len(pin)<6: 
            raise ValueError("Il PIN deve essere di almeno 6 cifre.")
       
        if re.search(r"(\d)\1\1", pin): 
            raise ValueError("Il PIN da lei inserito contiene una cifra ripetuta tre volte di seguito")
        
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

    utenti = relationship("Utente", back_populates="lavoro") #un lavoro può essere svolto da più utenti





class Conto(Base):
    __tablename__ = 'conti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    iban = Column(String, nullable=False, unique=True)
    saldo = Column(Numeric(10,2), nullable=False, default=Decimal("0.00"))

    #chiavi esterne
    utente_id = Column(Integer, ForeignKey('utenti.id'), nullable=False)

    #relazioni
    utente = relationship("Utente", back_populates="conti") #più conti possono appartenere ad un utente
    transazioni_effettuate = relationship("Transazione", foreign_keys="Transazione.conto_mittente_id", back_populates="conto_mittente")

    transazioni_ricevute = relationship("Transazione", foreign_keys="Transazione.conto_destinatario_id", back_populates="conto_destinatario")

    def applica_transazione(self, transazione: "Transazione"):
        importo = Decimal(transazione.importo)

        if importo <= 0:
            raise ValueError("L'importo deve essere positivo.")

        #il conto è il MITTENTE
        if transazione.conto_mittente_id == self.id:
            if self.saldo < importo:
                raise ValueError("Saldo insufficiente per eseguire la transazione.")
            self.saldo -= importo

        #il conto è il DESTINATARIO
        if transazione.conto_destinatario_id == self.id:
            self.saldo += importo





class TipoTransazione(PyEnum):
    BONIFICO = "bonifico"  #richiede mittente e destinatario
    DEPOSITO = "deposito"  #solo destinatario
    PRELIEVO = "prelievo"  #solo mittente
    PAGAMENTO = "pagamento" #come bonifico ma a un esercente

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

