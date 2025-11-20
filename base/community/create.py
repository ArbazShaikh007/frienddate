from datetime import datetime
from better_profanity import profanity

from flask import request, jsonify, Blueprint
from base.database.db import db
from dotenv import load_dotenv
from base.user.models import token_required, TagFriends, User, ChatMute, Notification, FriendRequest, Block
from base.community.models import SavedCommunity, CommunityPost, PostLike, PostThumsup, PostComment, PostThumpdown, \
    CreatedCommunity
from base.community.queryset import community_insert_data, add_like, delete_like, get_community_chat, liked_chats, \
    thumpsup_chats, thumsup, delete_thumsup, delete_thumsdown, thumpsdown_chats, thumsdown, get_user_data
import timeago, pytz
from base.common.utiils import COMMON_URL
from base.push_notification.push_notification import push_notification
from base.admin.models import BlockedWords, Category


def convert_tz():
    return datetime.now(tz=pytz.timezone('Asia/Kolkata'))


# now = datetime.now(tz=pytz.timezone('Asia/Kolkata'))
# utcnow = datetime.now().astimezone().now()

community_create = Blueprint('community_create', __name__)


@community_create.route('/add_community', methods=['GET', 'POST'])
@token_required
def add_community(active_user):
    category_id = request.json.get('category_id')
    comm_name = request.json.get('community_name')
    community_name = comm_name[0].upper() + comm_name[1:]
    print('community_nameeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', community_name)
    cat_info = Category.query.filter_by(id=category_id).first()

    get_community = CreatedCommunity.query.filter_by(category_id=category_id).all()

    if request.method == 'POST':

        community_exits = CreatedCommunity.query.filter_by(category_id=category_id,
                                                           community_name=community_name).first()

        if community_exits:
            saved_community_exits = SavedCommunity.query.filter_by(category_id=category_id,
                                                                   community_name=community_name,
                                                                   user_id=active_user.id).first()
            if saved_community_exits:
                return jsonify({'status': 1, 'messege': 'This Community Already You Saved'})
            else:
                communit = SavedCommunity(created_id=community_exits.id, community_name=community_exits.community_name,
                                          category_id=community_exits.category_id,
                                          user_id=active_user.id, created_time=datetime.utcnow(), is_saved=True)
                community_insert_data(communit)

                friend_ls = []
                check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).all()
                for f1 in check:
                    u1 = User.query.filter_by(id=f1.by_id).first()
                    friend_ls.append(u1)

                checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).all()

                for f2 in checked:
                    u2 = User.query.filter_by(id=f2.to_id).first()
                    friend_ls.append(u2)

                check.extend(checked)

                for friend in friend_ls:
                    if friend.add_new_community == True:

                        title = 'Update Interest'
                        # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                        msg = f'{active_user.fullname} saved {community_name} to their {cat_info.category_name} category'
                        add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=friend.id,
                                                        is_read=False, created_time=datetime.utcnow(), post_id=None,
                                                        community_id=communit.created_id, page='community')
                        db.session.add(add_notification)
                        db.session.commit()
                        # if friend.device_token:
                        notification = push_notification(device_token=friend.device_token, title=title, msg=msg,
                                                         image_url=None, device_type=friend.device_type)
                    else:
                        title = 'Update Interest'
                        msg = f'{active_user.fullname} saved {community_name} to their {cat_info.category_name} category'
                        add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=friend.id,
                                                        is_read=False, created_time=datetime.utcnow(), post_id=None,
                                                        community_id=communit.created_id, page='community')
                        db.session.add(add_notification)
                        db.session.commit()

                return jsonify({'status': 1, 'data': communit.as_dict(), 'messege': 'Sucessfully Saved Community'})

        if not community_exits:
            blocked_words_ls = []

            # censored = profanity.contains_profanity(community_name)
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

                community = CreatedCommunity(community_name=community_name, category_id=category_id,
                                             user_id=active_user.id, created_time=datetime.utcnow())
                community_insert_data(community)

                communit = SavedCommunity(created_id=community.id, community_name=community.community_name,
                                          category_id=community.category_id,
                                          user_id=active_user.id, created_time=community.created_time, is_saved=True)
                community_insert_data(communit)

                friend_lss = []
                check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).all()
                for f1 in check:
                    u1 = User.query.filter_by(id=f1.by_id).first()
                    friend_lss.append(u1)

                checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).all()

                for f2 in checked:
                    u2 = User.query.filter_by(id=f2.to_id).first()
                    friend_lss.append(u2)

                check.extend(checked)

                for friend in friend_lss:

                    if friend.add_new_community == True:

                        title = 'Update Interest'
                        # image_url = f'{COMMON_URL}{active_user.image_path[2:]}{active_user.image_name}'
                        msg = f'{active_user.fullname} saved {community_name} to their {cat_info.category_name} category'
                        add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=friend.id,
                                                        is_read=False, created_time=datetime.utcnow(), post_id=None,
                                                        community_id=communit.created_id, page='community')
                        db.session.add(add_notification)
                        db.session.commit()
                        # if friend.device_token:
                        notification = push_notification(device_token=friend.device_token, title=title, msg=msg,
                                                         image_url=None, device_type=friend.device_type)
                    else:
                        title = 'Update Interest'
                        msg = f'{active_user.fullname} saved {community_name} to their {cat_info.category_name} category'
                        add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=friend.id,
                                                        is_read=False, created_time=datetime.utcnow(), post_id=None,
                                                        community_id=communit.created_id, page='community')
                        db.session.add(add_notification)
                        db.session.commit()

                return jsonify({'status': 1, 'messege': 'Successfully Created Community', 'data': community.as_dict()})

    community_list = []

    if not get_community:
        return jsonify({'status': 1, 'messege': 'This Category Dont Have Any Community Yet'})

    if get_community:
        for i in get_community:
            dict = {'community_id': i.id,
                    'community_name': i.community_name}
            community_list.append(dict)
        return jsonify({'status': 1, 'community_list': community_list})


@community_create.route('/save_community', methods=['POST'])
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
            return jsonify({'status': 0, 'messege': 'Already saved this community'})
        else:
            communit = SavedCommunity(created_id=created_community.id, community_name=created_community.community_name,
                                      category_id=created_community.category_id,
                                      user_id=active_user.id, created_time=datetime.utcnow(), is_saved=True)
            community_insert_data(communit)
            return jsonify({'status': 1, 'messege': 'Successfully saved this community'})
    else:
        return jsonify({'status': 0, 'messege': 'Invalid community you select'})


@community_create.route('/join_community', methods=['POST'])
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


@community_create.route('/my_community', methods=['GET', 'POST'])
@token_required
def my_community(active_user):
    filter_text = request.json.get('filter')
    searching = request.json.get('search')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    community_check_is_saved = active_user.save_community_id

    y = []
    for saved in community_check_is_saved:
        if saved.is_saved == True:
            y.append(saved)

    list2 = [i.as_dict() for i in y]

    for l in list2:
        k = SavedCommunity.query.filter_by(created_id=l['created_id'], category_id=l['category_id'],
                                           is_saved=True).count()
        l['members_count'] = str(k)

    if filter_text == 1:
        sort_key = lambda d: d['community_name']
        reverse = True
    elif filter_text == 2:
        sort_key = lambda d: d['visited']
        reverse = True
    elif filter_text == 3:
        sort_key = lambda d: d['visited']
        reverse = False
    elif filter_text == 4:
        sort_key = lambda d: d['members_count']
        reverse = True
    elif filter_text == 5:
        sort_key = lambda d: d['members_count']
        reverse = False
    else:
        sort_key = lambda d: d['community_name']
        reverse = False

    results = []
    if request.method == 'POST':

        if searching:
            for item in list2:
                if searching.lower() in item["community_name"].lower():
                    results.append(item)

        if len(list2) > 0:
            if searching:
                if len(results) > 0:
                    return jsonify({'status': 1, 'data': results})
                else:
                    return jsonify({'status': 1, 'data': [], 'messege': 'Not Found'})
            else:
                sortings_list = sorted(list2, key=sort_key, reverse=reverse)

                # Calculate the start and end indices for the current page
                start_index = (page - 1) * per_page
                end_index = start_index + per_page

                # Slice the list to get the records for the current page
                current_page_records = sortings_list[start_index:end_index]

                # Calculate total pages and whether there is a next page
                total_items = len(sortings_list)
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
                    {'status': 1, 'data': current_page_records, 'messege': 'Sucess', 'pagination': pagination_info})
        if not len(list2) > 0:
            return jsonify({'status': 1, 'data': list2, 'messege': "You haven't joined any communities yet."})


@community_create.route('/community_library', methods=['POST'])
@token_required
def community_library(active_user):
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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


@community_create.route('/community_list', methods=['POST'])
@token_required
def community_list(active_user):
    filter_text = request.json.get('filter_text')
    category_id = request.json.get('category_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    xy = CreatedCommunity.query.filter_by(category_id=category_id).all()

    # x = CreatedCommunity.query.filter_by(category_id=category_id).all()
    # z = UnsavedCommunity.query.filter_by(category_id = category_id, user_id = active_user.id).all()
    # unsaved_community = []

    # for j in z:
    # find_unsaved = CreatedCommunity.query.filter_by(id = j.community_id).all()
    # if find_unsaved:
    # unsaved_community.extend(find_unsaved)
    # common_ids = set([obj.id for obj in x]).intersection(set([obj.community_id for obj in z]))
    # xy = [obj for obj in x if obj.id not in common_ids]

    community_data = []
    # for i in xy:
    for i in xy:
        saved_already = SavedCommunity.query.filter_by(category_id=i.category_id, user_id=active_user.id,
                                                       created_id=i.id).first()

        y = SavedCommunity.query.filter(SavedCommunity.category_id == category_id, SavedCommunity.created_id == i.id,
                                        SavedCommunity.is_saved == True).count()
        if saved_already:
            is_saved = True
        else:
            is_saved = False

        dict = {'community_id': str(i.id),
                'community_name': i.community_name,
                'members_count': str(y),
                'is_saved': is_saved}
        community_data.append(dict)

    if filter_text == 1:
        sort_key = lambda d: d['community_name']
        reverse = True
    elif filter_text == 2:
        sort_key = lambda d: d['community_id']
        reverse = True
    elif filter_text == 3:
        sort_key = lambda d: d['community_id']
        reverse = False
    elif filter_text == 4:
        sort_key = lambda d: d['members_count']
        reverse = True
    elif filter_text == 5:
        sort_key = lambda d: d['members_count']
        reverse = False
    else:
        sort_key = lambda d: d['community_name']
        reverse = False
    if len(community_data) > 0:

        list_data = sorted(community_data, key=sort_key, reverse=reverse)
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        # Slice the list to get the records for the current page
        current_page_records = list_data[start_index:end_index]

        # Calculate total pages and whether there is a next page
        total_items = len(list_data)
        total_pages = (total_items + per_page - 1) // per_page
        has_next = page < total_pages

        # Pagination information
        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1, 'data': current_page_records, 'messege': 'Sucess', 'pagination': pagination_info})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You Not Save Any Words Yet'})


@community_create.route('/community_post', methods=['GET', 'POST'])
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


@community_create.route('/like_post', methods=['POST'])
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


@community_create.route('/thumsup_post', methods=['POST'])
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


@community_create.route('/thumsdown_post', methods=['POST'])
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


@community_create.route('/post_comment', methods=['GET', 'POST'])
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


@community_create.route('/view/post_comment', methods=['POST'])
@token_required
def view_chat_comment(active_user):
    posts_id = request.json.get('post_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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


@community_create.route('/post_list', methods=['POST'])
@token_required
def chat_list(active_user):
    if request.method == 'POST':
        filter_number = request.json.get('filter_number')
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 10  # Number of items per page

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
                            'user_post': current_page_records, 'messege': 'Post List', 'is_saved': is_saved,
                            'messege': 'Sucess', 'pagination': pagination_info})
        else:
            return jsonify(
                {'status': 1, 'community_name': dict1, 'community_members': str(community_members), 'user_post': [],
                 'messege': 'Not Anyone Shared Interest Yet', 'is_saved': is_saved})


@community_create.route('/delete_post', methods=['POST'])
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