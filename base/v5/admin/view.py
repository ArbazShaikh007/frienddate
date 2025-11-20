from flask import redirect, render_template, request, url_for, Blueprint,abort
from base.user.models import User, Report,SelectedCategory,NewUserPosts,ReportNewUserPosts
from base.user.queryset import (insert_data, update_data)
from base.database.db import db
from flask_login import login_required, current_user
from base.admin.queryset import terms_condition, admin_update_data, block
from base.admin.models import Cms, Faqs,Category,ThingsCategory,CategoryQue,QuestionsCategory,CategoryAns,Buttons
from base.common.utiils import COMMON_PATH
from werkzeug.utils import secure_filename
import os,secrets,boto3
from base.community.models import CreatedThingsCommunity,SavedThingsCommunity,CreatedCommunity
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

admin_views_v5 = Blueprint('admin_views_v5', __name__)

REGION_NAME = os.getenv("REGION_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                             aws_secret_access_key=SECRET_KEY)

@admin_views_v5.route('/view/users', methods=['POST', 'GET'])
@login_required
def view_users():
    get_page = request.args.get('page', 1, type=int)

    x = User.query.filter_by(deleted=False, is_block=False).all()
    reported_list = []
    for i in x:
        xy = Report.query.filter_by(reported_user=i.id).all()
        reported_list.append(len(xy))

    print('listttttttttttttttttttt', reported_list)

    return render_template('viewUsers2.html', user_data=x, reports=reported_list, zip=zip, data=current_user,
                           page='view_users', common_path=COMMON_PATH)

@admin_views_v5.route('/view/business_list', methods=['POST', 'GET'])
@login_required
def view_business_list():
    get_page = request.args.get('page', 1, type=int)

    x = User.query.filter_by(is_business=True).all()

    return render_template('businessPage.html', user_data=x, data=current_user, page='view_business_list',
                           common_path=COMMON_PATH)

@admin_views_v5.route('/view/featured_list', methods=['POST', 'GET'])
@login_required
def view_featured_list():
    get_page = request.args.get('page', 1, type=int)

    x = User.query.filter_by(is_featured=True).all()

    return render_template('featuredPage.html', user_data=x, data=current_user, page='view_featured_list',
                           common_path=COMMON_PATH)

@admin_views_v5.route('/add_users_business_page', methods=['GET'])
@login_required
def add_users_business_page():
    user_id = request.args.get('user_id')
    page = request.args.get('page')
    print('pageeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', page)
    print('user_idddddddddddddddddddddddddd', user_id)
    user_data = User.query.filter_by(id=user_id).first()
    print('user_dataaaaaaaaaaaaaaaaaaaaaaaaa', user_data)
    if user_data:
        if user_data.is_business == False:
            user_data.is_business = True
            db.session.commit()
            if page == 'user_list':
                return redirect(url_for('admin_views_v5.view_users'))
            if page == 'business':
                return redirect(url_for('admin_views_v5.view_business_list'))

        if user_data.is_business == True:
            user_data.is_business = False
            db.session.commit()
            if page == 'user_list':
                return redirect(url_for('admin_views_v5.view_users'))
            if page == 'business':
                return redirect(url_for('admin_views_v5.view_business_list'))

    return redirect(url_for('admin_views_v5.view_users'))

@admin_views_v5.route('/add_users_featured_page', methods=['GET'])
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
                return redirect(url_for('admin_views_v5.view_users'))
            if page == 'feartured':
                return redirect(url_for('admin_views_v5.view_featured_list'))

        if user_data.is_featured == True:
            user_data.is_featured = False
            db.session.commit()
            if page == 'user_list':
                return redirect(url_for('admin_views_v5.view_users'))
            if page == 'feartured':
                return redirect(url_for('admin_views_v5.view_featured_list'))

    return redirect(url_for('admin_views_v5.view_users'))

@admin_views_v5.route('/user/reports', methods=['POST', 'GET'])
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


@admin_views_v5.route("/user/block/<int:id>", methods=['POST'])
@login_required
def block_user(id):
    # id = request.args.get('userId')

    user = block(id)

    if user.is_block == False:
        check = User(id=user.id, is_block=True)
        db.session.merge(check)
        db.session.commit()
        return redirect(url_for('admin_views_v5.view_users'))

    if user.is_block == True:
        check = User(id=user.id, is_block=False)
        db.session.merge(check)
        db.session.commit()
        return redirect(url_for('admin_views_v5.view_users'))


@admin_views_v5.route('/view/terms_conditions', methods=['POST', 'GET'])
@login_required
def terms_conditions():
    x = terms_condition(1)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v5.terms_conditions'))

    return render_template('termsConditions.html', data=current_user, content=x, page='terms', common_path=COMMON_PATH)


@admin_views_v5.route('/view/privacy_policies', methods=['POST', 'GET'])
@login_required
def privacy_policies():
    x = terms_condition(2)

    if request.method == 'POST':
        content = request.form.get('body')
        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v5.privacy_policies'))

    return render_template('privacyPolicies.html', data=current_user, content=x, page='privacy',
                           common_path=COMMON_PATH)


@admin_views_v5.route('/add/faq', methods=['POST', 'GET'])
@login_required
def add_faq():
    get_page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')

        faq_data = Faqs(question=question, answer=answer)
        insert_data(faq_data)

        return redirect(url_for('admin_views_v5.add_faq'))

    # x = Faqs.query.paginate(page=get_page, per_page=10)
    x = Faqs.query.all()

    return render_template('FAQ.html', data=current_user, user_data=x, page='faq', common_path=COMMON_PATH)


@admin_views_v5.route('/delete_faq/<int:id>', methods=['POST'])
@login_required
def delete_faq(id):
    faq = Faqs.query.get(id)
    db.session.delete(faq)
    db.session.commit()

    return redirect(url_for('admin_views_v5.add_faq'))


@admin_views_v5.route('/faq/update', methods=['POST', 'GET'])
@login_required
def update_faq():
    id = request.form.get('updateId')

    x = Faqs.query.filter_by(id=id).first()

    question = request.form.get('question')
    answer = request.form.get('answer')

    faq_data = Faqs(id=id, question=question, answer=answer)

    update_data(faq_data)

    return redirect(url_for('admin_views_v5.add_faq'))


@admin_views_v5.route('/how_to_use_friend_date', methods=['POST', 'GET'])
@login_required
def how_to_use_app():
    x = terms_condition(4)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v5.how_to_use_app'))

    return render_template('howtouseFrienddate.html', data=current_user, content=x, page='app_use',
                           common_path=COMMON_PATH)


@admin_views_v5.route('/information', methods=['POST', 'GET'])
@login_required
def information():
    x = terms_condition(5)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v5.information'))

    return render_template('information.html', data=current_user, content=x, page='info', common_path=COMMON_PATH)


@admin_views_v5.route('/store', methods=['POST', 'GET'])
@login_required
def store():
    x = terms_condition(6)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v5.store'))

    return render_template('store.html', data=current_user, content=x, page='store', common_path=COMMON_PATH)


@admin_views_v5.route('/brand', methods=['POST', 'GET'])
@login_required
def brand_deals():
    x = terms_condition(7)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_views_v5.brand_deals'))

    return render_template('brand_deals.html', data=current_user, content=x, page='brand', common_path=COMMON_PATH)


@admin_views_v5.route('/deleted/user')
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

@admin_views_v5.route('/reported_post')
@login_required
def reported_post():
    get_reported_posts = db.session.query(NewUserPosts).join(
        ReportNewUserPosts, ReportNewUserPosts.image_id == NewUserPosts.id
    ).all()

    return render_template('reported_post.html', data=current_user, report_post_data=get_reported_posts, common_path=COMMON_PATH,
                           page='reported_posts')

@admin_views_v5.route("/user/reports", methods=['GET', 'POST'])
@login_required
def view_reports():
    return render_template('reports.html', data=current_user, common_path=COMMON_PATH)

@admin_views_v5.route('/admin_things_community_list', methods=['POST', 'GET'])
@login_required
def admin_things_community_list():
    category_id = request.args.get('category_id')
    get_page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        link = request.form.get('link')
        community_id = request.form.get('community_id')
        category_id = request.args.get('category_id')
        print('category_idddddddddddddddddddddddddd',category_id)

        get_community_data = CreatedThingsCommunity.query.get(community_id)
        if not get_community_data:
            return "Invalid word"

        if link != '':
            get_community_data.link = link
            db.session.commit()

        return redirect(url_for('admin_views_v5.admin_things_community_list',category_id = category_id))

    get_community_data = CreatedThingsCommunity.query.filter_by(category_id = category_id).all()

    return render_template('ThingsCommunityList.html', data=current_user, community_data_data=get_community_data, page='things', indexing=1,
                           common_path=COMMON_PATH)

@admin_views_v5.route('/delete_things_community_link/<int:id>', methods=['POST'])
@login_required
def delete_things_community_link(id):
    community_data = CreatedThingsCommunity.query.get(id)
    if not community_data:
        abort(404, description="Word not found")

    community_data.link = None
    db.session.commit()

    return redirect(url_for('admin_views_v5.admin_things_community_list',category_id = community_data.category_id))

@admin_views_v5.route('/places_community_list', methods=['POST', 'GET'])
@login_required
def places_community_list():
    category_id = request.args.get('category_id')
    get_page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        link = request.form.get('link')
        community_id = request.form.get('community_id')
        category_id = request.args.get('category_id')
        print('category_idddddddddddddddddddddddddd',category_id)

        get_community_data = CreatedCommunity.query.get(community_id)
        if not get_community_data:
            return "Invalid word"

        if link != '':
            get_community_data.link = link
            db.session.commit()

        return redirect(url_for('admin_views_v5.places_community_list',category_id = category_id))

    get_community_data = CreatedCommunity.query.filter_by(category_id = category_id).all()

    return render_template('PlacesCommunityList.html', data=current_user, community_data_data=get_community_data, page='places', indexing=1,
                           common_path=COMMON_PATH)

@admin_views_v5.route('/delete_places_community_link/<int:id>', methods=['POST'])
@login_required
def delete_places_community_link(id):
    community_data = CreatedCommunity.query.get(id)
    if not community_data:
        abort(404, description="Word not found")

    community_data.link = None
    db.session.commit()

    return redirect(url_for('admin_views_v5.places_community_list',category_id = community_data.category_id))

@admin_views_v5.route('/add_things_category', methods=['POST', 'GET'])
@login_required
def add_things_category():
    eid = request.args.get('editId')
    get_page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        category_name = request.form.get('category')
        category_image = request.files.get('categoryImage')

        image_name = secure_filename(category_image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'
        x = secrets.token_hex(10)

        image_name = x + extension

        s3_client.upload_fileobj(category_image, S3_BUCKET, image_name,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

        category_data = ThingsCategory(category_name=category_name.capitalize(), image_name=image_name, image_path=image_url)
        insert_data(category_data)
        return redirect(url_for('admin_views_v5.add_things_category'))

    # x = Category.query.paginate(page=int(get_page), per_page=10)
    x = ThingsCategory.query.all()

    return render_template('AddThingsCategory.html', data=current_user, user_data=x, page='things', indexing=1,
                           common_path=COMMON_PATH)

@admin_views_v5.route('/delete_things_category/<int:id>', methods=['POST'])
@login_required
def delete_things_category(id):
    cat = ThingsCategory.query.get(id)
    if not cat:
        abort(404, description="Category not found")

    created_communities = CreatedThingsCommunity.query.filter_by(category_id=cat.id).all()
    for community in created_communities:
        saved_communities = SavedThingsCommunity.query.filter_by(created_id=community.id).all()
        for saved_community in saved_communities:
            db.session.delete(saved_community)

        db.session.delete(community)

    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=cat.image_name)

    except Exception as e:
        return ""
    db.session.delete(cat)
    db.session.commit()

    return redirect(url_for('admin_views_v5.add_things_category'))

@admin_views_v5.route('/things_category/update', methods=['POST', 'GET'])
@login_required
def update_things_category():
    id = request.form.get('updateId')

    x = ThingsCategory.query.filter_by(id=id).first()
    print('xxxxxxxxxxxxxxxxxxxxxxxxxxx', x)

    category_name = request.form.get('category')
    category_image = request.files.get('categoryImage')
    print('imageeeeeeeeeeeeeeeeeeeeeee ', category_image)

    category_data = ThingsCategory(id=id, category_name=category_name, image_name=x.image_name, image_path=x.image_path)

    update_data(category_data)

    if category_image:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=x.image_name)
        image_name = secure_filename(category_image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'

        x = secrets.token_hex(5)
        image_name = x + extension

        s3_client.upload_fileobj(category_image, S3_BUCKET, image_name,
                                             ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

        category_data = ThingsCategory(id=id, category_name=category_name, image_name=image_name, image_path=image_url)

        update_data(category_data)

        return redirect(url_for('admin_views_v5.add_things_category'))
    return redirect(url_for('admin_views_v5.add_things_category'))

@admin_views_v5.route('/add_buttons', methods=['POST', 'GET'])
@login_required
def add_buttons():

    if request.method == 'POST':
        button_original_name = request.form.get('button_original_name')
        button_name = request.form.get('button_name')
        button_image = request.files.get('button_image')

        image_name = secure_filename(button_image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'
        x = secrets.token_hex(10)

        image_name = x + extension

        s3_client.upload_fileobj(button_image, S3_BUCKET, image_name,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

        buttons_data = Buttons(button_original_name=button_original_name,button_name =button_name, image_name=image_name, image_path=image_url)
        insert_data(buttons_data)

        return redirect(url_for('admin_views_v5.add_buttons'))

    x = Buttons.query.all()

    return render_template('addButtons.html', data=current_user, user_data=x, page='buttons', indexing=1,
                           common_path=COMMON_PATH)

@admin_views_v5.route('/delete_buttons/<int:id>', methods=['POST'])
@login_required
def delete_buttons(id):
    button = Buttons.query.get(id)
    if not button:
        abort(404, description="Button data not found")

    try:
        if button.image_name is not None:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=button.image_name)

    except Exception as e:
        return ""

    db.session.delete(button)
    db.session.commit()

    return redirect(url_for('admin_views_v5.add_buttons'))

@admin_views_v5.route('/button_data/update', methods=['POST', 'GET'])
@login_required
def update_button_data():
    id = request.form.get('updateId')

    button_data = Buttons.query.filter_by(id=id).first()

    # button_original_name = request.form.get('button_original_name')
    button_name = request.form.get('button_name')
    button_image = request.files.get('button_image')

    image_name = button_data.image_name
    image_url = button_data.image_path

    if button_image:
        if button_data.image_name is not None:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=button_data.image_name)
        image_name = secure_filename(button_image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'

        x = secrets.token_hex(5)
        image_name = x + extension

        s3_client.upload_fileobj(button_image, S3_BUCKET, image_name,
                                             ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

    button_data.image_path = image_url
    button_data.image_name = image_name
    button_data.button_name = button_name
    # button_data.button_original_name = button_original_name

    db.session.commit()

    return redirect(url_for('admin_views_v5.add_buttons'))

@admin_views_v5.route('/add_questions_category', methods=['POST', 'GET'])
@login_required
def add_questions_category():
    eid = request.args.get('editId')
    get_page = request.args.get('page', 1, type=int)

    if request.method == 'POST':
        category_name = request.form.get('category')
        category_image = request.files.get('categoryImage')

        image_name = secure_filename(category_image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'
        x = secrets.token_hex(10)

        image_name = x + extension

        s3_client.upload_fileobj(category_image, S3_BUCKET, image_name,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

        category_data = QuestionsCategory(category_name=category_name.capitalize(), image_name=image_name, image_path=image_url)
        insert_data(category_data)
        return redirect(url_for('admin_views_v5.add_questions_category'))

    # x = Category.query.paginate(page=int(get_page), per_page=10)
    x = QuestionsCategory.query.all()

    return render_template('QuestionsCategory.html', data=current_user, user_data=x, page='question', indexing=1,
                           common_path=COMMON_PATH)

@admin_views_v5.route('/delete_questions_category/<int:id>', methods=['POST'])
@login_required
def delete_questions_category(id):
    cat = QuestionsCategory.query.get(id)
    if not cat:
        abort(404, description="Category not found")

    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=cat.image_name)

    except Exception as e:
        return ""

    category_que_data = CategoryQue.query.filter_by(questions_category_id=id).all()

    if len(category_que_data)>0:
        for i in category_que_data:
            category_ans_data = CategoryAns.query.filter_by(question_id=i.id).all()
            if len(category_ans_data)>0:
                for j in category_ans_data:
                    db.session.delete(j)
                    db.session.commit()
            db.session.delete(i)
            db.session.commit()

    db.session.delete(cat)
    db.session.commit()

    return redirect(url_for('admin_views_v5.add_questions_category'))

@admin_views_v5.route('/questions_category/update', methods=['POST', 'GET'])
@login_required
def update_questions_category():
    id = request.form.get('updateId')

    x = QuestionsCategory.query.filter_by(id=id).first()
    print('xxxxxxxxxxxxxxxxxxxxxxxxxxx', x)

    category_name = request.form.get('category')
    category_image = request.files.get('categoryImage')
    print('imageeeeeeeeeeeeeeeeeeeeeee ', category_image)

    category_data = QuestionsCategory(id=id, category_name=category_name, image_name=x.image_name, image_path=x.image_path)

    update_data(category_data)

    if category_image:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=x.image_name)
        image_name = secure_filename(category_image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'

        x = secrets.token_hex(5)
        image_name = x + extension

        s3_client.upload_fileobj(category_image, S3_BUCKET, image_name,
                                             ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

        category_data = QuestionsCategory(id=id, category_name=category_name, image_name=image_name, image_path=image_url)

        update_data(category_data)

        return redirect(url_for('admin_views_v5.add_questions_category'))
    return redirect(url_for('admin_views_v5.add_questions_category'))

@admin_views_v5.route('/add/questions', methods=['POST', 'GET'])
@login_required
def add_questions():
    id = request.args.get('id')

    print('idddddddddddddddddddddddddddddd',id)

    if request.method == 'POST':

        question = request.form.get('question')
        questions_category_id = request.form.get('category_id')

        add_question_data = CategoryQue(question=question, questions_category_id=questions_category_id)
        insert_data(add_question_data)

        return redirect(url_for('admin_views_v5.add_questions',id = questions_category_id))

    x = CategoryQue.query.filter_by(questions_category_id = id).all()

    return render_template('addQuestions.html',id = id, data=current_user, user_data=x, page='questions_page', common_path=COMMON_PATH)

@admin_views_v5.route('/edit/questions', methods=['POST', 'GET'])
@login_required
def edit_questions():
    id = request.form.get('updateId')

    question = request.form.get('question')

    get_question_data = CategoryQue.query.get(id)

    get_question_data.question = question
    db.session.commit()

    return redirect(url_for('admin_views_v5.add_questions',id = get_question_data.questions_category_id))

@admin_views_v5.route('/delete_question/<int:id>/<int:category_id>', methods=['POST'])
@login_required
def delete_question(id,category_id):
    get_question = CategoryQue.query.get(id)  # `get` is a shorthand to retrieve by primary key
    if not get_question:
        # handle the case where the category doesn't exist
        abort(404, description="Question not found")

    db.session.delete(get_question)
    db.session.commit()

    return redirect(url_for('admin_views_v5.add_questions', id = category_id))