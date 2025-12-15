import re
import traceback
from flask import Flask, jsonify, redirect, render_template, request, url_for, session, flash
from models import TipoTransazione, Utente, Lavoro, Conto, Transazione
from database import Base, engine, SessionLocal
from functools import wraps
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from datetime import datetime, timedelta
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)
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
    
    #controllo se esiste già un utente con quel codice fiscale
    utente_esistente = db.query(Utente).filter_by(codice_fiscale=codice_fiscale_inserito).first() 
    if utente_esistente:
        flash("Esiste già un utente con questo codice fiscale. Effettua il login per aprire un nuovo conto.", "error")
        return redirect(url_for('login'))
    
    try:
        nuovo_utente = Utente(
            nome_inserito,
            cognome_inserito,
            codice_fiscale_inserito,
            lavoro_inserito,
            db
        )
        nuovo_utente.crea_pin(pin1_inserito)
        db.add(nuovo_utente)
        db.flush()
        #creazione conto associato al nuovo utente
        nuovo_conto = Conto(
            nuovo_utente.id,
            db
        )
        db.add(nuovo_conto)
        db.flush()

        #bonus nuovo conto con saldo a 100€
        trans =Transazione(
            importo=Decimal("100.00"),
            descrizione="Bonus benvenuto nuovo conto",
            tipo=TipoTransazione.BONUS,
            conto_destinatario_id=nuovo_conto.id
        )
        db.add(trans)
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
        flash("Errore durante la registrazione. Riprovare.", "error")
        return redirect(url_for('registrazione'))
    
    finally:
        db.close()



def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "utente_id" not in session:
            flash("Devi effettuare il login prima!", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route('/pagina_privata', methods=['GET','POST'])
@login_required
def pagina_privata():
    db = SessionLocal()
    try:
        utente_id = session.get("utente_id")
        if not utente_id:
            flash("Sessione scaduta. Effettua nuovamente il login.", "error")
            return redirect(url_for('login'))

        utente = db.query(Utente).options(joinedload(Utente.conti)).filter_by(id=utente_id).first()
        if not utente:
            flash("Utente non trovato.", "error")
            return redirect(url_for('login'))

        conti = utente.conti
        conto_id_menu = request.form.get("conto_id", type=int) or request.args.get("conto_id", type=int)
         # Se l'utente ha selezionato un conto dal menu 
        if conto_id_menu:
            session["conto_selezionato"] = conto_id_menu 
            conto_selezionato = next((c for c in conti if c.id == conto_id_menu), None)
            if conto_selezionato is None: 
                flash("Conto non valido.", "error") 
                return redirect(url_for('pagina_privata')) 
        else:
            # Se è il primo ingresso e non esiste in sessione allora usa primo conto
            conto_selezionato = conti[0] 
            session["conto_selezionato"] = conto_selezionato.id

        # Carica le transazioni solo dal conto selezionato 
        transazioni = (
            db.query(Transazione)
            .filter(
                (Transazione.conto_mittente_id == conto_selezionato.id) |
                (Transazione.conto_destinatario_id == conto_selezionato.id)
            )
            .order_by(Transazione.data.desc())
            .all()
        )

        return render_template(
            "pagina_privata.html",
            utente=utente,
            conti=conti,
            conto_selezionato=conto_selezionato,
            transazioni=transazioni
        )

    except Exception as e:
        print(f"❌ ERRORE /pagina_privata: {e}")
        flash("Errore durante il caricamento della pagina.", "error")
        return redirect(url_for('login'))

    finally:
        db.close()


@app.route("/effettua_bonifico", methods=["GET", "POST"])
@login_required
def effettua_bonifico():
    db = SessionLocal()
    if request.method == "GET":
        return render_template("effettua_bonifico.html")
    
    try:
        utente_id = session.get("utente_id")
        conto_id = session.get("conto_selezionato")
        importo_inserito = Decimal(request.form["importo"])
        iban_destinatario = request.form["iban"].strip() #rimuove gli eventuali spazi
        descrizione_inserita = request.form.get("descrizione", "")

        conto_mittente = db.query(Conto).filter_by(
            id=conto_id,
            utente_id=utente_id
        ).first()

        if not conto_mittente:
            flash("Nessun conto disponibile.", "error")
            return redirect(url_for("pagina_privata"))

        # Trova destinatario
        conto_destinatario = db.query(Conto).filter_by(iban=iban_destinatario).first()
        if not conto_destinatario:
            flash("IBAN destinatario non valido.", "error")
            return redirect(url_for("effettua_bonifico"))

        # Crea transazione
        trans=conto_mittente.bonifico(
            conto_destinatario,
            importo_inserito,
            descrizione_inserita
        )
        db.add(trans)
        db.commit()
        flash("Bonifico effettuato con successo!", "success")
        return redirect(url_for("pagina_privata"))
    except Exception as e:
        print("ERRORE BONIFICO:", e)
        flash("Errore durante il bonifico.", "error")
        return redirect(url_for("effettua_bonifico"))
    finally:
        db.close()





@app.route("/apri_nuovo_conto", methods=["GET", "POST"])
@login_required
def apri_nuovo_conto():
    db = SessionLocal()
    try:
        utente_id = session.get("utente_id")
        utente = db.query(Utente).filter_by(id=utente_id).first()
        if request.method == "POST":
            pin = request.form.get("pin")
            # Verifica PIN
            if not utente.verifica_pin(pin):
                flash("PIN errato.", "error")
                return redirect(url_for("apri_nuovo_conto"))
            # Limite temporale — max 1 conto ogni 24 ore
            ultimo_conto = (
                db.query(Conto)
                .filter_by(utente_id=utente.id)
                .order_by(Conto.data_creazione.desc())
                .first()
            )
            if ultimo_conto:
                limite = ultimo_conto.data_creazione + timedelta(hours=24)
                if datetime.now(ultimo_conto.data_creazione.tzinfo) < limite:
                    flash("Puoi aprire un nuovo conto solo dopo 24 ore dall'ultima creazione conto.", "error")
                    return redirect(url_for("pagina_privata"))

            # CREA NUOVO CONTO
            nuovo = Conto(utente.id, db)
            db.add(nuovo)
            db.commit()
            flash("Nuovo conto aperto con successo!", "success")
            return redirect(url_for("pagina_privata"))

        return render_template("apri_nuovo_conto.html", utente=utente)

    finally:
        db.close()



@app.route("/modifica_profilo", methods=["GET", "POST"])
@login_required
def modifica_profilo():
    db = SessionLocal() 
    utente_id = session.get("utente_id")
    utente = db.query(Utente).filter_by(id=utente_id).first()

    if request.method == "POST":
        vecchio_pin_inserito = request.form["vecchio_pin"]
        nuovo_pin_inserito = request.form["nuovo_pin"]
        conferma_pin_inserito = request.form["conferma_pin"]

        # verifica campi vuoti
        if not vecchio_pin_inserito or not nuovo_pin_inserito or not conferma_pin_inserito:
            flash("Tutti i campi sono obbligatori.", "error")
            return redirect(url_for("modifica_profilo"))

        # verifica pin attuale
        if not utente.verifica_pin(vecchio_pin_inserito):
            flash("Il PIN attuale non è corretto.", "error")
            return redirect(url_for("modifica_profilo"))
        
        # verifica nuovi pin se ci sono ripetizioni dei numeri    
        if re.search(r"(\d)\1\1", nuovo_pin_inserito) or re.search(r"(\d)\1\1", conferma_pin_inserito):
            flash("Il nuovo PIN non può contenere una cifra ripetuta tre volte di seguito.", "error")
            return redirect(url_for("modifica_profilo"))
        
        # verifica nuovo pin diverso da attuale
        if vecchio_pin_inserito == nuovo_pin_inserito:
            flash("Il nuovo PIN deve essere diverso da quello attuale.", "error")
            return redirect(url_for("modifica_profilo"))
        
        # verifica corrispondenza nuovo pin
        if nuovo_pin_inserito != conferma_pin_inserito:
            flash("I PIN inseriti non coincidono.", "error")
            return redirect(url_for("modifica_profilo"))

        try:
            utente.crea_pin(nuovo_pin_inserito)
            db.commit()
            flash("Il PIN è stato aggiornato con successo. Effettua di nuovo il login.", "success")

            # LOGOUT AUTOMATICO
            session.clear()
            return redirect(url_for("login"))

        except ValueError as e:
            db.rollback()
            flash(str(e), "danger")
            return redirect(url_for("modifica_profilo"))
        except Exception:
            db.rollback()
            flash("Errore durante l'aggiornamento del PIN.", "danger")
            return redirect(url_for("modifica_profilo"))

    return render_template("modifica_profilo.html")

@app.route("/effettua_pagamento", methods=["GET", "POST"])
@login_required
def effettua_pagamento():
    db = SessionLocal()
    if request.method == "GET":
        return render_template("effettua_pagamento.html")
    
    try:
        utente_id = session.get("utente_id")
        conto_id = session.get("conto_selezionato")
        importo_inserito = Decimal(request.form["importo"])
        descrizione_inserito = request.form.get("descrizione", "")
        
        conto_mittente = db.query(Conto).filter_by(id=conto_id, utente_id=utente_id).first()

        if not conto_mittente:
            flash("Conto non trovato o non accessibile.", "error")
            return redirect(url_for("pagina_privata"))

        # Creazione transazione pagamento
        trans = conto_mittente.pagamento(
            importo_inserito,
            descrizione_inserito
        )
        db.add(trans)
        db.commit()
        flash("Pagamento effettuato con successo!", "success")
        return redirect(url_for("pagina_privata"))

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        flash(f"Errore durante il pagamento: {str(e)}", "danger")
        return redirect(url_for("effettua_pagamento"))

    finally:
        db.close()
  

@app.route('/richiesta_prestito', methods=['GET', 'POST'])
@login_required
def richiesta_prestito():
    if request.method == 'GET':
        return render_template('richiesta_prestito.html')


@app.post('/logout')
def logout():
    session.clear() 
    flash("Logout effettuato con successo.", "success")
    return redirect(url_for('home'))


#---- Documentazione Swagger/Flasgger ----

@app.route('/api/login', methods=['POST'])
def api_login():
    """
    Login utente
    ---
    tags:
      - Utenti
    consumes:
      - application/json
    parameters:
      - in: body
        name: credenziali
        required: true
        schema:
          type: object
          required:
            - codice_titolare
            - pin
          properties:
            codice_titolare:
              type: string
              example: CT804494
            pin:
              type: string
              example: "123456"
    responses:
      200:
        description: Login riuscito
        schema:
          type: object
          properties:
            message:
              type: string
              example: Login OK
      401:
        description: Credenziali non valide
        schema:
          type: object
          properties:
            error:
              type: string
              example: Credenziali non valide
    """
    data = request.get_json(silent=True) or {}
    db = SessionLocal()

    try:
        utente = db.query(Utente).filter(
            Utente.codice_titolare == data.get("codice_titolare")
        ).first()

        if utente and utente.verifica_pin(data.get("pin")):
            return jsonify({"message": "Login OK"}), 200

        return jsonify({"error": "Credenziali non valide"}), 401

    finally:
        db.close()


@app.route('/api/registrazione', methods=['POST'])
def api_registrazione():
    """
    Registrazione di un nuovo utente
    ---
    tags:
      - Utenti
    consumes:
      - application/json
    parameters:
      - in: body
        name: dati_utente
        required: true
        schema:
          type: object
          required:
            - nome
            - cognome
            - codice_fiscale
            - lavoro
            - pin1
            - pin2
          properties:
            nome:
              type: string
              example: Mario
            cognome:
              type: string
              example: Rossi
            codice_fiscale:
              type: string
              example: RSSMRA80A01H501U
            lavoro:
              type: string
              example: Impiegato
            pin1:
              type: string
              example: "123456"
            pin2:
              type: string
              example: "123456"
    responses:
      201:
        description: Registrazione completata con successo
        schema:
          type: object
          properties:
            message:
              type: string
              example: Registrazione completata
            codice_titolare:
              type: string
              example: CT804494
      400:
        description: Dati non validi o errore di registrazione
    """
    data = request.get_json(silent=True) or {}
    db = SessionLocal()

    try:
        nome = data.get("nome")
        cognome = data.get("cognome")
        codice_fiscale = data.get("codice_fiscale")
        lavoro = data.get("lavoro")
        pin1 = data.get("pin1")
        pin2 = data.get("pin2")

        # --- Controllo campi ---
        if not all([nome, cognome, codice_fiscale, lavoro, pin1, pin2]):
            return jsonify({"error": "Tutti i campi sono obbligatori"}), 400

        if pin1 != pin2:
            return jsonify({"error": "I PIN non coincidono"}), 400

        # --- Verifica utente esistente ---
        if db.query(Utente).filter_by(codice_fiscale=codice_fiscale).first():
            return jsonify({"error": "Utente già registrato"}), 400

        # --- Creazione utente ---
        nuovo_utente = Utente(
            nome,
            cognome,
            codice_fiscale,
            lavoro,
            db
        )
        nuovo_utente.crea_pin(pin1)
        db.add(nuovo_utente)
        db.flush()  # assegna ID e codice_titolare

        # --- Creazione conto ---
        nuovo_conto = Conto(nuovo_utente.id, db)
        db.add(nuovo_conto)
        db.flush()

        # --- Bonus di benvenuto ---
        trans = Transazione(
            importo=Decimal("100.00"),
            descrizione="Bonus benvenuto nuovo conto",
            tipo=TipoTransazione.BONUS,
            conto_destinatario_id=nuovo_conto.id
        )
        db.add(trans)

        # Copia dati PRIMA del rollback
        response = {
            "message": "Registrazione completata",
            "codice_titolare": nuovo_utente.codice_titolare
        }

        # --- Simulazione: non persistiamo realmente ---
        db.rollback()

        return jsonify(response), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        db.close()




@app.route('/api/conti/<int:conto_id>/saldo', methods=['GET'])
def api_saldo(conto_id):
    """
    Recupera il saldo corrente del conto
    ---
    tags:
      - Conti
    parameters:
      - in: path
        name: conto_id
        type: integer
        required: true
        example: 3
      - in: query
        name: utente_id
        type: integer
        required: true
        description: ID utente (simulazione autenticazione API)
        example: 2
    responses:
      200:
        description: Saldo corrente del conto
        schema:
          type: object
          properties:
            iban:
              type: string
              example: IT123456000001
            saldo_corrente:
              type: number
              example: 150
      404:
        description: Conto non trovato
      400:
        description: Utente non specificato
    """
    db = SessionLocal()
    try:
        utente_id = request.args.get("utente_id", type=int)
        if not utente_id:
            return jsonify({"error": "Utente non specificato"}), 400

        conto = db.query(Conto).filter_by(
            id=conto_id,
            utente_id=utente_id
        ).first()

        if not conto:
            return jsonify({"error": "Conto non trovato"}), 404

        return jsonify({
            "iban": conto.iban,
            "saldo_corrente": float(conto.saldo_corrente)
        }), 200

    finally:
        db.close()





@app.route('/api/conti/<int:conto_id>/transazioni', methods=['GET'])
def api_transazioni(conto_id):
    """
    Recupera le transazioni di un conto
    ---
    tags:
      - Conti
    parameters:
      - in: path
        name: conto_id
        type: integer
        required: true
        description: ID del conto
        example: 3
      - in: query
        name: utente_id
        type: integer
        required: true
        description: ID utente (simulazione autenticazione API)
        example: 2
    responses:
      200:
        description: Lista delle transazioni
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 1
              importo:
                type: number
                example: 100.50
              tipo:
                type: string
                example: Bonifico
              descrizione:
                type: string
                example: Pagamento fattura
              data:
                type: string
                example: "2025-12-15T13:30:00"
              conto_mittente_id:
                type: integer
                example: 1
              conto_destinatario_id:
                type: integer
                example: 2
      400:
        description: Utente non specificato
      404:
        description: Conto non trovato
    """
    db = SessionLocal()
    try:
        utente_id = request.args.get("utente_id", type=int)
        if not utente_id:
            return jsonify({"error": "Utente non specificato"}), 400

        conto = db.query(Conto).filter_by(
            id=conto_id,
            utente_id=utente_id
        ).first()

        if not conto:
            return jsonify({"error": "Conto non trovato"}), 404

        transazioni = (
            db.query(Transazione)
            .filter(
                (Transazione.conto_mittente_id == conto.id) |
                (Transazione.conto_destinatario_id == conto.id)
            )
            .order_by(Transazione.data.desc())
            .all()
        )

        return jsonify([
            {
                "id": t.id,
                "importo": float(t.importo),
                "tipo": t.tipo.value,
                "descrizione": t.descrizione,
                "data": t.data.isoformat(),
                "conto_mittente_id": t.conto_mittente_id,
                "conto_destinatario_id": t.conto_destinatario_id
            }
            for t in transazioni
        ]), 200

    finally:
        db.close()



@app.route('/api/conti/<int:conto_id>/bonifico', methods=['POST'])
def api_bonifico(conto_id):
    """
    Effettua un bonifico da un conto a un altro
    ---
    tags:
      - Transazioni
    consumes:
      - application/json
    parameters:
      - in: path
        name: conto_id
        type: integer
        required: true
        description: ID del conto mittente
        example: 1
      - in: body
        name: bonifico
        required: true
        schema:
          type: object
          required:
            - utente_id
            - iban_destinatario
            - importo
          properties:
            utente_id:
              type: integer
              example: 1
            iban_destinatario:
              type: string
              example: IT123456165276
            importo:
              type: number
              example: 50.00
            descrizione:
              type: string
              example: Regalo di compleanno
    responses:
      200:
        description: Bonifico effettuato con successo
        schema:
          type: object
          properties:
            message:
              type: string
              example: Bonifico effettuato con successo
            transazione_id:
              type: integer
              example: 10
            transazione_importo:
              type: number
              example: 50.00
            transazione_tipo:
              type: string
              example: Bonifico
            transazione_descrizione:
              type: string
              example: Regalo di compleanno
            transazione_data:
              type: string
              example: "2025-12-15T13:30:00"
            transazione_conto_mittente_id:
              type: integer
              example: 1
            transazione_conto_destinatario_id:
              type: integer
              example: 2
      400:
        description: Errore input o saldo insufficiente
      404:
        description: Conto mittente o destinatario non trovato
    """
    data = request.get_json()
    db = SessionLocal()

    try:
        # --- Validazione input ---
        utente_id = data.get("utente_id")
        iban_destinatario = data.get("iban_destinatario", "").strip()
        importo = data.get("importo")
        descrizione = data.get("descrizione", "")

        if not all([utente_id, iban_destinatario, importo]):
            return jsonify({"error": "Dati mancanti"}), 400

        # --- Conto mittente ---
        conto_mittente = db.query(Conto).filter_by(
            id=conto_id,
            utente_id=utente_id
        ).first()
        if not conto_mittente:
            return jsonify({"error": "Conto mittente non trovato"}), 404

        # --- Conto destinatario ---
        conto_destinatario = db.query(Conto).filter_by(
            iban=iban_destinatario
        ).first()
        if not conto_destinatario:
            return jsonify({"error": "IBAN destinatario non valido"}), 404

        # --- Creazione bonifico ---
        trans = conto_mittente.bonifico(
            conto_destinatario,
            Decimal(str(importo)),
            descrizione
        )

        db.add(trans)
        db.flush() 

        # --- Copia dati PRIMA del rollback ---
        response = {
            "message": "Bonifico effettuato con successo",
            "transazione_id": trans.id,
            "transazione_importo": float(trans.importo),
            "transazione_tipo": trans.tipo.value,
            "transazione_descrizione": trans.descrizione,
            "transazione_data": trans.data.isoformat(),
            "transazione_conto_mittente_id": trans.conto_mittente_id,
            "transazione_conto_destinatario_id": trans.conto_destinatario_id
        }

        # --- Simulazione: non persistiamo realmente ---
        db.rollback()

        return jsonify(response), 200

    except ValueError as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400

    except Exception:
        db.rollback()
        return jsonify({"error": "Errore durante il bonifico"}), 400

    finally:
        db.close()




