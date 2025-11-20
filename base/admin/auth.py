import jwt, os, secrets, smtplib
from datetime import datetime, timedelta
from flask import redirect, render_template, request, flash, jsonify, url_for, Blueprint
from flask_mail import Message, Mail
from base.user.models import User, token_required
from base.user.queryset import (insert_data, view_data, validate, update_data)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from base.database.db import db
from dotenv import load_dotenv
from base.admin.models import Admin, Category, Cms, BlockedWords, Badges, Buddys
from base.admin.queryset import admin_insert_data, admin_validate, terms_condition, admin_update_data
from flask_login import login_user, login_required, current_user
from base.user.auth import UPLOAD_FOLDER
from base.common.utiils import COMMON_PATH, send_reset_email
from base.community.models import SavedCommunity, CommunityPost, PostLike, PostThumsup, PostComment, PostThumpdown, \
    CreatedCommunity
from base.user.models import token_required, TagFriends, User, ChatMute, Notification, FriendRequest, Block, \
SelectedCategory, User

load_dotenv()

mail = Mail()

# UPLOAD_FOLDER = 'base/static/categoryResoueces/category_photos/'
CATEGORY_FOLDER = 'base/static/categoryResoueces/category_photos/'

ADMIN_FOLDER = 'base/static/adminResources/admin_photos/'

admin_auth = Blueprint('admin_auth', __name__)


@admin_auth.route('/admin/register', methods=['POST', 'GET'])
def admin_register():
    if request.method == 'POST':

        fullname = request.form.get('fullName')
        email = request.form.get('adminEmail')
        password = request.form.get('adminPassword')
        phonenumber = request.form.get('adminPhonenumber')

        hash_password = generate_password_hash(password)

        user = admin_validate(email)

        if user:
            return redirect(url_for('admin_auth.admin_login'))

        if not user:
            image_path = os.path.join(ADMIN_FOLDER)
            image_path = image_path.replace("base", "..")

            user_data = Admin(fullname=fullname, email=email,
                              phonenumber=phonenumber, password=hash_password, image_path=image_path)

            admin_insert_data(user_data)

            return redirect(url_for('admin_auth.admin_login'))
    return render_template('register.html', common_path=COMMON_PATH)


# @login_manager.user_loader
# def load_user(id):
#     return AdminVO.query.get(int(id))

@admin_auth.route('/', methods=['POST', 'GET'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('adminnEmail')
        password = request.form.get('adminPassword')

        check_email = admin_validate(email)

        if not check_email:
            flash("Email does not Exist !", "danger")
            return redirect(url_for('admin_auth.admin_login'))

        if check_email and check_email.check_password(password):
            login_user(check_email)

            return redirect(url_for('admin_auth.index'))
        else:
            flash("Wrong  Password  !", "danger")

    return render_template('login.html', common_path=COMMON_PATH)


@admin_auth.route('/index', methods=['POST', 'GET'])
@login_required
def index():
    x = Category.query.all()
    users = User.query.all()
    print('lennnnnnnnnnnnnnnnn', len(x))
    return render_template('index.html', data=current_user, y=len(x), z=len(users), page='index',
                           common_path=COMMON_PATH)


@admin_auth.route('/admin/profile', methods=['POST', 'GET'])
@login_required
def admin_profile():
    return render_template('profile.html', data=current_user, common_path=COMMON_PATH)


@admin_auth.route('/add_category', methods=['POST', 'GET'])
@login_required
def add_category():
    eid = request.args.get('editId')
    get_page = request.args.get('page', 1, type=int)

    print('eiddddddddddddddddddddddddddddd ', eid)

    if request.method == 'POST':
        category_name = request.form.get('category')
        category_image = request.files.get('categoryImage')

        image_name = secure_filename(category_image.filename)
        extension = os.path.splitext(image_name)[1]
        x = secrets.token_hex(10)

        image_name = x + extension

        image_path = os.path.join(CATEGORY_FOLDER)
        category_image.save(os.path.join(image_path, image_name))
        image_path = image_path.replace("base", "..")

        category_data = Category(category_name=category_name.capitalize(), image_name=image_name, image_path=image_path)

        insert_data(category_data)
        return redirect(url_for('admin_auth.add_category'))

    # x = Category.query.paginate(page=int(get_page), per_page=10)
    x = Category.query.all()

    return render_template('addCategory2.html', data=current_user, user_data=x, page='category', indexing=1,
                           common_path=COMMON_PATH)


@admin_auth.route('/admin/update', methods=['POST', 'GET'])
@login_required
def admin_update():
    if request.method == 'POST':

        fullname = request.form.get('fullName')
        email = request.form.get('adminEmail')
        phonenumber = request.form.get('adminPhonenumber')
        admin_image = request.files.get('imageName')
        print('imagenameeeeeeeeeeeeeeeeeee', admin_image)

        # user = validate(email)

        # if user:
        #     # flash()
        #     return redirect(url_for('admin_auth.admin_update'))
        #
        if not admin_image:
            user_data = Admin(id=current_user.id, fullname=fullname, email=email,
                              phonenumber=phonenumber, password=current_user.password,
                              image_name=current_user.image_name, image_path=current_user.image_path)

            update_data(user_data)
            flash("Profile successfully updated ! ", 'success')
            return redirect(url_for('admin_auth.admin_update'))
        if admin_image:
            if current_user.image_name != 'conprofile.png':
                os.remove(os.path.join(ADMIN_FOLDER, current_user.image_name))
            image_name = secure_filename(admin_image.filename)
            extension = os.path.splitext(image_name)[1]
            x = secrets.token_hex(10)
            image_name = x + extension

            image_path = os.path.join(ADMIN_FOLDER)
            admin_image.save(os.path.join(image_path, image_name))
            image_path = image_path.replace("base", "..")

            user_data = Admin(id=current_user.id, fullname=fullname, email=email,
                              phonenumber=phonenumber, password=current_user.password, image_name=image_name,
                              image_path=image_path)

            update_data(user_data)
            flash("Profile successfully updated ! ", 'success')
            return redirect(url_for('admin_auth.admin_update'))
    # return render_template('addCategory.html')
    return render_template('edit.html', data=current_user, common_path=COMMON_PATH)


@admin_auth.route('/admin/change_pwd', methods=['POST'])
@login_required
def change_password():
    old_pwd = request.form.get('oldPassword')
    new_pwd = request.form.get('newPassword')
    confirm_pwd = request.form.get('confirmPassword')

    hash_password = generate_password_hash(new_pwd)

    if current_user and current_user.check_password(old_pwd):
        if new_pwd == confirm_pwd:
            user_data = Admin(password=hash_password, id=current_user.id)

            update_data(user_data)
            flash('Password changed successfully.', 'success')
            return redirect(url_for('admin_auth.admin_update'))

        else:
            flash('New Password did not Match!', 'danger')
            return redirect(url_for('admin_auth.admin_update'))

    else:
        flash('Wrong Old Password!', 'danger')
        return redirect(url_for('admin_auth.admin_update'))


# @admin_auth.route('/admin/edit', methods=['GET'])
# @login_required
# def edit_category():
#     eid = request.args.get('id')
#     print('eiddddddddddddddddddddddddddddd ', eid)
#
#     x = Category.query.filter_by(id=eid).first()
#     return render_template('addCategory.html', eidx = x)




@admin_auth.route('/category/update', methods=['POST', 'GET'])
@login_required
def update_category():
    id = request.form.get('updateId')

    x = Category.query.filter_by(id=id).first()
    print('xxxxxxxxxxxxxxxxxxxxxxxxxxx', x)

    category_name = request.form.get('category')
    category_image = request.files.get('categoryImage')
    print('imageeeeeeeeeeeeeeeeeeeeeee ', category_image)

    category_data = Category(id=id, category_name=category_name, image_name=x.image_name, image_path=x.image_path)

    update_data(category_data)

    if category_image:
        os.remove(os.path.join(CATEGORY_FOLDER, x.image_name))
        image_name = secure_filename(category_image.filename)
        extension = os.path.splitext(image_name)[1]
        x = secrets.token_hex(5)
        image_name = x + extension

        image_path = os.path.join(CATEGORY_FOLDER)
        category_image.save(os.path.join(image_path, image_name))
        image_path = image_path.replace("base", "..")

        category_data = Category(id=id, category_name=category_name, image_name=image_name, image_path=image_path)

        update_data(category_data)

        return redirect(url_for('admin_auth.add_category'))
    # return render_template('addCategory.html')
    return redirect(url_for('admin_auth.add_category'))


@admin_auth.route('/delete_category/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    cat = Category.query.get(id)  # `get` is a shorthand to retrieve by primary key
    if not cat:
        # handle the case where the category doesn't exist
        abort(404, description="Category not found")

    # Handle associated Created Communities
    created_communities = CreatedCommunity.query.filter_by(category_id=cat.id).all()
    for community in created_communities:
        # Handle associated Saved Communities
        saved_communities = SavedCommunity.query.filter_by(created_id=community.id).all()
        for saved_community in saved_communities:
            # Handle associated Community Posts
            posts = CommunityPost.query.filter_by(community_id=saved_community.created_id).all()
            print('postsssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss', posts)
            for post in posts:
                # Delete associated tags and chat mutes
                TagFriends.query.filter_by(community_post_id=post.id).delete()
                ChatMute.query.filter_by(post_id=post.id).delete()
                # Delete post
                db.session.delete(post)

            # Delete SavedCommunity
            db.session.delete(saved_community)

        # Delete CreatedCommunity
        db.session.delete(community)
    remove_category_from_all_users = User.query.all()
    if len(remove_category_from_all_users) > 0:
        for users in remove_category_from_all_users:
            selected_categories = SelectedCategory.query.filter_by(user_id=users.id).first()
            print('selected_categoriessssssssssssssssssssssssssssssssssssssssssssssssssssssssss', selected_categories)
            if selected_categories:
                get_categories = selected_categories.category_id
                split_categories = get_categories.split(',')
                if str(cat.id) in split_categories:
                    split_categories.remove(str(cat.id))
                    join_categories = ','.join(split_categories)
                    selected_categories.category_id = join_categories
                    selected_categories.id = selected_categories.id
                    # db.session.commit()
    # Remove category image
    try:
        os.remove(os.path.join(CATEGORY_FOLDER, cat.image_name))
    except Exception as e:
        # handle any exceptions raised during file deletion
        current_app.logger.error(f"Error deleting category image: {e}")

    # Delete category
    db.session.delete(cat)
    db.session.commit()

    return redirect(url_for('admin_auth.add_category'))


@admin_auth.route('/add/news', methods=['GET', 'POST'])
@login_required
def add_news():
    x = terms_condition(3)

    if request.method == 'POST':
        content = request.form.get('body')

        cms = Cms(content=content, id=x.id)

        admin_update_data(cms)

        return redirect(url_for('admin_auth.add_news'))

    return render_template('addNews.html', data=current_user, content=x, page='news', common_path=COMMON_PATH)


@admin_auth.route('/view/news', methods=['GET', 'POST'])
@login_required
def view_news():
    x = terms_condition(3)
    return render_template('viewCms.html', data=current_user, content=x, page='news', common_path=COMMON_PATH)


@admin_auth.route('/view/privacy', methods=['GET', 'POST'])
@login_required
def view_privacy():
    x = terms_condition(2)
    return render_template('viewCms.html', data=current_user, content=x, page='privacy', common_path=COMMON_PATH)


@admin_auth.route('/view/terms', methods=['GET', 'POST'])
@login_required
def view_terms():
    x = terms_condition(1)
    return render_template('viewCms.html', data=current_user, content=x, page='terms', common_path=COMMON_PATH)


@admin_auth.route('/view/how_to_use', methods=['GET', 'POST'])
@login_required
def view_how_to_use():
    x = terms_condition(4)
    return render_template('viewCms.html', data=current_user, content=x, page='app_use', common_path=COMMON_PATH)


@admin_auth.route('/view/information', methods=['GET', 'POST'])
@login_required
def view_information():
    x = terms_condition(5)
    return render_template('viewCms.html', data=current_user, content=x, page='info', common_path=COMMON_PATH)


@admin_auth.route('/view/store', methods=['GET', 'POST'])
@login_required
def view_store():
    x = terms_condition(6)
    return render_template('viewCms.html', data=current_user, content=x, page='store', common_path=COMMON_PATH)


@admin_auth.route('/view/brand_deals', methods=['GET', 'POST'])
@login_required
def view_brand_deals():
    x = terms_condition(7)
    return render_template('viewCms.html', data=current_user, content=x, page='brand', common_path=COMMON_PATH)


def send_mail(user):
    token = user.get_token()
    msg = Message('Password Reset Request', recipients=[user.email], sender='testmail62566@gmail.com')
    msg.body = f''' To reset password. Please follow the link below
    {url_for('admin_auth.reset_token', token=token, _external = True)}

    '''

    mail.send(msg)


@admin_auth.route('/admin/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        admin_email = request.form.get('email')
        user = admin_validate(admin_email)

        if not user:
            flash("User Not Found With This Email ", "danger")
            return redirect(url_for('admin_auth.reset_request'))
        if user:
            send_reset_email(user)
            flash("Password Reset Request sent ", 'success')
            return redirect(url_for('admin_auth.admin_login'))
    return render_template('resetRequest.html', common_path=COMMON_PATH)


@admin_auth.route('/admin/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    admin = Admin.verify_token(token)

    if admin is None:
        flash("Invalid or Expire Token ", "danger")
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        admin_password = request.form.get('password')
        admin_confirm_password = request.form.get('confirmPassword')
        hax_password = generate_password_hash(admin_password)

        if admin_password == admin_confirm_password:
            admin.admin_password = hax_password
            db.session.commit()
            flash("Password Reset Sucessfully", "sucess")
            return redirect(url_for('admin_auth.admin_login'))
        else:
            flash("Password  Not Match Try Again.. ", "danger")
            return redirect(url_for('admin_auth.reset_token', token=token))
    return render_template('resetPassword.html', common_path=COMMON_PATH)


@admin_auth.route('/logout')
def logout():
    logout_user()
    flash('Logout successfully', 'info')
    return redirect(url_for('admin_auth.admin_login'))


@admin_auth.route('/blocked_words', methods=['POST', 'GET'])
@login_required
def blocked_words():
    if request.method == 'POST':
        blocked_word = request.form.get('blocked_word')
        blocked_word_data = BlockedWords(blocked_word=blocked_word)

        insert_data(blocked_word_data)
        return redirect(url_for('admin_auth.blocked_words'))
    x = BlockedWords.query.all()
    return render_template('blockWords.html', data=current_user, user_data=x, page='blocked_word', indexing=1,
                           common_path=COMMON_PATH)


@admin_auth.route('/delete_blocked_word/<int:id>', methods=['POST'])
@login_required
def delete_blocked_word(id):
    blocked = BlockedWords.query.get(id)
    db.session.delete(blocked)
    db.session.commit()

    return redirect(url_for('admin_auth.blocked_words'))


@admin_auth.route('/blocked_word/update', methods=['POST', 'GET'])
@login_required
def update_blocked_word():
    id = request.form.get('updateId')
    blocked_word = request.form.get('blocked_word')
    blocked_word_data = BlockedWords(id=id, blocked_word=blocked_word)

    update_data(blocked_word_data)

    return redirect(url_for('admin_auth.blocked_words'))


@admin_auth.route('/add_badges', methods=['POST', 'GET'])
@login_required
def add_badges():
    if request.method == 'POST':
        badge_name = request.form.get('badge_name')
        badge_name_data = Badges(badge_name=badge_name)

        insert_data(badge_name_data)
        return redirect(url_for('admin_auth.add_badges'))
    x = Badges.query.filter(Badges.deleted == False).all()
    return render_template('add_badge.html', data=current_user, user_data=x, page='add_badge', indexing=1,
                           common_path=COMMON_PATH)


@admin_auth.route('/delete_badge/<int:id>', methods=['POST'])
@login_required
def delete_badge(id):
    blocked = Badges.query.get(id)
    blocked.deleted = True
    db.session.commit()

    return redirect(url_for('admin_auth.add_badges'))


@admin_auth.route('/badge/update', methods=['POST', 'GET'])
@login_required
def update_badge():
    id = request.form.get('updateId')
    badge_name = request.form.get('badge_name')
    badge_name_data = Badges(id=id, badge_name=badge_name)

    update_data(badge_name_data)

    return redirect(url_for('admin_auth.add_badges'))


@admin_auth.route('/add_buddys', methods=['POST', 'GET'])
@login_required
def add_buddys():
    if request.method == 'POST':
        type = request.form.get('type')
        buddy_data = Buddys(type=type)

        insert_data(buddy_data)
        return redirect(url_for('admin_auth.add_buddys'))
    x = Buddys.query.filter(Buddys.deleted == False).all()
    return render_template('add_buddy.html', data=current_user, user_data=x, page='add_buddy', indexing=1,
                           common_path=COMMON_PATH)


@admin_auth.route('/delete_buddy/<int:id>', methods=['POST'])
@login_required
def delete_buddy(id):
    blocked = Buddys.query.get(id)
    blocked.deleted = True
    db.session.commit()

    return redirect(url_for('admin_auth.add_buddys'))


@admin_auth.route('/buddy/update', methods=['POST', 'GET'])
@login_required
def update_buddy():
    id = request.form.get('updateId')
    type = request.form.get('type')
    buddy_data = Buddys(id=id, type=type)

    update_data(buddy_data)

    return redirect(url_for('admin_auth.add_buddys'))

