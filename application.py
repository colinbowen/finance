import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    name = "Netflix Inc."
    user_info = db.execute(
        "SELECT * from users WHERE id = :id", id=session["user_id"])
    user_portfolio = db.execute(
        "SELECT ticker, price, SUM(amount) FROM portfolio WHERE user = :id GROUP BY ticker HAVING SUM(amount) > 0", id=session["user_id"])
    symbol = db.execute(
        "SELECT ticker, SUM(amount) FROM portfolio WHERE user = :id GROUP BY ticker HAVING SUM(amount) > 0", id=session["user_id"])
    amount = db.execute(
        "SELECT amount FROM portfolio WHERE user = :id", id=session["user_id"])
    total_amount = db.execute(
        "SELECT SUM(amount) FROM portfolio WHERE user = :id", id=session["user_id"])
    total_amount = total_amount[0]['SUM(amount)']
    purchase_price = db.execute(
        "SELECT price FROM portfolio WHERE user = :id", id=session["user_id"])
    current_price = {}
    myset = list({v['ticker']: v for v in symbol}.values())
    for x in myset:
        current_price[x['ticker']] = lookup(x['ticker'])
    cash = user_info[0]["cash"]

    return render_template("dash.html", user_portfolio=user_portfolio, symbol=symbol, name=name, amount=amount, price=purchase_price, total=total_amount, cash=cash, current_price=current_price)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # display form - get stock, number of shares
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Enter correct ticker")
        else:
            ticker = request.form.get("symbol")
        if not request.form.get("amount"):
            return apology("Must purchase an amount of stock.")
        else:
            amount = int(request.form.get("amount"))

        if amount < 1:
            return apology("Must purchase an amount of stock greater than 0.")
        checkLookup = lookup(ticker)
        if not checkLookup:
            return apology("Invalid Symbol")
        price = lookup(ticker)
        price = price['price']
        # - can the user afford the stock
        # Query database for username
        cash = db.execute(
            "SELECT cash from users WHERE id = :id", id=session["user_id"])
        available_cash = cash[0]["cash"]
        total_price = amount * price
        # if not return apology
        if total_price > available_cash:
            return apology("Cannot afford stock. :(")

        date = str(datetime.datetime.now())

        # - buy the stock
        db.execute("INSERT INTO portfolio(user, amount, ticker, price, timestamp) VALUES (:user, :amount, :ticker, :price, :timestamp)",
                   user=session["user_id"], amount=amount, ticker=ticker, price=price, timestamp=date)

        # update cash

        new_cash = available_cash - total_price
        db.execute("UPDATE users SET cash = :cash_left WHERE id = :id",
                   cash_left=new_cash, id=session["user_id"])

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format

    If the value of username is of length at least 1 and does not already belong
    to a user in the database, the route should return, in JSON format, true,
    signifying that the username is (as of that moment) available.
    Else it should return, in JSON format, false.

    Recall that jsonify in Flask can return a value in JSON format.
    """
    def checkDB(username):
        names_list = []
        inList = False
        usersDB = db.execute("SELECT username FROM users")
        for name in usersDB:
            names_list.append(name['username'])
        if username in names_list:
            inList = True
        return inList
    username = request.form.get("username")
    if len(username) > 1 and not checkDB(username):
        return jsonify(available="true")
    else:
        return jsonify(available="false")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute(
        "SELECT ticker, amount, price, timestamp FROM portfolio WHERE user=:id ORDER BY timestamp DESC", id=session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # display form
    # retrieve stock quote
    # display stock
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Must include a ticker to search.", 403)

        quote = lookup(request.form.get("symbol"))
        ticker = quote['symbol']
        name = quote['name']
        price = quote['price']

        return render_template("quoted.html", name=name, ticker=ticker, price=price)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # display form

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        hash = generate_password_hash(request.form.get("password"), "sha256")

        # add user to database - store hash password
        db.execute("INSERT INTO users(username, hash) VALUES(:username, :hash)",
                   username=request.form.get("username"), hash=hash)

        # log them in
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_portfolio = db.execute(
        "SELECT ticker, price, SUM(amount) FROM portfolio WHERE user = :id GROUP BY ticker HAVING SUM(amount) > 0", id=session["user_id"])
    if request.method == "POST":

        symbol = request.form.get("symbol")
        amount = request.form.get("amount")
        valid_amount = 0

        # check amount of shares is available to sell.
        if not amount:
            return apology("must provide an amount of shares greater than 0.", 403)
        for stock in user_portfolio:
            if stock["ticker"] == symbol:
                valid_amount = int(stock["SUM(amount)"])
                if int(amount) > int(valid_amount):
                    return apology("Can only sell shares that you own. You don't have enough shares.", 403)

        # sell shares.
        # update available cash by selling at current market price via lookup
        # update cash
        cash = db.execute(
            "SELECT cash from users WHERE id = :id", id=session["user_id"])
        available_cash = cash[0]["cash"]
        price = lookup(symbol)
        price = price['price']
        amount = int(amount)
        total_price = amount * price
        new_cash = available_cash + total_price
        db.execute("UPDATE users SET cash = :cash_left WHERE id = :id",
                   cash_left=new_cash, id=session["user_id"])
        amount = amount * -1

        date = str(datetime.datetime.now())
        # - buy the stock
        db.execute("INSERT INTO portfolio(user, amount, ticker, price, timestamp) VALUES (:user, :amount, :ticker, :price, :timestamp)",
                   user=session["user_id"], amount=amount, ticker=symbol, price=price, timestamp=date)
        return redirect("/")
    else:
        stocks = db.execute(
            "SELECT ticker FROM portfolio WHERE user=:id GROUP BY ticker", id=session["user_id"])
        return render_template("sell.html", user_portfolio=user_portfolio)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
