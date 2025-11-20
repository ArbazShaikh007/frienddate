import jwt, os, secrets
from datetime import datetime, timedelta
from flask import request, jsonify, Blueprint
from flask_mail import Mail
from base.user.models import User, token_required
from base.user.queryset import (insert_data, view_data, validate, update_data)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from base.database.db import db
from dotenv import load_dotenv
from base.admin.models import Category
from base.user.models import Block, Report, Notification, FriendRequest, SelectedCategory
from base.admin.queryset import block
from base.push_notification.push_notification import push_notification
from dateutil.relativedelta import relativedelta
import boto3

load_dotenv()

mail = Mail()

REGION_NAME = os.getenv("REGION_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY)
UPLOAD_FOLDER = 'base/static/userResoueces/user_photos/'

user_auth_v6 = Blueprint('user_auth_v6', __name__)

@user_auth_v6.route('/replace_s3', methods=['GET'])
def replace_s3():
    user_data = Category.query.all()
    for i in user_data:
        image_name = 'https://frienddate-app.s3.amazonaws.com/' + i.image_name
        i.image_path = image_name
        db.session.commit()
    return jsonify({'status': 1})

@user_auth_v6.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullName')
        print('fullname...........', fullname)

        age = request.form.get('age')
        print('age ', age)

        email = request.form.get('userEmail')
        print('email ', email)

        password = request.form.get('userPassword')
        print('password ', password)

        phonenumber = request.form.get('userPhonenumber')
        print('phonenumber ', phonenumber)

        country_code = request.form.get('country_code')
        print('country_code', country_code)

        # age_verify = request.form.get('ageVerify')
        # print('age_verify', age_verify)

        device_token = request.form.get('deviceToken')

        device_type = request.form.get('deviceType')

        if not device_token:
            return jsonify({'status':0, 'messege': 'Device token is required'})
        if not device_type:
            return jsonify({'status':0, 'messege': 'Device token is required'})

        # city = request.form.get('city')
        # print('city ', city)
        #
        # state = request.form.get('state')
        # print('state ', state)
        #
        # country = request.form.get('country')
        # print('country ', country)

        # hide_friends = request.form.get('hideFriends')
        # print('hide_friends', hide_friends)

        # gender = request.form.get('gender')
        # print('gender ', gender)

        # sexuality = request.form.get('sexuality'),
        # print('sexuality ', sexuality)

        sexuality = 'Straight'
        #
        # looking_for = request.form.get('lookingFor')
        # print('looking_for', looking_for)
        #
        # relationship_status = request.form.get('relationshipStatus')
        # print('relationship_status', relationship_status)
        #
        # profile_visible_for = request.form.get('visible_for')
        # print('profile_visible_for', profile_visible_for)

        # about_me = request.form.get('about_me')
        # print('about_me ', about_me)

        # college = request.form.get('college')

        user_image = request.files.get('userImage')
        print('user_image', user_image)
        # print('age_verifyyyyyyyyyyyyyyyyyyyy', age_verify)
        # if age_verify == "1":
        #     age_verify = True
        # else:
        #     age_verify = False
        #
        # if gender == '0':
        #     gender = 'Male'
        # elif gender == '1':
        #     gender = 'Female'
        # else:
        #     gender = 'Trans'

        # if looking_for == '0':
        #     looking_for = 'Here for friends'
        # elif looking_for == '1':
        #     looking_for = 'Here for dating'
        # else:
        #     looking_for = 'Here for friends and dating'
        #
        # if relationship_status == '0':
        #     relationship_status = 'Single'
        # elif relationship_status == '1':
        #     relationship_status = 'in a relationship'
        # else:
        #     relationship_status = 'Married'
        #
        # if sexuality == '0':
        #     sexuality = 'Straight'
        # elif sexuality == '1':
        #     sexuality = 'Bisexual'
        # elif sexuality == '2':
        #     sexuality = 'Gay'
        # else:
        #     sexuality = 'Other'

        hash_password = generate_password_hash(password)
        user = validate(email)
        # date_obj = datetime.strptime(age, '%Y-%m-%d').date()

        if user:
            return jsonify({'status': 0, 'messege': 'User Already Exits'})

        if not user:
            username_check = User.query.filter_by(fullname=fullname).first()
            phonenumber_check = User.query.filter_by(country_code=country_code, phonenumber=phonenumber).first()

            if username_check:
                return jsonify({'status': 0, 'messege': 'Already taken this username please choose another one'})
            if phonenumber_check:
                return jsonify({'status': 0, 'messege': 'This phonenumber already in use'})

            image_url = 'https://frienddate-app.s3.amazonaws.com/conprofile.png'
            image_name = 'conprofile.png'

            if user_image:
                print('Trueeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')

                image_name = secure_filename(user_image.filename)
                extension = os.path.splitext(image_name)[1]
                extension2 = os.path.splitext(image_name)[1][1:].lower()

                content_type = f'image/{extension2}'
                x = secrets.token_hex(10)

                image_name = x + extension

                s3_client.upload_fileobj(user_image, S3_BUCKET, image_name,
                                         ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
                image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

            user_data = User(
                               sexuality=sexuality,
                             fullname=fullname, email=email, country_code=country_code, device_token=device_token,
                             device_type=device_type,
                             phonenumber=phonenumber, password=hash_password,
                             image_path=image_url, image_name=image_name,
                             created_time=datetime.utcnow())
            insert_data(user_data)

            token = jwt.encode({'id': user_data.id, 'exp': datetime.utcnow() + timedelta(days=365)},
                                   '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')
            return jsonify({'status': 1, 'messege': 'success', 'data': user_data.as_dict(), 'token': token})


@user_auth_v6.route('/login', methods=['POST'])
def user_login():
    if request.method == 'POST':
        email = request.json.get('userEmail')
        password = request.json.get('userPassword')
        device_token = request.json.get('device_token')
        device_type = request.json.get('device_type')

        if not device_token:
            return jsonify({'status':0, 'messege': 'Device token is required'})
        if not device_type:
            return jsonify({'status':0, 'messege': 'Device token is required'})

        check_email = validate(email)

        if not check_email:
            return {'status': 0, 'message': 'User Not Exits'}

        if check_email.is_block == True:
            return jsonify({'status': 0, 'messege': 'You Are Block By Admin'})
        if check_email.deleted == True:
            return jsonify({'status': 0, 'messege': 'You Deleted Your Account'})

        if check_email and check_email.check_password(password):
            none_exitsting_device_token = User.query.all()
            for i in none_exitsting_device_token:
                if i.device_token == device_token:
                    if i.is_subscription_badge == True:
                        check_email.is_subscription_badge = True
                        check_email.subscription_start_time_badge = i.subscription_start_time_badge
                        check_email.subscription_end_time_badge = i.subscription_end_time_badge
                        check_email.badge_name = i.badge_name
                        check_email.product_id_badge = i.product_id_badge
                        check_email.transaction_id_badge = i.transaction_id_badge
                        check_email.purchase_date_badge = i.purchase_date_badge
                    i.device_token = None
                    i.device_type = None
                    db.session.commit()
            check_email.device_token = device_token
            check_email.device_type = device_type
            check_email.id = check_email.id
            db.session.commit()

            if check_email.is_block == True:
                return jsonify({'status': 0, 'messege': 'You Are Block By Admin'})
            if check_email.double_verification == True:
                check_email.otp_verify = False
                db.session.commit()

            token = jwt.encode({'id': check_email.id, 'exp': datetime.utcnow() + timedelta(days=365)},
                               '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')
            return jsonify(
                {'status': 1, 'message': 'login successfully', 'data': check_email.as_dict(), 'token': token})
        else:
            return jsonify({'status': 0, 'message': 'Wrong Password'})


@user_auth_v6.route('/social_register', methods=['POST'])
def social_register():
    if request.method == 'POST':
        social_id = request.json.get('social_id')
        social_type = request.json.get('social_type')
        device_token = request.json.get('device_token')
        device_type = request.json.get('device_type')
        email = request.json.get('userEmail')
        fullname = request.json.get('fullName')
        if not fullname:
            return jsonify({'status': 0, 'messege': 'fullname is required'})

        none_exitsting_device_token = User.query.all()
        for i in none_exitsting_device_token:
            if i.device_token == device_token:
                i.device_token = None
                i.device_type = None
                db.session.commit()

        check_user = User.query.filter_by(email=email).first()
        user = User.query.filter_by(social_id=social_id).first()

        if check_user and check_user.social_id == None:
            if check_user.deleted == True:
                return jsonify({'status': 1, 'messege': 'You cannot use same email which account you deleted already'})
            if check_user.is_block == True:
                return jsonify({'status': 1, 'messege': 'Your account by this email is block by admin'})
            return jsonify({'status': 1, 'message': 'User already exist'})

        if user:

            token = jwt.encode({'id': user.id, 'exp': datetime.utcnow() + timedelta(days=365)},
                               '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')
            return jsonify({'status': 1, 'messege': 'Login successfully', 'data': user.as_dict(), 'token': token})

        elif not user:

            user_data = User(fullname=fullname,email=email,social_id=social_id, social_type=social_type,
                             is_social_login=True,
                             is_completed_profile=False, device_token=device_token, device_type=device_type,
                              created_time=datetime.utcnow(),
                             image_path="https://frienddate-app.s3.amazonaws.com/conprofile.png"
                             )
            insert_data(user_data)

            token = jwt.encode({'id': user_data.id, 'exp': datetime.utcnow() + timedelta(days=365)},
                               '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')
            to_ids = [76,79]

            for i in to_ids:
                follow_user = Follow(by_id = user_data.id,to_id = i)
                db.session.add(follow_user)
                db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully registered', 'data': user_data.as_dict(), 'token': token})

@user_auth_v6.route("/token_verification")
@token_required
def token_verification(active_user):
    active_user.otp_verify = True
    db.session.commit()
    token = jwt.encode({'id': active_user.id, 'exp': datetime.utcnow() + timedelta(days=365)},
                       '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')

    return jsonify({'status': 1, 'message': 'OTP Verified', 'data': active_user.as_dict(), 'token': token})


@user_auth_v6.route('/change_pwd', methods=['POST'])
@token_required
def change_password(active_user):
    new_pwd = request.json.get('newPassword')
    confirm_pwd = request.json.get('confirmPassword')

    hash_password = generate_password_hash(new_pwd)

    if new_pwd == confirm_pwd:
        user_data = User(password=hash_password, id=active_user.id)

        update_data(user_data)

        return jsonify({'status': 1, 'message': 'Sucessfully Changed Password'})

    else:
        return jsonify({'status': 0, 'message': 'New Password Not Match'})

@user_auth_v6.route('/user_update', methods=['POST', 'GET'])
@token_required
def user_update(active_user):
    age = ''
    if active_user.age is not None:
        birthdate_datetime = datetime.combine(active_user.age, datetime.min.time())
        age = (datetime.utcnow() - birthdate_datetime).days // 365

    id = request.form.getlist('category_id')

    current_timestamp_ms = int(datetime.now().timestamp() * 1000)

    if active_user.is_subscription_badge == True:

        if int(active_user.subscription_start_time_badge) <= current_timestamp_ms <= int(
                active_user.subscription_end_time_badge):
            pass
        else:
            active_user.is_subscription_badge = False
            active_user.subscription_start_time_badge = None
            active_user.subscription_end_time_badge = None
            active_user.badge_name = None
            active_user.product_id_badge = None
            active_user.transaction_id_badge = None
            active_user.purchase_date_badge = None
            db.session.commit()

    if request.method == 'POST':
        fullname = request.form.get('userName')
        height = request.form.get('height')
        drink = request.form.get('drink')
        smoke = request.form.get('smoke')
        city = request.form.get('city')
        state = request.form.get('state')
        country = request.form.get('country')
        hide_friends = request.form.get('hideFriends')
        gender = request.form.get('gender')
        sexuality = request.form.get('sexuality')
        looking_for = request.form.get('lookingFor')
        relationship_status = request.form.get('relationshipStatus')
        profile_visible_for = request.form.get('visible_for')
        description_box = request.form.get('description_box')
        user_image = request.files.get('userImage')

        about_me = request.form.get('about_me')
        college = request.form.get('college')
        new_bio = request.form.get('new_bio')
        is_profile_private = request.form.get('is_profile_private')

        if gender == '0':
            gender = 'Male'
        elif gender == '1':
            gender = 'Female'
        elif gender == '2':
            gender = 'Trans'
        else:
            gender = None

        if looking_for == '0':
            looking_for = 'Here for friends'
        elif looking_for == '1':
            looking_for = 'Here for dating'
        elif looking_for == '2':
            looking_for = 'Here for friends and dating'
        else:
            looking_for = None

        if relationship_status == '0':
            relationship_status = 'Single'
        elif relationship_status == '1':
            relationship_status = 'in a relationship'
        elif relationship_status == '2':
            relationship_status = 'Married'
        else:
            relationship_status = None

        if sexuality == '0':
            sexuality = 'Straight'
        elif sexuality == '1':
            sexuality = 'Bisexual'
        elif sexuality == '2':
            sexuality = 'Gay'
        elif sexuality == '3':
            sexuality = 'Other'
        else:
            sexuality = None

        if user_image:

            if active_user.image_name != 'conprofile.png':
                s3_client.delete_object(Bucket=S3_BUCKET, Key=active_user.image_name)

            image_name = secure_filename(user_image.filename)
            extension = os.path.splitext(image_name)[1]
            extension2 = os.path.splitext(image_name)[1][1:].lower()

            content_type = f'image/{extension2}'
            x = secrets.token_hex(10)

            image_name = x + extension

            s3_client.upload_fileobj(user_image, S3_BUCKET, image_name,
                                     ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
            image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

            user_data = User(is_profile_private=is_profile_private,new_bio = new_bio,college=college, about_me=about_me, description_box=description_box, id=active_user.id,
                             email=active_user.email,
                             phonenumber=active_user.phonenumber, password=active_user.password, fullname=fullname,
                             height=height,
                             drink=drink, smoke=smoke, age=active_user.age, city=city, state=state, country=country,
                             hide_friends=hide_friends, gender=gender, sexuality=sexuality, looking_for=looking_for,
                             relationship_status=relationship_status, profile_visible_for=profile_visible_for,
                             image_name=image_name, image_path=image_url)

            update_data(user_data)
        else:

            user_data = User(is_profile_private=is_profile_private,new_bio = new_bio,college=college, about_me=about_me, description_box=description_box, id=active_user.id,
                             email=active_user.email,
                             phonenumber=active_user.phonenumber,
                             password=active_user.password, fullname=fullname, height=height,
                             drink=drink, smoke=smoke, age=active_user.age, city=city, state=state, country=country,
                             hide_friends=hide_friends, gender=gender, sexuality=sexuality, looking_for=looking_for,
                             relationship_status=relationship_status, profile_visible_for=profile_visible_for,
                             image_name=active_user.image_name, image_path=active_user.image_path)

            update_data(user_data)

        if active_user.gender == 'Male':
            gender = '0'
        elif active_user.gender == 'Female':
            gender = '1'
        elif active_user.gender == 'Trans':
            gender = '2'
        else:
            gender = ''

        if active_user.sexuality == 'Straight':
            sexuality = '0'
        elif active_user.sexuality == 'Bisexual':
            sexuality = '1'

        elif active_user.sexuality == 'Gay':
            sexuality = '2'

        elif active_user.sexuality == 'Other':
            sexuality = '3'
        else:
            sexuality = ''

        if active_user.looking_for == 'Here for friends':
            looking_for = '0'
        elif active_user.looking_for == 'Here for dating':
            looking_for = '1'
        elif active_user.looking_for == 'Here for friends and dating':
            looking_for = '2'

        else:
            looking_for = ''

        if active_user.relationship_status == 'Single':
            relationship_status = '0'
        elif active_user.relationship_status == 'in a relationship':
            relationship_status = '1'

        elif active_user.relationship_status == 'Married':
            relationship_status = '2'

        else:
            relationship_status = ''

        description_box = ""
        if active_user.description_box != None:
            description_box = active_user.description_box
        else:
            description_box = ""

        badge_name = ""
        if active_user.badge_name is not None:
            badge_name = active_user.badge_name

        college_value = ""
        if active_user.college is not None:
            college_value = active_user.college
        if is_profile_private and is_profile_private != '':
            active_user.is_profile_private = is_profile_private

        users_data = {'id': str(active_user.id),
                      'age': str(age),
                      'city': active_user.city,
                      'country': active_user.country,
                      'state': active_user.state,
                      'username': active_user.fullname,
                      'user_image': active_user.image_path,
                      'email': active_user.email,
                      'height': active_user.height,
                      'drink': active_user.drink,
                      'smoke': active_user.smoke,
                      'hide_friends': active_user.hide_friends,
                      'gender': gender,
                      'sexuality': sexuality,
                      'what_relationship_are_you_here_for': looking_for,
                      'relationship_status': relationship_status,
                      'profile_visible_for': active_user.profile_visible_for,
                      'description_box': description_box,
                      'is_subscription': active_user.is_subscription,
                      'is_subscription_badge': active_user.is_subscription_badge,

                      'buddy_list': [],
                      'coffe_badge': "I'll Buy Us Coffee",
                      'food_badge': "I'll Buy Us Food",
                      'fancy_badge': "I'll Buy Us Food & Drinks",
                      'badge_name': badge_name,
                      'about_me': active_user.about_me,
                      'college': college_value,
                       'new_bio': active_user.new_bio if active_user.new_bio is not None else '',
                      'is_profile_private': active_user.is_profile_private

                      }

        ls = []
        if len(id) > 0 and id[0] != "":

            if not len(active_user.category_id) > 0:

                join_id = ",".join(id)
                ob = SelectedCategory(category_id=join_id, user_id=active_user.id)
                insert_data(ob)

                selected_list = []
                categories = Category.query.all()
                selected_by = SelectedCategory.query.filter_by(user_id=active_user.id).first()

                if selected_by:
                    objs = selected_by.category_id
                    split = objs.split(',')

                    selected_list.extend(split)

                cat_list = []

                for cat in categories:
                    if str(cat.id) in selected_list:
                        is_category = True
                    else:
                        is_category = False

                    cat_dict = cat.as_dict()
                    status = {'category_id': cat.id,
                              'category_name': cat.category_name,
                              'is_category': is_category}
                    cat_list.append(status)

                add_dict = {'categories': cat_list}
                users_data.update(add_dict)
                if len(users_data) != 0:
                    return jsonify({'status': 1, 'message': 'Profile Updated', 'data': users_data})
                else:
                    return jsonify({'status': 1, 'message': 'Page Not Reach At This Time Please Try Again Later'})

            else:
                x = SelectedCategory.query.filter_by(user_id=active_user.id).first()
                category_idss = x.category_id.split(',')
                idss = id[0].split(',')
                print('idssssssssssssssssssssssssssssssssssssssssssssssss', idss)
                id = list(set(idss))

                x.category_id = ",".join(id)
                x.id = x.id
                db.session.commit()

                selected_list = []
                categories = Category.query.all()
                selected_by = SelectedCategory.query.filter_by(user_id=active_user.id).first()

                if selected_by:
                    objs = selected_by.category_id
                    split = objs.split(',')

                    selected_list.extend(split)

                cat_list = []

                for cat in categories:
                    if str(cat.id) in selected_list:
                        is_category = True
                    else:
                        is_category = False

                    status = {'category_id': cat.id,
                              'category_name': cat.category_name,
                              'is_category': is_category}
                    # cat_dict.update(status)
                    cat_list.append(status)

                add_dict = {'categories': cat_list}
                users_data.update(add_dict)

                if len(users_data) != 0:
                    return jsonify({'status': 1, 'message': 'Profile Updated', 'data': users_data})
                else:
                    return jsonify({'status': 1, 'message': 'Page Not Reach At This Time Please Try Again Later'})

        if not len(id) > 0 or id[0] == "":
            catss = []
            xyz = SelectedCategory.query.filter_by(user_id=active_user.id).first()
            if xyz:
                db.session.delete(xyz)
                db.session.commit()
            categories = Category.query.all()
            for cats in categories:
                dict = {'category_id': cats.id,
                        'category_name': cats.category_name,
                        'is_category': False}
                catss.append(dict)
            xy = {'categories': catss}
            users_data.update(xy)
            if len(users_data) != 0:
                return jsonify({'status': 1, 'message': 'Profile Updated', 'data': users_data})
            else:
                return jsonify({'status': 1, 'message': 'Page Not Reach At This Time Please Try Again Later'})

    active_user.as_dict()

    if active_user.gender == 'Male':
        gender = '0'
    elif active_user.gender == 'Female':
        gender = '1'
    elif active_user.gender == 'Trans':
        gender = '2'
    else:
        gender = ''

    if active_user.sexuality == 'Straight':
        sexuality = '0'
    elif active_user.sexuality == 'Bisexual':
        sexuality = '1'

    elif active_user.sexuality == 'Gay':
        sexuality = '2'

    elif active_user.sexuality == 'Other':
        sexuality = '3'
    else:
        sexuality = ''

    if active_user.looking_for == 'Here for friends':
        looking_for = '0'
    elif active_user.looking_for == 'Here for dating':
        looking_for = '1'
    elif active_user.looking_for == 'Here for friends and dating':
        looking_for = '2'

    else:
        looking_for = ''

    if active_user.relationship_status == 'Single':
        relationship_status = '0'
    elif active_user.relationship_status == 'in a relationship':
        relationship_status = '1'

    elif active_user.relationship_status == 'Married':
        relationship_status = '2'

    else:
        relationship_status = ''

    description_box = ""
    if active_user.description_box != None:
        description_box = active_user.description_box
    else:
        description_box = ""

    badge_name = ""
    if active_user.badge_name is not None:
        badge_name = active_user.badge_name

    college_value = ""
    if active_user.college is not None:
        college_value = active_user.college
    total_data = {'id': str(active_user.id),
                  'age': str(age),
                  'city': active_user.city,
                  'country': active_user.country,
                  'state': active_user.state,
                  'username': active_user.fullname,
                  'user_image': active_user.image_path,
                  'email': active_user.email,
                  'height': active_user.height,
                  'drink': active_user.drink,
                  'smoke': active_user.smoke,
                  'hide_friends': active_user.hide_friends,
                  'gender': gender,
                  'sexuality': sexuality,
                  'what_relationship_are_you_here_for': looking_for,
                  'relationship_status': relationship_status,
                  'profile_visible_for': active_user.profile_visible_for,
                  'description_box': description_box,
                  'is_subscription': active_user.is_subscription,
                  'is_subscription_badge': active_user.is_subscription_badge,

                  'buddy_list': [],
                  'coffe_badge': "I'll Buy Us Coffee",
                  'food_badge': "I'll Buy Us Food",
                  'fancy_badge': "I'll Buy Us Food & Drinks",
                  'badge_name': badge_name,
                  'about_me': active_user.about_me,
                  'college': college_value,
                       'new_bio': active_user.new_bio if active_user.new_bio is not None else '',
                  'is_profile_private': active_user.is_profile_private

                  }

    add_dict = {'categories': []}
    total_data.update(add_dict)
    return jsonify({'status': 1, 'data': total_data, 'messege': 'Success'})

@user_auth_v6.route('/double_verification', methods=['POST'])
@token_required
def double_verification(active_user):
    value = request.json.get('value')
    if value == False:
        active_user.double_verification = False
        db.session.commit()

        return jsonify({'status': 1, 'is_double_verification': active_user.double_verification,
                        'messege': 'double verification applied'})

    if value == True:
        active_user.double_verification = True
        db.session.commit()
        return jsonify({'status': 1, 'is_double_verification': active_user.double_verification,
                        'messege': 'double verification removed'})


@user_auth_v6.route("/user_to_user/block", methods=['POST'])
@token_required
def block_user_to_user(active_user):
    id = request.json.get('user_id')

    user = block(id)

    x = Block.query.filter_by(user_id=active_user.id, blocked_user=user.id).first()

    if x:
        db.session.delete(x)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Succcesfully Unblock User', 'is_block': 0})

    if not x:
        check = Block(user_id=active_user.id, blocked_user=user.id, is_block=True)
        db.session.add(check)
        db.session.commit()
        check = FriendRequest.query.filter_by(to_id=active_user.id, by_id=id).first()

        checked = FriendRequest.query.filter_by(by_id=active_user.id, to_id=id).first()

        if check:
            db.session.delete(check)
            db.session.commit()
        if checked:
            db.session.delete(checked)
            db.session.commit()

        return jsonify({'status': 1, 'messege': 'Succcesfully Block User', 'is_block': 1})


@user_auth_v6.route("/block_list", methods=['GET'])
@token_required
def block_list(active_user):
    blocked_list = []

    for i in active_user.user_id:
        user_info = User.query.filter_by(id=i.blocked_user, deleted=False).first()
        blocked_dict = {
            'user_id': user_info.id,
            'username': user_info.fullname,
            'user_image': user_info.image_path}
        blocked_list.append(blocked_dict)
    if len(blocked_list) > 0:
        return jsonify({'status': 1, 'list': blocked_list})
    else:
        return jsonify({'status': 0, 'list': [], 'messege': 'You Not Blocked Anyone Yet'})


@user_auth_v6.route("/user/report", methods=['POST'])
@token_required
def user_report(active_user):
    id = request.json.get('user_id')
    messege = request.json.get('messege')
    y = Report.query.filter_by(user_id=active_user.id, reported_user=id).first()
    if not y:
        x = Report(user_id=active_user.id, reported_user=id, messege=messege, reported_time=datetime.utcnow())
        db.session.add(x)
        db.session.commit()
        return jsonify({'status': 1, 'report_data': x.as_dict()})
    else:
        return jsonify({'status': 0, 'messege': 'You Already Reported This User'})


@user_auth_v6.route("/user/forget_password", methods=['POST'])
def user_forget_password():
    country_code = request.json.get('country_code')
    phonenumber = request.json.get('phonenumber')

    x = User.query.filter_by(country_code=country_code, phonenumber=phonenumber).first()
    if x:
        token = jwt.encode({'id': x.id, 'exp': datetime.utcnow() + timedelta(days=365)},
                           '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')

        return jsonify({'status': 1, 'messege': 'Otp Successfully Send Your Number', 'token': token})
    else:
        return jsonify(
            {'status': 0, 'messege': 'Dont Have Any Account With This Number!! Please Verify Your Number Again !!'})


@user_auth_v6.route("/user/new_password", methods=['POST'])
@token_required
def user_new_password(active_user):
    new_password = request.json.get('new_password')
    confirm_password = request.json.get('confirm_password')

    hash_password = generate_password_hash(new_password)

    if new_password == confirm_password:

        user_data = User(password=hash_password, id=active_user.id)

        update_data(user_data)

        return jsonify({'status': 1, 'messege': 'Sucessfully Changed Password'})

    else:
        return jsonify({'status': 0, 'messege': 'New Password Not Match'})


@user_auth_v6.route("/subscription", methods=['POST'])
@token_required
def user_subscription(active_user):
    product_id = request.json.get('product_id')
    if not product_id:
        return jsonify({'status': 0, 'messege': 'Product id required'})
    else:
        active_user.id = active_user.ids
        active_user.is_subscription = True
        active_user.product_id = product_id

        active_user.subscription_price = "5.99"
        active_user.subscription_start_time = datetime.utcnow()
        active_user.subscription_end_time = datetime.utcnow() + relativedelta(months=1)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Sucessfully get subscription'})


@user_auth_v6.route('/add_image_s', methods=['GET', 'POST'])
def add_image_s():
    image = request.files.get('image')
    picture_fn = secure_filename(image.filename)
    s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                             aws_secret_access_key=SECRET_KEY)
    s3_client.upload_fileobj(image, S3_BUCKET, picture_fn, ExtraArgs={'ACL': 'public-read'})
    image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{picture_fn}"
    return jsonify({"image": image_url})