from flask import Blueprint, render_template, request, flash, redirect, url_for,jsonify
from sqlalchemy.sql import table
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user
import random
import string
import json
import smtplib
from email.message import EmailMessage
EMAIL_ADDRESS = "EMAIL"
EMAIL_PASSWORD = "PASSWORD"
auth = Blueprint('auth', __name__)
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
          if user.verified:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
          else:
            flash("Account not verified, the OTP has been sent to your email. ",category='error')
        else:
            flash('Email does not exist.', category='error')
    return render_template("login.html", user=current_user)
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
@auth.route('/confirm',methods=["GET","POST"])
def confirm():
  if request.method == "POST":
    user = User.query.filter_by(otp=request.form["otp"]).first()
    if user and user.verified:
      flash("Account already verified, please log in")
    elif user:
      user.verified = True
      user.otp = ""
      login_user(user)
      db.session.commit()
      return redirect(url_for("views.home"))
    else:
      flash("Invalid OTP", category = "error")
  return render_template("confirm.html",user=current_user)
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
  if request.method == 'POST':
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        user = User.query.filter_by(email=email).first()
        if user:
          if user.verified == True:
            flash('Email already exists.', category='error')
            return redirect(url_for("auth.confirm"))
          else:
            flash("Account already exists, please verify it",category="error")
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 8:
            flash('Password must be at least 8 characters.', category='error')
        else:
            #send otp
            otp = (''.join(random.choices(string.digits, k=6)))
            while User.query.filter_by(otp=otp).first():
              otp = (''.join(random.choices(string.digits, k=6)))
            user = User(email=email,  password=generate_password_hash(password1, method='sha256'),verified=False,otp = otp)  
            db.session.add(user)
            msg = EmailMessage()
            msg["Subject"] = "OTP for Lumina DBapp"
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = email
            msg.set_content("Your OTP is "+otp+"\n"+"Verify it at https://efbd0a85-3acc-4dd8-9f91-ffff64e8b877-00-2xz72zbze2et0.pike.replit.dev/confirm"+"\n"+"If you did not request this, please ignore this email.")

            with smtplib.SMTP_SSL("smtp.elasticemail.com", 465) as smtp:
              try:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
                db.session.commit()
                flash("An OTP has been sent to your email",category="success")
                return redirect(url_for("auth.confirm"))
              except Exception as e:
                print(e)
                flash("An error occured, please try again",category="error")
  return render_template("sign_up.html", user=current_user)
@auth.route("/forgot",methods=["GET","POST"])
def forgot():
  if request.method == "POST":
    user = User.query.filter_by(email=request.form.get("email")).first()
    if user:
      flash("An OTP has been sent to your account.",category="success")
  return render_template("forgot.html",user=current_user)
@auth.route("/verify-forgot",methods=["GET","POST"])
def check_forgot():
  print("verify forgot")
  if request.data:
    email = json.loads(request.data)["email"]
    user = User.query.filter_by(email=email).first()
    if user and user.verified:
      otp = (''.join(random.choices(string.digits, k=6)))
      while User.query.filter_by(otp=otp).first():
        otp = (''.join(random.choices(string.digits, k=6)))
      if user.otp == "":
        user.otp = otp
      else:
        return jsonify({"exists":"n"})
      #send email
      msg = EmailMessage()
      msg["Subject"] = "OTP for Lumina DBapp"
      msg["From"] = EMAIL_ADDRESS
      msg["To"] = email
      msg.set_content("Your OTP is "+otp+"\n"+"Verify it at https://efbd0a85-3acc-4dd8-9f91-ffff64e8b877-00-2xz72zbze2et0.pike.replit.dev/restore"+"\n"+"If you did not request this, please ignore this email.")

      with smtplib.SMTP_SSL("smtp.elasticemail.com", 465) as smtp:
        try:
          smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
          smtp.send_message(msg)
          db.session.commit()
          flash("An OTP has been sent to your email",category="success")
          return jsonify({"exists":"y"})
        except Exception as e:
          print(e)
          flash("An error occured, please try again",category="error")
          return jsonify({"exists":"n"})
    else:
      return jsonify({"exists":"n"})
  else:
    return redirect(url_for("views.nopage"))
@auth.route("/restore",methods=["GET","POST"])
def restore():
  if request.method == "POST":
    otp = request.form.get("otp")
    user = User.query.filter_by(otp=otp).first()
    if user and user.verified:
      password1 = request.form.get("password1")
      password2 = request.form.get("password2")
      if len(password1)<8:
        flash("Passwords have to be at least 8 characters",category="error")
      elif password1!=password2:
        flash("Passwords do not match",category = "error")
      else:
        user.otp = ""
        flash("Changed password successfully!",category="success")
        login_user(user=user)
        user.password = generate_password_hash(password1,method='sha256')
        db.session.commit()
        return redirect(url_for("views.home"))
    else:
      flash("Invalid OTP",category="error")
  return render_template("restore.html",user=current_user)
