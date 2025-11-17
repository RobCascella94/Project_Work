from flask import Flask, redirect, render_template, request, url_for, session, flash
from models import Utente, Lavoro, Conto, Transazione
from database import Base, engine, SessionLocal
from functools import wraps
from sqlalchemy.orm import joinedload


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
    if request.method == 'GET':
        return render_template('registrazione.html')
    else:
        #imprementazione registrazione
        return render_template('login.html')


@app.post('/logout')
def logout():
    session.clear()
    flash("Logout effettuato con successo.", "success")
    return redirect(url_for('home'))

@app.post("/logout_auto") #logout automantico quando si chiude il browser
def logout_auto():
    session.clear()
    return ("", 204)




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
        utente = db.query(Utente).options(
            joinedload(Utente.conti).joinedload(Conto.transazioni),
            joinedload(Utente.lavoro)
        ).get(session['utente_id'])

        if not utente:
            flash("Utente non trovato, effettua di nuovo il login.", "error")
            return redirect(url_for('login'))

        # raccogli tutte le transazioni dai conti dell’utente
        transazioni = []
        for conto in utente.conti:
            for t in conto.transazioni:
                transazioni.append({
                    'id': t.id,
                    'data': t.data,
                    'importo': t.importo,
                    'iban': conto.iban
                })

        # pagina HTML con i dati
        return render_template('pagina_privata.html', utente=utente, transazioni=transazioni)

    except Exception as e:
        print(f"❌ Errore in /pagina_privata: {e}")
        flash("Errore durante il caricamento della pagina privata.", "error")
        return redirect(url_for('login'))

    finally:
        db.close()






