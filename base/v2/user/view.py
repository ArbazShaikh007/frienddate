from flask import redirect, render_template, request, flash, jsonify, url_for, Blueprint
from base.user.queryset import view_data
from base.user.models import token_required, FriendRequest, User, SelectedCategory, DateRequest, Report, TagFriends, \
    ChatMute, Notification, Block, TblCountries, TblStates
from base.user.queryset import insert_data, sent_frnd_req, delete_frnd_req, update_data, check_cat_id, delete_cat
from base.admin.models import Category, Cms, Faqs
from base import db
from base.community.models import SavedCommunity, CreatedCommunity, CommunityPost
from base.admin.queryset import terms_condition
import pprint
from datetime import datetime
from base.common.utiils import COMMON_URL
from base.push_notification.push_notification import push_notification
from base.community.queryset import get_community_chat
import pandas as pd, os, secrets, chardet
from datetime import datetime
import requests
from sqlalchemy import and_
from flask_sqlalchemy import Pagination
import random
from sqlalchemy.sql.expression import func
from sqlalchemy import text

user_view_v2 = Blueprint('user_view_v2', __name__)


# hi

@user_view_v2.route('/homepage_verify_token', methods=['POST'])
@token_required
def homepage_verify_token(active_user):
    data = request.get_json()
    receipt_data = data['receipt']
    product_id = data['product_id']
    print(
        'homeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')
    print('product_iddddddddddddddddddddddddddddddddddddddddddd', product_id)
    # if receipt_data:

    # In production, use 'https://buy.itunes.apple.com/verifyReceipt'
    # VERIFY_RECEIPT_URL = 'https://sandbox.itunes.apple.com/verifyReceipt'


    # Your shared secret from App Store Connect
    SHARED_SECRET = '8a0d876692da43a18044a99680c8dbf8'
    VERIFY_RECEIPT_URL = 'https://buy.itunes.apple.com/verifyReceipt'

    response = requests.post(
        VERIFY_RECEIPT_URL,
        json={
            'receipt-data': receipt_data,
            'password': SHARED_SECRET,
            'exclude-old-transactions': True
        }
    )
    if response.status_code == 200:
        receipt_info = response.json()
        print('receipt_infoooooooooooooooooooooooooooooooooooooooooooooooooooooooooorrrrr', receipt_info)
        if receipt_info.get('status') == 0 and receipt_info.get('latest_receipt_info'):
            entry1 = receipt_info['latest_receipt_info']

            found = False
            for entry in entry1:
                if entry['product_id'] == product_id:
                    found = True
                    current_timestamp_ms = int(datetime.now().timestamp() * 1000)
                    if int(entry['purchase_date_ms']) <= current_timestamp_ms <= int(entry['expires_date_ms']):
                        return jsonify({"status": 1, "messege": "Verified"})
                    else:
                        active_user.is_subscription_badge = False
                        active_user.subscription_start_time_badge = None
                        active_user.subscription_end_time_badge = None
                        # active_user.subscription_price = None
                        active_user.product_id_badge = None
                        active_user.transaction_id_badge = None
                        active_user.purchase_date_badge = None
                        active_user.badge_name = None

                        db.session.commit()
                        return jsonify({"status": 1, "messege": "Expired"})
                    break
            return jsonify({"status": 0, "messege": "Invalid product id."})
    else:
        active_user.is_subscription_badge = False
        active_user.subscription_start_time_badge = None
        active_user.subscription_end_time_badge = None
        # active_user.subscription_price = None
        active_user.product_id_badge = None
        active_user.transaction_id_badge = None
        active_user.purchase_date_badge = None
        active_user.badge_name = None

        db.session.commit()

        return jsonify({"status": 0, "messege": "Not purchashed"})
        # else:
        # return jsonify({"status": 0,"messege": "You not sending recipt"})


@user_view_v2.route('/homepage', methods=['POST'])
@token_required
def homepage(active_user):
    device_token = request.json.get('device_token')
    device_type = request.json.get('device_type')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    active_user.device_token = device_token
    active_user.device_type = device_type
    active_user.id = active_user.id
    db.session.commit()

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    active_user_saved_ids = [j.created_id for j in active_user.save_community_id]

    # Subquery to count matches for each user based on active_user's saved_community_id
    matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('matches'))
                    .join(User, User.id == SavedCommunity.user_id)
                    .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
                    .group_by(SavedCommunity.user_id)
                    .subquery())

    # Main query that joins the matches subquery and orders by the number of matches
    user_data = (db.session.query(User, matches_subq.c.matches)
                 .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
                 .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
                 .filter(~User.id.in_(blocked_user_ids))
                 .filter(~User.id.in_(blocked_by_user_ids))
                 .order_by(matches_subq.c.matches.desc()).paginate(page=page, per_page=per_page, error_out=False))
    response_list = []

    saved_my_favorites = []

    for j in active_user.save_community_id:
        saved_my_favorites.append(j.created_id)

    if user_data.items:
        for specific_response, count in user_data.items:
            count_value = str(count)
            if not count:
                count_value = '0'

            badge = ""
            if specific_response.badge_name is not None:
                if specific_response.badge_name == "I'll Buy Us Coffee":
                    badge = "â˜•"
                if specific_response.badge_name == "I'll Buy Us Food":
                    badge = "ðŸ”"
                    # badge = specific_response.badge_name
            college = ""
            if specific_response.college is not None:
                college = specific_response.college
            sexuality = ""
            if specific_response.sexuality is not None:
                sexuality = specific_response.sexuality

            relationship_status = ""
            if specific_response.relationship_status is not None:
                relationship_status = specific_response.relationship_status

            looking_for = ""
            if specific_response.looking_for is not None:
                looking_for = specific_response.looking_for

            response_dict = {'user_id': str(specific_response.id),
                             'user_name': specific_response.fullname,
                             'user_image': specific_response.image_path,
                             'state': specific_response.state,
                             'city': specific_response.city,
                             'badge': badge,
                             'matches_count': count_value,
                             'about_me': specific_response.about_me,
                             'college': college,
                             'sexuality': sexuality,
                             'relationship_status': relationship_status,
                             'looking_for': looking_for,

                             }
            response_list.append(response_dict)

    has_next = user_data.has_next  # Check if there is a next page
    total_pages = user_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if len(response_list) > 0:
        # sorted_list = sorted(response_list, key=lambda x: x['matches_count'], reverse=True)
        return jsonify({'status': 1, 'data': response_list, 'messege': 'Sucess', 'pagination': pagination_info})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You have zero matches. Click on Save to get started'})


# @user_view_v2.route('/homepage', methods=['POST'])
# @token_required
# def homepage(active_user):
#     device_token = request.json.get('device_token')
#     device_type = request.json.get('device_type')
#     page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#     per_page = 10  # Number of items per page
#
#     active_user.device_token = device_token
#     active_user.device_type = device_type
#     active_user.id = active_user.id
#     db.session.commit()
#     list = [i for i in view_data()]
#     list.remove(active_user)
#     block_check = Block.query.filter_by(blocked_user=active_user.id).all()
#     if len(block_check) > 0:
#         for b in block_check:
#             user_block_info = User.query.filter_by(id=b.user_id).first()
#             list.remove(user_block_info)
#     list1 = []
#     userList = []
#
#     for k in active_user.save_community_id:
#         list1.append(k.created_id)
#
#     for j in list:
#         dict1 = j.as_dict()
#
#         list2 = [i.created_id for i in j.save_community_id]
#
#         common_list = [x for x in list1 if x in list2]
#         dict1.update({'matched_count': len(common_list)})
#
#         if dict1['matched_count'] != 0:
#             userList.append(dict1)
#
#     user_list = sorted(userList, key=lambda x: x['matched_count'], reverse=True)
#
#     filter_data = []
#     response_list = []
#     for search in user_list:
#         check_delete = User.query.filter_by(id=search['id'], deleted=False).first()
#         if check_delete:
#
#             birthdate_datetime = datetime.combine(search['age'], datetime.min.time())
#             age = (datetime.utcnow() - birthdate_datetime).days // 365
#
#             if search['looking_for'] in ['Friends', 'Dating'] and search['gender'] in ["Male", "Female"] and search[
#                 'sexuality'] == "Straight" and "18" <= str(age) <= "40" and search[
#                 'relationship_status'] == "Single":
#                 filter_data.append(search)
#     for specific_response in filter_data:
#         response_dict = {'user_id': str(specific_response['id']),
#                          'user_name': specific_response['username'],
#                          'user_image': specific_response['user_image'],
#                          'state': specific_response['state'],
#                          'city': specific_response['city'],
#                          'matches_count': specific_response['matched_count']}
#
#         response_list.append(response_dict)
#     notification_count = Notification.query.filter(
#         and_(Notification.title != 'Friends', Notification.to_id == active_user.id,
#              Notification.is_read == False)).count()
#
#     friend_request_count = Notification.query.filter_by(to_id=active_user.id, is_read=False, title='Friends').count()
#
#     # Calculate the start and end indices for the current page
#     start_index = (page - 1) * per_page
#     end_index = start_index + per_page
#
#     # Slice the list to get the records for the current page
#     current_page_records = response_list[start_index:end_index]
#
#     # Calculate total pages and whether there is a next page
#     total_items = len(response_list)
#     total_pages = (total_items + per_page - 1) // per_page
#     has_next = page < total_pages
#
#     # Pagination information
#     pagination_info = {
#         "current_page": page,
#         "has_next": has_next,
#         "per_page": per_page,
#         "total_pages": total_pages,
#     }
#
#     if len(response_list) != 0:
#         return jsonify({'status': 1, 'data': current_page_records, 'messege': 'Sucess',
#                         'notification_count': str(notification_count), 'is_subscription': active_user.is_subscription,
#                         'friend_request_count': str(friend_request_count), 'pagination': pagination_info})
#     else:
#         return jsonify({'status': 1, 'data': [], 'messege': 'You have zero matches. Click on Save to get started',
#                         'notification_count': str(notification_count), 'is_subscription': active_user.is_subscription,
#                         'friend_request_count': str(friend_request_count)})




@user_view_v2.route('/homepage_filter', methods=['GET', 'POST'])
@token_required
def homepage_filter(active_user):
    if request.method == 'POST':
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 10  # Number of items per page

        current_date = func.current_date()
        blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
        blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

        # relationships = request.json.get('relationships')
        # relationships_list = []
        # if relationships == 0:
        #     relationships_list.append('Friends')
        #
        # if relationships == 1:
        #     relationships_list.append("Dating")
        # if relationships == 2:
        #     relationships_list.extend(["Friends", "Dating"])

        gender = request.json.get('gender')
        print('genderrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr', gender)
        gender_list = []
        if gender == 0:
            gender_list.append("Male")
        if gender == 1:
            gender_list.append("Female")
        # if gender == 2:
        #     gender_list.append("Other")
        if gender == 2:
            gender_list.extend(['Male', 'Female'])

        age_start = request.json.get('age_start')
        print('age_starttttttttttttttttttttttttttttttttttttttttttttt', age_start)

        age_end = request.json.get('age_end')
        print('age_enddddddddddddddddddddddddddddddddddddddddddddddd', age_end)

        # sexuality = request.json.get('sexuality')
        # if sexuality == 0:
        #     sexuality = "Straight"
        # if sexuality == 1:
        #     sexuality = "Biesexual"
        # if sexuality == 2:
        #     sexuality = "Gay"
        # if sexuality == 3:
        #     sexuality = "Other"
        # relationship_status = request.json.get('relationship_status')
        # if relationship_status == 0:
        #     relationship_status = "Single"
        # if relationship_status == 1:
        #     relationship_status = "In a Relationship"
        # if relationship_status == 2:
        #     relationship_status = "Married"
        # if relationship_status == 3:
        #     relationship_status = "Other"

        country = request.json.get('country')
        print('countryyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', country)
        state = request.json.get('state')
        print('stateeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', state)
        city = request.json.get('city')
        print('cityyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', city)

        # age_expression = func.timestampdiff(text('YEAR'), User.age, current_date)

        active_user_saved_ids = [j.created_id for j in active_user.save_community_id]

        # Subquery for match counts
        matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('matches'))
                        .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
                        .group_by(SavedCommunity.user_id)
                        .subquery())

        # Filters for age between age_start and age_end
        # age_filter = and_(age_expression >= age_start, age_expression <= age_end)
        query = (db.session.query(User, matches_subq.c.matches).outerjoin(matches_subq,
                                                                          User.id == matches_subq.c.user_id).filter(
            User.gender.in_(gender_list),
            User.id != active_user.id,
            User.is_block != True, User.deleted != True,
            User.id.not_in(blocked_user_ids),
            User.id.not_in(blocked_by_user_ids)).order_by(matches_subq.c.matches.desc()))
        if country:
            query = query.filter(func.lower(User.country) == country.lower())
        if state:
            query = query.filter(func.lower(User.state) == state.lower())
        if city:
            query = query.filter(func.lower(User.city) == city.lower())

        user_list = query.paginate(page=page, per_page=per_page, error_out=False)
        has_next = user_list.has_next  # Check if there is a next page
        total_pages = user_list.pages  # Total number of pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        response_list = []
        if user_list.items:
            for specific_response, count in user_list.items:
                count_value = str(count)
                if not count:
                    count_value = '0'
                badge = ""
                if specific_response.badge_name is not None:
                    badge = specific_response.badge_name

                college = ""
                if specific_response.college is not None:
                    college = specific_response.college
                sexuality = ""
                if specific_response.sexuality is not None:
                    sexuality = specific_response.sexuality

                relationship_status = ""
                if specific_response.relationship_status is not None:
                    relationship_status = specific_response.relationship_status

                looking_for = ""
                if specific_response.looking_for is not None:
                    looking_for = specific_response.looking_for

                response_dict = {'user_id': str(specific_response.id),
                                 'user_name': specific_response.fullname,
                                 'user_image': specific_response.image_path
                    ,
                                 'state': specific_response.state,
                                 'city': specific_response.city,
                                 'badge': badge,
                                 'matches_count': count_value,
                                 'about_me': specific_response.about_me,
                                 'college': college,
                                 'sexuality': sexuality,
                                 'relationship_status': relationship_status,
                                 'looking_for': looking_for

                                 }

                response_list.append(response_dict)

        if len(response_list) > 0:

            return jsonify({'status': 1, 'data': response_list,
                            'messege': '', 'pagination': pagination_info})
        else:
            return jsonify({'status': 1, 'data': [],
                            'messege': 'You have zero matches. Click on Save to get started',
                            })

    filter_dict = {'relationships': 0,
                   'gender': 0,
                   'age_start': '18',
                   'age_end': '40',
                   'sexuality': 0,
                   'relationship_status': 0}

    return jsonify({'status': 1, 'is_subscription': active_user.is_subscription_badge, 'data': filter_dict,
                    })


# @user_view_v2.route('/homepage_filter', methods=['GET', 'POST'])
# @token_required
# def homepage_filter(active_user):
#     notification_count = Notification.query.filter(
#         and_(Notification.title != 'Friends', Notification.to_id == active_user.id,
#              Notification.is_read == False)).count()
#     friend_request_count = Notification.query.filter_by(to_id=active_user.id, is_read=False, title='Friends').count()
#
#     if request.method == 'POST':
#         page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#         per_page = 10  # Number of items per page
#
#         list = [i for i in view_data()]
#         list.remove(active_user)
#         list1 = []
#         userList = []
#
#         for k in active_user.save_community_id:
#             list1.append(k.created_id)
#
#         for j in list:
#             dict1 = j.as_dict()
#
#             list2 = [i.created_id for i in j.save_community_id]
#
#             common_list = [x for x in list1 if x in list2]
#             # dict1['matched_count'] = len(common_list)
#             dict1.update({'matched_count': len(common_list)})
#
#             if dict1['matched_count'] != 0:
#                 userList.append(dict1)
#
#         user_list = sorted(userList, key=lambda x: x['matched_count'], reverse=True)
#
#         relationships = request.json.get('relationships')
#         if relationships == 0:
#             relationships = 'Friends'
#         if relationships == 1:
#             relationships = "Dating"
#         if relationships == 2:
#             relationships = ['Friends', 'Dating']
#
#         gender = request.json.get('gender')
#         if gender == 0:
#             gender = "Male"
#         if gender == 1:
#             gender = "Female"
#         if gender == 2:
#             gender = "Other"
#         if gender == 3:
#             gender = ['Male', 'Female']
#         age_start = request.json.get('age_start')
#         age_end = request.json.get('age_end')
#
#         sexuality = request.json.get('sexuality')
#         if sexuality == 0:
#             sexuality = "Straight"
#         if sexuality == 1:
#             sexuality = "Biesexual"
#         if sexuality == 2:
#             sexuality = "Gay"
#         if sexuality == 3:
#             sexuality = "Other"
#         relationship_status = request.json.get('relationship_status')
#         if relationship_status == 0:
#             relationship_status = "Single"
#         if relationship_status == 1:
#             relationship_status = "In a Relationship"
#         if relationship_status == 2:
#             relationship_status = "Married"
#         if relationship_status == 3:
#             relationship_status = "Other"
#
#         country = request.json.get('country')
#         state = request.json.get('state')
#         city = request.json.get('city')
#
#         filter_data = []
#         response_list = []
#         for search in user_list:
#             check_delete = User.query.filter_by(id=search['id'], deleted=False).first()
#             block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=search['id']).first()
#             if not block_check:
#                 if check_delete:
#                     birthdate_datetime = datetime.combine(search['age'], datetime.min.time())
#                     age = (datetime.utcnow() - birthdate_datetime).days // 365
#
#                     if (relationships == 'Both' or search['looking_for'] in relationships) and (
#                                     gender == 'Both' or search['gender'] in gender) and search[
#                         'sexuality'] == sexuality and str(age_start) <= str(age) <= str(age_end) and search[
#                         'relationship_status'] == relationship_status:
#
#                         if country and search['country'].lower() != country.lower():
#                             continue  # Skip to the next iteration if country does not match
#
#                         if state and search['state'].lower() != state.lower():
#                             continue  # Skip to the next iteration if state does not match
#
#                         if city and search['city'].lower() != city.lower():
#                             continue  # Skip to the next iteration if city does not match
#
#                         filter_data.append(search)
#         for specific_response in filter_data:
#             response_dict = {'user_id': str(specific_response['id']),
#                              'user_name': specific_response['username'],
#                              'user_image': specific_response['user_image'],
#                              'state': specific_response['state'],
#                              'city': specific_response['city'],
#
#                              'matches_count': specific_response['matched_count']}
#
#             response_list.append(response_dict)
#         if len(response_list) > 0:
#
#             # Calculate the start and end indices for the current page
#             start_index = (page - 1) * per_page
#             end_index = start_index + per_page
#
#             # Slice the list to get the records for the current page
#             current_page_records = response_list[start_index:end_index]
#
#             # Calculate total pages and whether there is a next page
#             total_items = len(response_list)
#             total_pages = (total_items + per_page - 1) // per_page
#             has_next = page < total_pages
#
#             # Pagination information
#             pagination_info = {
#                 "current_page": page,
#                 "has_next": has_next,
#                 "per_page": per_page,
#                 "total_pages": total_pages,
#             }
#
#             return jsonify({'status': 1, 'is_subscription': active_user.is_subscription, 'data': current_page_records,
#                             'messege': '', 'notification_count': str(notification_count),
#                             'friend_request_count': str(friend_request_count), 'pagination': pagination_info})
#         else:
#             return jsonify({'status': 1, 'is_subscription': active_user.is_subscription, 'data': [],
#                             'messege': 'You have zero matches. Click on Save to get started',
#                             'notification_count': notification_count, 'friend_request_count': friend_request_count})
#
#     filter_dict = {'relationships': 0,
#                    'gender': 0,
#                    'age_start': '18',
#                    'age_end': '40',
#                    'sexuality': 0,
#                    'relationship_status': 0}
#
#     return jsonify({'status': 1, 'is_subscription': active_user.is_subscription, 'data': filter_dict,
#                     'notification_count': str(notification_count), 'friend_request_count': str(friend_request_count)})


@user_view_v2.route('/category_list', methods=['GET', 'POST'])
@token_required
def category_list(active_user):
    filter_text = request.json.get('filter_text')

    ex = []
    ls = []

    if not active_user.category_id:
        x = Category.query.all()

        list = [i.as_dict() for i in x]

        ex.extend(list)

    if active_user.category_id:
        x = SelectedCategory.query.filter_by(user_id=active_user.id).first()
        if x:
            splt = x.category_id.split(',')
            if len(splt) > 0:
                for i in splt:
                    y = Category.query.filter_by(id=i).first()
                    if y:
                        ex.append(y.as_dict())
    if filter_text == 1:
        sort_key = lambda d: d['category_name']
        reverse = True
    elif filter_text == 2:
        sort_key = lambda d: d['id']
        reverse = True
    elif filter_text == 3:
        sort_key = lambda d: d['id']
        reverse = False
    else:
        sort_key = lambda d: d['category_name']
        reverse = False
    if len(ex) > 0:
        return jsonify({'status': 1, 'category_list': sorted(ex, key=sort_key, reverse=reverse)})
    else:
        return jsonify(
            {'status': 1, 'category_list': [], 'messege': 'You Not Save Any Category Please Save From Edit Profile'})


@user_view_v2.route('/users_list', methods=['GET'])
@token_required
def users_list(active_user):
    list = [i for i in view_data()]
    list.remove(active_user)
    block_check = Block.query.filter_by(blocked_user=active_user.id).all()
    if len(block_check) > 0:
        for check in block_check:
            user_info = User.query.filter_by(id=check.user_id).first()
            list.remove(user_info)
    list2 = [i.as_dict() for i in list]

    ls = []
    for i in list2:
        dict = {'user_id': str(i['id']),
                'username': '@' + i['username'],
                'user_image': i['user_image']
                }
        ls.append(dict)

    return jsonify({'status': 1, 'data': ls})


@user_view_v2.route('/send_friend_req', methods=['POST'])
@token_required
def send_friend_req(active_user):
    user = request.json.get('id')

    user_delete = User.query.filter_by(id=user, deleted=False).first()

    if user_delete:

        # already_send = sent_frnd_req(active_user.id,user)
        friend_request = FriendRequest.query.filter(
            (FriendRequest.to_id == active_user.id) & (FriendRequest.by_id == user)
            | (FriendRequest.by_id == active_user.id) & (FriendRequest.to_id == user)
        ).first()

        if not friend_request:

            frd_req = FriendRequest(by_id=active_user.id, to_id=user, request_status=2, created_time=datetime.utcnow())
            # frd_req = FriendRequest(by_id = active_user.id,to_id=user,request_status = 1)

            insert_data(frd_req)

            reciver_user = User.query.filter_by(id=user).first()
            if reciver_user.friend_request == True:

                title = 'Friends'
                # image_url = f'{active_user.image_path}'
                msg = f'{active_user.fullname} Send You A Friend Request'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), page='user')
                db.session.add(add_notification)
                db.session.commit()
                # if reciver_user.device_token:
                notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=reciver_user.device_type)
            else:
                title = 'Friends'
                msg = f'{active_user.fullname} Send You A Friend Request'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), page='user')
                db.session.add(add_notification)
                db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully Send Friend Request', 'is_friend': 1})
            # return jsonify({'status': 1,'messege': 'Successfully Added In Friendlist','is_friend': 1})

        if friend_request:
            reciver_user = User.query.filter_by(id=user).first()
            check_before = FriendRequest.query.filter_by(by_id=active_user.id, to_id=user, request_status=2).first()
            # check_true = FriendRequest.query.filter_by(by_id = active_user.id, to_id = user,request_status = 1).first()
            if check_before:
                delete_frnd_req(active_user.id, user)
                reciver_user = User.query.filter_by(id=user).first()
                return jsonify({'status': 1, 'messege': 'Successfully Cencle Friend Request', 'is_friend': 0})
            if friend_request.request_status == 1:
                db.session.delete(friend_request)
                db.session.commit()
                if reciver_user.unfriend == True:

                    title = 'Unfriend'
                    image_url = f'{active_user.image_path}'
                    msg = f'{active_user.fullname} Remove You From Friendlist'
                    add_notification = Notification(title=title, messege=msg, by_id=active_user.id,
                                                    to_id=reciver_user.id, is_read=False,
                                                    created_time=datetime.utcnow(), page='user')
                    db.session.add(add_notification)
                    db.session.commit()
                    # if reciver_user.device_token:
                    notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                                     image_url=None, device_type=reciver_user.device_type)
                else:
                    title = 'Unfriend'
                    msg = f'{active_user.fullname} Remove You From Friendlist'
                    add_notification = Notification(title=title, messege=msg, by_id=active_user.id,
                                                    to_id=reciver_user.id, is_read=False,
                                                    created_time=datetime.utcnow(), page='user')
                    db.session.add(add_notification)
                    db.session.commit()
                return jsonify({'status': 1, 'messege': 'Successfully Unfriend', 'is_friend': 0})
            # return jsonify({'status': 1,'messege': 'Successfully Removed From Friendlist', 'is_friend': 0})
            return jsonify(
                {'status': 0, 'messege': 'This User Already Send Request To You!! Please Check In Your Request List!!'})
    else:
        return jsonify({'status': 0, 'messege': 'User Deleted There Account'})


@user_view_v2.route('/req_list', methods=['GET', 'POST'])
@token_required
def req_list(active_user):
    friend_request_count = Notification.query.filter_by(to_id=active_user.id, is_read=False, title='Friends').all()
    if len(friend_request_count) > 0:
        for notify in friend_request_count:
            notify.is_read = True
            notify.id = notify.id
            db.session.commit()

    frd_req = FriendRequest.query.filter_by(to_id=active_user.id, request_status=2).all()
    ls = []
    for i in frd_req:
        x = User.query.filter_by(id=i.by_id, deleted=False).all()
        for j in x:
            block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=j.id).first()
            if not block_check:
                input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                dict = {
                    'id': str(j.id),
                    'username': j.fullname,
                    'user_image': j.image_path,
                    'time': output_date,
                    'req_status': 0}

                ls.append(dict)

    if len(ls) != 0:
        return jsonify({'status': 1, 'list': ls})
    else:
        return jsonify({'status': 1, 'list': ls, 'messege': 'You Dont Have Any Friend Request'})


@user_view_v2.route('/req_action', methods=['POST'])
@token_required
def accept_friend_req(active_user):
    user = request.json.get('id')
    req_status = request.json.get('status')
    reciver_user = User.query.filter_by(id=user).first()

    check = FriendRequest.query.filter_by(by_id=user, to_id=active_user.id).first()

    if check and req_status == '1':
        accept = FriendRequest(id=check.id, by_id=user, to_id=active_user.id, request_status=1)
        db.session.merge(accept)
        db.session.commit()

        title = 'Friend Request Accepted'
        # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
        msg = f'{active_user.fullname} has accepted your friend request'
        add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                        is_read=False, created_time=datetime.utcnow(), post_id=None, community_id=None,
                                        page='friend request')
        db.session.add(add_notification)
        db.session.commit()
        # if reciver_user.device_token:
        notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg, image_url=None,
                                         device_type=reciver_user.device_type)

        return jsonify({'status': 1, 'messege': 'Friend Request Accepted'})

    if check and req_status == '2':
        FriendRequest.query.filter_by(by_id=user, to_id=active_user.id).delete()
        db.session.commit()

        title = 'Friend Request Decliend'
        # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
        msg = f'{active_user.fullname} has declied your friend request'
        add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                        is_read=False, created_time=datetime.utcnow(), post_id=None, community_id=None,
                                        page='friend request')
        db.session.add(add_notification)
        db.session.commit()
        # if reciver_user.device_token:
        notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg, image_url=None,
                                         device_type=reciver_user.device_type)

        return jsonify({'status': 1, 'messege': 'Friend Request Decline'})


@user_view_v2.route('/friends_list', methods=['POST'])
@token_required
def friends_list(active_user):
    list = []

    ls = []

    check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).all()

    checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).all()

    if check:
        for i in check:
            # block_check = Block.query.filter_by(blocked_user = active_user.id, user_id = j.id).first()
            # if not block_user
            x = User.query.filter_by(id=i.by_id, deleted=False).all()
            ls.extend(x)
    if checked:
        for k in checked:
            y = User.query.filter_by(id=k.to_id, deleted=False).all()
            ls.extend(y)
    for j in ls:
        dict = {
            'id': str(j.id),
            'username': j.fullname,
            'user_image': j.image_path}
        list.append(dict)
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    # Calculate the start and end indices for the current page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    current_page_records = list[start_index:end_index]

    # Calculate total pages and whether there is a next page
    total_items = len(list)
    total_pages = (total_items + per_page - 1) // per_page
    has_next = page < total_pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if len(list) != 0:
        return jsonify(
            {'status': 1, 'friends_list': current_page_records, 'messege': 'Sucess', 'pagination': pagination_info})
    else:
        return jsonify({'status': 1, 'friends_list': list, 'messege': 'You Dont Have Any Friends Yet',
                        'pagination': pagination_info})


@user_view_v2.route('/friends_list_id', methods=['GET', 'POST'])
@token_required
def friends_list_id(active_user):
    list = []

    ls = []

    check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).all()

    checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).all()

    if check:
        for i in check:
            x = User.query.filter_by(id=i.by_id, deleted=False).all()
            ls.extend(x)
    if checked:
        for k in checked:
            y = User.query.filter_by(id=k.to_id, deleted=False).all()
            ls.extend(y)
    for j in ls:
        list.append(str(j.id))
    if len(list) != 0:
        return jsonify({'status': 1, 'friends_list': list, 'messege': 'Friend List'})
    else:
        return jsonify({'status': 1, 'friends_list': list, 'messege': 'You Dont Have Any Friends Yet'})


@user_view_v2.route('/get_category', methods=['GET', 'POST'])
@token_required
def get_category(active_user):
    id = request.args.get('id')
    x = Category.query.filter_by(id=id).first()

    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxx ', x)

    return jsonify({'status': 1, 'category_data': x.as_dict()})


@user_view_v2.route('/view_profile', methods=['POST'])
@token_required
def view_profile(active_user):
    user = request.json.get('user_id')
    x = User.query.filter_by(id=user).first()
    ls = []

    check1 = FriendRequest.query.filter_by(to_id=x.id, request_status=1).all()
    checked1 = FriendRequest.query.filter_by(by_id=x.id, request_status=1).all()

    if len(check1) > 0:
        for i in check1:
            x_delete = User.query.filter_by(id=i.by_id, deleted=False).all()
            ls.extend(x_delete)
    if len(checked1) > 0:
        for k in checked1:
            y_delete = User.query.filter_by(id=k.to_id, deleted=False).all()
            ls.extend(y_delete)

    check = FriendRequest.query.filter_by(to_id=active_user.id, by_id=x.id, request_status=1).first()
    checked = FriendRequest.query.filter_by(by_id=active_user.id, to_id=x.id, request_status=1).first()

    birthdate_datetime = datetime.combine(x.age, datetime.min.time())
    age = (datetime.utcnow() - birthdate_datetime).days // 365
    if not check and not checked:
        dict = [
            {'value': str(age), 'name': 'Age'},
            {'value': x.gender, 'name': 'Gender'},
            # {'value': str(len(ls)), 'name': 'Total Friends'},
            {'value': x.sexuality, 'name': 'Sexuality'},
            {'value': x.relationship_status, 'name': 'Relationship'},
            {'value': x.looking_for, 'name': 'Looking For'},
            {'value': x.country, 'name': 'Country'},
            {'value': x.state, 'name': 'State'},
            {'value': x.city, 'name': 'City'},
            {'value': x.height, 'name': 'Height'},
            {'value': x.drink, 'name': 'Drink'},
            {'value': x.smoke, 'name': 'Smoke'}

        ]

        return jsonify({'status': 1, 'messege': 'sucess', 'user_data': dict})

    if check or checked:
        dict = [
            {'value': str(age), 'name': 'Age'},
            {'value': x.gender, 'name': 'Gender'},
            # {'value': str(len(ls)), 'name': 'Total Friends'},
            {'value': x.sexuality, 'name': 'Sexuality'},
            {'value': x.relationship_status, 'name': 'Relationship'},
            {'value': x.looking_for, 'name': 'Looking For'},
            {'value': x.country, 'name': 'Country'},
            {'value': x.state, 'name': 'State'},
            {'value': x.city, 'name': 'City'},
            {'value': x.height, 'name': 'Height'},
            {'value': x.drink, 'name': 'Drink'},
            {'value': x.smoke, 'name': 'Smoke'}

        ]
        return jsonify({'status': 1, 'messege': 'sucess', 'user_data': dict})


@user_view_v2.route("/user/delete", methods=['GET', 'POST'])
@token_required
def delete(active_user):
    active_user.deleted = True
    active_user.deleted_time = datetime.utcnow()
    db.session.commit()

    if request.method == 'POST':

        reason = request.json.get('delete_reason')
        if reason:
            active_user.deleted = True
            active_user.deleted_time = datetime.utcnow()
            active_user.delete_reason = reason

            db.session.commit()

            return jsonify({'status': 1, 'Reason': reason, 'messege': 'Sucessfully Your Account Deleted'})

    return jsonify({'status': 1, 'messege': 'Sucessfully Your Account Deleted'})


@user_view_v2.route("/matches/category_vise", methods=['POST'])
@token_required
def matches_category_vice(active_user):
    user_id = request.json.get('user_id')
    filter_text = request.json.get('filter_text')

    only_user = User.query.filter_by(id=user_id).first()
    if not only_user:
        return jsonify({'status': 0, 'messege': 'Invalid user'})
    if only_user:
        if only_user.is_subscription_badge == True:
            current_timestamp_ms = int(datetime.now().timestamp() * 1000)
            if int(only_user.subscription_start_time_badge) <= current_timestamp_ms <= int(
                    only_user.subscription_end_time_badge):
                pass
        else:

            only_user.is_subscription_badge = False
            only_user.subscription_start_time_badge = None
            only_user.subscription_end_time_badge = None
            only_user.badge_name = None
            only_user.product_id_badge = None
            only_user.transaction_id_badge = None
            only_user.purchase_date_badge = None
            db.session.commit()

    block_check = Block.query.filter_by(blocked_user=user_id, user_id=active_user.id).first()
    if block_check:
        is_block = True
    else:
        is_block = False

    user_dict = {'user_name': '@' + only_user.fullname,
                 'user_image': only_user.image_path, }

    friend_request = FriendRequest.query.filter(
        (FriendRequest.to_id == active_user.id) & (FriendRequest.by_id == user_id)
        | (FriendRequest.by_id == active_user.id) & (FriendRequest.to_id == user_id)
    ).first()

    print('friend_requesttttttttttttttttttttttttttttttttttttt', friend_request)

    if filter_text == 1:
        sort_key = lambda d: d['community_name']
        reverse = True
    elif filter_text == 2:
        sort_key = lambda d: d['created_time']
        reverse = True
    elif filter_text == 3:
        sort_key = lambda d: d['created_time']
        reverse = False
    else:
        sort_key = lambda d: d['community_name']
        reverse = False

    ls1 = []

    for m in active_user.save_community_id:
        community_save = SavedCommunity.query.filter_by(created_id=m.created_id, user_id=user_id).first()

        if community_save:
            ls1.append(community_save)

    cat_list = Category.query.filter(Category.id.in_([c.category_id for c in ls1])).all()

    dict_list1 = []
    dict_list2 = []

    res = []
    res2 = []

    [res.append(x) for x in ls1 if x not in res]
    main_count_list = []

    for category in cat_list:
        community_list = [c.as_dict() for c in res if c.category_id == category.id]
        dict1 = {
            'category_name': category.category_name,
            'community_count': str(len(community_list)),
            'community_list': sorted(community_list, key=sort_key, reverse=reverse)
        }
        check_counts = (len(community_list))
        main_count_list.append(check_counts)
        dict_list1.append(dict1)

    all_community = SavedCommunity.query.filter_by(user_id=user_id).all()
    unmatched = [c for c in all_community if c not in ls1]
    [res2.append(y) for y in unmatched if y not in res2]
    cat_list2 = Category.query.filter(Category.id.in_([c.category_id for c in unmatched])).all()

    for category in cat_list2:
        community_list = [c.as_dict() for c in res2 if c.category_id == category.id]
        dict2 = {
            'category_name': category.category_name,
            'community_count': str(len(community_list)),
            'community_list': sorted(community_list, key=sort_key, reverse=reverse)
        }
        dict_list2.append(dict2)
    already_send = DateRequest.query.filter(DateRequest.by_id == active_user.id, DateRequest.to_id == id).count() > 0
    is_subscribed = False
    if only_user.is_subscription_badge == True:
        is_subscribed = True
    else:
        is_subscribed = False
    description_box = ""
    if only_user.description_box != None:
        description_box = only_user.description_box
    else:
        description_box = ""
    sum_count = sum(main_count_list)

    if not friend_request:
        return jsonify({'status': 1, 'is_friends': 0, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1, 'unmatches': ['this is static value'], 'filter': filter_text or 0,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(sum_count)})

    elif friend_request.request_status == 2:
        return jsonify({'status': 1, 'is_friends': 2, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1, 'unmatches': ['this is static value'], 'filter': filter_text or 0,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(sum_count)})

    else:
        return jsonify({'status': 1, 'is_friends': 1, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1, 'unmatches': dict_list2, 'filter': filter_text or 0,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(sum_count)})


@user_view_v2.route("/get/terms_conditions", methods=['GET'])
def get_terms_conditions():
    x = terms_condition(1)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/privacy_policy", methods=['GET'])
def get_privacy_policy():
    x = terms_condition(2)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/news", methods=['GET'])
@token_required
def get_news(active_user):
    x = terms_condition(3)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/how_to_use", methods=['GET'])
@token_required
def how_to_use(active_user):
    x = terms_condition(4)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/information", methods=['GET'])
@token_required
def information(active_user):
    x = terms_condition(5)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/stores", methods=['GET'])
@token_required
def get_store(active_user):
    x = terms_condition(6)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/brands_deals", methods=['GET'])
@token_required
def brands_deals(active_user):
    x = terms_condition(7)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v2.route("/get/faq", methods=['GET'])
@token_required
def get_faq(active_user):
    x = Faqs.query.all()
    list = [i.as_dict() for i in x]
    return jsonify({'status': 1, 'list': list})


@user_view_v2.route("/search/user", methods=['GET', 'POST'])
@token_required
def search_user(active_user):
    # list = [i for i in view_data()]
    # list.remove(active_user)

    # userlist = []
    # for j in list:
    # block_check = Block.query.filter_by(blocked_user = active_user.id, user_id= j.id).first()
    # if j.deleted == False:
    # if not block_check:

    # dict = {
    # 'user_id': str(j.id),
    # 'user_name': '@'+j.fullname,
    # 'user_image': COMMON_URL+j.image_path[2:] + j.image_name}
    # userlist.append(dict)

    if request.method == 'POST':
        x = request.json.get('search')
        search = User.query.filter(User.fullname.like('%' + x + '%')).all()
        if active_user in search:
            search.remove(active_user)
        print('searchhhhhhhhhhhhh', search)

        ls = []
        if len(search) > 0:
            for i in search:
                block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=i.id).first()
                if i.deleted == False:

                    if not block_check:
                        dict = {
                            'user_id': str(i.id),
                            'user_name': '@' + i.fullname,
                            'user_image': i.image_path}
                        ls.append(dict)

            return jsonify({'status': 1, 'search_result': ls})
        else:
            return jsonify({'status': 0, 'messege': 'No User Found', 'search_result': []})
    return jsonify({'status': 1, 'search_result': []})


@user_view_v2.route('/get/tag_friends', methods=['POST'])
@token_required
def get_tag_friends(active_user):
    check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).all()
    checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).all()

    friends = check + checked
    interest_id = request.json.get('post_id')
    tag_friends = TagFriends.query.filter_by(community_post_id=interest_id, user_id=active_user.id).first()
    if tag_friends:
        split_data = tag_friends.users.split(',')
    if not tag_friends:
        split_data = []

    friends_list = []
    rmove = CommunityPost.query.filter_by(id=interest_id).first()
    for friend in friends:
        friend_user = User.query.filter_by(id=friend.by_id if friend.by_id != active_user.id else friend.to_id).first()
        check_tag = str(friend_user.id) in split_data
        if friend_user:

            if friend_user.deleted == False:
                if rmove.user_id != friend_user.id:
                    friends_list.append({
                        'id': str(friend_user.id),
                        'username': friend_user.fullname,
                        'user_image': friend_user.image_path,
                        'is_tagged': check_tag
                    })

    return jsonify({'status': 1, 'friends_list': friends_list})


@user_view_v2.route('/tag_friends', methods=['GET', 'POST'])
@token_required
def tag_friends(active_user):
    check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).all()
    checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).all()

    friends = check + checked
    tag_ids = request.json.get('user_id')
    tag_id = [str(item['id']) for item in tag_ids]

    interest_id = request.json.get('post_id')
    post_info_id = get_community_chat(interest_id)

    comm_info = CreatedCommunity.query.filter_by(id=post_info_id.community_id).first()
    cat_info = Category.query.filter_by(id=comm_info.category_id).first()

    tag_friends = TagFriends.query.filter_by(community_post_id=interest_id, user_id=active_user.id).first()
    if tag_friends:
        split_data = tag_friends.users.split(',')
    if not tag_friends:
        split_data = []

    community_info = CommunityPost.query.filter_by(id=interest_id).first()
    if not len(tag_id) > 0:
        tag_not = TagFriends.query.filter_by(community_post_id=interest_id, user_id=active_user.id).first()
        if tag_not:
            db.session.delete(tag_not)
            db.session.commit()

    if len(tag_id) > 0:
        values_not_in_second_list = [value for value in tag_id if value not in split_data]
        if len(values_not_in_second_list) > 0:
            for notify in values_not_in_second_list:
                notify_user = User.query.filter_by(id=notify).first()

                if notify_user.tag_you == True:
                    title = 'Tagged'
                    # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                    msg = f'{active_user.fullname} Tagged you in {comm_info.community_name} community post within the {cat_info.category_name} category'
                    add_notification = Notification(title=title, messege=msg, by_id=active_user.id,
                                                    to_id=notify_user.id, is_read=False, created_time=datetime.utcnow(),
                                                    post_id=interest_id, community_id=community_info.community_id,
                                                    page='post')
                    db.session.add(add_notification)
                    db.session.commit()
                    # if notify_user.device_token:
                    notification = push_notification(device_token=notify_user.device_token, title=title, msg=msg,
                                                     image_url=None, device_type=notify_user.device_type)
                else:
                    title = 'Tagged'
                    msg = f'{active_user.fullname} Tagged you in {comm_info.community_name} community post within the {cat_info.category_name} category'
                    add_notification = Notification(title=title, messege=msg, by_id=active_user.id,
                                                    to_id=notify_user.id, is_read=False, created_time=datetime.utcnow(),
                                                    post_id=interest_id, community_id=community_info.community_id,
                                                    page='post')
                    db.session.add(add_notification)
                    db.session.commit()

        join_id = ",".join(tag_id)
        if not tag_friends:
            x = TagFriends(users=join_id, community_post_id=interest_id, user_id=active_user.id)
            db.session.add(x)
            db.session.commit()
        if tag_friends:
            y = TagFriends(id=tag_friends.id, users=join_id, community_post_id=interest_id, user_id=active_user.id)
            db.session.merge(y)
            db.session.commit()

    friends_list = []
    rmove = CommunityPost.query.filter_by(id=interest_id).first()
    tag_friends_updated = TagFriends.query.filter_by(community_post_id=interest_id, user_id=active_user.id).first()
    if tag_friends_updated:
        split_data1 = tag_friends_updated.users.split(',')
    if not tag_friends_updated:
        split_data1 = []
    for friend in friends:
        friend_user = User.query.filter_by(id=friend.by_id if friend.by_id != active_user.id else friend.to_id).first()
        check_tag = str(friend_user.id) in split_data1
        if friend_user:
            if friend_user.deleted == False:
                if rmove.user_id != friend_user.id:
                    friends_list.append({
                        'id': str(friend_user.id),
                        'username': friend_user.fullname,
                        'user_image': friend_user.image_path,
                        'is_tagged': check_tag
                    })

    return jsonify({'status': 1, 'friends_list': friends_list})


@user_view_v2.route('/post/mute_unmute', methods=['GET', 'POST'])
@token_required
def chat_mute(active_user):
    post_id = request.json.get('post_id')

    x = ChatMute.query.filter_by(user_id=active_user.id, post_id=post_id).first()

    if x:
        db.session.delete(x)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Succcesfully Unmute Post'})

    if not x:
        check = ChatMute(user_id=active_user.id, post_id=post_id, is_chat_mute=True)
        db.session.add(check)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Succcesfully Mute Post'})

    return jsonify({'status': 1, 'messege': 'Succcesfully Unblock User'})


@user_view_v2.route('/community/unsave', methods=['POST'])
@token_required
def community_unsave(active_user):
    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')

    obj = SavedCommunity.query.filter_by(user_id=active_user.id, created_id=community_id,
                                         category_id=category_id).first()

    if obj:
        db.session.delete(obj)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Sucessfully Deleted Word'})
    else:
        return jsonify({'status': 0, 'messege': 'Word Not Found'})


@user_view_v2.route('/featured_page', methods=['POST'])
@token_required
def featured_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    user_data = User.query.filter(User.is_featured == True,
                                  User.is_block != True,
                                  User.deleted != True,
                                  User.id.not_in(blocked_user_ids),
                                  User.id.not_in(blocked_by_user_ids)).paginate(page=page, per_page=per_page,
                                                                                error_out=False)
    final_list = []

    if user_data.items:
        for i in user_data.items:
            badge = ""
            if i.badge_name is not None:
                badge = i.badge_name
            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'badge': badge}
            final_list.append(response_dict)

        has_next = user_data.has_next  # Check if there is a next page
        total_pages = user_data.pages  # Total number of pages

        # Pagination informatio
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': final_list, 'messege': 'sucess', 'pagination_info': pagination_info})
    else:
        return jsonify(
            {'status': 1, 'data': [], 'messege': 'No result'})


@user_view_v2.route('/matches/filter_community_vice', methods=['POST'])
@token_required
def matches_community_vice(active_user):
    if request.method == 'POST':
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 10  # Number of items per page
        created_id = request.json.get('community_id')

        current_date = func.current_date()
        blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
        blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

        relationships = request.json.get('relationships')
        relationships_list = []
        if relationships == 0:
            relationships_list.append('Friends')

        if relationships == 1:
            relationships_list.append("Dating")
        if relationships == 2:
            relationships_list.extend(["Friends", "Dating"])

        gender = request.json.get('gender')
        gender_list = []
        if gender == 0:
            gender_list.append("Male")
        if gender == 1:
            gender_list.append("Female")
        if gender == 2:
            gender_list.append("Other")
        if gender == 3:
            gender_list.extend(['Male', 'Female'])

        age_start = request.json.get('age_start')

        age_end = request.json.get('age_end')

        sexuality = request.json.get('sexuality')
        if sexuality == 0:
            sexuality = "Straight"
        if sexuality == 1:
            sexuality = "Biesexual"
        if sexuality == 2:
            sexuality = "Gay"
        if sexuality == 3:
            sexuality = "Other"
        relationship_status = request.json.get('relationship_status')
        if relationship_status == 0:
            relationship_status = "Single"
        if relationship_status == 1:
            relationship_status = "In a Relationship"
        if relationship_status == 2:
            relationship_status = "Married"
        if relationship_status == 3:
            relationship_status = "Other"

        country = request.json.get('country')
        state = request.json.get('state')
        city = request.json.get('city')

        age_expression = func.timestampdiff(text('YEAR'), User.age, current_date)

        # Filters for age between age_start and age_end
        age_filter = and_(age_expression >= age_start, age_expression <= age_end)

        matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('matches'))
                        .join(User, User.id == SavedCommunity.user_id)
                        .group_by(SavedCommunity.user_id)
                        .subquery())

        query = (db.session.query(User, matches_subq.c.matches)
            .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
            .filter(
            SavedCommunity.created_id == str(created_id), age_filter, User.gender.in_(gender_list),
            User.sexuality == sexuality,
            User.relationship_status == relationship_status,
            User.looking_for.in_(relationships_list), User.id != active_user.id,
            User.is_block != True, User.deleted != True,
            User.id.not_in(blocked_user_ids),
            User.id.not_in(blocked_by_user_ids))).filter(User.id.in_(db.session.query(SavedCommunity.user_id)
                                                                     .filter(
            SavedCommunity.created_id == created_id))).order_by(matches_subq.c.matches.desc())
        if country:
            query = query.filter(func.lower(User.country) == country.lower())
        if state:
            query = query.filter(func.lower(User.state) == state.lower())
        if city:
            query = query.filter(func.lower(User.city) == city.lower())

        user_list = query.order_by(func.random()).paginate(page=page, per_page=per_page, error_out=False)
        has_next = user_list.has_next  # Check if there is a next page
        total_pages = user_list.pages  # Total number of pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        response_list = []
        if user_list.items:
            for specific_response, count in user_list.items:
                badge = ""
                if specific_response.badge_name is not None:
                    badge = specific_response.badge_name
                count_value = str(count)
                if not count:
                    count_value = '0'
                response_dict = {'user_id': str(specific_response.id),
                                 'user_name': specific_response.fullname,
                                 'user_image': specific_response.image_path,
                                 'state': specific_response.state,
                                 'city': specific_response.city,
                                 'badge': badge,
                                 'community_id': str(created_id),
                                 'matches_count': count_value}
                response_list.append(response_dict)

        if len(response_list) > 0:

            return jsonify({'status': 1, 'data': response_list,
                            'messege': '', 'pagination': pagination_info})
        else:
            return jsonify({'status': 1, 'data': [],
                            'messege': 'You Dont Have Any Matches Yet, Save More Words..',
                            })


@user_view_v2.route('/matches/community_vice', methods=['POST'])
@token_required
def matches_filter_community_vice(active_user):
    created_id = request.json.get('community_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
    active_user_saved_ids = [j.created_id for j in active_user.save_community_id]

    matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('matches'))
                    .join(User, User.id == SavedCommunity.user_id)
                    .group_by(SavedCommunity.user_id)
                    .subquery())

    # Fetch user data, ensuring they have a match with the specific 'created_id'
    user_data = (db.session.query(User, matches_subq.c.matches)
                 .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
                 .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
                 .filter(~User.id.in_(blocked_user_ids))
                 .filter(~User.id.in_(blocked_by_user_ids))
                 .filter(User.id.in_(db.session.query(SavedCommunity.user_id)
                                     .filter(SavedCommunity.created_id == created_id)))
                 .order_by(
        matches_subq.c.matches.desc())  # Order users by their total match counts across all created_ids
                 .paginate(page=page, per_page=per_page, error_out=False))

    final_list = []

    if user_data.items:
        for i, count in user_data.items:
            # saved_data = SavedCommunity.query.filter_by(created_id=str(created_id), user_id=i.id).first()
            badge = ""
            if i.badge_name is not None:
                badge = i.badge_name
            count_value = str(count)
            if not count:
                count_value = '0'
            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'state': i.state,
                             'city': i.city,
                             'badge': badge,
                             'community_id': str(created_id),
                             'matches_count': count_value}
            final_list.append(response_dict)

        has_next = user_data.has_next  # Check if there is a next page
        total_pages = user_data.pages  # Total number of pages

        # Pagination informatio
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': final_list, 'messege': 'sucess', 'pagination_info': pagination_info})
    else:
        return jsonify(
            {'status': 1, 'data': [], 'messege': 'You Dont Have Any Matches Yet, Save More Words..'})


# @user_view_v2.route('/matches/community_vice', methods=['POST'])
# @token_required
# def matches_community_vice(active_user):
#     created_id = request.json.get('community_id')
#     list = [i for i in view_data()]
#     list.remove(active_user)
#     final_list = []
#
#     for rem in list:
#         block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=rem.id).first()
#         if not block_check:
#             remv = SavedCommunity.query.filter_by(created_id=str(created_id), user_id=rem.id).first()
#             if remv:
#                 final_list.append(rem)
#
#     list1 = []
#     userList = []
#
#     for k in active_user.save_community_id:
#         list1.append(k.created_id)
#
#     for j in final_list:
#         dict1 = j.as_dict()
#
#         list2 = [i.created_id for i in j.save_community_id]
#
#         common_list = [x for x in list1 if x in list2]
#         dict1.update({'matched_count': len(common_list)})
#
#         if dict1['matched_count'] != 0:
#             userList.append(dict1)
#
#     user_list = sorted(userList, key=lambda x: x['matched_count'], reverse=True)
#     response_list = []
#     for specific_response in user_list:
#         not_deleted_user = User.query.filter_by(id=specific_response['id'], deleted=False).first()
#         if not_deleted_user:
#             response_dict = {'user_id': str(specific_response['id']),
#                              'user_name': specific_response['username'],
#                              'user_image': specific_response['user_image'],
#                              'matches_count': str(specific_response['matched_count']),
#                              'community_id': created_id}
#             response_list.append(response_dict)
#
#     if len(response_list) != 0:
#         return jsonify({'status': 1, 'data': response_list, 'messege': 'sucess'})
#     else:
#         return jsonify(
#             {'status': 1, 'data': response_list, 'messege': 'You Dont Have Any Matches Yet, Save More Words..'})


@user_view_v2.route('/notification_list', methods=['POST'])
@token_required
def notification_list(active_user):
    notify = Notification.query.filter(
        and_(Notification.title != 'Friends', Notification.to_id == active_user.id)).all()
    friends_ls = []
    other_ls = []
    tab = request.json.get('tab')
    if len(notify) > 0:
        for i in notify:

            if i.is_read == False:
                i.is_read = True
                db.session.commit()
            user_info = User.query.filter_by(id=i.by_id).first()
            check = FriendRequest.query.filter_by(to_id=active_user.id, by_id=i.by_id, request_status=1).first()

            checked = FriendRequest.query.filter_by(to_id=i.by_id, by_id=active_user.id, request_status=1).first()
            block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=user_info.id).first()
            if check or checked:
                if user_info.deleted == False:
                    if not block_check:
                        input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                        notify_dict = {
                            'id': str(i.id),
                            'user_id': str(user_info.id),
                            'username': user_info.fullname,
                            'user_image': user_info.image_path,
                            'title': i.title,
                            'messege': i.messege,
                            'post_id': str(i.post_id),
                            'community_id': str(i.community_id),
                            'page': i.page,
                            'created_time': output_date,
                            'is_read': i.is_read}
                        friends_ls.append(notify_dict)
            else:
                if user_info.deleted == False:
                    if not block_check:
                        input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                        output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                        notify_dict = {
                            'id': str(i.id),
                            'user_id': str(user_info.id),
                            'username': user_info.fullname,
                            'user_image': user_info.image_path,
                            'title': i.title,
                            'messege': i.messege,
                            'post_id': str(i.post_id),
                            'community_id': str(i.community_id),
                            'page': i.page,
                            'created_time': output_date,
                            'is_read': i.is_read}
                        other_ls.append(notify_dict)
        friends_ls.reverse()
        other_ls.reverse()
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 10  # Number of items per page

        def paginate_list(input_list, page, per_page):
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            return input_list[start_index:end_index]

        current_page_records = []
        total_items = 0
        total_pages = 0
        has_next = False

        if not tab or tab == '0':
            current_page_records = paginate_list(friends_ls, page, per_page)
            total_items = len(friends_ls)
        elif tab == '1':
            current_page_records = paginate_list(other_ls, page, per_page)
            total_items = len(other_ls)

        total_pages = (total_items + per_page - 1) // per_page
        has_next = page < total_pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        if tab == '0':
            if not len(friends_ls) > 0:
                return jsonify(
                    {'status': 1, 'list': [], 'messege': 'You Dont Have Any Notification Yet', 'tab': 'Friends',
                     'pagination': pagination_info})
            else:

                return jsonify(
                    {'status': 1, 'list': current_page_records, 'tab': 'Friends', 'pagination': pagination_info,
                     'messege': 'Sucess'})
        if not tab:
            if not len(friends_ls) > 0:
                return jsonify(
                    {'status': 1, 'list': [], 'messege': 'You Dont Have Any Notification Yet', 'tab': 'Friends',
                     'pagination': pagination_info})
            else:

                return jsonify(
                    {'status': 1, 'list': current_page_records, 'tab': 'Friends', 'pagination': pagination_info,
                     'messege': 'Sucess'})
        if tab == '1':
            if not len(other_ls) > 0:
                return jsonify(
                    {'status': 1, 'list': [], 'messege': 'You Dont Have Any Notification Yet', 'tab': 'Others',
                     'pagination': pagination_info})
            else:

                return jsonify(
                    {'status': 1, 'list': current_page_records, 'tab': 'Others', 'pagination': pagination_info,
                     'messege': 'Sucess'})
    if not len(friends_ls) > 0:
        if not tab:
            return jsonify({'status': 1, 'list': [], 'messege': 'You Dont Have Any Notification Yet', 'tab': 'Friends',
                            'pagination': pagination_info})
        if tab == '0':
            return jsonify({'status': 1, 'list': [], 'messege': 'You Dont Have Any Notification Yet', 'tab': 'Friends',
                            'pagination': pagination_info})

    if not len(other_ls) > 0:
        if tab == '1':
            return jsonify({'status': 1, 'list': [], 'messege': 'You Dont Have Any Notification Yet', 'tab': 'Others',
                            'pagination': pagination_info})


@user_view_v2.route('/notification_button', methods=['POST'])
@token_required
def notification_button(active_user):
    index_number = request.json.get('id')

    if index_number is not None:

        if index_number == '1':
            active_user.heart_your_comment = not active_user.heart_your_comment
        elif index_number == '2':
            active_user.like_your_comment = not active_user.like_your_comment
        elif index_number == '3':
            active_user.messege_friends = not active_user.messege_friends
        elif index_number == '4':
            active_user.messege_frienddate = not active_user.messege_frienddate
        elif index_number == '5':
            active_user.messege_new_user = not active_user.messege_new_user
        elif index_number == '6':
            active_user.dislike_your_comment = not active_user.dislike_your_comment
        elif index_number == '7':
            active_user.tag_you = not active_user.tag_you
        elif index_number == '8':
            active_user.friend_request = not active_user.friend_request
        elif index_number == '9':
            active_user.unfriend = not active_user.unfriend
        elif index_number == '10':
            active_user.add_new_community = not active_user.add_new_community
        elif index_number == '11':
            active_user.profile_pic = not active_user.profile_pic
        elif index_number == '12':
            active_user.relationship_status_change = not active_user.relationship_status_change

        db.session.commit()

    button_dict = [{

        'id': '1', 'value': active_user.heart_your_comment, 'name': 'User Hearts your comment'},
        {'id': '2', 'value': active_user.like_your_comment, 'name': 'User Likes your comment'},
        {'id': '3', 'value': active_user.messege_friends, 'name': 'Messeges from friends'},
        {'id': '4', 'value': active_user.messege_frienddate, 'name': 'Messeges from friend dates'},
        {'id': '5', 'value': active_user.messege_new_user, 'name': 'Messeges from friend new users'},
        {'id': '6', 'value': active_user.dislike_your_comment, 'name': 'User Dislike your comment'},
        {'id': '7', 'value': active_user.tag_you, 'name': 'User Tags You'},
        {'id': '8', 'value': active_user.friend_request, 'name': 'User Sends Friend Request'},
        {'id': '9', 'value': active_user.unfriend, 'name': 'User UnFriends You'},
        {'id': '10', 'value': active_user.add_new_community, 'name': 'Friends Update theire interests'},
        {'id': '11', 'value': active_user.profile_pic, 'name': 'Friends Upload a new profile picture'},
        {'id': '12', 'value': active_user.relationship_status_change,
         'name': 'Friends Changes theire Relationship Status'
         }]

    return jsonify({'status': 1, 'messege': 'Success', 'button_status': button_dict})


@user_view_v2.route('/get_notification_button', methods=['GET'])
@token_required
def get_notification_button(active_user):
    button_dict = [{

        'id': '1', 'value': active_user.heart_your_comment, 'name': 'User Hearts your comment'},
        {'id': '2', 'value': active_user.like_your_comment, 'name': 'User Likes your comment'},
        {'id': '3', 'value': active_user.messege_friends, 'name': 'Messeges from friends'},
        {'id': '4', 'value': active_user.messege_frienddate, 'name': 'Messeges from friend dates'},
        {'id': '5', 'value': active_user.messege_new_user, 'name': 'Messeges from friend new users'},
        {'id': '6', 'value': active_user.dislike_your_comment, 'name': 'User Dislike your comment'},
        {'id': '7', 'value': active_user.tag_you, 'name': 'User Tags You'},
        {'id': '8', 'value': active_user.friend_request, 'name': 'User Sends Friend Request'},
        {'id': '9', 'value': active_user.unfriend, 'name': 'User UnFriends You'},
        {'id': '10', 'value': active_user.add_new_community, 'name': 'Friends Update theire interests'},
        {'id': '11', 'value': active_user.profile_pic, 'name': 'Friends Upload a new profile picture'},
        {'id': '12', 'value': active_user.relationship_status_change,
         'name': 'Friends Changes theire Relationship Status'
         }]

    return jsonify({'status': 1, 'messege': 'Success', 'button_status': button_dict})


@user_view_v2.route('/ranking_page', methods=['POST'])
@token_required
def ranking_page(active_user):
    user_data = User.query.all()
    saved_words_count = []
    for i in user_data:
        user_saved = SavedCommunity.query.filter_by(user_id=i.id).count()
        if user_saved > 0:
            user_dict = {
                'user_id': i.id,
                'user_name': i.fullname,
                'user_image': i.image_path,
                'word_count': user_saved
            }
            saved_words_count.append(user_dict)

    # Sort the users based on word_count in descending order
    saved_words_count.sort(key=lambda x: x['word_count'], reverse=True)

    # Assign ranks to users based on their position in the sorted list
    for rank, user_dict in enumerate(saved_words_count, start=1):
        user_dict['rank'] = rank

    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    # Calculate the start and end indices for the current page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    # Slice the list to get the records for the current page
    current_page_records = saved_words_count[start_index:end_index]

    # Calculate total pages and whether there is a next page
    total_items = len(saved_words_count)
    total_pages = (total_items + per_page - 1) // per_page
    has_next = page < total_pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if len(current_page_records) > 0:
        return jsonify(
            {'status': 1, 'messege': 'Success', 'ranking_list': current_page_records, 'pagination': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'No saved words by any of users', 'ranking_list': [],
                        'pagination': pagination_info})


@user_view_v2.route('/verify-receipt', methods=['POST'])
@token_required
def verify_receipt(active_user):
    data = request.get_json()
    receipt_data = data['receipt']
    # subscription_type = data['subscription_type']
    product_id = data['product_id']
    badge_name = data['badge_name']
    # print('subscription_typeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',subscription_type)
    print('product_idddddddddddddddddddddddddddddddddddddddddddddddd', product_id)
    print('receipt_dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', receipt_data)
    print('badge_nameeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', badge_name)
    if not product_id:
        return jsonify({'status': 0, 'messege': 'Product id is missing'})

    # In production, use 'https://buy.itunes.apple.com/verifyReceipt'
    # VERIFY_RECEIPT_URL = 'https://sandbox.itunes.apple.com/verifyReceipt'
    VERIFY_RECEIPT_URL = 'https://buy.itunes.apple.com/verifyReceipt'

    # Your shared secret from App Store Connect
    SHARED_SECRET = '8a0d876692da43a18044a99680c8dbf8'

    response = requests.post(
        VERIFY_RECEIPT_URL,
        json={
            'receipt-data': receipt_data,
            'password': SHARED_SECRET,
            'exclude-old-transactions': True
        }
    )

    if response.status_code == 200:
        receipt_info = response.json()
        print('receipt_infooooooooooooooooooooooooooooooooooooooo', receipt_info)

        if receipt_info.get('status') == 0 and receipt_info.get('latest_receipt_info'):
            entry1 = receipt_info['latest_receipt_info']

            print('entry11111111111111111111111111111111111111111111111111111', entry1)
            found = False
            for entry in entry1:
                if entry['product_id'] == product_id:
                    found = True
                    current_timestamp_ms = int(datetime.now().timestamp() * 1000)
                    if int(entry['purchase_date_ms']) <= current_timestamp_ms <= int(entry['expires_date_ms']):

                        active_user.is_subscription_badge = True
                        active_user.subscription_start_time_badge = entry['purchase_date_ms']
                        active_user.subscription_end_time_badge = entry['expires_date_ms']
                        # active_user.subscription_price_badge = "5.99"
                        active_user.product_id_badge = entry['product_id']
                        active_user.transaction_id_badge = entry['transaction_id']
                        active_user.purchase_date_badge = entry['purchase_date']
                        active_user.badge_name = badge_name
                        db.session.commit()

                        return jsonify({"status": 1, "messege": "Subscription verified successfully!"})
                    else:
                        active_user.is_subscription_badge = False
                        active_user.subscription_start_time_badge = None
                        active_user.subscription_end_time_badge = None
                        # active_user.subscription_price_badge = None
                        active_user.product_id_badge = None
                        active_user.transaction_id_badge = None
                        active_user.purchase_date_badge = None
                        active_user.badge_name = None

                        db.session.commit()
                        return jsonify({"status": 1, "messege": "No subscription theire."})
                    break
            # if not found:
            return jsonify({"status": 0, "messege": "Invalid product id."})
        else:
            return jsonify({"status": 0, "messege": "Invalid recipt data"})

    return jsonify({"status": 0, "messege": "Invalid receipt or no active subscription found."}), 400


@user_view_v2.route('/get/countries', methods=['GET'])
def get_countries():
    country_data = TblCountries.query.all()
    country_list = [i.as_dict() for i in country_data]

    return jsonify({'status': 1, 'message': 'Sucess', 'list': country_list})


@user_view_v2.route('/get/states', methods=['POST'])
def get_states():
    # country_id = request.json.get('country_id')
    states_data = TblStates.query.filter_by(country_id=233).all()
    states_list = [i.as_dict() for i in states_data]

    return jsonify({'status': 1, 'message': 'Sucess', 'list': states_list})
