from datetime import datetime
from better_profanity import profanity

from flask import request, jsonify, Blueprint
from base.database.db import db
from base.user.models import FavoriteSubCategory,RecommendationComments,NewNotification,token_required, TagFriends, User, ChatMute, Notification, Block,Feed,Follow,LikeRecommendation
from base.community.models import HideCommunity,HideThingsCommunity,ThingsRecommendation,PlacesRecommendation,ThingsReview,PlacesReview, SavedThingsCommunity,CreatedThingsCommunity, SavedCommunity, CommunityPost, PostLike, PostThumsup, PostComment, PostThumpdown, \
    CreatedCommunity,CategoryVisited,ThingsCategoryVisited
from base.community.queryset import community_insert_data, add_like, delete_like, get_community_chat, liked_chats, \
    thumpsup_chats, thumsup, delete_thumsup, delete_thumsdown, thumpsdown_chats, thumsdown, get_user_data
import timeago, pytz, boto3,os,secrets
from base.common.utiils import COMMON_URL
from base.push_notification.push_notification import push_notification
from base.admin.models import BlockedWords, Category,ThingsCategory
from sqlalchemy import func
from werkzeug.utils import secure_filename
from base.v5.user.view import upload_photos
from dotenv import load_dotenv
from pathlib import Path

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

def convert_tz():
    return datetime.now(tz=pytz.timezone('Asia/Kolkata'))

community_create_v5 = Blueprint('community_create_v5', __name__)

REGION_NAME = os.getenv("REGION_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY)


@community_create_v5.route('/badge_wise_user_list', methods=['POST'])
@token_required
def badge_wise_user_list(active_user):
    data = request.get_json()

    if not data:
        return jsonify({'status': 0,'messege': 'Json is empty'})

    badge_category = data.get('badge_category')
    page = int(data.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    city = data.get('city')
    state = data.get('state')
    fullname = data.get('fullname')

    if not badge_category:
        return jsonify({'status': 0,'messege': 'Please select badge category first'})

    # badge_category_list = ['Clothes Badge','Makeup + Perfume Badge','Spa Day Badge','Shopping Spree Badge']
    # if badge_category not in badge_category_list:
    #     return jsonify({'status':0,'messege': 'Invalid badge category selected'})

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    query = User.query.filter(
        User.user_badge == badge_category,
        User.id != active_user.id,
        User.deleted == False,
        User.is_block == False,
        ~User.id.in_(blocked_user_ids),
        ~User.id.in_(blocked_by_user_ids)
    )

    if city:
        query = query.filter(User.city.ilike(f"{city}%"))

    if state:
        query = query.filter(User.state.ilike(f"{state}%"))

    if fullname:
        query = query.filter(User.fullname.ilike(f"{fullname}%"))

    paginated_users = query.paginate(page=page, per_page=per_page, error_out=False)

    # Extract users and pagination info
    users = paginated_users.items

    pagination_info = {
        "current_page": paginated_users.page,
        "has_next": paginated_users.has_next,
        "per_page": paginated_users.per_page,
        "total_pages": paginated_users.pages
    }

    user_list = []

    badge_dict = {
         "Clothes Crush": '🛍️',
        "Glam & Glow": '💅',
        "Self-Care Queen": '💇‍♀️',
        "Ultimate Spoil Me": '💎'

    }

    if users:
        for i in users:
            emoji = badge_dict.get(i.badge_name, '')  # Get emoji or empty if not found
            username = i.fullname + ' ' + emoji

            user_dict = {

                'user_id': i.id,
                'username': username,
                'user_image': i.image_path,
                'city': i.city if i.city is not None else '',
                'state': i.state if i.state is not None else ''
            }
            user_list.append(user_dict)

    return jsonify({'status': 1,'messege': 'Success','user_list': user_list,'pagination_info': pagination_info})


@community_create_v5.route('/recommendation_comments_list', methods=['POST'])
@token_required
def recommendation_comments_list(active_user):
    data = request.get_json()

    if not data:
        return jsonify({'status': 0,'messege': 'Json is empty'})

    type = data.get('type')
    id = data.get('id')
    page = int(data.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    if type == 'things':
        things_data = ThingsRecommendation.query.get(id)
        if not things_data:
            return jsonify({'status': 0,'messege': 'Invalid data'})

        get_all_comments = RecommendationComments.query.filter_by(type='things',
                                                                  things_id=things_data.id).order_by(
            RecommendationComments.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

        has_next = get_all_comments.has_next  # Check if there is a next page
        total_pages = get_all_comments.pages  # Total number of pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        comment_list = []

        if get_all_comments.items:
            for i in get_all_comments.items:
                user_data = User.query.get(i.user_id)

                input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                if not user_data:
                    return jsonify({'status': 0, 'messege': 'Something went wrong'})
                user_details = {

                    'user_id': user_data.id,
                    'username': user_data.fullname,
                    'user_image': user_data.image_path,
                    'comment': i.comment,
                    'created_time': output_date
                }
                comment_list.append(user_details)

        return jsonify({'status': 1, 'messege': 'Success', 'comment_list': comment_list,'pagination_info': pagination_info})


    elif type == 'places':
        places_data = PlacesRecommendation.query.get(id)
        if not places_data:
            return jsonify({'status': 0, 'messege': 'Invalid data'})

        get_all_comments = RecommendationComments.query.filter_by(type='places',
                                                                  places_id=places_data.id).order_by(
            RecommendationComments.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

        has_next = get_all_comments.has_next  # Check if there is a next page
        total_pages = get_all_comments.pages  # Total number of pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        comment_list = []

        if get_all_comments.items:
            for i in get_all_comments.items:
                user_data = User.query.get(i.user_id)
                if not user_data:
                    return jsonify({'status': 0, 'messege': 'Something went wrong'})
                user_details = {

                    'user_id': user_data.id,
                    'username': user_data.fullname,
                    'user_image': user_data.image_path,
                    'comment': i.comment
                }
                comment_list.append(user_details)

        return jsonify(
            {'status': 1, 'messege': 'Success', 'comment_list': comment_list, 'pagination_info': pagination_info})

    else:
        return jsonify({'status': 0,'messege': 'Invalid type must be places or things'})


@community_create_v5.route('/recommendation_my_community_list', methods=['POST'])
@token_required
def recommendation_my_community_list(active_user):
    filter_text = request.json.get('filter_text')
    category_id = request.json.get('category_id')
    city = request.json.get('city')
    state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        return jsonify({'status': 0,'messege':'please provide category id'})

    places_recommendation_data = PlacesRecommendation.query.filter_by(category_id = category_id,user_id = active_user.id).all()
    get_community_ids_list = [i.community_id for i in places_recommendation_data]
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    query = db.session.query(
        CreatedCommunity.id,CreatedCommunity.city,CreatedCommunity.state,
        CreatedCommunity.community_name,
        func.count(SavedCommunity.id).label('saved_count')
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id).\
filter(CreatedCommunity.id.in_(get_community_ids_list)).\
        filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
               SavedCommunity.user_id.not_in(blocked_user_ids),
               SavedCommunity.user_id.not_in(blocked_by_user_ids)). \
        group_by(CreatedCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedCommunity.community_name.desc(),
                               CreatedCommunity.id)
    elif filter_text == 2:
        query = query.order_by(CreatedCommunity.id.desc())
    elif filter_text == 3:
        query = query.order_by(CreatedCommunity.id.asc())
    elif filter_text == 4:
        query = query.order_by(func.count(SavedCommunity.id).desc(),
                               CreatedCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedCommunity.id).asc(),
                               CreatedCommunity.id)
    else:
        query = query.order_by(CreatedCommunity.community_name.asc(),
                               CreatedCommunity.id)

    if city:
        query = query.filter(CreatedCommunity.city == city)
    if state:
        query = query.filter(CreatedCommunity.state == state)

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items',created_data.items)
        for id, city, state, community_name, count in created_data.items:
            print('created_data.items',created_data.items)
            print('category_id',category_id)
            saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id).first()

            print('saved_already',saved_already)

            places_data = PlacesRecommendation.query.filter_by(user_id=active_user.id, community_id=id,
                                                               category_id=category_id).first()
            if not places_data:
                return jsonify({'status': 0, 'messege': 'Invalid data'})

            get_like_exists = LikeRecommendation.query.filter_by(user_id=active_user.id, type='places',
                                                                 places_id=places_data.id).first()

            total_liked_counts = LikeRecommendation.query.filter_by(type='places',
                                                                    places_id=places_data.id).count()
            total_comments_counts = RecommendationComments.query.filter_by(type='places',
                                                                           places_id=places_data.id).count()

            is_liked = False

            if get_like_exists:
                is_liked = True

            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            dict = {'id': str(places_data.id),
                    'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'is_liked': is_liked,
                    'content_type': places_data.content_type if places_data.content_type is not None else '',
                    'text': places_data.text if places_data.text is not None else '',
                    'link': places_data.link if places_data.link is not None else '',
                    'image': places_data.image_path if places_data.image_path is not None else '',
                    'have_image': places_data.have_image if places_data.have_image is not None else False,
                    'total_liked_counts': total_liked_counts,
                    'total_comments_counts': total_comments_counts}
            community_data.append(dict)

        has_next = created_data.has_next  # Check if there is a next page
        total_pages = created_data.pages  # Total number of pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
                        "category_id": category_id})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id})

@community_create_v5.route('/recommendation_community_list', methods=['POST'])
@token_required
def recommendation_community_list(active_user):
    filter_text = request.json.get('filter_text')
    category_id = request.json.get('category_id')
    user_id = request.json.get('user_id')
    city = request.json.get('city')
    state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        return jsonify({'status': 0,'messege':'please provide category id'})

    places_recommendation_data = PlacesRecommendation.query.filter_by(category_id = category_id,user_id = user_id).all()
    get_community_ids_list = [i.community_id for i in places_recommendation_data]
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    query = db.session.query(
        CreatedCommunity.id,CreatedCommunity.city,CreatedCommunity.state,
        CreatedCommunity.community_name,
        func.count(SavedCommunity.id).label('saved_count')
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id).\
filter(CreatedCommunity.id.in_(get_community_ids_list)).\
        filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
               SavedCommunity.user_id.not_in(blocked_user_ids),
               SavedCommunity.user_id.not_in(blocked_by_user_ids)). \
        group_by(CreatedCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedCommunity.community_name.desc(),
                               CreatedCommunity.id)
    elif filter_text == 2:
        query = query.order_by(CreatedCommunity.id.desc())
    elif filter_text == 3:
        query = query.order_by(CreatedCommunity.id.asc())
    elif filter_text == 4:
        query = query.order_by(func.count(SavedCommunity.id).desc(),
                               CreatedCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedCommunity.id).asc(),
                               CreatedCommunity.id)
    else:
        query = query.order_by(CreatedCommunity.community_name.asc(),
                               CreatedCommunity.id)

    if city:
        query = query.filter(CreatedCommunity.city == city)
    if state:
        query = query.filter(CreatedCommunity.state == state)

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items',created_data.items)
        for id, city, state, community_name, count in created_data.items:
            print('created_data.items',created_data.items)
            print('category_id',category_id)
            saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id).first()

            print('saved_already',saved_already)

            places_data = PlacesRecommendation.query.filter_by(user_id=user_id, community_id=id,
                                                               category_id=category_id).first()

            if not places_data:
                return jsonify({'status': 0, 'messege': 'Invalid data'})

            get_like_exists = LikeRecommendation.query.filter_by(user_id=active_user.id, type='places',
                                                                 places_id=places_data.id).first()

            total_liked_counts = LikeRecommendation.query.filter_by(type='places',
                                                                 places_id=places_data.id).count()
            total_comments_counts = RecommendationComments.query.filter_by(type='places',
                                                                    places_id=places_data.id).count()

            is_liked = False

            if get_like_exists:
                is_liked = True

            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            dict = {'id': str(places_data.id),
                    'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'is_liked': is_liked,
                    'total_liked_counts': total_liked_counts,
                    'content_type': places_data.content_type if places_data.content_type is not None else '',
                    'text': places_data.text if places_data.text is not None else '',
                    'link': places_data.link if places_data.link is not None else '',
                    'image': places_data.image_path if places_data.image_path is not None else '',
                    'have_image': places_data.have_image if places_data.have_image is not None else False,
                    'total_comments_counts': total_comments_counts

                    }
            community_data.append(dict)

        has_next = created_data.has_next  # Check if there is a next page
        total_pages = created_data.pages  # Total number of pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
                        "category_id": category_id})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id})

@community_create_v5.route('/recommendation_my_things_community_list', methods=['POST'])
@token_required
def recommendation_my_things_community_list(active_user):
    filter_text = request.json.get('filter_text')
    city = request.json.get('city')
    state = request.json.get('state')
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))
    per_page = 30
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        return jsonify({'status': 'Please provide category id'})
        # category_id = 135
    things_recommendation_data = ThingsRecommendation.query.filter_by(category_id=category_id, user_id=active_user.id).all()
    get_community_ids_list = [i.community_id for i in things_recommendation_data]
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    query = db.session.query(
        CreatedThingsCommunity.id,CreatedThingsCommunity.city,CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        func.count(SavedThingsCommunity.id).label('saved_count')
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(CreatedThingsCommunity.id.in_(get_community_ids_list)). \
        filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
               SavedThingsCommunity.user_id.not_in(blocked_user_ids),
               SavedThingsCommunity.user_id.not_in(blocked_by_user_ids)). \
        group_by(CreatedThingsCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedThingsCommunity.community_name.desc(),
                               CreatedThingsCommunity.id)

    elif filter_text == 2:
        query = query.order_by(CreatedThingsCommunity.id.desc())

    elif filter_text == 3:
        query = query.order_by(CreatedThingsCommunity.id.asc())

    elif filter_text == 4:
        query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
                               CreatedThingsCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedThingsCommunity.id).asc(),
                               CreatedThingsCommunity.id)
    else:
        query = query.order_by(CreatedThingsCommunity.community_name.asc(),
                               CreatedThingsCommunity.id)

    if city:
        query = query.filter(CreatedThingsCommunity.city == city)
    if state:
        query = query.filter(CreatedThingsCommunity.state == state)


    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items',created_data.items)
        for id, city, state, community_name, count in created_data.items:
            print('created_data.items',created_data.items)
            print('category_id',category_id)
            saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id).first()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            # print('saved_already',saved_already)

            things_data = ThingsRecommendation.query.filter_by(user_id=active_user.id, community_id=id,
                                                               category_id=category_id).first()
            if not things_data:
                return jsonify({'status': 0, 'messege': 'Invalid data'})
            get_like_exists = LikeRecommendation.query.filter_by(user_id=active_user.id, type='things',
                                                                 things_id=things_data.id).first()

            total_liked_counts = LikeRecommendation.query.filter_by(type='things',
                                                                    things_id=things_data.id).count()

            total_comments_counts = RecommendationComments.query.filter_by(type='things',
                                                                           things_id=things_data.id).count()

            is_liked = False

            if get_like_exists:
                is_liked = True

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            dict = {'id': str(things_data.id),
                    'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'is_liked': is_liked,
                    'content_type': things_data.content_type if things_data.content_type is not None else '',
                    'text': things_data.text if things_data.text is not None else '',
                    'link': things_data.link if things_data.link is not None else '',
                    'image': things_data.image_path if things_data.image_path is not None else '',
                    'have_image': things_data.have_image if things_data.have_image is not None else False,
                    'total_liked_counts': total_liked_counts,
                    'total_comments_counts': total_comments_counts}
            community_data.append(dict)

        has_next = created_data.has_next
        total_pages = created_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
                        "category_id": category_id})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id})

@community_create_v5.route('/recommendation_things_community_list', methods=['POST'])
@token_required
def recommendation_things_community_list(active_user):
    filter_text = request.json.get('filter_text')
    city = request.json.get('city')
    state = request.json.get('state')
    category_id = request.json.get('category_id')
    user_id = request.json.get('user_id')
    page = int(request.json.get('page', 1))
    per_page = 30
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        return jsonify({'status': 'Please provide category id'})
        # category_id = 135
    things_recommendation_data = ThingsRecommendation.query.filter_by(category_id=category_id, user_id=user_id).all()
    get_community_ids_list = [i.community_id for i in things_recommendation_data]
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    query = db.session.query(
        CreatedThingsCommunity.id,CreatedThingsCommunity.city,CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        func.count(SavedThingsCommunity.id).label('saved_count')
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(CreatedThingsCommunity.id.in_(get_community_ids_list)). \
        filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
               SavedThingsCommunity.user_id.not_in(blocked_user_ids),
               SavedThingsCommunity.user_id.not_in(blocked_by_user_ids)). \
        group_by(CreatedThingsCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedThingsCommunity.community_name.desc(),
                               CreatedThingsCommunity.id)

    elif filter_text == 2:
        query = query.order_by(CreatedThingsCommunity.id.desc())

    elif filter_text == 3:
        query = query.order_by(CreatedThingsCommunity.id.asc())

    elif filter_text == 4:
        query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
                               CreatedThingsCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedThingsCommunity.id).asc(),
                               CreatedThingsCommunity.id)
    else:
        query = query.order_by(CreatedThingsCommunity.community_name.asc(),
                               CreatedThingsCommunity.id)

    if city:
        query = query.filter(CreatedThingsCommunity.city == city)
    if state:
        query = query.filter(CreatedThingsCommunity.state == state)


    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items',created_data.items)
        for id, city, state, community_name, count in created_data.items:
            print('created_data.items',created_data.items)
            print('category_id',category_id)
            saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id).first()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            print('saved_already',saved_already)

            things_data = ThingsRecommendation.query.filter_by(user_id=user_id, community_id=id,
                                                               category_id=category_id).first()
            if not things_data:
                return jsonify({'status': 0, 'messege': 'Invalid data'})
            get_like_exists = LikeRecommendation.query.filter_by(user_id=active_user.id, type='things',
                                                                 things_id=things_data.id).first()
            total_liked_counts = LikeRecommendation.query.filter_by(type='things',
                                                                    things_id=things_data.id).count()

            total_comments_counts = RecommendationComments.query.filter_by(type='things',
                                                                           things_id=things_data.id).count()

            is_liked = False

            if get_like_exists:
                is_liked = True

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            dict = {'id': str(things_data.id),
                    'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'is_liked': is_liked,
                    'content_type': things_data.content_type if things_data.content_type is not None else '',
                    'text': things_data.text if things_data.text is not None else '',
                    'link': things_data.link if things_data.link is not None else '',
                    'image': things_data.image_path if things_data.image_path is not None else '',
                    'have_image': things_data.have_image if things_data.have_image is not None else False,
                    'total_liked_counts': total_liked_counts,
                    'total_comments_counts': total_comments_counts}
            community_data.append(dict)

        has_next = created_data.has_next
        total_pages = created_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
                        "category_id": category_id})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id})


@community_create_v5.route('/add_recommendation_content', methods=['GET', 'POST'])
@token_required
def add_recommendation_content(active_user):

    community_id = request.form.get('community_id')
    category_type = request.form.get('category_type')

    content_type = request.form.get('content_type')
    link = request.form.get('link')
    caption = request.form.get('caption')
    image = request.files.get('image')

    # category_list = ["places","things"]
    #
    # if not category_type in category_list:
    #     return jsonify({'status': 0, 'messege': 'Invalid category selected'})

    text_feild = None
    link_feild = None

    # if content_type == "text":
    #     text_feild = caption
    # elif content_type == "link":
    #     link_feild = link
    check_content_type = "text"
    if content_type == "link":
        check_content_type = "link"

    # else:
    #     return jsonify({'status': 0, 'messege': 'Invalid category selected'})

    image_path = None
    have_image = False

    if image and image.filename:
        file_path, picture = upload_photos(image)
        image_path = file_path
        have_image = True

    if category_type == "places":
        get_reccomandations = PlacesRecommendation.query.filter_by(user_id = active_user.id,community_id=community_id).first()
        if not get_reccomandations:
            return jsonify({'status': 0, 'messege': 'Invalid community selected'})

        get_reccomandations.image_path = image_path
        get_reccomandations.have_image = have_image
        get_reccomandations.text = caption
        get_reccomandations.link = link
        get_reccomandations.content_type = check_content_type

        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully content added'})

    elif category_type == "things":
        get_reccomandations = ThingsRecommendation.query.filter_by(user_id=active_user.id,
                                                                   community_id=community_id).first()
        if not get_reccomandations:
            return jsonify({'status': 0, 'messege': 'Invalid community selected'})

        get_reccomandations.image_path = image_path
        get_reccomandations.have_image = have_image
        get_reccomandations.text = caption
        get_reccomandations.link = link
        get_reccomandations.content_type = check_content_type

        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully content added'})

    else:
        return jsonify({'status': 0, 'messege': 'Invalid category selected'})


@community_create_v5.route('/add_places_recommendation', methods=['GET', 'POST'])
@token_required
def add_places_recommendation(active_user):

    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')

    if not community_id:
        return jsonify({'status':0,'messege': 'Please provide community'})
    if not category_id:
        return jsonify({'status':0,'messege': 'Please provide category'})

    get_community_data = CreatedCommunity.query.get(community_id)
    if not get_community_data:
        return jsonify({'status':0,'messege': 'Invalid community'})

    get_community_data = CreatedCommunity.query.filter_by(id=community_id, category_id=category_id).first()

    check_recommendation = PlacesRecommendation.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                                community_id=community_id).first()

    if check_recommendation:
        if check_recommendation.image_path is not None:
            image = check_recommendation.image_path.replace("https://frienddate-app.s3.amazonaws.com/", "")
            s3_client.delete_object(Bucket=S3_BUCKET, Key=image)

        db.session.delete(check_recommendation)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully removed from my recommendation'})

    else:
        add_places_recommendation_data = PlacesRecommendation(category_id=category_id,user_id = active_user.id, community_id = community_id)
        db.session.add(add_places_recommendation_data)
        db.session.commit()

        text = f'{active_user.fullname} added a new recommendation {get_community_data.community_name} in {places_category_data.category_name} category'

        # add_feed_data = Feed(type='text', text=text, image_name=None, image_path=None,
        #                      created_time=datetime.utcnow(), user_id=active_user.id)
        #
        # db.session.add(add_feed_data)
        # db.session.commit()

        title = f'{active_user.fullname} added a recommendation of your word.'

        add_notification_data = NewNotification(title=title, message=text, page='places recommendation', is_read=False,
                                                created_time=datetime.utcnow(), by_id=active_user.id,
                                                to_id=get_community_data.user_id)
        db.session.add(add_notification_data)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully added to my recommendation'})

@community_create_v5.route('/add_things_recommendation', methods=['GET', 'POST'])
@token_required
def add_things_recommendation(active_user):

    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')

    if not community_id:
        return jsonify({'status':0,'messege': 'Please provide community'})
    if not category_id:
        return jsonify({'status':0,'messege': 'Please provide category'})

    get_community_data = CreatedThingsCommunity.query.filter_by(id = community_id,category_id=category_id).first()
    if not get_community_data:
        return jsonify({'status':0,'messege': 'Invalid community'})

    things_category_data = ThingsCategory.query.get(category_id)

    check_recommendation = ThingsRecommendation.query.filter_by(category_id = category_id,user_id = active_user.id, community_id = community_id).first()

    if check_recommendation:
        if check_recommendation.image_path is not None:
            image = check_recommendation.image_path.replace("https://frienddate-app.s3.amazonaws.com/", "")
            s3_client.delete_object(Bucket=S3_BUCKET, Key=image)

        db.session.delete(check_recommendation)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully removed from my recommendation'})
    else:
        add_things_recommendation_data = ThingsRecommendation(category_id = category_id,user_id = active_user.id, community_id = community_id)
        db.session.add(add_things_recommendation_data)
        db.session.commit()

        text = f'{active_user.fullname} added a new recommendation {get_community_data.community_name} in {things_category_data.category_name} category'
        title =  f'{active_user.fullname} added a recommendation of your word.'

        # add_feed_data = Feed(type = 'text',text=text, image_name=None, image_path=None,
        #                                  created_time=datetime.utcnow(), user_id=active_user.id)
        #
        # db.session.add(add_feed_data)
        # db.session.commit()

        add_notification_data = NewNotification(title = title,message = text,page = 'things recommendation',is_read = False,created_time = datetime.utcnow(),by_id = active_user.id, to_id = get_community_data.user_id)
        db.session.add(add_notification_data)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully added to my recommendation'})


@community_create_v5.route('/delete_places_community_review', methods=['POST'])
@token_required
def delete_places_community_review(active_user):
    review_id = request.json.get('review_id')

    if not review_id:
        return jsonify({'status':0,'messege': 'Please provide review for deletation'})

    get_review_data = PlacesReview.query.filter_by(id = review_id,user_id= active_user.id).first()
    if not get_review_data:
        return jsonify({'status':0,'messege': 'Invalid review'})

    if get_review_data.image_name is not None:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=get_review_data.image_name)

    db.session.delete(get_review_data)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Review deleted successfully'})

@community_create_v5.route('/get_places_community_review', methods=['POST'])
@token_required
def get_places_community_review(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    community_id = request.json.get('community_id')

    if not community_id:
        return jsonify({'status':0,'messege': 'Please provide community'})

    get_community_data = CreatedCommunity.query.get(community_id)
    if not get_community_data:
        return jsonify({'status':0,'messege': 'Invalid community'})

    get_all_reviews = PlacesReview.query.filter(PlacesReview.community_id == community_id).order_by(PlacesReview.id.desc()).paginate(page=page, per_page=per_page,
                                                                                error_out=False)
    has_next = get_all_reviews.has_next
    total_pages = get_all_reviews.pages

    get_all_reviews_list = [ i.as_dict(active_user.id) for i in get_all_reviews.items]

    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    return jsonify({'status': 1,'messege': 'Success', 'places_list': get_all_reviews_list,'pagination_info': pagination_info})

@community_create_v5.route('/add_places_community_review', methods=['GET', 'POST'])
@token_required
def add_places_community_review(active_user):
    title = request.form.get('title')
    text = request.form.get('text')
    image = request.files.get('image')
    community_id = request.form.get('community_id')
    rating = request.form.get('rate')
    rate = 0
    if rating:
        rate = rating

    if not text and not image.filename:
        return jsonify({'status': 0,'messege': 'Please provide inputs'})

    if not community_id:
        return jsonify({'status':0,'messege': 'Please provide community'})

    get_community_data = CreatedCommunity.query.get(community_id)
    if not get_community_data:
        return jsonify({'status':0,'messege': 'Invalid community'})

    image_name = None
    image_url = None
    type = 'text'

    if image and image.filename:
        type = 'image'
        image_name = secure_filename(image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'
        x = secrets.token_hex(10)

        image_name = x + extension

        s3_client.upload_fileobj(image, S3_BUCKET, image_name,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

    text_for_review = f'added a new review in {get_community_data.community_name} community in {get_community_data.community_places_id.category_name} places category review is: ' +  ('\n' + text if text is not None else '')

    add_places_review = PlacesReview(title =title,rate=rate,text = text,image_name = image_name,image_path = image_url,created_time = datetime.utcnow(),community_id = community_id,user_id = active_user.id)
    db.session.add(add_places_review)
    db.session.commit()

    # add_feed_data = Feed(review_table='places', review_id=add_places_review.id, is_review=True, type=type,
    #                      text=text_for_review, image_name=image_name, image_path=image_url,
    #                      created_time=datetime.utcnow(), user_id=active_user.id)
    #
    # db.session.add(add_feed_data)
    # db.session.commit()

    title = f'{active_user.fullname} added a review on your word.'

    add_notification_data = NewNotification(title=title, message=text_for_review, page='places review', is_read=False,
                                            created_time=datetime.utcnow(), by_id=active_user.id,
                                            to_id=get_community_data.user_id)
    db.session.add(add_notification_data)
    db.session.commit()

    all_reviews = PlacesReview.query.filter_by(community_id=community_id).all()
    get_all_rates = [i.rate for i in all_reviews if i.rate != 0 and i.rate is not None]
    get_all_rates_calculation = [i.rate for i in all_reviews if i.rate != 0 and i.rate is not None]

    avarage_rating = 0
    if not sum(get_all_rates) == 0 and len(get_all_rates_calculation) != 0:
        avarage_rating = sum(get_all_rates) / len(get_all_rates_calculation)

    get_community_data = CreatedCommunity.query.get(community_id)
    get_community_data.avarage_rating = avarage_rating
    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully added your review'})


@community_create_v5.route('/delete_things_community_review', methods=['POST'])
@token_required
def delete_things_community_review(active_user):
    review_id = request.json.get('review_id')

    if not review_id:
        return jsonify({'status':0,'messege': 'Please provide review for deletation'})

    get_review_data = ThingsReview.query.filter_by(id = review_id,user_id= active_user.id).first()
    if not get_review_data:
        return jsonify({'status':0,'messege': 'Invalid review'})

    if get_review_data.image_name is not None:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=get_review_data.image_name)

    db.session.delete(get_review_data)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Review deleted successfully'})

@community_create_v5.route('/get_things_community_review', methods=['POST'])
@token_required
def get_things_community_review(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    community_id = request.json.get('community_id')

    if not community_id:
        return jsonify({'status':0,'messege': 'Please provide community'})

    get_community_data = CreatedThingsCommunity.query.get(community_id)
    if not get_community_data:
        return jsonify({'status':0,'messege': 'Invalid community'})

    get_all_reviews = ThingsReview.query.filter(ThingsReview.community_id == community_id).order_by(ThingsReview.id.desc()).paginate(page=page, per_page=per_page,
                                                                                error_out=False)
    has_next = get_all_reviews.has_next
    total_pages = get_all_reviews.pages

    get_all_reviews_list = [ i.as_dict(active_user.id) for i in get_all_reviews.items]

    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    return jsonify({'status': 1,'messege': 'Success', 'things_list': get_all_reviews_list,'pagination_info': pagination_info})

@community_create_v5.route('/add_things_community_review', methods=['GET', 'POST'])
@token_required
def add_things_community_review(active_user):
    title = request.form.get('title')
    text = request.form.get('text')
    image = request.files.get('image')
    community_id = request.form.get('community_id')



    if not text and not image.filename:
        return jsonify({'status': 0,'messege': 'Please provide inputs'})

    if not community_id:
        return jsonify({'status':0,'messege': 'Please provide community'})

    get_community_data = CreatedThingsCommunity.query.get(community_id)
    if not get_community_data:
        return jsonify({'status':0,'messege': 'Invalid community'})

    image_name = None
    image_url = None
    type = 'text'
    if image and image.filename:
        type = 'image'
        image_name = secure_filename(image.filename)
        extension = os.path.splitext(image_name)[1]
        extension2 = os.path.splitext(image_name)[1][1:].lower()

        content_type = f'image/{extension2}'
        x = secrets.token_hex(10)

        image_name = x + extension

        s3_client.upload_fileobj(image, S3_BUCKET, image_name,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

    add_things_review = ThingsReview(title =title,text = text,image_name = image_name,image_path = image_url,created_time = datetime.utcnow(),community_id = community_id,user_id = active_user.id)
    db.session.add(add_things_review)
    db.session.commit()

    text_for_review = f'added a new review in {get_community_data.community_name} community in {get_community_data.community_things_id.category_name} things category review is: ' +  ('\n' + text if text is not None else '')

    # add_feed_data = Feed(review_table = 'things',review_id = add_things_review.id,is_review = True,type=type, text=text_for_review, image_name=image_name, image_path=image_url,
    #                      created_time=datetime.utcnow(), user_id=active_user.id)
    #
    # db.session.add(add_feed_data)
    # db.session.commit()

    title = f'{active_user.fullname} added a review on your word.'

    add_notification_data = NewNotification(title=title, message=text_for_review, page='things review', is_read=False,
                                            created_time=datetime.utcnow(), by_id=active_user.id,
                                            to_id=get_community_data.user_id)
    db.session.add(add_notification_data)
    db.session.commit()

    all_reviews = ThingsReview.query.filter_by(community_id=community_id).all()
    get_all_rates = [i.rate for i in all_reviews if i.rate != 0 and i.rate is not None]
    print('get_all_ratesssssssssssssssssssssssssssssssssssssss',get_all_rates)
    get_all_rates_calculation = [i.rate for i in all_reviews if i.rate != 0 and i.rate is not None]

    print('get_all_rates_calculationnnnnnnnnnnnnnnnnnnnnn',get_all_rates_calculation)

    avarage_rating = 0
    if not sum(get_all_rates) == 0 and len(get_all_rates_calculation) != 0:
        avarage_rating = sum(get_all_rates) / len(get_all_rates_calculation)

    get_community_data = CreatedThingsCommunity.query.get(community_id)
    get_community_data.avarage_rating = avarage_rating
    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully added your review'})

@community_create_v5.route('/add_community', methods=['GET', 'POST'])
@token_required
def add_community(active_user):
    category_id = request.json.get('category_id')
    comm_name = request.json.get('community_name')
    state = request.json.get('state')
    city = request.json.get('city')
    community_name = comm_name[0].upper() + comm_name[1:]
    cat_info = Category.query.filter_by(id=category_id).first()

    if not cat_info:
        return jsonify({'status': 0,'messege': 'Invalid category'})

    get_community = CreatedCommunity.query.filter_by(category_id=category_id).all()

    if request.method == 'POST':

        community_exits = CreatedCommunity.query.filter_by(category_id=category_id,
                                                           community_name=community_name,
                                                                   user_id=active_user.id).first()

        if community_exits:
            return jsonify({'status': 1, 'messege': 'Community already saved by you'})

        blocked_words_ls = []

        blocked_words = BlockedWords.query.all()
        for blocks in blocked_words:
            blocked_words_ls.append(blocks.blocked_word.lower())

        split_community_name = community_name.split()

        for word in split_community_name:
            if word.lower() in blocked_words_ls:
                return jsonify({'status': 0, 'messege': 'Community Name Contains Abusive Words'})

        if community_name.lower() in blocked_words_ls:
            return jsonify({'status': 0, 'messege': 'Community Name Contains Abusive Words'})

        else:

            community = CreatedCommunity(city = city,state = state,community_name=community_name, category_id=category_id,
                                             user_id=active_user.id, created_time=datetime.utcnow())
            community_insert_data(community)

            communit = SavedCommunity(city=city,state=state,created_id=community.id, community_name=community.community_name,
                                          category_id=community.category_id,
                                          user_id=active_user.id, created_time=community.created_time, is_saved=True)
            community_insert_data(communit)

            return jsonify({'status': 1, 'messege': 'Saved', 'data': community.as_dict()})

    community_list = []

    if not get_community:
        return jsonify({'status': 1, 'messege': 'This category dont have any community yet'})

    if get_community:
        for i in get_community:
            dict = {'community_id': i.id,
                    'community_name': i.community_name,
                    'city': i.city if i.city is not None else '',
                    'state': i.state if i.state is not None else ''}
            community_list.append(dict)
        return jsonify({'status': 1, 'community_list': community_list})


@community_create_v5.route('/add_things_community', methods=['GET', 'POST'])
@token_required
def add_things_community(active_user):
    category_id = request.json.get('category_id')
    comm_name = request.json.get('community_name')
    state = request.json.get('state')
    city = request.json.get('city')
    community_name = comm_name[0].upper() + comm_name[1:]
    cat_info = ThingsCategory.query.filter_by(id=category_id).first()

    if not cat_info:
        return jsonify({'status': 0,'messege': 'Invalid category'})

    get_community = CreatedThingsCommunity.query.filter_by(category_id=category_id).all()

    if request.method == 'POST':

        community_exits = CreatedThingsCommunity.query.filter_by(category_id=category_id,
                                                           community_name=community_name,
                                                                   user_id=active_user.id).first()

        if community_exits:
            return jsonify({'status': 1, 'messege': 'Word already saved by you'})

        blocked_words_ls = []

        blocked_words = BlockedWords.query.all()
        for blocks in blocked_words:
            blocked_words_ls.append(blocks.blocked_word.lower())

        split_community_name = community_name.split()

        for word in split_community_name:
            if word.lower() in blocked_words_ls:
                return jsonify({'status': 0, 'messege': 'Community Name Contains Abusive Words'})

        if community_name.lower() in blocked_words_ls:
            return jsonify({'status': 0, 'messege': 'Community Name Contains Abusive Words'})

        else:

            community = CreatedThingsCommunity(city = city,state = state,community_name=community_name, category_id=category_id,
                                             user_id=active_user.id, created_time=datetime.utcnow())
            community_insert_data(community)

            communit = SavedThingsCommunity(city=city,state=state,created_id=community.id, community_name=community.community_name,
                                          category_id=community.category_id,
                                          user_id=active_user.id, created_time=community.created_time, is_saved=True)
            community_insert_data(communit)

            return jsonify({'status': 1, 'messege': 'Saved', 'data': community.as_dict()})

    community_list = []

    if not get_community:
        return jsonify({'status': 1, 'messege': 'This category dont have any community yet'})

    if get_community:
        for i in get_community:
            dict = {'community_id': i.id,
                    'community_name': i.community_name,
                    'city': i.city if i.city is not None else '',
                    'state': i.state if i.state is not None else ''}
            community_list.append(dict)
        return jsonify({'status': 1, 'community_list': community_list})


@community_create_v5.route('/save_community', methods=['POST'])
@token_required
def save_community(active_user):
    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')
    if not community_id:
        return jsonify({'status': 0, 'messege': 'Community id is required'})
    if not category_id:
        return jsonify({'status': 0, 'messege': 'Category id is required'})

    created_community = CreatedCommunity.query.filter_by(id=community_id, category_id=category_id).first()
    if created_community:
        validate = SavedCommunity.query.filter_by(created_id=community_id, user_id=active_user.id).first()

        if validate:

            db.session.delete(validate)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully removed community'})

            # if validate.is_saved == True:
            #     validate.is_saved = False
            #     db.session.commit()
            #     return jsonify({'status': 1, 'messege': 'Successfully unsave'})
            #
            # else:
            #     validate.is_saved = True
            #     db.session.commit()
            #     return jsonify({'status': 1, 'messege': 'Successfully saved this community'})

        else:
            communit = SavedCommunity(city=created_community.city, state=created_community.state,
                                      created_id=created_community.id, community_name=created_community.community_name,
                                      category_id=created_community.category_id,
                                      user_id=active_user.id, created_time=datetime.utcnow(), is_saved=True)
            community_insert_data(communit)
            return jsonify({'status': 1, 'messege': 'Successfully saved this community'})
    else:
        return jsonify({'status': 0, 'messege': 'Invalid community you select'})


@community_create_v5.route('/save_things_community', methods=['POST'])
@token_required
def save_things_community(active_user):
    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')
    if not community_id:
        return jsonify({'status': 0, 'messege': 'Community id is required'})
    if not category_id:
        return jsonify({'status': 0, 'messege': 'Category id is required'})

    created_community = CreatedThingsCommunity.query.filter_by(id=community_id, category_id=category_id).first()
    if created_community:
        validate = SavedThingsCommunity.query.filter_by(created_id=community_id, user_id=active_user.id).first()

        if validate:

            db.session.delete(validate)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully removed community'})

            # if validate.is_saved == True:
            #     validate.is_saved = False
            #     db.session.commit()
            #     return jsonify({'status': 1, 'messege': 'Successfully unsave'})
            #
            # else:
            #     validate.is_saved = True
            #     db.session.commit()
            #     return jsonify({'status': 1, 'messege': 'Successfully saved this community'})
        else:
            communit = SavedThingsCommunity(city = created_community.city,state = created_community.state,created_id=created_community.id, community_name=created_community.community_name,
                                      category_id=created_community.category_id,
                                      user_id=active_user.id, created_time=datetime.utcnow(), is_saved=True)
            community_insert_data(communit)
            return jsonify({'status': 1, 'messege': 'Successfully saved this community'})
    else:
        return jsonify({'status': 0, 'messege': 'Invalid community you select'})


@community_create_v5.route('/join_community', methods=['POST'])
@token_required
def join_community(active_user):
    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')
    if not community_id:
        return jsonify({'status': 0, 'messege': 'Community id is required'})
    if not category_id:
        return jsonify({'status': 0, 'messege': 'Category id is required'})

    created_community = CreatedCommunity.query.filter_by(id=community_id, category_id=category_id).first()
    if created_community:
        validate = SavedCommunity.query.filter_by(created_id=community_id, user_id=active_user.id).first()
        if validate:
            if validate.is_saved == True:
                validate.is_saved = False
                validate.id = validate.id
                db.session.commit()
                return jsonify({'status': 1, 'messege': 'Unjoin this community', 'join_status': 0})
            else:
                validate.is_saved = True
                validate.id = validate.id
                db.session.commit()
            return jsonify({'status': 1, 'messege': 'Successfully join this community', 'join_status': 1})
    else:
        return jsonify({'status': 0, 'messege': 'Invalid community you select'})


@community_create_v5.route('/my_community', methods=['GET', 'POST'])
@token_required
def my_community(active_user):
    filter_text = request.json.get('filter')
    searching = request.json.get('search')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    counts_subquery = (db.session.query(
        SavedCommunity.created_id,
        func.count(SavedCommunity.user_id.distinct()).label("user_count")
    )
                       .filter(SavedCommunity.is_saved == True)
                       .filter(SavedCommunity.user_id.notin_(blocked_user_ids),
                               SavedCommunity.user_id.notin_(blocked_by_user_ids))
                       .group_by(SavedCommunity.created_id)
                       .subquery())

    # Main query to join SavedCommunity with the counts subquery
    query = (db.session.query(SavedCommunity, counts_subquery.c.user_count)
             .join(counts_subquery, SavedCommunity.created_id == counts_subquery.c.created_id)
             .join(User, SavedCommunity.user_id == User.id)  # Ensuring we join with User for additional filters
             .filter(User.deleted == False, User.is_block == False, User.id == active_user.id))

    if filter_text == 1:
        query = query.order_by(SavedCommunity.community_name.desc())
    elif filter_text == 2:
        query = query.order_by(SavedCommunity.visited.desc())
    elif filter_text == 3:
        query = query.order_by(SavedCommunity.visited.asc())
    elif filter_text == 4:
        query = query = query.order_by(counts_subquery.c.user_count.desc())

    elif filter_text == 5:

        query = query = query.order_by(counts_subquery.c.user_count.asc())
    else:
        query = query.order_by(SavedCommunity.community_name)
    saved_data = query.paginate(page=page, per_page=per_page, error_out=False)

    results = []
    if request.method == 'POST':

        if searching:
            if saved_data.items:
                for item in saved_data.items:
                    if searching.lower() in item.community_name.lower():
                        results.append(item)
        data_list = []

        if saved_data.items:
            print('saved_dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', saved_data.items)
            if searching:
                if len(results) > 0:
                    return jsonify({'status': 1,'messege': 'Success', 'data': results})
                else:
                    return jsonify({'status': 1, 'data': [], 'messege': 'Not Found'})
            else:
                if saved_data.items:
                    for save, count in saved_data.items:
                        visited = 0
                        if save.visited:
                            visited = save.visited
                        saves_dict = {
                            "city": save.city if save.city is not None else '',
                            "state": save.state if save.state is not None else '',
                            "category_id": save.category_id,
                            "community_name": save.community_name,
                            "created_id": save.created_id,
                            "created_time": save.created_time,
                            "id": save.id,
                            "members_count": str(count),
                            "user_id": str(save.user_id),
                            "visited": visited
                        }
                        data_list.append(saves_dict)
                # data_list = [i.as_dict() for i in saved_data.items]
                has_next = saved_data.has_next  # Check if there is a next page
                total_pages = saved_data.pages  # Total number of pages

                pagination_info = {
                    "current_page": page,
                    "has_next": has_next,
                    "per_page": per_page,
                    "total_pages": total_pages,
                }

                return jsonify(
                    {'status': 1, 'data': data_list, 'messege': 'Sucess', 'pagination': pagination_info})
        if not len(data_list) > 0:
            return jsonify({'status': 1, 'data': [], 'messege': "You haven't joined any communities yet."})

@community_create_v5.route('/my_things_community', methods=['GET', 'POST'])
@token_required
def my_things_community(active_user):
    filter_text = request.json.get('filter')
    searching = request.json.get('search')
    page = int(request.json.get('page', 1))
    per_page = 30
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    counts_subquery = (db.session.query(
        SavedThingsCommunity.created_id,
        func.count(SavedThingsCommunity.user_id.distinct()).label("user_count")
    )
                       .filter(SavedThingsCommunity.is_saved == True)
                       .filter(SavedThingsCommunity.user_id.notin_(blocked_user_ids),
                               SavedThingsCommunity.user_id.notin_(blocked_by_user_ids))
                       .group_by(SavedThingsCommunity.created_id)
                       .subquery())

    # Main query to join SavedCommunity with the counts subquery
    query = (db.session.query(SavedThingsCommunity, counts_subquery.c.user_count)
             .join(counts_subquery, SavedThingsCommunity.created_id == counts_subquery.c.created_id)
             .join(User, SavedThingsCommunity.user_id == User.id)  # Ensuring we join with User for additional filters
             .filter(User.deleted == False, User.is_block == False, User.id == active_user.id))

    if filter_text == 1:
        query = query.order_by(SavedThingsCommunity.community_name.desc())
    elif filter_text == 2:
        query = query.order_by(SavedThingsCommunity.visited.desc())
    elif filter_text == 3:
        query = query.order_by(SavedThingsCommunity.visited.asc())
    elif filter_text == 4:
        query = query = query.order_by(counts_subquery.c.user_count.desc())

    elif filter_text == 5:

        query = query = query.order_by(counts_subquery.c.user_count.asc())
    else:
        query = query.order_by(SavedThingsCommunity.community_name)
    saved_data = query.paginate(page=page, per_page=per_page, error_out=False)

    results = []
    if request.method == 'POST':

        if searching:
            if saved_data.items:
                for item in saved_data.items:
                    if searching.lower() in item.community_name.lower():
                        results.append(item)
        data_list = []

        if saved_data.items:
            print('saved_dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', saved_data.items)
            if searching:
                if len(results) > 0:
                    return jsonify({'status': 1,'messege': 'Success', 'data': results})
                else:
                    return jsonify({'status': 1, 'data': [], 'messege': 'Not Found'})
            else:
                if saved_data.items:
                    for save, count in saved_data.items:
                        visited = 0
                        if save.visited:
                            visited = save.visited
                        saves_dict = {
                            "city": save.city if save.city is not None else '',
                            "state": save.state if save.state is not None else '',
                            "category_id": save.category_id,
                            "community_name": save.community_name,
                            "created_id": save.created_id,
                            "created_time": save.created_time,
                            "id": save.id,
                            "members_count": str(count),
                            "user_id": str(save.user_id),
                            "visited": visited
                        }
                        data_list.append(saves_dict)
                # data_list = [i.as_dict() for i in saved_data.items]
                has_next = saved_data.has_next  # Check if there is a next page
                total_pages = saved_data.pages  # Total number of pages

                pagination_info = {
                    "current_page": page,
                    "has_next": has_next,
                    "per_page": per_page,
                    "total_pages": total_pages,
                }

                return jsonify(
                    {'status': 1, 'data': data_list, 'messege': 'Sucess', 'pagination': pagination_info})
        if not len(data_list) > 0:
            return jsonify({'status': 1, 'data': [], 'messege': "You haven't joined any communities yet."})


@community_create_v5.route('/community_library', methods=['POST'])
@token_required
def community_library(active_user):
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    community_data = CreatedCommunity.query.filter_by(category_id=category_id).all()
    community_list = []
    if len(community_data) > 0:
        for i in community_data:
            saved_already = SavedCommunity.query.filter_by(category_id=i.category_id, user_id=active_user.id,
                                                           created_id=i.id).first()
            community_members = SavedCommunity.query.filter_by(category_id=i.category_id, created_id=i.id).count()

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            community_dict = {'id': str(i.id),
                              'community_name': i.community_name,
                              'category_id': str(i.category_id),
                              'is_saved': is_saved,
                              'community_members': str(community_members)
                              }
            community_list.append(community_dict)
    community_list = sorted(community_list, key=lambda x: x['community_name'])
    if len(community_list) > 0:
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        # Slice the list to get the records for the current page
        current_page_records = community_list[start_index:end_index]

        # Calculate total pages and whether there is a next page
        total_items = len(community_list)
        total_pages = (total_items + per_page - 1) // per_page
        has_next = page < total_pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'list': current_page_records, 'messege': "Sucess", 'pagination': pagination_info})
    else:
        return jsonify({'status': 1, 'list': [], 'messege': "No words saved by anyone"})

@community_create_v5.route('/community_homepage', methods=['POST'])
@token_required
def community_homepage(active_user):
    filter_text = request.json.get('filter_text')
    category_id = request.json.get('category_id')
    # city = request.json.get('city')
    # state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        category_id = 167

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    query = db.session.query(
        CreatedCommunity.id, CreatedCommunity.link, CreatedCommunity.city, CreatedCommunity.state,
        CreatedCommunity.community_name,
        func.count(SavedCommunity.id).label('saved_count')
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
               SavedCommunity.user_id.not_in(blocked_user_ids),
               SavedCommunity.user_id.not_in(blocked_by_user_ids)). \
        group_by(CreatedCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedCommunity.community_name.desc(),
                               CreatedCommunity.id)
    elif filter_text == 2:
        query = query.order_by(CreatedCommunity.id.desc())
    elif filter_text == 3:
        query = query.order_by(CreatedCommunity.id.asc())
    elif filter_text == 4:
        query = query.order_by(func.count(SavedCommunity.id).desc(),
                               CreatedCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedCommunity.id).asc(),
                               CreatedCommunity.id)
    else:
        query = query.order_by(CreatedCommunity.community_name.asc(),
                               CreatedCommunity.id)

    # if city:
    #     query = query.filter(CreatedCommunity.city == city)
    # if state:
    #     query = query.filter(CreatedCommunity.state == state)

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items', created_data.items)
        for id,link, city, state, community_name, count in created_data.items:
            print('created_data.items', created_data.items)
            print('category_id', category_id)
            saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id,is_saved = True).first()

            print('saved_already', saved_already)

            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedCommunity, User)
                                           .join(User, SavedCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id, SavedCommunity.category_id == category_id,
                                                   SavedCommunity.created_id == id,
                                                   ~SavedCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            if same_community_members_data:
                each_saved_community, member_user = same_community_members_data

                if saved_already:
                    is_saved = True
                else:
                    is_saved = False

                dict = {'community_id': str(id),
                        'community_name': community_name,
                        'members_count': str(count),
                        'is_saved': is_saved,
                        'city': city if city is not None else '',
                        'state': state if state is not None else '',
                        'is_recommendation': bool(have_recommendation),
                        'link': link if link is not None else '',
                        'user_id': str(member_user.id),
                        'username': member_user.fullname,
                        'user_image': member_user.image_path
                        }

                community_data.append(dict)

    has_next = created_data.has_next  # Check if there is a next page
    total_pages = created_data.pages  # Total number of pages

    pagination_info = {
                    "current_page": page,
                    "has_next": has_next,
                    "per_page": per_page,
                    "total_pages": total_pages,
                }

    if len(community_data)>0:

        return jsonify({'status': 1, 'data': community_data, 'counts': str(total_community_count), 'messege': 'Sucess',
                                'pagination': pagination_info,
                                "category_id": category_id})

    else:
        return jsonify(
            {'status': 1, 'data': [], 'counts': str(total_community_count),
             'messege': 'Dont have any user matches with you in resturant category',
             "category_id": category_id,
                                'pagination': pagination_info})

# @community_create_v5.route('/community_list', methods=['POST'])
# @token_required
# def community_list(active_user):
#     filter_text = request.json.get('filter_text')
#     category_id = request.json.get('category_id')
#     city = request.json.get('city')
#     state = request.json.get('state')
#     page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#     per_page = 10  # Number of items per page
#     if filter_text is None:
#         filter_text = 4
#     if category_id is None:
#         category_id = 135
#
#     saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
#     saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()
#
#     total_community_count = saved_places_community_count + saved_things_community_count
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     query = db.session.query(
#         CreatedCommunity.id, CreatedCommunity.link, CreatedCommunity.city, CreatedCommunity.state,
#         CreatedCommunity.community_name,
#         func.count(SavedCommunity.id).label('saved_count')
#     ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
#         join(User, SavedCommunity.user_id == User.id). \
#         filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
#                SavedCommunity.user_id.not_in(blocked_user_ids),
#                SavedCommunity.user_id.not_in(blocked_by_user_ids)). \
#         group_by(CreatedCommunity.id)
#
#     if filter_text == 1:
#         query = query.order_by(CreatedCommunity.community_name.desc(),
#                                CreatedCommunity.id)
#     elif filter_text == 2:
#         query = query.order_by(CreatedCommunity.id.desc())
#     elif filter_text == 3:
#         query = query.order_by(CreatedCommunity.id.asc())
#     elif filter_text == 4:
#         query = query.order_by(func.count(SavedCommunity.id).desc(),
#                                CreatedCommunity.id)
#     elif filter_text == 5:
#         query = query.order_by(func.count(SavedCommunity.id).asc(),
#                                CreatedCommunity.id)
#     else:
#         query = query.order_by(CreatedCommunity.community_name.asc(),
#                                CreatedCommunity.id)
#
#     if city:
#         query = query.filter(CreatedCommunity.city == city)
#     if state:
#         query = query.filter(CreatedCommunity.state == state)
#
#     created_data = query.paginate(page=page, per_page=per_page, error_out=False)
#
#     community_data = []
#
#     if created_data.items:
#         print('created_data.items', created_data.items)
#         for id,link, city, state, community_name, count in created_data.items:
#             print('created_data.items', created_data.items)
#             print('category_id', category_id)
#             saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
#                                                            created_id=id,is_saved = True).first()
#
#             print('saved_already', saved_already)
#
#             have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
#
#             same_community_members_data = (db.session.query(SavedCommunity, User)
#                                            .join(User, SavedCommunity.user_id == User.id)
#                                            .filter(User.is_block == False, User.deleted == False,
#                                                    User.id != active_user.id, SavedCommunity.category_id == category_id,
#                                                    SavedCommunity.created_id == id,
#                                                    ~SavedCommunity.user_id.in_(blocked_user_ids),
#                                                    ~SavedCommunity.user_id.in_(blocked_by_user_ids)).limit(1).all())
#             print('same_community_members_data', same_community_members_data)
#
#             same_community_memebers_list = []
#             for each_saved_community, member_user in same_community_members_data:
#                 member_basic_data = {
#                     'user_id': str(member_user.id),
#                     'username': member_user.fullname,
#                     'user_image': member_user.image_path}
#                 same_community_memebers_list.append(member_basic_data)
#
#             if saved_already:
#                 is_saved = True
#             else:
#                 is_saved = False
#
#             dict = {'community_id': str(id),
#                     'community_name': community_name,
#                     'members_count': str(count),
#                     'is_saved': is_saved,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'is_recommendation': bool(have_recommendation),
#                     'same_community_memebrs': same_community_memebers_list,
#                     'link': link if link is not None else ''
#             }
#             community_data.append(dict)
#
#         has_next = created_data.has_next  # Check if there is a next page
#         total_pages = created_data.pages  # Total number of pages
#
#         pagination_info = {
#             "current_page": page,
#             "has_next": has_next,
#             "per_page": per_page,
#             "total_pages": total_pages,
#         }
#
#         return jsonify({'status': 1, 'data': community_data, 'counts': str(total_community_count), 'messege': 'Sucess',
#                         'pagination': pagination_info,
#                         "category_id": category_id})
#     else:
#         return jsonify(
#             {'status': 1, 'data': [], 'counts': str(total_community_count), 'messege': 'You Not Save Any Words Yet',
#              "category_id": category_id})


@community_create_v5.route('/liked_places_community_list', methods=['POST'])
@token_required
def liked_community_list(active_user):
    filter_text = request.json.get('filter_text')
    category_id = request.json.get('category_id')
    city = request.json.get('city')
    state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        category_id = 135

    print('city', city)
    print('state', state)
    print('category_id', category_id)
    print('page', page)

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    # query = db.session.query(
    #     CreatedCommunity.id, CreatedCommunity.link, CreatedCommunity.city, CreatedCommunity.state,
    #     CreatedCommunity.community_name,
    #     func.count(SavedCommunity.id).label('saved_count')
    # ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
    #     join(User, SavedCommunity.user_id == User.id). \
    #     filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
    #            SavedCommunity.user_id.not_in(blocked_user_ids),
    #            SavedCommunity.user_id.not_in(blocked_by_user_ids),SavedCommunity.user_id != active_user.id). \
    #     group_by(CreatedCommunity.id)


    included_created_ids = db.session.query(SavedCommunity.created_id).filter(
        SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
    ).subquery()

    # Main query
    query = db.session.query(
        CreatedCommunity.id,
        CreatedCommunity.link,
        CreatedCommunity.city,
        CreatedCommunity.state,
        CreatedCommunity.community_name,
        func.count(SavedCommunity.id).label('saved_count')
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        SavedCommunity.category_id == category_id,
        User.is_block == False,
        SavedCommunity.user_id.not_in(blocked_user_ids),
        SavedCommunity.user_id.not_in(blocked_by_user_ids),
        # SavedCommunity.user_id != active_user.id,
        SavedCommunity.created_id.in_(included_created_ids)
    ). \
        group_by(CreatedCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedCommunity.community_name.desc(),
                               CreatedCommunity.id)
    elif filter_text == 2:
        query = query.order_by(CreatedCommunity.id.desc())
    elif filter_text == 3:
        query = query.order_by(CreatedCommunity.id.asc())
    elif filter_text == 4:
        query = query.order_by(func.count(SavedCommunity.id).desc(),
                               CreatedCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedCommunity.id).asc(),
                               CreatedCommunity.id)
    else:
        query = query.order_by(CreatedCommunity.community_name.asc(),
                               CreatedCommunity.id)

    if city:
        query = query.filter(CreatedCommunity.city == city)
    if state:
        query = query.filter(CreatedCommunity.state == state)

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items', created_data.items)
        for id, link, city, state, community_name, count in created_data.items:
            # print('created_data.items',created_data.items)
            # print('category_id',category_id)
            saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id, is_saved=True).first()

            # print('saved_already',saved_already)

            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedCommunity, User)
                                           .join(User, SavedCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id, SavedCommunity.category_id == category_id,
                                                   SavedCommunity.created_id == id,
                                                   ~SavedCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            user_id = ""
            username = ""
            user_image = ""

            if same_community_members_data:
                same_community_memebers_list = []
                each_saved_community, member_user = same_community_members_data
                print('each_saved_community', each_saved_community)
                print('member_user', member_user)

                user_id = str(member_user.id)
                username = member_user.fullname
                user_image = member_user.image_path
                print('user_id', user_id)

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            dict = {'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'user_id': user_id,
                    'username': username,
                    'user_image': user_image,
                    # 'same_community_memebrs': same_community_memebers_list,
                    'link': link if link is not None else ''
                    }
            community_data.append(dict)

        has_next = created_data.has_next  # Check if there is a next page
        total_pages = created_data.pages  # Total number of pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'counts': str(total_community_count), 'messege': 'Sucess',
                        'pagination': pagination_info,
                        "category_id": category_id})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify(
            {'status': 1, 'data': [], 'counts': str(total_community_count), 'messege': 'You Not Save Any Words Yet',
             "category_id": category_id, 'pagination_info': pagination_info})

@community_create_v5.route('/trending_page', methods=['POST'])
@token_required
def trending_page(active_user):

    data = request.get_json()

    tab = data.get('tab',"0")
    search_text = data.get('search_text')
    city = data.get('city')
    state = data.get('state')

    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    if not tab:
        return jsonify({"status": 0,"message": "Please select tab"})

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    if tab == "0":

        # excluded_created_ids = db.session.query(SavedCommunity.created_id).filter(
        #     SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
        # ).subquery()

        # ,
        # ~SavedCommunity.created_id.in_(excluded_created_ids)

        # Main query
        query = db.session.query(
            CreatedCommunity.id,
            CreatedCommunity.link,
            CreatedCommunity.city,
            CreatedCommunity.state,
            CreatedCommunity.community_name,
            CreatedCommunity.category_id,
            func.count(SavedCommunity.id).label('saved_count')
        ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
            join(User, SavedCommunity.user_id == User.id). \
            group_by(CreatedCommunity.id)

        if search_text:
            query = query.filter(CreatedCommunity.community_name.ilike(f"{search_text}%"))

        if city:
            query = query.filter(CreatedCommunity.city.ilike(f"{city}%"))
        if state:
            query = query.filter(CreatedCommunity.state.ilike(f"{state}%"))

        query = query.order_by(func.count(SavedCommunity.id).desc(),
                               CreatedCommunity.id)

        created_data = query.paginate(page=page, per_page=per_page, error_out=False)

        community_data = []

        if created_data.items:
            print('created_data.items', created_data.items)
            for id, link, city, state, community_name,category_id, count in created_data.items:
                category_data = Category.query.get(category_id)

                saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                                created_id=id, is_saved=True).first()



                dict = {'community_id': str(id),
                        'community_name': community_name,
                        'members_count': str(count),
                        'is_saved': bool(saved_already),
                        'city': city if city is not None else '',
                        'state': state if state is not None else '',
                        'link': link if link is not None else '',
                        'category_id': str(category_id),
                        'category_name': category_data.category_name,
                        'type': 'places'
                        }
                community_data.append(dict)

            has_next = created_data.has_next  # Check if there is a next page
            total_pages = created_data.pages  # Total number of pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            return jsonify({'status': 1, 'data': community_data,  'messege': 'Sucess','pagination': pagination_info})
        else:
            pagination_info = {
                "current_page": 1,
                "has_next": False,
                "per_page": 10,
                "total_pages": 1,
            }
            return jsonify(
                {'status': 1, 'data': [], 'messege': 'No one create words yet', 'pagination_info': pagination_info})

    elif tab == "1":

        # excluded_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
        #     SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
        # ).subquery()

        # ~SavedThingsCommunity.created_id.in_(excluded_created_ids)

        query = db.session.query(
            CreatedThingsCommunity.id, CreatedThingsCommunity.link, CreatedThingsCommunity.city,
            CreatedThingsCommunity.state,
            CreatedThingsCommunity.community_name,
            CreatedThingsCommunity.category_id,
            func.count(SavedThingsCommunity.id).label('saved_count')
        ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
            join(User, SavedThingsCommunity.user_id == User.id). \
            group_by(CreatedThingsCommunity.id)

        if search_text:
            query = query.filter(CreatedThingsCommunity.community_name.ilike(f"{search_text}%"))

        query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
                               CreatedThingsCommunity.id)

        if city:
            query = query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
        if state:
            query = query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))

        created_data = query.paginate(page=page, per_page=per_page, error_out=False)

        community_data = []

        if created_data.items:
            print('created_data.items', created_data.items)
            for id, link, city, state, community_name, category_id , count in created_data.items:
                category_data = ThingsCategory.query.get(category_id)

                saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                                     created_id=id, is_saved=True).first()

                get_saved_things_users = (
                    SavedThingsCommunity.query
                        .join(User, SavedThingsCommunity.user_id == User.id)
                        .filter(
                        SavedThingsCommunity.created_id == id,
                        SavedThingsCommunity.category_id == category_id,
                        SavedThingsCommunity.user_id != active_user.id,
                        ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
                        ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
                        User.deleted == False,
                        User.is_block == False
                    )
                        .limit(6)
                        .all()
                )

                get_saved_things_user_list = []

                if len(get_saved_things_users) > 0:
                    for j in get_saved_things_users:
                        user_dict = {

                            'user_id': j.save_things_community.id,
                            'username': j.save_things_community.fullname,
                            'user_image': j.save_things_community.image_path
                        }

                        get_saved_things_user_list.append(user_dict)

                dict = {'community_id': str(id),
                        'community_name': community_name,
                        'members_count': str(count),
                        'members_list': get_saved_things_user_list,
                        'is_saved': bool(saved_already),
                        'city': city if city is not None else '',
                        'state': state if state is not None else '',
                        'link': link if link is not None else '',
                        'category_id': str(category_id),
                        'category_name': category_data.category_name,
                        'type': 'things'}

                community_data.append(dict)

            has_next = created_data.has_next
            total_pages = created_data.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            return jsonify(
                {'status': 1, 'data': community_data, 'messege': 'Sucess',
                 'pagination': pagination_info})
        else:
            pagination_info = {
                "current_page": 1,
                "has_next": False,
                "per_page": 10,
                "total_pages": 1,
            }
            return jsonify(
                {'status': 1, 'data': [], 'messege': 'No one save any words yet',
                  'pagination': pagination_info})

    else:
        return jsonify({'status': 0,'messege': "Invalid tab"})


@community_create_v5.route('/hide_community', methods=['POST'])
@token_required
def hide_community(active_user):
    try:
        category_id = request.json.get('category_id')
        community_id = request.json.get('community_id')

        if not category_id:
            return jsonify({'status': 0,'messege': 'Please select category first'})
        if not community_id:
            return jsonify({'status': 0,'messege': 'Please select community first'})

        get_community = CreatedCommunity.query.filter_by(category_id = category_id,id = community_id).first()
        if not get_community:
            return jsonify({'status': 0,'messege': 'Invalid community data'})

        check_already_hide = HideCommunity.query.filter_by(created_id=community_id,category_id = category_id,user_id = active_user.id).first()
        if check_already_hide:
            db.session.delete(check_already_hide)
            db.session.commit()

            return jsonify({'status': 1,'messege': 'Successfully remove from hide'})

        else:
            add_hide_community_data = HideCommunity(created_id=community_id,category_id=category_id,user_id = active_user.id)
            db.session.add(add_hide_community_data)
            db.session.commit()

            return jsonify({'status': 1,'messege': 'Successfully community hide'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500


@community_create_v5.route('/hide_community_list', methods=['POST'])
@token_required
def hide_community_list(active_user):
    try:
        category_id = request.json.get('category_id')
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 30  # Number of items per page

        if not category_id:
            return jsonify({'status': 0,'messege': 'Please select category first'})

        get_category = Category.query.get(category_id)
        if not get_category:
            return jsonify({'status': 0,'messege': 'Invalid category'})

        hide_subq = db.session.query(HideCommunity.created_id).filter(HideCommunity.category_id == category_id,
                                                                      HideCommunity.user_id == active_user.id)

        # get_created_community = (
        #     CreatedCommunity.query
        #         .filter(
        #         CreatedCommunity.category_id == category_id,
        #         CreatedCommunity.id.in_(hide_subq)
        #     )
        #         .paginate(page=page, per_page=per_page,
        #                   error_out=False)
        # )

        get_created_community = (
            db.session.query(CreatedCommunity, User)  # Return both models
                .join(User, CreatedCommunity.user_id == User.id)  # Inner join
                .filter(
                CreatedCommunity.category_id == category_id,
                CreatedCommunity.id.in_(hide_subq)
            )
                .paginate(page=page, per_page=per_page, error_out=False)
        )

        has_next = get_created_community.has_next  # Check if there is a next page
        total_pages = get_created_community.pages  # Total number of pages

        # Pagination informatio
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        community_list = []

        if get_created_community.items:
            for i, user in get_created_community.items:

                community_dict = {'community_id': str(i.id),
                        'community_name': i.community_name,
                        'city': i.city if i.city is not None else '',
                        'state': i.state if i.state is not None else '',
                        'user_id': user.id,
                        'username': user.fullname,
                        'user_image': user.image_path,
                        'link': i.link if i.link is not None else ''
                        }

                community_list.append(community_dict)

        return jsonify({'status': 1,'messege': 'Success','community_list': community_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@community_create_v5.route('/new_community_list', methods=['POST'])
@token_required
def new_community_list(active_user):
    try:
        category_id = request.json.get('category_id')
        city = request.json.get('city')
        state = request.json.get('state')
        community_name = request.json.get('community_name')

        if not category_id:
            return jsonify({'status': 0,'messege': 'Please select category first'})

        get_category = Category.query.get(category_id)
        if not get_category:
            return jsonify({'status': 0,'messege': 'Invalid category'})

        hide_subq = db.session.query(HideCommunity.created_id).filter(HideCommunity.category_id == category_id,
                                                                      HideCommunity.user_id == active_user.id)
        saved_subq = db.session.query(SavedCommunity.created_id).filter(SavedCommunity.category_id == category_id,
                                                                        SavedCommunity.user_id == active_user.id)

        query = (
            CreatedCommunity.query
                .filter(
                CreatedCommunity.category_id == category_id,
                ~CreatedCommunity.id.in_(hide_subq),
                ~CreatedCommunity.id.in_(saved_subq)
            )

        )

        if community_name:
            query = query.filter(CreatedCommunity.community_name.ilike(f"{community_name}%"))

        if city:
            query = query.filter(CreatedCommunity.city.ilike(f"{city}%"))

        if state:
            query = query.filter(CreatedCommunity.state.ilike(f"{state}%"))

        get_created_community = query.first()

        if not get_created_community:
            return jsonify({'status': 1,'messege': 'No data found','community_data': {}})

        user_data = User.query.filter_by(id = get_created_community.user_id).first()
        if not user_data:
            return jsonify({'status': 0,'messege': 'Invalid data'})

        # get_members_data = SavedCommunity.query.filter(SavedCommunity.created_id == get_created_community.id,SavedCommunity.is_saved == True).limit(2).all()

        get_members_data = (
            db.session.query(SavedCommunity, User)
                .join(User, SavedCommunity.user_id == User.id)
                .filter(
                SavedCommunity.created_id == get_created_community.id,
                SavedCommunity.is_saved == True,
                SavedCommunity.user_id != active_user.id
            )
                .limit(6)
                .all()
        )

        members_list = []

        if len(get_members_data)>0:
            for saved_community, user in get_members_data:

                members_dict = {
                        'user_id': user.id,
                    'username': user.fullname,
                    'user_image': user.image_path

                }

                members_list.append(members_dict)

        community_dict = {'community_id': str(get_created_community.id),
                'community_name': get_created_community.community_name,
                'city': get_created_community.city if get_created_community.city is not None else '',
                'state': get_created_community.state if get_created_community.state is not None else '',
                'user_id': user_data.id,
                'username': user_data.fullname,
                'user_image': user_data.image_path,
                'link': get_created_community.link if get_created_community.link is not None else '',
                'members_list': members_list
                }

        return jsonify({'status': 1,'messege': 'Success','community_data': community_dict})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@community_create_v5.route('/community_list', methods=['POST'])
@token_required
def community_list(active_user):
    filter_text = request.json.get('filter_text')
    category_id = request.json.get('category_id')
    city = request.json.get('city')
    state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        category_id = 135

    print('city',city)
    print('state',state )
    print('category_id',category_id)
    print('page',page)

    check_visited = CategoryVisited.query.filter_by(user_id = active_user.id,category_id=category_id).first()

    if check_visited:
        check_visited.visited_counts += 1
        db.session.commit()
    else:
        add_visited = CategoryVisited(user_id = active_user.id,category_id=category_id,visited_counts=1)
        db.session.add(add_visited)
        db.session.commit()

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    # query = db.session.query(
    #     CreatedCommunity.id, CreatedCommunity.link, CreatedCommunity.city, CreatedCommunity.state,
    #     CreatedCommunity.community_name,
    #     func.count(SavedCommunity.id).label('saved_count')
    # ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
    #     join(User, SavedCommunity.user_id == User.id). \
    #     filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
    #            SavedCommunity.user_id.not_in(blocked_user_ids),
    #            SavedCommunity.user_id.not_in(blocked_by_user_ids),SavedCommunity.user_id != active_user.id). \
    #     group_by(CreatedCommunity.id)


    excluded_created_ids = db.session.query(SavedCommunity.created_id).filter(
        SavedCommunity.user_id == active_user.id,SavedCommunity.is_saved == True
    ).subquery()

    # Main query
    query = db.session.query(
        CreatedCommunity.id,
        CreatedCommunity.link,
        CreatedCommunity.city,
        CreatedCommunity.state,
        CreatedCommunity.community_name,
        func.count(SavedCommunity.id).label('saved_count')
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        SavedCommunity.category_id == category_id,
        User.is_block == False,
        SavedCommunity.user_id.not_in(blocked_user_ids),
        SavedCommunity.user_id.not_in(blocked_by_user_ids),
        SavedCommunity.user_id != active_user.id,
        ~SavedCommunity.created_id.in_(excluded_created_ids)  # Exclude the IDs from the subquery
    ). \
        group_by(CreatedCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedCommunity.community_name.desc(),
                               CreatedCommunity.id)
    elif filter_text == 2:
        query = query.order_by(CreatedCommunity.id.desc())
    elif filter_text == 3:
        query = query.order_by(CreatedCommunity.id.asc())
    elif filter_text == 4:
        query = query.order_by(func.count(SavedCommunity.id).desc(),
                               CreatedCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedCommunity.id).asc(),
                               CreatedCommunity.id)
    else:
        query = query.order_by(CreatedCommunity.community_name.asc(),
                               CreatedCommunity.id)

    if city:
        query = query.filter(CreatedCommunity.city == city)
    if state:
        query = query.filter(CreatedCommunity.state == state)

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items', created_data.items)
        for id,link, city, state, community_name, count in created_data.items:
            # print('created_data.items',created_data.items)
            # print('category_id',category_id)
            saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id, is_saved=True).first()

            # print('saved_already',saved_already)

            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedCommunity, User)
                                           .join(User, SavedCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id, SavedCommunity.category_id == category_id,
                                                   SavedCommunity.created_id == id,
                                                   ~SavedCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            user_id = ""
            username = ""
            user_image = ""

            if same_community_members_data:
                same_community_memebers_list = []
                each_saved_community, member_user = same_community_members_data
                print('each_saved_community',each_saved_community)
                print('member_user',member_user)

                user_id = str(member_user.id)
                username = member_user.fullname
                user_image = member_user.image_path
                print('user_id',user_id)

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            check_star = FavoriteSubCategory.query.filter_by(user_id = active_user.id,type='places',places_id = id).first()

            dict = {'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'user_id': user_id,
                    'username': username,
                    'user_image': user_image,
                    # 'same_community_memebrs': same_community_memebers_list,
                    'link': link if link is not None else '',
                    'is_star': bool(check_star)
                    }
            community_data.append(dict)

        has_next = created_data.has_next  # Check if there is a next page
        total_pages = created_data.pages  # Total number of pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'counts': str(total_community_count), 'messege': 'Sucess',
                        'pagination': pagination_info,
                        "category_id": category_id})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify(
            {'status': 1, 'data': [], 'counts': str(total_community_count), 'messege': 'You Not Save Any Words Yet',
             "category_id": category_id, 'pagination_info': pagination_info})


@community_create_v5.route('/search_in_community_list', methods=['POST'])
@token_required
def search_in_community_list(active_user):
    community_name = request.json.get('community_name')
    category_id = request.json.get('category_id')
    city = request.json.get('city')
    state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    # query = db.session.query(
    #     CreatedCommunity.id, CreatedCommunity.link, CreatedCommunity.city, CreatedCommunity.state,
    #     CreatedCommunity.community_name,
    #     func.count(SavedCommunity.id).label('saved_count')
    # ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
    #     join(User, SavedCommunity.user_id == User.id). \
    #     filter(User.deleted == False, SavedCommunity.category_id == category_id, User.is_block == False,
    #            SavedCommunity.user_id.not_in(blocked_user_ids),
    #            SavedCommunity.user_id.not_in(blocked_by_user_ids)). \
    #     group_by(CreatedCommunity.id)

    excluded_created_ids = db.session.query(SavedCommunity.created_id).filter(
        SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
    ).subquery()

    # Main query
    query = db.session.query(
        CreatedCommunity.id,
        CreatedCommunity.link,
        CreatedCommunity.city,
        CreatedCommunity.state,
        CreatedCommunity.community_name,
        func.count(SavedCommunity.id).label('saved_count')
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        SavedCommunity.category_id == category_id,
        User.is_block == False,
        SavedCommunity.user_id.not_in(blocked_user_ids),
        SavedCommunity.user_id.not_in(blocked_by_user_ids),
        SavedCommunity.user_id != active_user.id,
        # ~SavedCommunity.created_id.in_(excluded_created_ids)  # Exclude the IDs from the subquery
    ). \
        group_by(CreatedCommunity.id)

    query = query.order_by(func.count(SavedCommunity.id).desc(),
                           CreatedCommunity.id)

    if city:
        query = query.filter(CreatedCommunity.city.ilike(f"{city}%"))
    if state:
        query = query.filter(CreatedCommunity.state.ilike(f"{state}%"))
    if community_name:
        query = query.filter(CreatedCommunity.community_name.ilike(f"{community_name}%"))

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    # community_data = []
    #
    # if created_data.items:
    #     print('created_data.items', created_data.items)
    #     for id,link, city, state, community_name, count in created_data.items:
    #         print('created_data.items', created_data.items)
    #         print('category_id', category_id)
    #         saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
    #                                                        created_id=id).first()
    #
    #         print('saved_already', saved_already)
    #
    #         have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
    #
    #         same_community_members_data = (db.session.query(SavedCommunity, User)
    #                                        .join(User, SavedCommunity.user_id == User.id)
    #                                        .filter(User.is_block == False, User.deleted == False,
    #                                                User.id != active_user.id, SavedCommunity.category_id == category_id,
    #                                                SavedCommunity.created_id == id,
    #                                                ~SavedCommunity.user_id.in_(blocked_user_ids),
    #                                                ~SavedCommunity.user_id.in_(blocked_by_user_ids)).first())
    #         print('same_community_members_data', same_community_members_data)
    #
    #         user_id = ""
    #         username = ""
    #         user_image = ""
    #
    #         if same_community_members_data:
    #             each_saved_community, member_user = same_community_members_data
    #
    #             user_id = str(member_user.id)
    #             username = member_user.fullname
    #             user_image = member_user.image_path
    #
    #         if saved_already:
    #             is_saved = True
    #         else:
    #             is_saved = False
    #
    #         dict = {'community_id': str(id),
    #                 'community_name': community_name,
    #                 'members_count': str(count),
    #                 'is_saved': is_saved,
    #                 'city': city if city is not None else '',
    #                 'state': state if state is not None else '',
    #                 'is_recommendation': bool(have_recommendation),
    #                 'user_id': user_id,
    #                 'username': username,
    #                 'user_image': user_image,
    #                 # 'same_community_memebrs': same_community_memebers_list,
    #                 'link': link if link is not None else ''}
    #         community_data.append(dict)
    #
    #     has_next = created_data.has_next  # Check if there is a next page
    #     total_pages = created_data.pages  # Total number of pages
    #
    #     pagination_info = {
    #         "current_page": page,
    #         "has_next": has_next,
    #         "per_page": per_page,
    #         "total_pages": total_pages,
    #     }
    #
    #     return jsonify({'status': 1, 'data': community_data, 'counts': str(total_community_count), 'messege': 'Sucess',
    #                     'pagination': pagination_info,
    #                     "category_id": category_id})
    # else:
    #     pagination_info = {
    #         "current_page": 1,
    #         "has_next": False,
    #         "per_page": 10,
    #         "total_pages": 1,
    #     }
    #     return jsonify(
    #         {'status': 1, 'data': [], 'counts': str(total_community_count), 'messege': 'You Not Save Any Words Yet',
    #          "category_id": category_id,'pagination_info': pagination_info})

    community_data = []

    if created_data.items:
        print('created_data.items', created_data.items)
        for id, link, city, state, community_name, count in created_data.items:
            # print('created_data.items',created_data.items)
            # print('category_id',category_id)
            saved_already = SavedCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id, is_saved=True).first()

            # print('saved_already',saved_already)

            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedCommunity, User)
                                           .join(User, SavedCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id, SavedCommunity.category_id == category_id,
                                                   SavedCommunity.created_id == id,
                                                   ~SavedCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            user_id = ""
            username = ""
            user_image = ""

            if same_community_members_data:
                same_community_memebers_list = []
                each_saved_community, member_user = same_community_members_data
                print('each_saved_community', each_saved_community)
                print('member_user', member_user)

                user_id = str(member_user.id)
                username = member_user.fullname
                user_image = member_user.image_path
                print('user_id', user_id)

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
                                                             places_id=id).first()

            dict = {'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'user_id': user_id,
                    'username': username,
                    'user_image': user_image,
                    # 'same_community_memebrs': same_community_memebers_list,
                    'link': link if link is not None else '',
                    'is_star': bool(check_star)
                    }
            community_data.append(dict)

        has_next = created_data.has_next  # Check if there is a next page
        total_pages = created_data.pages  # Total number of pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': community_data, 'counts': str(total_community_count), 'messege': 'Sucess',
                        'pagination': pagination_info,
                        "category_id": category_id})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify(
            {'status': 1, 'data': [], 'counts': str(total_community_count), 'messege': 'You Not Save Any Words Yet',
             "category_id": category_id, 'pagination_info': pagination_info})

# @community_create_v5.route('/things_community_list', methods=['POST'])
# @token_required
# def things_community_list(active_user):
#     filter_text = request.json.get('filter_text')
#     city = request.json.get('city')
#     state = request.json.get('state')
#     category_id = request.json.get('category_id')
#     page = int(request.json.get('page', 1))
#     per_page = 10
#     if filter_text is None:
#         filter_text = 4
#     if category_id is None:
#         return jsonify({'status': 'Please provide category id'})
#         # category_id = 135
#
#     saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
#     saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()
#
#     total_community_count = saved_places_community_count + saved_things_community_count
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     query = db.session.query(
#         CreatedThingsCommunity.id,CreatedThingsCommunity.link,CreatedThingsCommunity.city,CreatedThingsCommunity.state,
#         CreatedThingsCommunity.community_name,
#         func.count(SavedThingsCommunity.id).label('saved_count')
#     ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
#         join(User, SavedThingsCommunity.user_id == User.id). \
#         filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
#                SavedThingsCommunity.user_id.not_in(blocked_user_ids),
#                SavedThingsCommunity.user_id.not_in(blocked_by_user_ids)). \
#         group_by(CreatedThingsCommunity.id)
#
#     if filter_text == 1:
#         query = query.order_by(CreatedThingsCommunity.community_name.desc(),
#                                CreatedThingsCommunity.id)
#
#     elif filter_text == 2:
#         query = query.order_by(CreatedThingsCommunity.id.desc())
#
#     elif filter_text == 3:
#         query = query.order_by(CreatedThingsCommunity.id.asc())
#
#     elif filter_text == 4:
#         query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
#                                CreatedThingsCommunity.id)
#     elif filter_text == 5:
#         query = query.order_by(func.count(SavedThingsCommunity.id).asc(),
#                                CreatedThingsCommunity.id)
#     else:
#         query = query.order_by(CreatedThingsCommunity.community_name.asc(),
#                                CreatedThingsCommunity.id)
#
#     if city:
#         query = query.filter(CreatedThingsCommunity.city == city)
#     if state:
#         query = query.filter(CreatedThingsCommunity.state == state)
#
#
#     created_data = query.paginate(page=page, per_page=per_page, error_out=False)
#
#     community_data = []
#
#     if created_data.items:
#         print('created_data.items',created_data.items)
#         for id,link, city, state, community_name, count in created_data.items:
#             print('created_data.items',created_data.items)
#             print('category_id',category_id)
#             saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
#                                                            created_id=id,is_saved = True).first()
#             have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
#
#             same_community_members_data = (db.session.query(SavedThingsCommunity, User)
#                                            .join(User, SavedThingsCommunity.user_id == User.id)
#                                            .filter(User.is_block == False, User.deleted == False,
#                                                    User.id != active_user.id, SavedThingsCommunity.category_id == category_id,
#                                                    SavedThingsCommunity.created_id == id,
#                                                    ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
#                                                    ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)).limit(1).all())
#             print('same_community_members_data', same_community_members_data)
#
#             same_community_memebers_list = []
#             for each_saved_community, member_user in same_community_members_data:
#                 member_basic_data = {
#                     'user_id': str(member_user.id),
#                     'username': member_user.fullname,
#                     'user_image': member_user.image_path}
#                 same_community_memebers_list.append(member_basic_data)
#
#             print('saved_already',saved_already)
#
#
#             if saved_already:
#                 is_saved = True
#             else:
#                 is_saved = False
#
#
#
#             dict = {'community_id': str(id),
#                     'community_name': community_name,
#                     'members_count': str(count),
#                     'is_saved': is_saved,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'is_recommendation': bool(have_recommendation),
#                     'same_community_memebrs': same_community_memebers_list,
#                     'link': link if link is not None else ''}
#             community_data.append(dict)
#
#         has_next = created_data.has_next
#         total_pages = created_data.pages
#
#         pagination_info = {
#             "current_page": page,
#             "has_next": has_next,
#             "per_page": per_page,
#             "total_pages": total_pages,
#         }
#
#         return jsonify({'status': 1,'counts': str(total_community_count), 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
#                         "category_id": category_id})
#     else:
#         return jsonify({'status': 1,'counts': str(total_community_count), 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id})

@community_create_v5.route('/liked_things_community_list', methods=['POST'])
@token_required
def liked_things_community_list(active_user):
    filter_text = request.json.get('filter_text')
    city = request.json.get('city')
    state = request.json.get('state')
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))
    per_page = 30
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        return jsonify({'status': 'Please provide category id'})
        # category_id = 135

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    # query = db.session.query(
    #     CreatedThingsCommunity.id,CreatedThingsCommunity.link,CreatedThingsCommunity.city,CreatedThingsCommunity.state,
    #     CreatedThingsCommunity.community_name,
    #     func.count(SavedThingsCommunity.id).label('saved_count')
    # ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
    #     join(User, SavedThingsCommunity.user_id == User.id). \
    #     filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
    #            SavedThingsCommunity.user_id.not_in(blocked_user_ids),
    #            SavedThingsCommunity.user_id.not_in(blocked_by_user_ids),SavedThingsCommunity.user_id != active_user.id). \
    #     group_by(CreatedThingsCommunity.id)

    included_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
        SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
    ).subquery()

    query = db.session.query(
        CreatedThingsCommunity.id, CreatedThingsCommunity.link, CreatedThingsCommunity.city,
        CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        func.count(SavedThingsCommunity.id).label('saved_count')
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
               SavedThingsCommunity.user_id.not_in(blocked_user_ids),
               SavedThingsCommunity.user_id.not_in(blocked_by_user_ids),
               # SavedThingsCommunity.user_id != active_user.id,
               SavedThingsCommunity.created_id.in_(included_created_ids)). \
        group_by(CreatedThingsCommunity.id)

    if filter_text == 1:
        query = query.order_by(CreatedThingsCommunity.community_name.desc(),
                               CreatedThingsCommunity.id)

    elif filter_text == 2:
        query = query.order_by(CreatedThingsCommunity.id.desc())

    elif filter_text == 3:
        query = query.order_by(CreatedThingsCommunity.id.asc())

    elif filter_text == 4:
        query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
                               CreatedThingsCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedThingsCommunity.id).asc(),
                               CreatedThingsCommunity.id)
    else:
        query = query.order_by(CreatedThingsCommunity.community_name.asc(),
                               CreatedThingsCommunity.id)

    if city:
        query = query.filter(CreatedThingsCommunity.city == city)
    if state:
        query = query.filter(CreatedThingsCommunity.state == state)


    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items',created_data.items)
        for id,link, city, state, community_name, count in created_data.items:
            print('created_data.items',created_data.items)
            print('category_id',category_id)
            saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id,is_saved = True).first()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedThingsCommunity, User)
                                           .join(User, SavedThingsCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id, SavedThingsCommunity.category_id == category_id,
                                                   SavedThingsCommunity.created_id == id,
                                                   ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            user_id = ""
            username = ""
            user_image = ""

            if same_community_members_data:
                each_saved_community, member_user = same_community_members_data

                user_id = str(member_user.id)
                username = member_user.fullname
                user_image = member_user.image_path

            print('saved_already',saved_already)


            if saved_already:
                is_saved = True
            else:
                is_saved = False



            dict = {'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'user_id':user_id,
                    'username': username,
                    'user_image': user_image,
                    # 'same_community_memebrs': same_community_memebers_list,
                    'link': link if link is not None else ''}
            community_data.append(dict)

        has_next = created_data.has_next
        total_pages = created_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1,'counts': str(total_community_count), 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
                        "category_id": category_id})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify({'status': 1,'counts': str(total_community_count), 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id, 'pagination': pagination_info})


@community_create_v5.route('/search_in_things_community_list', methods=['POST'])
@token_required
def search_in_things_community_list(active_user):
    community_name = request.json.get('community_name')
    city = request.json.get('city')
    state = request.json.get('state')
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))
    per_page = 30

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    excluded_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
        SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
    ).subquery()

    query = db.session.query(
        CreatedThingsCommunity.id, CreatedThingsCommunity.link, CreatedThingsCommunity.city,
        CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        func.count(SavedThingsCommunity.id).label('saved_count')
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
               SavedThingsCommunity.user_id.not_in(blocked_user_ids),
               SavedThingsCommunity.user_id.not_in(blocked_by_user_ids), SavedThingsCommunity.user_id != active_user.id).group_by(CreatedThingsCommunity.id)


    # ~SavedThingsCommunity.created_id.in_(excluded_created_ids)). \


    query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
                           CreatedThingsCommunity.id)

    if city:
        query = query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
    if state:
        query = query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))
    if community_name:
        query = query.filter(CreatedThingsCommunity.community_name.ilike(f"{community_name}%"))

    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items', created_data.items)
        for id, link, city, state, community_name, count in created_data.items:
            print('created_data.items', created_data.items)
            print('category_id', category_id)
            saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                                 created_id=id, is_saved=True).first()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedThingsCommunity, User)
                                           .join(User, SavedThingsCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id,
                                                   SavedThingsCommunity.category_id == category_id,
                                                   SavedThingsCommunity.created_id == id,
                                                   ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            user_id = ""
            username = ""
            user_image = ""

            if same_community_members_data:
                each_saved_community, member_user = same_community_members_data

                user_id = str(member_user.id)
                username = member_user.fullname
                user_image = member_user.image_path

            print('saved_already', saved_already)

            if saved_already:
                is_saved = True
            else:
                is_saved = False

            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
                                                             things_id=id).first()

            dict = {'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'user_id': user_id,
                    'username': username,
                    'user_image': user_image,
                    # 'same_community_memebrs': same_community_memebers_list,
                    'link': link if link is not None else '',
                    'is_star': bool(check_star)}
            community_data.append(dict)

        has_next = created_data.has_next
        total_pages = created_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'counts': str(total_community_count), 'data': community_data, 'messege': 'Sucess',
                        'pagination': pagination_info,
                        "category_id": category_id})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify(
            {'status': 1, 'counts': str(total_community_count), 'data': [], 'messege': 'You Not Save Any Words Yet',
             "category_id": category_id, 'pagination': pagination_info})

@community_create_v5.route('/hide_things_community_list', methods=['POST'])
@token_required
def hide_things_community_list(active_user):
    try:
        category_id = request.json.get('category_id')
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 30  # Number of items per page

        if not category_id:
            return jsonify({'status': 0,'messege': 'Please select category first'})

        get_category = ThingsCategory.query.get(category_id)
        if not get_category:
            return jsonify({'status': 0,'messege': 'Invalid category'})

        hide_subq = db.session.query(HideThingsCommunity.created_id).filter(HideThingsCommunity.category_id == category_id,
                                                                            HideThingsCommunity.user_id == active_user.id)

        # get_created_community = (
        #     CreatedCommunity.query
        #         .filter(
        #         CreatedCommunity.category_id == category_id,
        #         CreatedCommunity.id.in_(hide_subq)
        #     )
        #         .paginate(page=page, per_page=per_page,
        #                   error_out=False)
        # )

        get_created_things_community = (
            db.session.query(CreatedThingsCommunity, User)  # Return both models
                .join(User, CreatedThingsCommunity.user_id == User.id)  # Inner join
                .filter(
                CreatedThingsCommunity.category_id == category_id,
                CreatedThingsCommunity.id.in_(hide_subq)
            )
                .paginate(page=page, per_page=per_page, error_out=False)
        )

        has_next = get_created_things_community.has_next  # Check if there is a next page
        total_pages = get_created_things_community.pages  # Total number of pages

        # Pagination informatio
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        community_list = []

        if get_created_things_community.items:
            for i, user in get_created_things_community.items:

                community_dict = {'community_id': str(i.id),
                        'community_name': i.community_name,
                        'city': i.city if i.city is not None else '',
                        'state': i.state if i.state is not None else '',
                        'user_id': user.id,
                        'username': user.fullname,
                        'user_image': user.image_path,
                        'link': i.link if i.link is not None else ''
                        }

                community_list.append(community_dict)

        return jsonify({'status': 1,'messege': 'Success','community_list': community_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@community_create_v5.route('/hide_things_community', methods=['POST'])
@token_required
def hide_things_community(active_user):
    try:
        category_id = request.json.get('category_id')
        community_id = request.json.get('community_id')

        if not category_id:
            return jsonify({'status': 0, 'messege': 'Please select category first'})
        if not community_id:
            return jsonify({'status': 0, 'messege': 'Please select community first'})

        get_community = CreatedThingsCommunity.query.filter_by(category_id=category_id, id=community_id).first()
        if not get_community:
            return jsonify({'status': 0, 'messege': 'Invalid community data'})

        check_already_hide = HideThingsCommunity.query.filter_by(created_id=community_id, category_id=category_id,
                                                           user_id=active_user.id).first()
        if check_already_hide:
            db.session.delete(check_already_hide)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully remove from hide'})

        else:
            add_hide_community_data = HideThingsCommunity(created_id=community_id, category_id=category_id,
                                                    user_id=active_user.id)
            db.session.add(add_hide_community_data)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully community hide'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@community_create_v5.route('/new_things_community_list', methods=['POST'])
@token_required
def new_things_community_list(active_user):
    try:
        category_id = request.json.get('category_id')
        city = request.json.get('city')
        state = request.json.get('state')
        community_name = request.json.get('community_name')

        if not category_id:
            return jsonify({'status': 0,'messege': 'Please select category first'})

        get_things_category = ThingsCategory.query.get(category_id)
        if not get_things_category:
            return jsonify({'status': 0,'messege': 'Invalid category'})

        hide_subq = db.session.query(HideThingsCommunity.created_id).filter(HideThingsCommunity.category_id == category_id,HideThingsCommunity.user_id == active_user.id)
        saved_subq = db.session.query(SavedThingsCommunity.created_id).filter(SavedThingsCommunity.category_id == category_id,SavedThingsCommunity.user_id == active_user.id)

        query = (
            CreatedThingsCommunity.query
                .filter(
                CreatedThingsCommunity.category_id == category_id,
                ~CreatedThingsCommunity.id.in_(hide_subq),
                ~CreatedThingsCommunity.id.in_(saved_subq)
            )

        )

        if community_name:
            query = query.filter(CreatedThingsCommunity.community_name.ilike(f"{community_name}%"))

        if city:
            query = query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))

        if state:
            query = query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))

        get_created_things_community = query.first()

        if not get_created_things_community:
            return jsonify({'status': 1,'messege': 'No data found','community_data': {}})

        user_data = User.query.filter_by(id = get_created_things_community.user_id).first()
        if not user_data:
            return jsonify({'status': 0,'messege': 'Invalid data'})

        get_members_data = (
            db.session.query(SavedThingsCommunity, User)
                .join(User, SavedThingsCommunity.user_id == User.id)
                .filter(
                SavedThingsCommunity.created_id == get_created_things_community.id,
                SavedThingsCommunity.is_saved == True,
                SavedThingsCommunity.user_id != active_user.id
            )
                .limit(6)
                .all()
        )

        members_list = []

        if len(get_members_data) > 0:
            for saved_community, user in get_members_data:
                members_dict = {
                    'user_id': user.id,
                    'username': user.fullname,
                    'user_image': user.image_path

                }

                members_list.append(members_dict)

        community_dict = {'community_id': str(get_created_things_community.id),
                'community_name': get_created_things_community.community_name,
                'city': get_created_things_community.city if get_created_things_community.city is not None else '',
                'state': get_created_things_community.state if get_created_things_community.state is not None else '',
                'user_id': user_data.id,
                'username': user_data.fullname,
                'user_image': user_data.image_path,
                'link': get_created_things_community.link if get_created_things_community.link is not None else '',
                'members_list': members_list
                }

        return jsonify({'status': 1,'messege': 'Success','community_data': community_dict})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@community_create_v5.route('/things_community_list', methods=['POST'])
@token_required
def things_community_list(active_user):
    filter_text = request.json.get('filter_text')
    city = request.json.get('city')
    state = request.json.get('state')
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))
    per_page = 30
    if filter_text is None:
        filter_text = 4
    if category_id is None:
        return jsonify({'status': 'Please provide category id'})
        # category_id = 135

    check_visited = ThingsCategoryVisited.query.filter_by(user_id=active_user.id, category_id=category_id).first()

    if check_visited:
        check_visited.visited_counts += 1
        db.session.commit()
    else:
        add_visited = ThingsCategoryVisited(user_id=active_user.id, category_id=category_id, visited_counts=1)
        db.session.add(add_visited)
        db.session.commit()

    saved_places_community_count = SavedCommunity.query.filter_by(user_id=active_user.id).count()
    saved_things_community_count = SavedThingsCommunity.query.filter_by(user_id=active_user.id).count()

    total_community_count = saved_places_community_count + saved_things_community_count

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    excluded_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
        SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
    ).subquery()

    query = db.session.query(
        CreatedThingsCommunity.id, CreatedThingsCommunity.link, CreatedThingsCommunity.city,
        CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        func.count(SavedThingsCommunity.id).label('saved_count')
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(User.deleted == False, SavedThingsCommunity.category_id == category_id, User.is_block == False,
               SavedThingsCommunity.user_id.not_in(blocked_user_ids),
               SavedThingsCommunity.user_id.not_in(blocked_by_user_ids), SavedThingsCommunity.user_id != active_user.id,~SavedThingsCommunity.created_id.in_(excluded_created_ids)).group_by(CreatedThingsCommunity.id)

    # ~SavedThingsCommunity.created_id.in_(excluded_created_ids)). \

    if filter_text == 1:
        query = query.order_by(CreatedThingsCommunity.community_name.desc(),
                               CreatedThingsCommunity.id)

    elif filter_text == 2:
        query = query.order_by(CreatedThingsCommunity.id.desc())

    elif filter_text == 3:
        query = query.order_by(CreatedThingsCommunity.id.asc())

    elif filter_text == 4:
        query = query.order_by(func.count(SavedThingsCommunity.id).desc(),
                               CreatedThingsCommunity.id)
    elif filter_text == 5:
        query = query.order_by(func.count(SavedThingsCommunity.id).asc(),
                               CreatedThingsCommunity.id)
    else:
        query = query.order_by(CreatedThingsCommunity.community_name.asc(),
                               CreatedThingsCommunity.id)

    if city:
        query = query.filter(CreatedThingsCommunity.city == city)
    if state:
        query = query.filter(CreatedThingsCommunity.state == state)


    created_data = query.paginate(page=page, per_page=per_page, error_out=False)

    community_data = []

    if created_data.items:
        print('created_data.items',created_data.items)
        for id,link, city, state, community_name, count in created_data.items:
            print('created_data.items',created_data.items)
            print('category_id',category_id)
            saved_already = SavedThingsCommunity.query.filter_by(category_id=category_id, user_id=active_user.id,
                                                           created_id=id,is_saved = True).first()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()

            same_community_members_data = (db.session.query(SavedThingsCommunity, User)
                                           .join(User, SavedThingsCommunity.user_id == User.id)
                                           .filter(User.is_block == False, User.deleted == False,
                                                   User.id != active_user.id, SavedThingsCommunity.category_id == category_id,
                                                   SavedThingsCommunity.created_id == id,
                                                   ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
                                                   ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)).first())
            print('same_community_members_data', same_community_members_data)

            user_id = ""
            username = ""
            user_image = ""

            if same_community_members_data:
                each_saved_community, member_user = same_community_members_data

                user_id = str(member_user.id)
                username = member_user.fullname
                user_image = member_user.image_path

            print('saved_already',saved_already)


            if saved_already:
                is_saved = True
            else:
                is_saved = False

            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
                                                             things_id=id).first()

            dict = {'community_id': str(id),
                    'community_name': community_name,
                    'members_count': str(count),
                    'is_saved': is_saved,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'is_recommendation': bool(have_recommendation),
                    'user_id':user_id,
                    'username': username,
                    'user_image': user_image,
                    # 'same_community_memebrs': same_community_memebers_list,
                    'link': link if link is not None else '',
                    'is_star': bool(check_star)}
            community_data.append(dict)

        has_next = created_data.has_next
        total_pages = created_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1,'counts': str(total_community_count), 'data': community_data, 'messege': 'Sucess', 'pagination': pagination_info,
                        "category_id": category_id})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify({'status': 1,'counts': str(total_community_count), 'data': [], 'messege': 'You Not Save Any Words Yet', "category_id": category_id, 'pagination': pagination_info})


# @community_create_v5.route('/community_list', methods=['POST'])
# @token_required
# def community_list(active_user):
#     filter_text = request.json.get('filter_text')
#     category_id = request.json.get('category_id')
#     page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#     per_page = 10  # Number of items per page
#
#     xy = CreatedCommunity.query.filter_by(category_id=category_id).all()
#
#     # x = CreatedCommunity.query.filter_by(category_id=category_id).all()
#     # z = UnsavedCommunity.query.filter_by(category_id = category_id, user_id = active_user.id).all()
#     # unsaved_community = []
#
#     # for j in z:
#     # find_unsaved = CreatedCommunity.query.filter_by(id = j.community_id).all()
#     # if find_unsaved:
#     # unsaved_community.extend(find_unsaved)
#     # common_ids = set([obj.id for obj in x]).intersection(set([obj.community_id for obj in z]))
#     # xy = [obj for obj in x if obj.id not in common_ids]
#
#     community_data = []
#     # for i in xy:
#     for i in xy:
#         saved_already = SavedCommunity.query.filter_by(category_id=i.category_id, user_id=active_user.id,
#                                                        created_id=i.id).first()
#
#         y = SavedCommunity.query.filter(SavedCommunity.category_id == category_id, SavedCommunity.created_id == i.id,
#                                         SavedCommunity.is_saved == True).count()
#         if saved_already:
#             is_saved = True
#         else:
#             is_saved = False
#
#         dict = {'community_id': str(i.id),
#                 'community_name': i.community_name,
#                 'members_count': str(y),
#                 'is_saved': is_saved}
#         community_data.append(dict)
#
#     if filter_text == 1:
#         sort_key = lambda d: d['community_name']
#         reverse = True
#     elif filter_text == 2:
#         sort_key = lambda d: d['community_id']
#         reverse = True
#     elif filter_text == 3:
#         sort_key = lambda d: d['community_id']
#         reverse = False
#     elif filter_text == 4:
#         sort_key = lambda d: d['members_count']
#         reverse = True
#     elif filter_text == 5:
#         sort_key = lambda d: d['members_count']
#         reverse = False
#     else:
#         sort_key = lambda d: d['community_name']
#         reverse = False
#     if len(community_data) > 0:
#
#         list_data = sorted(community_data, key=sort_key, reverse=reverse)
#         # Calculate the start and end indices for the current page
#         start_index = (page - 1) * per_page
#         end_index = start_index + per_page
#
#         # Slice the list to get the records for the current page
#         current_page_records = list_data[start_index:end_index]
#
#         # Calculate total pages and whether there is a next page
#         total_items = len(list_data)
#         total_pages = (total_items + per_page - 1) // per_page
#         has_next = page < total_pages
#
#         # Pagination information
#         pagination_info = {
#             "current_page": page,
#             "has_next": has_next,
#             "per_page": per_page,
#             "total_pages": total_pages,
#         }
#
#         return jsonify({'status': 1, 'data': current_page_records, 'messege': 'Sucess', 'pagination': pagination_info})
#     else:
#         return jsonify({'status': 1, 'data': [], 'messege': 'You Not Save Any Words Yet'})


@community_create_v5.route('/community_post', methods=['GET', 'POST'])
@token_required
def community_post(active_user):
    filter_number = request.args.get('filter_number')

    if request.method == 'POST':
        community_id_p = request.json.get('community_id')

        text = request.json.get('text')
        censored = profanity.contains_profanity(text)

        if censored == True:
            return jsonify({'status': 0, 'messege': 'Post Contains Abusive Words'})
        else:

            chats = CommunityPost(text=text, community_id=community_id_p, user_id=active_user.id,
                                  created_time=datetime.utcnow())
            community_insert_data(chats)

            return jsonify({'status': 1, 'community_chat': chats.as_dict(), 'messegs': 'Sucessfully Added Your Post'})

    ls = []
    create_id = []
    community_id = request.args.get('community_id')
    print('communityyyyyyyyyyyyyyyy', community_id)

    community_members = CreatedCommunity.query.filter_by(id=community_id).count()
    comm_visited = CreatedCommunity.query.filter_by(id=community_id).first()
    save_visited = SavedCommunity.query.filter_by(created_id=community_id).first()
    dict1 = {'community_id': comm_visited.id, 'community_name': comm_visited.community_name,
             }
    if comm_visited:
        if comm_visited.visited:
            exits = comm_visited.visited
            comm_visited.visited = exits + 1
            db.session.commit()
            save_visited.visited = comm_visited.visited
            db.session.commit()

        else:
            comm_visited.visited = 1
            db.session.commit()
            save_visited.visited = 1
            db.session.commit()

    list = CommunityPost.query.filter_by(community_id=community_id).all()

    if list:
        for i in list:
            tag_friends = TagFriends.query.filter_by(community_post_id=i.id, user_id=active_user.id).first()
            user_data = get_user_data(i.user_id)
            now = i.created_time
            date = datetime.now()
            delta = date - now

            len_like = len(i.like_id)
            len_thumsup = len(i.thusup_id)
            len_thumsdown = len(i.thusdown_id)
            len_comment = len(i.comment_id)
            listing = []
            xy = PostLike.query.filter_by(user_id=active_user.id, post_id=i.id).first()
            xz = PostThumsup.query.filter_by(user_id=active_user.id, post_id=i.id).first()
            yz = PostThumpdown.query.filter_by(user_id=active_user.id, post_id=i.id).first()

            if tag_friends:
                split_data = tag_friends.users.split(',')
                for j in split_data:
                    x = User.query.filter_by(id=j).first()
                    listing.append(x.image_path + x.image_name)
            if len(listing) != 0:
                tag_list = listing[:4]
            else:
                tag_list = [{
                    "id": 3,
                    "is_tagged": False,
                    "user_image": "../static/userResoueces/user_photos/2d06386a8d50eecaccaa.jpg",
                    "username": "Johnny Depp"
                }, ]
            dict = {
                'post_id': i.id,
                'is_like': bool(xy),
                'is_thumsup': bool(xz),
                'is_thumsdown': bool(yz),
                'user_name': user_data.fullname,
                'user_image': COMMON_URL + user_data.image_path[2:] + user_data.image_name,
                'description': i.text,
                'community_id': i.community_id,
                'user_id': str(i.user_id),
                'like_count': len_like,
                'thumsup_count': len_thumsup,
                'thumsdown_count': len_thumsdown,
                'comment_count': len_comment,
                'time_ago': timeago.format(delta),
                'tagged': tag_list,
                'chat': False

            }
            ls.append(dict)
        if filter_number == 1:
            sort_key = lambda d: d['thumsup_count']
            reverse = True
        elif filter_number == 2:
            sort_key = lambda d: d['id']
            reverse = True
        elif filter_number == 3:
            sort_key = lambda d: d['id']
            reverse = False
        else:
            sort_key = lambda d: d['like_count']
            reverse = True

        sorted_list = sorted(ls, key=sort_key, reverse=reverse)

        return jsonify(
            {'status': 1, 'community_name': dict1, 'community_members': str(community_members), 'list': sorted_list})
    else:
        return jsonify({'status': 1, 'community_name': dict1, 'community_members': str(community_members), 'list': [],
                        'messege': 'Not Anyone Shared Interest Yet'})


@community_create_v5.route('/like_post', methods=['POST'])
@token_required
def like_post(active_user):
    id = request.json.get('post_id')

    post_id = get_community_chat(id)

    like_exits = liked_chats(active_user.id, post_id.id)

    comm_info = CreatedCommunity.query.filter_by(id=post_id.community_id).first()
    cat_info = Category.query.filter_by(id=comm_info.category_id).first()

    if not like_exits:
        add_like(active_user.id, post_id.id)
        reciver_user = User.query.filter_by(id=post_id.user_id).first()
        if not active_user.id == post_id.user_id:
            if reciver_user.heart_your_comment == True:
                title = 'Heart'
                # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                msg = f'{active_user.fullname} Hearted your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=post_id.id,
                                                community_id=post_id.community_id, page='post')
                db.session.add(add_notification)
                db.session.commit()
                notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=reciver_user.device_type)
            else:
                title = 'Heart'
                msg = f'{active_user.fullname} Hearted your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=post_id.id,
                                                community_id=post_id.community_id, page='post')
                db.session.add(add_notification)
                db.session.commit()

        return jsonify({'status': 1, 'messege': 'Liked'})

    if like_exits:
        delete_like(active_user.id, post_id.id)

        return jsonify({'status': 1, 'messege': 'UnLiked'})


@community_create_v5.route('/thumsup_post', methods=['POST'])
@token_required
def thumsup_post(active_user):
    id = request.json.get('post_id')

    post_id = get_community_chat(id)

    comm_info = CreatedCommunity.query.filter_by(id=post_id.community_id).first()
    cat_info = Category.query.filter_by(id=comm_info.category_id).first()

    thumpsup_exits = thumpsup_chats(active_user.id, post_id.id)

    if not thumpsup_exits:
        thumsup(active_user.id, post_id.id)
        delete_thumsdown(active_user.id, post_id.id)

        reciver_user = User.query.filter_by(id=post_id.user_id).first()
        if not active_user.id == post_id.user_id:
            if reciver_user.like_your_comment == True:
                title = 'Like'
                # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                msg = f'{active_user.fullname} Liked your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=post_id.id,
                                                community_id=post_id.community_id, page='post')
                db.session.add(add_notification)
                db.session.commit()
                # if reciver_user.device_token:
                notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=reciver_user.device_type)
            else:
                title = 'Like'
                msg = f'{active_user.fullname} Liked your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=post_id.id,
                                                community_id=post_id.community_id, page='post')
                db.session.add(add_notification)
                db.session.commit()

        return jsonify({'status': 1, 'messege': 'Thumsup'})

    if thumpsup_exits:
        delete_thumsup(active_user.id, post_id.id)
        reciver_user = User.query.filter_by(id=post_id.user_id).first()

        return jsonify({'status': 1, 'messege': 'Thumsup Deleted'})


@community_create_v5.route('/thumsdown_post', methods=['POST'])
@token_required
def thumsdown_post(active_user):
    id = request.json.get('post_id')

    post_id = get_community_chat(id)
    comm_info = CreatedCommunity.query.filter_by(id=post_id.community_id).first()
    cat_info = Category.query.filter_by(id=comm_info.category_id).first()

    thumpsdown_exits = thumpsdown_chats(active_user.id, post_id.id)

    if not thumpsdown_exits:
        thumsdown(active_user.id, post_id.id)
        delete_thumsup(active_user.id, post_id.id)
        reciver_user = User.query.filter_by(id=post_id.user_id).first()

        if not active_user.id == post_id.user_id:
            if reciver_user.dislike_your_comment == True:
                title = 'Dislike'
                # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                msg = f'{active_user.fullname} Disliked your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=post_id.id,
                                                community_id=post_id.community_id, page='post')
                db.session.add(add_notification)
                db.session.commit()
                # if reciver_user.device_token:
                notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=reciver_user.device_type)
            else:
                title = 'Dislike'
                image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                msg = f'{active_user.fullname} Disliked your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=post_id.id,
                                                community_id=post_id.community_id, page='post')
                db.session.add(add_notification)
                db.session.commit()

        return jsonify({'status': 1, 'messege': 'Thumsdown'})

    if thumpsdown_exits:
        delete_thumsdown(active_user.id, post_id.id)

        return jsonify({'status': 1, 'messege': 'Thumsdown Deleted'})


@community_create_v5.route('/post_comment', methods=['GET', 'POST'])
@token_required
def chat_comment(active_user):
    post_id = request.json.get('post_id')

    comment = request.json.get('comment')
    censored = profanity.contains_profanity(comment)
    if censored == True:
        return jsonify({'status': 0, 'messege': 'Comment Contains Abusive Words'})
    else:
        comments = PostComment(comment=comment, post_id=post_id, user_id=active_user.id, created_time=datetime.utcnow())
        community_insert_data(comments)

        x = CommunityPost.query.filter_by(id=post_id).first()
        comm_info = CreatedCommunity.query.filter_by(id=x.community_id).first()
        cat_info = Category.query.filter_by(id=comm_info.category_id).first()
        y = ChatMute.query.filter_by(post_id=post_id).all()
        xy = ChatMute.query.filter_by(post_id=post_id, user_id=x.user_id).first()
        z = PostComment.query.filter_by(post_id=post_id).all()
        user_info = User.query.filter_by(id=x.user_id).first()
        if not active_user.id == x.user_id:
            xz = ChatMute.query.filter_by(post_id=post_id, user_id=x.user_id).first()
            if not xz:
                title = 'Comment'
                # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                msg = f'{active_user.fullname} Commented on your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=user_info.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=x.id,
                                                community_id=x.community_id, page='comment')
                db.session.add(add_notification)
                db.session.commit()
                # if reciver_user.device_token:
                notification = push_notification(device_token=user_info.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=user_info.device_type)
            else:
                title = 'Comment'
                # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                msg = f'{active_user.fullname} Commented on your {comm_info.community_name} community post within the {cat_info.category_name} category'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=user_info.id,
                                                is_read=False, created_time=datetime.utcnow(), post_id=x.id,
                                                community_id=x.community_id, page='comment')
                db.session.add(add_notification)
                db.session.commit()

        return jsonify({'status': 1, 'post_comments': comments.as_dict(), 'messege': 'Comment Sucessfully Added'})


@community_create_v5.route('/view/post_comment', methods=['POST'])
@token_required
def view_chat_comment(active_user):
    posts_id = request.json.get('post_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    x = PostComment.query.filter_by(post_id=posts_id).all()

    comments_list = []
    if len(x) > 0:
        for i in x:
            y = User.query.filter_by(id=i.user_id, deleted=False).first()
            block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=y.id).first()
            if not block_check:
                if y:
                    input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                    output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    dict = {'comment_id': i.id,
                            'comment': i.comment,
                            'time_ago': output_date,
                            'user_id': str(y.id),
                            'user_name': y.fullname,
                            'user_image': COMMON_URL + y.image_path[2:] + y.image_name
                            }
                    comments_list.append(dict)
    comments_list.reverse()
    if len(comments_list) != 0:

        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        # Slice the list to get the records for the current page
        current_page_records = comments_list[start_index:end_index]

        # Calculate total pages and whether there is a next page
        total_items = len(comments_list)
        total_pages = (total_items + per_page - 1) // per_page
        has_next = page < total_pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify(
            {'status': 1, 'post_comments': current_page_records, 'messege': 'Sucess', 'pagination': pagination_info})
    else:

        return jsonify({'status': 1, 'post_comments': [], 'messege': 'This Post Dont Have Any Comment Yet'})

@community_create_v5.route('/post_list', methods=['POST'])
@token_required
def chat_list(active_user):
    if request.method == 'POST':
        filter_number = request.json.get('filter_number')
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 30  # Number of items per page

        ls = []
        create_id = []
        community_id = request.json.get('community_id')
        check_saved = SavedCommunity.query.filter_by(created_id=community_id, user_id=active_user.id,
                                                     is_saved=True).first()
        if check_saved:
            is_saved = True
        else:
            is_saved = False

        community_members = SavedCommunity.query.filter_by(created_id=community_id).count()
        comm_visited = CreatedCommunity.query.filter_by(id=community_id).first()
        save_visited = SavedCommunity.query.filter_by(created_id=community_id).first()
        dict1 = {'community_id': str(comm_visited.id), 'community_name': comm_visited.community_name,
                 }
        if comm_visited:
            if comm_visited.visited:
                exits = comm_visited.visited
                comm_visited.visited = exits + 1
                db.session.commit()
                save_visited.visited = comm_visited.visited
                db.session.commit()

            else:
                comm_visited.visited = 1
                db.session.commit()
                save_visited.visited = 1
                db.session.commit()

        list = CommunityPost.query.filter_by(community_id=community_id).all()

        if len(list) > 0:
            for i in list:
                tag_friends = TagFriends.query.filter_by(community_post_id=i.id, user_id=active_user.id).first()
                user_data = get_user_data(i.user_id)
                input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                like_counts = []
                for counts in i.like_id:
                    userss = User.query.filter_by(id=counts.user_id, deleted=False).first()
                    if userss:
                        block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=userss.id).first()
                        if not block_check:
                            like_counts.append(counts)

                thumsup_counts = []
                for thum_counts in i.thusup_id:
                    userss = User.query.filter_by(id=thum_counts.user_id, deleted=False).first()
                    if userss:
                        block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=userss.id).first()
                        if not block_check:
                            thumsup_counts.append(thum_counts)

                thumsdown_counts = []
                for down_counts in i.thusdown_id:
                    userss = User.query.filter_by(id=down_counts.user_id, deleted=False).first()
                    if userss:
                        block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=userss.id).first()
                        if not block_check:
                            thumsdown_counts.append(down_counts)

                comments_counts = []
                for comm_counts in i.comment_id:
                    userss = User.query.filter_by(id=comm_counts.user_id, deleted=False).first()
                    if userss:
                        block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=userss.id).first()
                        if not block_check:
                            comments_counts.append(comm_counts)
                # len_like = len(i.like_id)
                # len_thumsup = len(i.thusup_id)
                # len_thumsdown = len(i.thusdown_id)
                # len_comment = len(i.comment_id)

                listing = []
                xy = PostLike.query.filter_by(user_id=active_user.id, post_id=i.id).first()
                xz = PostThumsup.query.filter_by(user_id=active_user.id, post_id=i.id).first()
                yz = PostThumpdown.query.filter_by(user_id=active_user.id, post_id=i.id).first()

                if tag_friends:
                    split_data = tag_friends.users.split(',')
                    for j in split_data:
                        x = User.query.filter_by(id=j).first()
                        listing.append(COMMON_URL + x.image_path[2:] + x.image_name)
                if len(listing) != 0:
                    tag_list = listing[:4]
                else:
                    tag_list = []
                    # for j in split_data:
                    #     x = User.query.filter_by(id = j).first()
                    #     listing.append(x.image_path+x.image_name)
                is_mute = ChatMute.query.filter_by(post_id=i.id, user_id=active_user.id).first()
                delete_check = User.query.filter_by(id=i.user_id, deleted=False).first()
                block_check = Block.query.filter_by(blocked_user=active_user.id, user_id=i.user_id).first()
                if delete_check:
                    if not block_check:
                        if i.user_id == active_user.id:
                            is_active_user_post = True
                        else:
                            is_active_user_post = False

                        dict = {

                            'post_id': i.id,
                            'is_like': bool(xy),
                            'is_thumsup': bool(xz),
                            'is_thumsdown': bool(yz),
                            'user_name': user_data.fullname,
                            'user_image': COMMON_URL + user_data.image_path[2:] + user_data.image_name,
                            'description': i.text,
                            'community_id': i.community_id,
                            # 'community_name': i.community_name,
                            'user_id': str(i.user_id),
                            'like_count': len(like_counts),
                            'thumsup_count': len(thumsup_counts),
                            'thumsdown_count': len(thumsdown_counts),
                            'comment_count': len(comments_counts),
                            'time_ago': output_date,
                            'tagged': tag_list,
                            "is_active_user_post": is_active_user_post,
                            'chat': bool(is_mute)

                        }
                        ls.append(dict)
            if filter_number == 1:
                sort_key = lambda d: d['thumsup_count']
                reverse = True
            elif filter_number == 2:
                sort_key = lambda d: d['post_id']
                reverse = True
            elif filter_number == 3:
                sort_key = lambda d: d['post_id']
                reverse = False
            else:
                sort_key = lambda d: d['like_count']
                reverse = True

            sorted_list = sorted(ls, key=sort_key, reverse=reverse)

            # Calculate the start and end indices for the current page
            start_index = (page - 1) * per_page
            end_index = start_index + per_page

            # Slice the list to get the records for the current page
            current_page_records = sorted_list[start_index:end_index]

            # Calculate total pages and whether there is a next page
            total_items = len(sorted_list)
            total_pages = (total_items + per_page - 1) // per_page
            has_next = page < total_pages

            # Pagination information
            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            return jsonify({'status': 1, 'community_name': dict1, 'community_members': str(community_members),
                            'user_post': current_page_records, 'is_saved': is_saved,
                            'messege': 'Sucess', 'pagination': pagination_info})
        else:
            return jsonify(
                {'status': 1, 'community_name': dict1, 'community_members': str(community_members), 'user_post': [],
                 'messege': 'Not Anyone Shared Interest Yet', 'is_saved': is_saved})


@community_create_v5.route('/delete_post', methods=['POST'])
@token_required
def delete_post(active_user):
    post_id = request.json.get('post_id')
    if not post_id:
        return jsonify({'status': 0, 'messege': 'Post required'})
    post_data = CommunityPost.query.filter_by(id=post_id, user_id=active_user.id).first()

    if post_data:

        db.session.delete(post_data)
        db.session.commit()

        tags_data = TagFriends.query.filter_by(community_post_id=post_id).all()
        if len(tags_data) > 0:
            for tag_data in tags_data:
                db.session.delete(tag_data)
            db.session.commit()
        chat_mute_data = ChatMute.query.filter_by(post_id=post_id).all()
        if len(chat_mute_data) > 0:
            for mute_data in chat_mute_data:
                db.session.delete(mute_data)
            db.session.commit()
        return jsonify({'status': 1, 'messege': 'Post deleted sucessfully'})
    else:
        return jsonify({'status': 0, 'messege': 'Invalid post'})