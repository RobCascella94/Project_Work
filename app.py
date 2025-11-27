import traceback
from flask import Flask, redirect, render_template, request, url_for, session, flash
from models import Utente, Lavoro, Conto, Transazione
from servizi_banca import crea_transazione, crea_deposito, crea_prelievo, crea_pagamento, crea_bonifico, esegui_transazione_su_conti, genera_iban, crea_nuovo_conto_utente
from database import Base, engine, SessionLocal
from functools import wraps
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from decimal import Decimal


app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

Base.metadata.create_all(bind=engine)




@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html') 
    
    codice_titolare_inserito = request.form.get("codice_titolare")
    pin_inserito = request.form.get("pin")
    # Controllo campi vuoti
    if not codice_titolare_inserito or not pin_inserito:
        flash("Inserisci sia il codice titolare che il PIN.", "error")
        return redirect(url_for("login"))

    db = SessionLocal()
    try:
        utente = db.query(Utente).filter(Utente.codice_titolare == codice_titolare_inserito).first()

        if utente and utente.verifica_pin(pin_inserito):
            session["utente_id"] = utente.id
            flash(f"Benvenuto {utente.nome}!", "success")
            return redirect(url_for("pagina_privata"))
        else:
            flash("Codice titolare o PIN errato. Riprova!", "error")
            return redirect(url_for("login"))
    finally:
        db.close()



@app.route('/registrazione', methods=['GET','POST'])
def registrazione():
    db = SessionLocal()
    if request.method == 'GET':
        lavori_db=db.query(Lavoro).all()
        return render_template('registrazione.html', lavori=lavori_db)
    
    nome_inserito = request.form.get('nome') 
    cognome_inserito = request.form.get('cognome') 
    codice_fiscale_inserito = request.form.get('codice_fiscale')
    lavoro_inserito = request.form.get('lavoro') 
    pin1_inserito = request.form.get('pin1')
    pin2_inserito = request.form.get('pin2')

    #controllo campi vuoti
    if not nome_inserito or not cognome_inserito or not codice_fiscale_inserito or not lavoro_inserito or not pin1_inserito or not pin2_inserito:
        flash ("Tutti i campi sono obbligatori. Riprova!", "error")
        return redirect(url_for('registrazione'))
    
    #controllo pin
    if pin1_inserito != pin2_inserito:
        flash ("I pin non corrispondono. Riprova!", "error")
        return redirect(url_for('registrazione'))
    
    try:
        nuovo_utente = Utente(
            nome = nome_inserito,
            cognome = cognome_inserito,
            codice_fiscale = codice_fiscale_inserito,
            lavoro_id = lavoro_inserito
        )
        nuovo_utente.crea_pin(pin1_inserito)
        db.add(nuovo_utente)
        db.flush()

        crea_nuovo_conto_utente(db, nuovo_utente)
        db.commit()
        flash(f"Registrazione avvenuta con successo! Il suo codice titolare è {nuovo_utente.codice_titolare}. Usalo per effettuare il login.", "success")
        return redirect(url_for('login'))
    
    except ValueError as e:
        db.rollback()
        flash(str(e), "error")
        return redirect(url_for('registrazione'))
    
    except IntegrityError:
        db.rollback()
        flash("Errore interno durante la generazione dei codici. Riprovare.", "error")
        return redirect(url_for('registrazione'))

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        flash("Errore durante la registrazione. Riprovare.", "error")
        return redirect(url_for('registrazione'))
    
    finally:
        db.close()




#@app.route('/effettua_bonifico', methods=['GET','POST'])
##def effettua_bonifico():





def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "utente_id" not in session:
            flash("Devi effettuare il login prima!", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper



@app.route('/pagina_privata')
@login_required  #Ogni volta che un utente prova ad accedere a /pagina_privata, prima di eseguire il codice di pagina_privata() viene eseguito login_required(). se autentificato continua altrimenti no
def pagina_privata():
    db = SessionLocal()
    try:
        utente_id = session.get("utente_id")
        utente = db.execute(select(Utente).options(
            joinedload(Utente.lavoro),
            joinedload(Utente.conti).joinedload(Conto.transazioni_effettuate),
            joinedload(Utente.conti).joinedload(Conto.transazioni_ricevute)
            ).where(Utente.id == utente_id)).unique().scalar_one_or_none()

        if not utente:
            flash("Utente non trovato, effettua il login.", "error")
            return redirect(url_for('login'))

        # Raccogli tutte le transazioni dei conti (sia effettuate che ricevute)
        transazioni = []
        for conto in utente.conti:
            movimenti = list(conto.transazioni_effettuate) + list(conto.transazioni_ricevute)
            for t in movimenti:
                transazioni.append({
                    "id": t.id,
                    "data": t.data,
                    "importo": t.importo,
                    "iban": conto.iban,
                    "descrizione": t.descrizione,
                    "tipo": t.tipo.value
                })

        # Ordinate per data DESC
        transazioni.sort(key=lambda x: x["data"], reverse=True)

        return render_template("pagina_privata.html", utente=utente, transazioni=transazioni)


    except Exception as e:
        print(f"❌ Errore in /pagina_privata: {e}")
        flash("Errore durante il caricamento della pagina privata.", "error")
        return redirect(url_for('login'))

    finally:
        db.close()




@app.post('/logout')
def logout():
    session.clear()
    flash("Logout effettuato con successo.", "success")
    return redirect(url_for('home'))

@app.post("/logout_auto") #logout automantico quando si chiude il browser
def logout_auto():
    session.clear()
    return ("", 204)




