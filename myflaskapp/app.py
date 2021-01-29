from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
#from data import Articles
from flask_mysqldb import MySQL
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt


app = Flask(__name__)

# config mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init mysql
mysql = MySQL(app)


#Articles = Articles()

# index


@app.route('/')
def index():
    return render_template('home.html')

# about


@app.route('/about')
def about():
    return render_template('about.html')

# articles


@app.route('/articles')
def articles():
    # create cursoe
    cur = mysql.connection.cursor()

    # get articls
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'NO ARTICLES FOUND'
        return render_template('articles.html', msg=msg)
    # close connection
    cur.close()
# single article


@app.route('/article/<string:id>/')
def article(id):
    # create cursoe
    cur = mysql.connection.cursor()

    # get article
    result = cur.execute("SELECT * FROM articles WHERE id=%s", [id])

    article = cur.fetchone()

    return render_template('article.html', article=article)

# form


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.data_required(),
        validators.EqualTo('confirm', message='Passwords do not Match')
    ])
    confirm = PasswordField('Confirm Password')

# user register


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create cursor
        cur = mysql.connection.cursor()

        cur.execute('INSERT INTO users(name, email, username, password) VALUES(%s,%s,%s,%s)',
                    (name, email, username, password))
        # commit to db
        mysql.connection.commit()

        # close connection
        cur.close()

        flash('You are now Registered and can log in', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# user login


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # get form filds
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = mysql.connection.cursor()
        # get user by username
        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password = data['password']

            # compare password
            if sha256_crypt.verify(password_candidate, password):
                # passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# chech if user logged in


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please Login', 'danger')
            return redirect(url_for('login'))
    return wrap


# logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now Logged out', 'success')
    return redirect(url_for('login'))


# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursoe
    cur = mysql.connection.cursor()

    # get articls
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'NO ARTICLES FOUND'
        return render_template('dashboard.html', msg=msg)
    # close connection
    cur.close()

# Article Form Class


class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# add Article


@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():

    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # create cursor
        cur = mysql.connection.cursor()

        # EXECUTE
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",
                    (title, body, session['username']))

        # commit
        mysql.connection.commit()

        # close
        cur.close()
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# edit Article


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor
    cur = mysql.connection.cursor()
    # get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    #  Get form
    form = ArticleForm(request.form)
    # populate article form filds
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # create cursor
        cur = mysql.connection.cursor()

        # EXECUTE
        cur.execute(
            "UPDATE articles SET title=%s, body=%s WHERE id =%s", (title, body, id))

        # commit
        mysql.connection.commit()

        # close
        cur.close()
        flash('Article Updates', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)


# delete article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # create cursor
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM articles WHERE id=%s', [id])
    # commit
    mysql.connection.commit()

    # close
    cur.close()

    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'mysecret'
    app.run(debug=True)
