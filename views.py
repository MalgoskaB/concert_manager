#!/usr/bin/env python
# encoding: utf-8
from main import app, db, loginManager
from models import User, Ticket, Concert
from flask import render_template, request, session, abort, url_for, redirect
from flask_login import login_user, login_required, logout_user, current_user
from functools import wraps
import re


# stworzenie roli do sprawdzania autoryzacji
# ze strony http://flask.pocoo.org/snippets/98/
def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.usertype not in roles:
                return "Nie masz autoryzacji do podglądu tej strony"
            return f(*args, **kwargs)
        return wrapped
    return wrapper



@loginManager.user_loader
def load_user(user_id):
    loaded_user = User.query.filter_by(id=user_id).first()
    if type(loaded_user) is str:
        return None
    else:
        return loaded_user


@app.route('/', methods=['GET', 'POST'])
def info():
    shows = Concert.query.all()
    shows.sort(key=lambda x: x.id, reverse=True)
    return render_template('info.html', session=session, shows = shows)

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/login-confirm', methods=['POST'])
def login_confirm():
    message = ""
    email = request.form['email']
    password = request.form['password']
    existing_user = User.query.filter_by(email=email).first()

    if not existing_user:
        message += "Nie ma takiego użytkownika w bazie. "
    else:
        if not existing_user.check_password(password):
            message += "Podano niepoprawne hasło. "
        else:
            # tutaj trzeba już dokonać operacji logowania
            db.session.commit()
            login_user(existing_user)
            return redirect("/")

    return render_template("login-failed.html", message=message)


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return render_template('logout.html')


#strona do dodawania koncertow - tylko dla zalogowanych organizatorów
@app.route("/concerts-add", methods=['GET', 'POST'])
@login_required
@requires_roles("admin", "organizer")
def concerts_add():
    if request.method == 'POST':
        band = request.form['band']
        name = request.form['name']
        opis = request.form['opis']
        gatunek = request.form['gatunek']
        price_plyta_ticket = int(request.form['price_plyta_ticket'])
        price_trybuny_ticket = int(request.form['price_trybuny_ticket'])
        price_gc_ticket = int(request.form['price_gc_ticket'])
        price_vip_ticket = int(request.form['price_vip_ticket'])
        nr_plyta_ticket = int(request.form['nr_plyta_ticket'])
        nr_trybuny_ticket = int(request.form['nr_trybuny_ticket'])
        nr_gc_ticket = int(request.form['nr_gc_ticket'])
        nr_vip_ticket = int(request.form['nr_vip_ticket'])
        data = request.form['data']
        venue = request.form['venue']

        new_concert = Concert()
        new_concert.band = band
        new_concert.opis = opis
        new_concert.name = name
        new_concert.gatunek = gatunek
        new_concert.price_plyta_ticket = price_plyta_ticket
        new_concert.price_trybuny_ticket = price_trybuny_ticket
        new_concert.price_gc_ticket = price_gc_ticket
        new_concert.price_vip_ticket = price_vip_ticket
        new_concert.nr_plyta_ticket = nr_plyta_ticket
        new_concert.nr_trybuny_ticket = nr_trybuny_ticket
        new_concert.nr_gc_ticket = nr_gc_ticket
        new_concert.nr_vip_ticket = nr_vip_ticket
        new_concert.data = data
        new_concert.venue = venue

        db.session.add(new_concert)
        db.session.commit()

        # db.session.delete(new_concert)
        # db.session.commit()
        return render_template('dodano_koncert.html')

    return render_template('concert_add_remove.html', naglowek='Dodaj nowe wydarzenie')

#strona do usuwania koncertow - tylko dla admina
@app.route("/concerts-delete/<int:id>", methods=['GET', 'POST'])
@login_required
@requires_roles("admin")
def concerts_delete(id):
    koncert = db.session.query(Concert).get(id)
    db.session.delete(koncert)
    db.session.commit()
    return render_template("concert-delete.html", id = id)


#strona do kupowania biletow - tylko dla zalogowanych
@app.route('/buy_ticket', methods=['GET','POST'])
@login_required
def buy_ticket():
    show_id = request.args.get('id')
    koncert = Concert.query.get(show_id)
    bilet = Ticket.query.filter_by(show_id=show_id).all()
    plyta, trybuny, gc, vip = 0,0,0,0
    for i in bilet:
        plyta += i.nr_plyta_ticket
        trybuny += i.nr_trybuny_ticket
        gc += i.nr_gc_ticket
        vip += i.nr_vip_ticket
    plyta2 = koncert.nr_plyta_ticket - plyta
    trybuny2 = koncert.nr_trybuny_ticket - trybuny
    gc2 = koncert.nr_gc_ticket - gc
    vip2 = koncert.nr_vip_ticket - vip
    return render_template("buy_ticket.html", koncert = koncert, show_id = show_id, bilet = bilet, plyta2= plyta2,
                           trybuny2 = trybuny2, gc2 = gc2, vip2 = vip2)


#potwierdzenie po zaznaczeniu biletow do kupienia
@app.route('/buy_ticket/confirm', methods=['GET', 'POST'])
@login_required
def confirm():
    show_id = request.args.get('id')
    koncert = Concert.query.get(show_id)
    l_plyta = int(request.form["l_plyta"])
    l_trybuny = int(request.form["l_trybuny"])
    l_gc = int(request.form["l_gc"])
    l_vip = int(request.form["l_vip"])
    suma = l_plyta + l_trybuny + l_gc + l_vip
    kwota =(l_plyta * koncert.price_plyta_ticket) + (l_trybuny * koncert.price_trybuny_ticket) \
           + (l_gc * koncert.price_gc_ticket) + (l_vip * koncert.price_vip_ticket)
    new_ticket = Ticket()
    new_ticket.user_login = current_user.username
    new_ticket.nr_plyta_ticket = l_plyta
    new_ticket.price_plyta_ticket = l_plyta * koncert.price_plyta_ticket
    new_ticket.nr_trybuny_ticket = l_trybuny
    new_ticket.price_trybuny_ticket = l_trybuny * koncert.price_trybuny_ticket
    new_ticket.nr_gc_ticket = l_gc
    new_ticket.price_gc_ticket = l_gc * koncert.price_gc_ticket
    new_ticket.nr_vip_ticket = l_vip
    new_ticket.price_vip_ticket = l_vip * koncert.price_vip_ticket
    new_ticket.show_id = show_id
    new_ticket.band = koncert.band
    db.session.add(new_ticket)
    db.session.commit()
    return render_template("confirm.html", suma = suma, koncert = koncert, kwota = kwota, show_id = show_id)


#strona ze szczegółami konkretnego biletu, tylko dla zalogowanych
#strona ma być widoczna tylko jeśli zalogowana osoba to ta która kupiła bilet
@app.route('/ticket', methods=['GET','POST'])
@login_required
def ticket():
    ticket_id = request.args.get('id')
    ticket = Ticket.query.get(ticket_id)
    return render_template("ticket.html", ticket = ticket, ticket_id = ticket_id)


# tu są informacje o wszystkich zakupionych biletach, tylko dla zalogowanych
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_login = current_user.username
    ticket = Ticket.query.filter_by(user_login=user_login).order_by(Ticket.ticket_id.desc())
    return render_template("buy_dashboard.html", ticket = ticket)


@app.route('/show/<int:id>', methods=['GET', 'POST'])
def show(id):
    koncert = Concert.query.get(id)
    return render_template('koncert.html', id = id, koncert = koncert)


@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')


@app.route('/register-confirm', methods=['POST'])
def register_confirm():

    is_okay_to_register = True
    is_email_okay = True
    message = ""

    username = request.form["username"]
    email = request.form["email"]
    password1 = request.form["password1"]
    password2 = request.form["password2"]
    usertype = request.form["usertype"]
    about = request.form["about"]

    # Walidacja nazwy użytkownika ------------------------------------------
    if len(username) > 20:
        is_okay_to_register = False
        message += "Podana nazwa użytkownika jest zbyt długa. "
    # ----------------------------------------------------------------------

    # Walidacja adresu e-mail ----------------------------------------------
    if re.match("^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@+[a-z.0-9_]*[a-z.0-9_]\.[a-z]{2,4}$", email) is None:
        message += "Podano błędny adres e-mail. "
        is_okay_to_register = False
        is_email_okay = False
    elif len(email) > 30:
        message += "Podany adres e-mail jest zbyt długi. "
        is_okay_to_register = False
        is_email_okay = False
    # ----------------------------------------------------------------------

    # Walidacja hasła ------------------------------------------------------
    if password1 != password2:
        message += "Podane hasła różnią się. "
        is_okay_to_register = False
    elif len(password1) > 20 or len(password2) > 20:
        message += "Podane hasło jest zbyt długie. "
        is_okay_to_register = False
    # ----------------------------------------------------------------------

    # Sprawdzanie, czy przypadkiem nie istnieje już użytkownik o takim username i email w bazie
    if is_email_okay:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            message += "Istnieje użytkownik o podanym adresie e-mail! Adres e-mail zajęty. "
            is_okay_to_register = False

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            message += "Istnieje użytkownik o podanej nazwie użytkownika! Nazwa użytkownika zajęta. "
            is_okay_to_register = False
    # -----------------------------------------------------------------------------------------

    # Walidacja tekstu 'o mnie' --------------------------------------------
    if len(about) > 200:
        is_okay_to_register = False
        message += "Napisałeś za dużo o sobie. Max 200 znaków. "
    # ----------------------------------------------------------------------

    # Po przejściu powyższych warunków można się zarejestrować: -------------------------------
    if is_okay_to_register:
        new_user = User()
        new_user.username = username
        new_user.email = email
        new_user.set_password(password1)
        new_user.usertype = usertype
        new_user.about = about
        db.session.add(new_user)
        db.session.commit()
        message = "Zarejestrowałeś się. Możesz się zalogować. "
    # -----------------------------------------------------------------------------------------

    return render_template("register-confirm.html", message=message)


