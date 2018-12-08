from flask import Flask,render_template, flash, redirect, url_for, session, logging,request
from data import Articles
from flask_mysqldb import MySQL
from wtforms import *
from passlib.hash import sha256_crypt
from functools import wraps
from flask_ckeditor import CKEditor
import json
import base64

app = Flask(__name__)
app.config['CKEDITOR_PKG_TYPE'] = 'basic'
CKEDITOR_SERVE_LOCAL=True
ckeditor = CKEditor(app)
def create_app():
    app = Flask(__name__)
    ckeditor.init_app(app)
    return app


#Config flask_mysql
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='php'
app.config['MYSQL_PASSWORD']='localhost'
app.config['MYSQL_DB']='myflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'
#init MYSQL
mysql=MySQL(app)

@app.route('/')
def index():
    return render_template('home.html')

class RegisterForm(Form):
    name= StringField('Name',[validators.Length(min=1,max=50),validators.DataRequired()])
    roll= StringField('Roll-Number',[validators.Length(6)])
    username=StringField('Username',[validators.Length(min=4,max=25),validators.DataRequired()])
    email=StringField('Email',[validators.Length(min=6,max=50),validators.DataRequired()])
    password= PasswordField('Password',[
       validators.DataRequired(),
       validators.EqualTo('confirm',message="Passwords do not match")
    ])
    confirm=PasswordField('Confirm Password')

@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method=='POST' and form.validate():
        name=form.name.data
        roll=form.roll.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(str(form.password.data))

        #cursor
        cur= mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,roll,email,username,password) values(%s,%s,%s,%s,%s)",(name,roll,email,username,password))

        #commit to DB
        mysql.connection.commit()

        #close connection
        cur.close()

        flash('You are now registered','success')
        return redirect(url_for('index'))    #write function where u want the page to redirect
    return render_template('register.html',data=form)


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
         #get form fields
         username=request.form['username']
         password_candidate=request.form['password']

         #cursor
         cur= mysql.connection.cursor()
         result=cur.execute("select * from users where username=%s",[username])

         if result>0:
             data=cur.fetchone()
             password=data['password']

             if sha256_crypt.verify(password_candidate,password):
                 app.logger.info('PASSWORD MATCHED')#prints in terminal
                 session['logged_in']=True
                 session['username']=username
                 session['name']=data['name']
                 session['roll']=data['roll']
                 flash("You are now logged in",'success')
                 return redirect(url_for('dashboard'))

             else:
                 app.logger.info('PASSWORD NOT MATCHED')
                 msg="Invalid Password"
                 return render_template('login.html',error=msg)

         else:
             app.logger.info("No User")
             msg="username not found"
             return render_template('login.html',error=msg)

         #close connection
         cur.close()

    return render_template('login.html')

#check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash("Unauthorized, Please Login",'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
def logout():
    session.clear()
    flash("You are now logged out",'success')
    return redirect(url_for('login'))


@app.route('/get_ini')
def getdata():
	username = session['username']
	idd = int(request.args.get('id'))
	app.logger.info(idd);
	cur = mysql.connection.cursor();
	s = "select project_title,description,tagArray from projects where id="+str(idd)+" and username = ";
	result = cur.execute((s+ "%s"),[username]);
	if(result):
		TagList = cur.fetchone();
		return json.dumps(TagList);
	return "[]";


@app.route('/proj')
@is_logged_in
def getProj():
	username = session['username']
	cur = mysql.connection.cursor();
	result = cur.execute("select id,project_title,description,tagArray from projects where username=%s",[username]);
	if(result):
		return json.dumps(cur.fetchall());
	return "[]";

@app.route('/projects')
@is_logged_in
def Projects():
	return render_template('projects.html')

@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')

@app.route('/update',methods=['GET','POST'])
@is_logged_in
def update():
	if request.method=='POST':
		title = request.form["title"];
		description = request.form["desc"];
		tagArray = request.form["tag"];
		idd = request.form["idd"];
		cur = mysql.connection.cursor()
		s = "Update projects SET project_title=%s,description=%s,tagArray=%s where username=%s and id="+idd;
		res = cur.execute(s,(title,description,tagArray,session['username']));
		mysql.connection.commit()
		cur.close()
		if(res):
			flash('Project Updated','success')
		else:
			flash('Failure','failure')
		return redirect(url_for('Projects'))
	return render_template('update.html',data=form)


# class ckeditorForm(Form):
#     description= CKEditorField('Description')

@app.route('/add_project',methods=['GET','POST'])
@is_logged_in
def add_project():
    if request.method=='POST' :
        #title=form.title.data
        #description=form.description.data
        title = request.form["title"];
        description = request.form["desc"];
        tagArray = request.form["tag"];
        cur=mysql.connection.cursor()
        cur.execute("Insert into projects(username,project_title,description,tagArray) values(%s, %s, %s, %s)",(session['username'],title,description,tagArray))
        mysql.connection.commit()
        cur.close()

        flash('project added','success')
        return redirect(url_for('dashboard'))
    return render_template('add_project.html',data=form)

@app.route('/search')
@is_logged_in
def search():
    return render_template('search.html')

@app.route('/searchData')
@is_logged_in
def searchD():
        tag = request.args.get("tag");
        tag=str(tag)
        tagArray=tag.split(',')
        app.logger.info(tagArray)
        cur=mysql.connection.cursor()
        cur.execute("select id,username,project_title,description,tagArray from projects")
        data = cur.fetchall()
        mysql.connection.commit()
        #cur.close()

        list=[]
        for pro in data:
            user = pro["username"]
            cur.execute("select name,email from users where username=%s",[user])
            d = cur.fetchone()
            name = d['name']
            email = d['email']
            app.logger.info(user)
            for i in tagArray:
                if i in str(pro['tagArray']):
                    pro['name'] = name
                    pro['email'] = email
                    list.append(pro)
                    break

        # print(list)
        app.logger.info(list)
        if(list):
            return json.dumps(list)

        return "[]";

@app.route('/del')
@is_logged_in
def dell():
    cur=mysql.connection.cursor()
    s = request.args.get("idd");
    app.logger.info(session['username'])
    s = "delete from projects where username=\""+session['username']+"\" and id ="+s;
    res = cur.execute(s)
    mysql.connection.commit()
    if res:
        flash("Deleted Successfully",'success')
    else:
        flash("Denied",'failure')
    return "[]"

@app.route('/input.html')
@is_logged_in
def input():
	return render_template('input_data.html')

if __name__=='__main__':
    app.secret_key='123456'
    app.run(debug=True)
