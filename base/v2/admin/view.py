import jwt, os, secrets, boto3
from datetime import datetime, timedelta
from flask import redirect, render_template, request, flash, jsonify, url_for, Blueprint
from flask_mail import Message, Mail
from base.user.models import User, token_required, Report
from base.user.queryset import (insert_data, view_data, validate, update_data)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from base.database.db import db
from dotenv import load_dotenv
from base.admin.models import Admin, Category
from base.admin.queryset import admin_insert_data, admin_validate
from flask_login import login_user, login_required, current_user
from base.user.auth import UPLOAD_FOLDER
from base.admin.queryset import terms_condition, admin_update_data, block
from base.admin.models import Cms, Faqs
from base.common.utiils import COMMON_PATH

admin_views_v2 = Blueprint('admin_views_v2', __name__)


@admin_views_v2.route('/view/users', methods=['POST', 'GET'])
@login_required
def view_users():
    get_page = request.args.get('page', 1, type=int)

    x = User.query.all()
    reported_list = []
    for i in x:
        xy = Report.query.filter_by(reported_user=i.id).all()
        reported_list.append(len(xy))

    print('listttttttttttttttttttt', reported_list)

    return render_template('viewUsers2.html', user_data=x, reports=reported_list, zip=zip, data=current_user,
                           page='view_users', common_path=COMMON_PATH)


@admin_views_v2.route('/view/featured_list', methods=['POST', 'GET'])
@login_required
def view_featured_list():
    get_page = request.args.get('page', 1, type=int)

    x = User.query.filter_by(is_featured=True).all()

    return render_template('featuredPage.html', user_data=x, data=current_user, page='view_featured_list',
                           common_path=COMMON_PATH)


@admin_views_v2.route('/add_users_featured_page', methods=['GET'])
@login_required
def add_users_featured_page():
    user_id = request.args.get('user_id')
    page = request.args.get('page')
    print('pageeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', page)
    print('user_idddddddddddddddddddddddddd', user_id)
    user_data = User.query.filter_by(id=user_id).first()
    print('user_dataaaaaaaaaaaaaaaaaaaaaaaaa', user_data)
    if user_data:
        if user_data.is_featured == False:
            user_data.is_featured = True
            db.session.commit()
            if page == 'user_list':
                return redirect(url_for('admin_views_v2.view_users'))
            if page == 'feartured':
                return redirect(url_for('admin_views_v2.view_featured_list'))

        if user_data.is_featured == True:
            user_data.is_featured = False
            db.session.commit()
            if page == 'user_list':
                return redirect(url_for('admin_views_v2.view_users'))
            if page == 'feartured':
                return redirect(url_for('admin_views_v2.view_featured_list'))

    return redirect(url_for('admin_views_v2.view_users'))


@admin_views_v2.route('/user/reports', methods=['POST', 'GET'])
@login_required
def user_reports():
    # get_page = request.args.get('page', 1, type=int)
    reported_id = request.args.get('id')
    user_who = User.query.filter_by(id=reported_id).first()

    reports_list = []

    x = Report.query.filter_by(reported_user=reported_id).all()
    for i in x:
        user_list = User.query.filter_by(id=i.user_id).first()
        reports_list.append(user_list)

    print('listttttttttttttttttttt', reports_list)

    return render_template('reports.html', reports=x, users=reports_list, main_user=user_who, zip=zip,
                           data=current_user, page='view_users', common_path=COMMON_PATH)


@admin_views_v2.route("/user/block/<int:id>", methods=['POST'])
@login_required
def block_user(id):
    # id = request.args.get('userId')

    user = block(id)

    if user.is_block == False:
        check = User(id=user.id, is_block=True)
        db.session.merge(check)
        db.session.commit()
        return redirect(url_for('admin_views_v2.view_users'))

    if user.is_block == True:
        check = User(id=user.id, is_block=False)
        db.session.merge(check)
        db.session.commit()
        return redirect(url_for('admin_views_v2.view_users'))


@admin_views_v2.route('/view/terms_conditions', methods=['POST', 'GET'])
@login_required
def terms_conditions():
    x = terms_condition(1)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v2.terms_conditions'))

    return render_template('termsConditions.html', data=current_user, content=x, page='terms', common_path=COMMON_PATH)


@admin_views_v2.route('/view/privacy_policies', methods=['POST', 'GET'])
@login_required
def privacy_policies():
    x = terms_condition(2)

    if request.method == 'POST':
        content = request.form.get('body')
        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v2.privacy_policies'))

    return render_template('privacyPolicies.html', data=current_user, content=x, page='privacy',
                           common_path=COMMON_PATH)


@admin_views_v2.route('/add/faq', methods=['POST', 'GET'])
@login_required
def add_faq():
    get_page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')

        faq_data = Faqs(question=question, answer=answer)
        insert_data(faq_data)

        return redirect(url_for('admin_views_v2.add_faq'))

    # x = Faqs.query.paginate(page=get_page, per_page=10)
    x = Faqs.query.all()

    return render_template('FAQ.html', data=current_user, user_data=x, page='faq', common_path=COMMON_PATH)


@admin_views_v2.route('/delete_faq/<int:id>', methods=['POST'])
@login_required
def delete_faq(id):
    faq = Faqs.query.get(id)
    db.session.delete(faq)
    db.session.commit()

    return redirect(url_for('admin_views_v2.add_faq'))


@admin_views_v2.route('/faq/update', methods=['POST', 'GET'])
@login_required
def update_faq():
    id = request.form.get('updateId')

    x = Faqs.query.filter_by(id=id).first()

    question = request.form.get('question')
    answer = request.form.get('answer')

    faq_data = Faqs(id=id, question=question, answer=answer)

    update_data(faq_data)

    return redirect(url_for('admin_views_v2.add_faq'))


@admin_views_v2.route('/how_to_use_friend_date', methods=['POST', 'GET'])
@login_required
def how_to_use_app():
    x = terms_condition(4)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v2.how_to_use_app'))

    return render_template('howtouseFrienddate.html', data=current_user, content=x, page='app_use',
                           common_path=COMMON_PATH)


@admin_views_v2.route('/information', methods=['POST', 'GET'])
@login_required
def information():
    x = terms_condition(5)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v2.information'))

    return render_template('information.html', data=current_user, content=x, page='info', common_path=COMMON_PATH)


@admin_views_v2.route('/store', methods=['POST', 'GET'])
@login_required
def store():
    x = terms_condition(6)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v2.store'))

    return render_template('store.html', data=current_user, content=x, page='store', common_path=COMMON_PATH)


@admin_views_v2.route('/brand', methods=['POST', 'GET'])
@login_required
def brand_deals():
    x = terms_condition(7)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v2.brand_deals'))

    return render_template('brand_deals.html', data=current_user, content=x, page='brand', common_path=COMMON_PATH)


@admin_views_v2.route('/deleted/user')
@login_required
def deleted_user():
    ls = []
    get_page = request.args.get('page', 1, type=int)

    list = User.query.filter_by(deleted=True).all()
    # for i in list:
    #     if i.deleted:
    #
    #         if i.deleted > 0:
    #             ls.append(i)


    return render_template('deletedUser.html', data=current_user, user_data=list, common_path=COMMON_PATH,
                           page='deleted')


@admin_views_v2.route("/user/reports", methods=['GET', 'POST'])
@login_required
def view_reports():
    return render_template('reports.html', data=current_user, common_path=COMMON_PATH)

