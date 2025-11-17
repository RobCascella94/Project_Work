import bcrypt, re, random
from sqlalchemy import Column, Date, Double, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


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

    def crea_codice_titolare(self):
        prova_codice_titolare = 'CT' + str(random.randint(100000, 999999))
        return prova_codice_titolare

    def set_codice_titolare(self, codice_generato ):
        self.codice_titolare = codice_generato

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
        pin_bytes = pin_inserito.encode('utf-8') #Ricontrolla automaticamente con lo stesso salt e serve per il main che controlla sia la stessa password e dovrebbe ritornare true se matchano
        db_hash_bytes = self.pin_hash.encode('utf-8')
        return bcrypt.checkpw(pin_bytes, db_hash_bytes)



class Lavoro(Base):
    __tablename__ = "lavori"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_lavoro = Column(String, nullable=False, unique=True)
    stipendio_medio = Column(Double, nullable=False)

    utenti = relationship("Utente", back_populates="lavoro") #un lavoro può essere svolto da più utenti





class Conto(Base):
    __tablename__ = 'conti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    iban = Column(String, nullable=False, unique=True)

    #chiavi esterne
    utente_id = Column(Integer, ForeignKey('utenti.id'), nullable=False)

    #relazioni
    utente = relationship("Utente", back_populates="conti") #più conti possono appartenere ad un utente
    transazioni = relationship("Transazione", back_populates="conto", cascade="all, delete-orphan") #un conto può avere più transazioni


    def crea_iban(self):
        prova_iban = 'IT' + str(random.randint(100, 999)) + '00' +str(random.randint(100, 999))
        return prova_iban

    def set_iban(self, iban_generato ): #forse inutile
        self.iban = iban_generato


class Transazione(Base):
    __tablename__ = 'transazioni'
    id = Column(Integer, primary_key=True, autoincrement=True)
    importo = Column(Double, nullable=False)
    data = Column(Date, nullable=False)

    #chiave esterna
    conto_id = Column(Integer, ForeignKey('conti.id'), nullable=False)

    #relazioni
    conto = relationship("Conto", back_populates="transazioni") #più transazioni possono essere fatte da un conto