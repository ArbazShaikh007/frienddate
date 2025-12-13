from flask import request, jsonify, Blueprint
from base.user.queryset import view_data
from base.user.models import ReportMeetup,HideMeetup,VisitGroupComments,GroupComments,GroupNotification,GroupPosts,GroupChatNotificationOnOff,UserPhotoComments,NewUserPostComments,MeetupRequest,Meetup,EventComments,IamGoing,Events,HideUser,FavoriteUser,ReportNewUserPosts,HideNewUserPosts,NewUserPosts,LikeNewUserPosts,NewGroup,JoinedNewGroup,ProfileReviewComments,FavoriteSubCategory,GroupChat,RecommendationComments,HideFeed,UserVideos,LikeUserVideos,ProfileReviewLike, LikeUserPhotos,UserPhotos, ProfileReviewRequest,token_required, FriendRequest, User, DateRequest, TagFriends, \
    ChatMute, Notification, Block, TblCountries, TblStates,Follow,Feed,FeedLike,FeedComments,FeedCommentLike,PlacesReviewLike,PlacesReviewCommentLike,PlacesReviewComments,ThingsReviewCommentLike,ThingsReviewComments,ThingsReviewLike,NewNotification,LikeRecommendation
from base.user.queryset import insert_data, delete_frnd_req
from base.admin.models import CommentsUserAnswer,LikeUserAnswer,Category, Faqs,ThingsCategory,CategoryQue,CategoryAns,QuestionsCategory,Buttons
from base import db
from base.community.models import SavedThingsCommunity,SavedCommunity,CreatedThingsCommunity, CreatedCommunity, CommunityPost,ThingsRecommendation,PlacesRecommendation,PlacesReview,ThingsReview
from base.admin.queryset import terms_condition
from base.push_notification.push_notification import push_notification
from base.community.queryset import get_community_chat
from datetime import datetime,date
import requests,secrets,os,boto3
from sqlalchemy import and_
from sqlalchemy.sql.expression import func,desc
from sqlalchemy import text
from werkzeug.utils import secure_filename
from moviepy.editor import VideoFileClip

import tempfile
from sqlalchemy import cast, Float,or_
from sqlalchemy import case
from dotenv import load_dotenv
from pathlib import Path
from dateutil.relativedelta import relativedelta

import qrcode
from werkzeug.datastructures import FileStorage
import io

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

user_view_v5 = Blueprint('user_view_v5', __name__)

REGION_NAME = os.getenv("REGION_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY)

def generate_qr_code_fun(user_id,fullname):
    # QR URL (replace id dynamically as needed)
    qr_url = f"http://52.15.172.172/v5/verify_qr?id={user_id}"

    # Generate QR image
    qr_img = qrcode.make(qr_url)

    # Prepare an in-memory file
    name = fullname if fullname is not None else 'N/A'
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{name}_{timestamp}.png"

    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    # Wrap as FileStorage so it matches upload_photos expectations
    qr_file = FileStorage(
        stream=buffer,
        filename=filename,
        content_type='image/png'
    )

    # Use your existing function (no changes)
    file_path, picture = upload_photos(qr_file)

    return file_path

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "tif",
        "webp",
        "svg",
        "psd",
        "raw",
        "crw",
        "cr2",
        "cr3",
        "nef",
        "arw",
        "orf",
        "raf",
        "dng",
        "pef",
        "srf",
        "sr2",
        "rw2",
    }

def upload_photos(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        extension = os.path.splitext(filename)[1]
        extension2 = os.path.splitext(filename)[1][1:].lower()
        content_type = f'image/{extension2}'
        x = secrets.token_hex(10)
        picture = x + extension
        file.seek(0)
        s3_client.upload_fileobj(file, S3_BUCKET, picture,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        file_path = f"https://{S3_BUCKET}.s3.amazonaws.com/{picture}"

        return file_path, picture

@user_view_v5.route('/share_group', methods=['POST'])
@token_required
def share_group(active_user):
    try:
        data = request.get_json() or {}

        community_id = data.get("community_id")
        community_type = data.get("type")

        if not community_id:
            return jsonify({"status": 0,"messege": "Please select group first"})
        if not community_type:
            return jsonify({"status": 0,"messege": "Please provide group type"})

        if community_type == "things":
            get_community_data = CreatedThingsCommunity.query.get(community_id)
            if not get_community_data:
                return jsonify({"status": 0, "messege": "Invalid group"})

            community_name = get_community_data.community_name

        elif community_type == "places":
            get_community_data = CreatedCommunity.query.get(community_id)
            if not get_community_data:
                return jsonify({"status": 0, "messege": "Invalid group"})

            community_name = get_community_data.community_name

        else:
            community_name = ""

            return jsonify({"status": 0,"messege": "Invalid group type"})

        text = f"{active_user.fullname} shared the {community_name}  group with you! Check it out!"

        add_feed_data = Feed(community_name=community_name,type="text",feed_type ="feed", community_type=community_type, community_id=community_id, text=text,
                             created_time=datetime.utcnow(), user_id=active_user.id)
        db.session.add(add_feed_data)
        db.session.commit()

        follower_ids = [
            f.by_id
            for f in Follow.query.filter(Follow.to_id == active_user.id).all()
        ]

        incoming_ids = [
            fr.by_id
            for fr in FriendRequest.query.filter_by(
                to_id=active_user.id, request_status=1
            ).all()
        ]

        outgoing_ids = [
            fr.to_id
            for fr in FriendRequest.query.filter_by(
                by_id=active_user.id, request_status=1
            ).all()
        ]

        unique_user_ids = list(set(follower_ids + incoming_ids + outgoing_ids))

        users = User.query.filter(
            User.id.in_(unique_user_ids),
            User.deleted == False
        ).all()

        if len(users)>0:
            for i in users:
                title = f"{active_user.fullname} shared the {community_name}  group with you"

                msg = f"{active_user.fullname} shared the {community_name}  group with you"

                if i.device_token:
                    notification = push_notification(device_token=i.device_token, title=title, msg=msg,
                                                     image_url=None, device_type=i.device_type)

                add_notification = GroupNotification(title=title, message=msg, by_id=active_user.id,
                                                     to_id=i.id,
                                                     is_read=False, created_time=datetime.utcnow(),
                                                     community_type=type, community_id=community_id,
                                                     page='share group post')
                db.session.add(add_notification)
                db.session.commit()

        return jsonify({
            "status": 1,
            "messege": "Group shared successfully"
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            'status': 0,
            'messege': 'Something went wrong'
        }), 500

@user_view_v5.route('/generate_all_qr_code', methods=['GET'])
def generate_all_qr_code():
    try:
        get_all_users = User.query.filter(User.qr_code== None).all()

        if len(get_all_users)>0:

            for i in get_all_users:

                # QR URL (replace id dynamically as needed)
                qr_url = f"http://52.15.172.172/v5/verify_qr?id={i.id}"

                # Generate QR image
                qr_img = qrcode.make(qr_url)

                # Prepare an in-memory file
                name = i.fullname if i.fullname is not None else 'N/A'
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{name}_{timestamp}.png"

                buffer = io.BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)

                # Wrap as FileStorage so it matches upload_photos expectations
                qr_file = FileStorage(
                    stream=buffer,
                    filename=filename,
                    content_type='image/png'
                )

                # Use your existing function (no changes)
                file_path, picture = upload_photos(qr_file)

                i.qr_code = file_path
                db.session.commit()

        return jsonify({
            "status": 1,
            "messege": "Qr code generated successfully",
            "qr_code": ''
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            'status': 0,
            'messege': 'Something went wrong'
        }), 500

@user_view_v5.route('/share_qr_code', methods=['GET'])
@token_required
def share_qr_code(active_user):
    try:

        return jsonify({
            "status": 1,
            "messege": "Successfully qr code shared",
            "qr_code": active_user.qr_code if active_user.qr_code is not None else ''
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            'status': 0,
            'messege': 'Something went wrong'
        }), 500

@user_view_v5.route('/generate_qr_code', methods=['GET'])
@token_required
def generate_qr_code(active_user):
    try:
        # QR URL (replace id dynamically as needed)
        qr_url = f"http://52.15.172.172/v5/verify_qr?id={active_user.id}"

        # Generate QR image
        qr_img = qrcode.make(qr_url)

        # Prepare an in-memory file
        name = active_user.fullname if active_user.fullname is not None else 'N/A'
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{name}_{timestamp}.png"

        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)

        # Wrap as FileStorage so it matches upload_photos expectations
        qr_file = FileStorage(
            stream=buffer,
            filename=filename,
            content_type='image/png'
        )

        # Use your existing function (no changes)
        file_path, picture = upload_photos(qr_file)

        active_user.qr_code = file_path
        db.session.commit()

        return jsonify({
            "status": 1,
            "messege": "Qr code generated successfully",
            "qr_code": file_path
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            'status': 0,
            'messege': 'Something went wrong'
        }), 500

@user_view_v5.route('/group_comment_list', methods=['POST'])
@token_required
def group_comment_list(active_user):
    try:
        data = request.get_json()

        page = int(data.get('page', 1))
        per_page = 30
        type = data.get('type')
        community_id = data.get('community_id')

        if not community_id:
            return jsonify({'status': 0,'messege': 'Please select word first'})
        if not type:
            return jsonify({'status': 0,'messege': 'Please give type'})

        if type == "places":

            get_community = CreatedCommunity.query.get(community_id)
            if not get_community:
                return jsonify({'status': 0,'messege': 'Invalid group'})

            get_comment_data = GroupComments.query.filter(GroupComments.places_created_id==community_id,GroupComments.type=="places").order_by(GroupComments.id.desc()).paginate(page=page,
                                                                                                  per_page=per_page,
                                                                                                  error_out=False)

            comment_list = [ i.as_dict(active_user.id) for i in get_comment_data.items ]

            check_visit = VisitGroupComments.query.filter(VisitGroupComments.places_created_id == community_id,
                                                          VisitGroupComments.user_id == active_user.id,
                                                          VisitGroupComments.type == 'places').order_by(
                VisitGroupComments.id.desc()).first()

            if check_visit:
                check_visit.visit_time = datetime.utcnow()
                db.session.commit()

            else:
                add_check_visit = VisitGroupComments(places_created_id = community_id,
                                                              user_id = active_user.id,
                                                              type = 'places',visit_time = datetime.utcnow())
                db.session.add(add_check_visit)
                db.session.commit()

            pagination_info = {
                "current_page": get_comment_data.page,
                "has_next": get_comment_data.has_next,
                "per_page": get_comment_data.per_page,
                "total_pages": get_comment_data.pages
            }

            return jsonify({'status': 1,'messege': 'Success','comment_list':comment_list,'pagination_info': pagination_info})

        elif type == "things":

            get_community = CreatedThingsCommunity.query.get(community_id)
            if not get_community:
                return jsonify({'status': 0, 'messege': 'Invalid group'})

            # ----------------------------------------------------------------------------

            get_comment_data = GroupComments.query.filter(GroupComments.things_created_id == community_id,
                                                          GroupComments.type == "things").order_by(
                GroupComments.id.desc()).paginate(page=page,
                                                  per_page=per_page,
                                                  error_out=False)

            comment_list = [i.as_dict(active_user.id) for i in get_comment_data.items]

            check_visit = VisitGroupComments.query.filter(VisitGroupComments.things_created_id == community_id,
                                                          VisitGroupComments.user_id == active_user.id,
                                                          VisitGroupComments.type == 'things').order_by(
                VisitGroupComments.id.desc()).first()

            if check_visit:
                check_visit.visit_time = datetime.utcnow()
                db.session.commit()

            else:
                add_check_visit = VisitGroupComments(things_created_id=community_id,
                                                     user_id=active_user.id,
                                                     type='things', visit_time=datetime.utcnow())
                db.session.add(add_check_visit)
                db.session.commit()

            pagination_info = {
                "current_page": get_comment_data.page,
                "has_next": get_comment_data.has_next,
                "per_page": get_comment_data.per_page,
                "total_pages": get_comment_data.pages
            }

            return jsonify(
                {'status': 1, 'messege': 'Success', 'comment_list': comment_list, 'pagination_info': pagination_info})

        else:
            return jsonify({'status': 0, 'messege': 'Invalid type'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/delete_group_comment', methods=['POST'])
@token_required
def delete_group_comment(active_user):
    try:
        data = request.get_json()

        comment_id = data.get('comment_id')

        if not comment_id:
            return jsonify({'status': 0,'messege': 'Please select comment first'})

        get_comment = GroupComments.query.filter_by(user_id = active_user.id,id=comment_id).first()
        if not get_comment:
            return jsonify({'status': 0,'messege': 'Invalid comment'})

        db.session.delete(get_comment)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully comment deleted'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/add_group_comment', methods=['POST'])
@token_required
def add_group_comment(active_user):
    try:
        data = request.get_json()

        comment = data.get('comment')
        type = data.get('type')
        community_id = data.get('community_id')

        if not comment:
            return jsonify({'status': 0,'messege': 'Please enter comment'})
        if not community_id:
            return jsonify({'status': 0,'messege': 'Please select word first'})
        if not type:
            return jsonify({'status': 0,'messege': 'Please give type'})

        if type == "places":

            get_community = CreatedCommunity.query.get(community_id)
            if not get_community:
                return jsonify({'status': 0,'messege': 'Invalid group'})

            add_new_data = GroupComments(comment=comment,created_time =datetime.utcnow(),user_id=active_user.id,places_created_id=community_id,type="places")
            db.session.add(add_new_data)
            db.session.commit()

            return jsonify({'status': 1,'messege': 'Successfully added group comment'})

        elif type == "things":

            get_community = CreatedThingsCommunity.query.get(community_id)
            if not get_community:
                return jsonify({'status': 0, 'messege': 'Invalid group'})

            add_new_data = GroupComments(comment=comment,created_time =datetime.utcnow(),user_id=active_user.id,things_created_id=community_id,type="things")
            db.session.add(add_new_data)
            db.session.commit()

            return jsonify({'status': 1,'messege': 'Successfully added group comment'})

        else:
            return jsonify({'status': 0, 'messege': 'Invalid type'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/post_notification_setting', methods=['POST'])
@token_required
def group_post_notification_setting(active_user):
    try:
        gender = request.json.get('gender')
        if not gender:
            return jsonify({'status': 0,'messege': 'Please provide gender'})

        if not gender in ["Male", "Female", "All"]:
            return jsonify({'status': 0,'messege': 'Invalid gender'})

        active_user.notify_gender = gender
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully saved','notify_gender': active_user.notify_gender})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/get_post_notification_setting', methods=['GET'])
@token_required
def get_post_notification_setting(active_user):
    try:
        return jsonify({'status': 1, 'messege': 'Success', 'notify_gender': active_user.notify_gender})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/group_post_notification_list', methods=['POST'])
@token_required
def group_post_notification_list(active_user):
    try:
        page = int(request.json.get('page', 1))
        per_page = 30

        unread_group_post_notification_data = GroupNotification.query.filter_by(to_id=active_user.id,is_read=False).all()

        if len(unread_group_post_notification_data)>0:
            for i in unread_group_post_notification_data:
                i.is_read = True
            db.session.commit()

        get_group_post_notification_data = GroupNotification.query.filter(GroupNotification.to_id==active_user.id).order_by(GroupNotification.id.desc()).paginate(page=page,
                                                                                                  per_page=per_page,
                                                                                                  error_out=False)

        group_post_notification_list = [ i.as_dict() for i in get_group_post_notification_data.items ]

        pagination_info = {
            "current_page": get_group_post_notification_data.page,
            "has_next": get_group_post_notification_data.has_next,
            "per_page": get_group_post_notification_data.per_page,
            "total_pages": get_group_post_notification_data.pages
        }

        return jsonify({'status': 1,'messege': 'Success','post_notification_list': group_post_notification_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/delete_group_post', methods=['POST'])
@token_required
def delete_group_post(active_user):
    try:
        post_id = request.json.get('id')

        if not post_id:
            return jsonify({'status': 0,'messege': 'Please select post first'})

        get_group_post_data = GroupPosts.query.filter_by(id=post_id,user_id=active_user.id).first()

        if not get_group_post_data:
            return jsonify({'status': 0,'messege': 'Invalid post'})

        db.session.delete(get_group_post_data)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully post deleted'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500


# live one

# @user_view_v5.route('/group_post_list', methods=['POST'])
# @token_required
# def group_post_list(active_user):
#     try:
#         community_id = request.json.get('community_id')
#         type = request.json.get('type')
#         page = int(request.json.get('page', 1))
#         per_page = 30
#
#         if not community_id:
#             return jsonify({'status': 0, 'messege': 'Please select word first'})
#         if not type:
#             return jsonify({'status': 0, 'messege': 'Community type not found'})
#
#         check_gender = [active_user.gender, 'All'] if active_user.gender is not None else ['All']
#
#         if active_user.notify_gender is not None and active_user.notify_gender != '' and active_user.notify_gender != 'All':
#
#             if type == 'things':
#                 print('things workingggggggggg')
#
#                 get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,
#                                                               GroupPosts.things_created_id == community_id,
#                                                               GroupPosts.gender == active_user.notify_gender).order_by(
#                     GroupPosts.id.desc()).paginate(page=page,
#                                                    per_page=per_page,
#                                                    error_out=False)
#             elif type == 'places':
#
#                 get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,
#                                                               GroupPosts.places_created_id == community_id,
#                                                               GroupPosts.gender == active_user.notify_gender).order_by(
#                     GroupPosts.id.desc()).paginate(page=page,
#                                                    per_page=per_page,
#                                                    error_out=False)
#
#             else:
#                 return jsonify({'status': 0, 'messege': 'Invalid community type'})
#
#         else:
#
#             if type == 'things':
#                 print('thingsss workingggggggggg 2222')
#
#                 get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,
#                                                               GroupPosts.things_created_id == community_id).order_by(
#                     GroupPosts.id.desc()).paginate(page=page,
#                                                    per_page=per_page,
#                                                    error_out=False)
#
#             elif type == 'places':
#
#                 get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,
#                                                               GroupPosts.places_created_id == community_id,
#                                                               GroupPosts.gender.in_(check_gender)).order_by(
#                     GroupPosts.id.desc()).paginate(page=page,
#                                                    per_page=per_page,
#                                                    error_out=False)
#
#             else:
#                 return jsonify({'status': 0, 'messege': 'Invalid community type'})
#
#         group_post_list = [i.as_dict(active_user.id) for i in get_group_post_data.items]
#
#         pagination_info = {
#             "current_page": get_group_post_data.page,
#             "has_next": get_group_post_data.has_next,
#             "per_page": get_group_post_data.per_page,
#             "total_pages": get_group_post_data.pages
#         }
#
#         return jsonify(
#             {'status': 1, 'messege': 'Success', 'group_post_list': group_post_list, 'pagination_info': pagination_info})
#
#
#     except Exception as e:
#         print('errorrrrrrrrrrrrrrrrr:', str(e))
#         return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/group_post_list', methods=['POST'])
@token_required
def group_post_list(active_user):
    try:
        community_id = request.json.get('community_id')
        type = request.json.get('type')
        page = int(request.json.get('page', 1))
        per_page = 30

        if not community_id:
            return jsonify({'status': 0,'messege': 'Please select word first'})
        if not type:
            return jsonify({'status': 0,'messege': 'Community type not found'})

        check_gender = [active_user.gender,'All'] if active_user.gender is not None else ['All']

        # if active_user.notify_gender is not None or active_user.notify_gender != '' or active_user.notify_gender != 'All':
        #
        #     if type == 'things':
        #
        #         get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,GroupPosts.things_created_id == community_id,GroupPosts.gender==active_user.notify_gender).order_by(GroupPosts.id.desc()).paginate(page=page,
        #                                                                                    per_page=per_page,
        #                                                                                    error_out=False)
        #     elif type == 'places':
        #
        #         get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,
        #                                                       GroupPosts.places_created_id == community_id,
        #                                                       GroupPosts.gender == active_user.notify_gender).order_by(
        #             GroupPosts.id.desc()).paginate(page=page,
        #                                            per_page=per_page,
        #                                            error_out=False)
        #
        #     else:
        #         return jsonify({'status': 0,'messege': 'Invalid community type'})

        # else:

        if type == 'things':

            get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,GroupPosts.things_created_id==community_id,
    GroupPosts.gender.in_(check_gender)).order_by(GroupPosts.id.desc()).paginate(page=page,
                                                                                                  per_page=per_page,
                                                                                                  error_out=False)

        elif type == 'places':
            # check_gender = active_user.gender if active_user.gender is not None else 'All'

            get_group_post_data = GroupPosts.query.filter(GroupPosts.type == type,
                                                              GroupPosts.places_created_id == community_id,
    GroupPosts.gender.in_(check_gender)).order_by(
                    GroupPosts.id.desc()).paginate(page=page,
                                                   per_page=per_page,
                                                   error_out=False)

        else:
            return jsonify({'status': 0,'messege': 'Invalid community type'})

        group_post_list = [i.as_dict(active_user.id) for i in get_group_post_data.items]

        pagination_info = {
            "current_page": get_group_post_data.page,
            "has_next": get_group_post_data.has_next,
            "per_page": get_group_post_data.per_page,
            "total_pages": get_group_post_data.pages
        }

        return jsonify({'status': 1,'messege': 'Success','group_post_list': group_post_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/create_group_post', methods=['POST'])
@token_required
def create_group_post(active_user):
    try:
        data = request.get_json()

        place = data.get('place')
        address = data.get('address')
        description = data.get('description')
        time = data.get('time')
        date = data.get('date')
        gender = data.get('gender')
        age_start = data.get('age_start')
        age_end = data.get('age_end')
        looking_for = data.get('looking_for')
        sexual_orientation = data.get('sexual_orientation')
        type = data.get('type')
        community_id = data.get('community_id')
        relationship_for = data.get('relationship_for')

        if not community_id:
            return jsonify({'status': 0,'messege': 'Please select word first'})
        if not type:
            return jsonify({'status': 0,'messege': 'Please give type'})

        validate_gender = ["Male", "Female", "All"]

        if gender:
            if not gender in validate_gender:
                return jsonify({'status':0,'message': 'Please select gender Male,Female or All'})

        if type == "places":

            get_community = CreatedCommunity.query.get(community_id)
            if not get_community:
                return jsonify({'status': 0,'messege': 'Invalid group'})

            add_new_data = GroupPosts(relationship_for=relationship_for,place=place,address=address,created_time =datetime.utcnow(),user_id=active_user.id,places_created_id=community_id,type="places",description=description,time=time,date=date,gender=gender,age_start=age_start,age_end=age_end,looking_for=looking_for,sexual_orientation=sexual_orientation)
            db.session.add(add_new_data)
            db.session.commit()

            # if active_user.gender is not None:

            remove_users = GroupChatNotificationOnOff.query.filter_by(type=type, places_created_id=community_id).all()

            remove_users_list = [i.user_id for i in remove_users]

            get_reciver_users = User.query.filter(User.id.notin_(remove_users_list)).all()

            # print('get_reciver_users',get_reciver_users)

            if len(get_reciver_users) > 0:
                for i in get_reciver_users:
                    # print('iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii',i)

                    is_notification_sent = False

                    if i.notify_gender in validate_gender:
                        if active_user.gender == i.notify_gender or i.notify_gender == 'All':
                            is_notification_sent = True

                    else:
                        is_notification_sent = True

                    print('is_notification_sent', is_notification_sent)

                    if is_notification_sent == True:
                        title = 'New frienddate group post'

                        msg = f'{active_user.fullname} from the {get_community.community_name} group wants to meet for a FriendDate.'

                        if i.device_token:
                            notification = push_notification(device_token=i.device_token, title=title, msg=msg,
                                                             image_url=None, device_type=i.device_type)
                        add_notification = GroupNotification(title=title, message=msg, by_id=active_user.id, to_id=i.id,
                                                             is_read=False, created_time=datetime.utcnow(),
                                                             community_type=type, community_id=community_id,
                                                             page='new group post')
                        db.session.add(add_notification)
                        db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully created group post'})

        elif type == "things":

            get_community = CreatedThingsCommunity.query.get(community_id)
            if not get_community:
                return jsonify({'status': 0, 'messege': 'Invalid group'})

            add_new_data = GroupPosts(relationship_for=relationship_for,place=place,address=address,created_time =datetime.utcnow(),user_id=active_user.id,things_created_id=community_id,type="things",description=description,time=time,date=date,gender=gender,age_start=age_start,age_end=age_end,looking_for=looking_for,sexual_orientation=sexual_orientation)
            db.session.add(add_new_data)
            db.session.commit()

            # if active_user.gender is not None:

            remove_users = GroupChatNotificationOnOff.query.filter_by(type=type,
                                                                          things_created_id=community_id).all()

            remove_users_list = [i.user_id for i in remove_users]

            get_reciver_users = User.query.filter(User.id.notin_(remove_users_list)).all()

            if len(get_reciver_users) > 0:
                for i in get_reciver_users:

                    is_notification_sent = False

                    if i.notify_gender in validate_gender:
                        if active_user.gender == i.notify_gender or i.notify_gender == 'All':
                            is_notification_sent = True

                    else:
                        is_notification_sent = True

                    if is_notification_sent == True:

                        title = 'New frienddate group post'

                        msg = f'{active_user.fullname} from {get_community.community_name} group wants to meet for a FriendDate'

                        if i.device_token:
                            notification = push_notification(device_token=i.device_token, title=title, msg=msg,
                                                                 image_url=None, device_type=i.device_type)

                        add_notification = GroupNotification(title=title, message=msg, by_id=active_user.id,
                                                                 to_id=i.id,
                                                                 is_read=False, created_time=datetime.utcnow(),
                                                                 community_type=type, community_id=community_id,
                                                                 page='new group post')
                        db.session.add(add_notification)
                        db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully created group post'})

        else:
            return jsonify({'status': 0, 'messege': 'Invalid type'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/get_user_new_bio', methods=['POST'])
@token_required
def get_user_new_bio(active_user):
    try:
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({'status': 0,'messege': 'Please select user first'})

        user_data = User.query.get(user_id)
        if not user_data:
            return jsonify({'status': 0,'message': 'Invalid user'})

        user_bio = user_data.user_bio if user_data.user_bio is not None else ''

        return jsonify({'status': 1,'messege': 'Success','user_bio': user_bio})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/get_notification_counts', methods=['GET'])
@token_required
def get_notification_counts(active_user):
    try:
        main_notification_counts = NewNotification.query.filter_by(to_id= active_user.id,is_read= False).count()
        meetup_notification_counts = MeetupRequest.query.filter_by(to_id=active_user.id, is_read=False).count()

        total_counts = main_notification_counts+meetup_notification_counts

        return jsonify({'status': 1,'messege': 'Success','notification_count': str(total_counts)})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/user_photos_comment_list', methods=['POST'])
@token_required
def user_photos_comment_list(active_user):
    try:
        photo_id = request.json.get('photo_id')
        page = int(request.json.get('page', 1))
        per_page = 30

        if not photo_id:
            return jsonify({'status': 0, 'messege': 'Please select photo first'})

        get_photo = UserPhotos.query.filter_by(id=photo_id).first()
        if not get_photo:
            return jsonify({'status': 0, 'messege': 'Invalid photo'})

        get_comment_data = UserPhotoComments.query.order_by(UserPhotoComments.id.desc()).paginate(page=page,per_page=per_page,error_out=False)

        comment_list = [i.as_dict() for i in get_comment_data.items]

        pagination_info = {
            "current_page": get_comment_data.page,
            "has_next": get_comment_data.has_next,
            "per_page": get_comment_data.per_page,
            "total_pages": get_comment_data.pages
        }

        return jsonify({'status': 1,'messege': 'Success','comment_list': comment_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/user_photo_comment', methods=['POST'])
@token_required
def user_photo_comment(active_user):
    try:
        photo_id = request.json.get('photo_id')
        comment = request.json.get('comment')

        if not comment:
            return jsonify({'status': 0, 'messege': 'Please provide comment'})
        if not photo_id:
            return jsonify({'status': 0, 'messege': 'Please select photo first'})

        get_photo = UserPhotos.query.filter_by(id=photo_id).first()
        if not get_photo:
            return jsonify({'status': 0, 'messege': 'Invalid photo'})

        new_photo_comment = UserPhotoComments(comment=comment,user_photo_id=photo_id,user_id = active_user.id,created_time=datetime.utcnow())
        db.session.add(new_photo_comment)
        db.session.commit()

        get_user = User.query.get(get_photo.user_id)
        if not get_user:
            return jsonify({'status': 0,'messege':'User not found'})

        if get_user.id != active_user.id:

            title = 'New comment on your photo'

            msg = f'{active_user.fullname} commented on your photo.'

            if get_user.device_token:
                notification = push_notification(device_token=get_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=get_user.device_type)

            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=get_user.id,
                                               is_read=False, created_time=datetime.utcnow(), page='new comment on photo')
            db.session.add(add_notification)
            db.session.commit()

        return jsonify({'status': 1,'messege': 'Comment added successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/new_post_comment_list', methods=['POST'])
@token_required
def new_post_comment_list(active_user):
    try:
        post_id = request.json.get('post_id')
        page = int(request.json.get('page', 1))
        per_page = 30

        if not post_id:
            return jsonify({'status': 0, 'messege': 'Please select post first'})

        get_post = NewUserPosts.query.filter_by(id=post_id).first()
        if not get_post:
            return jsonify({'status': 0, 'messege': 'Invalid post'})

        get_comment_data = NewUserPostComments.query.order_by(NewUserPostComments.id.desc()).paginate(page=page,per_page=per_page,error_out=False)

        comment_list = [i.as_dict() for i in get_comment_data.items]

        pagination_info = {
            "current_page": get_comment_data.page,
            "has_next": get_comment_data.has_next,
            "per_page": get_comment_data.per_page,
            "total_pages": get_comment_data.pages
        }

        return jsonify({'status': 1,'messege': 'Success','comment_list': comment_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/new_post_comment', methods=['POST'])
@token_required
def new_post_comment(active_user):
    try:
        post_id = request.json.get('post_id')
        comment = request.json.get('comment')

        if not comment:
            return jsonify({'status': 0, 'messege': 'Please provide comment'})
        if not post_id:
            return jsonify({'status': 0, 'messege': 'Please select post first'})

        get_post = NewUserPosts.query.filter_by(id=post_id).first()
        if not get_post:
            return jsonify({'status': 0, 'messege': 'Invalid post'})

        add_new_post_comment = NewUserPostComments(comment=comment,new_user_post_id=post_id,user_id = active_user.id,created_time=datetime.utcnow())
        db.session.add(add_new_post_comment)
        db.session.commit()

        get_user = User.query.get(get_post.user_id)
        if not get_user:
            return jsonify({'status': 0, 'messege': 'User not found'})

        if get_user.id != active_user.id:

            title = 'New comment on your post'

            msg = f'{active_user.fullname} added comment on your post.'

            if get_user.device_token:
                notification = push_notification(device_token=get_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=get_user.device_type)

            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=get_user.id,
                                               is_read=False, created_time=datetime.utcnow(),
                                               page='new comment on new post page')
            db.session.add(add_notification)
            db.session.commit()

        return jsonify({'status': 1,'messege': 'Comment added successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500


# live one

# @user_view_v5.route('/meetup_notification_list', methods=['POST'])
# @token_required
# def meetup_notification_list(active_user):
#     try:
#         page = int(request.json.get('page', 1))
#         tab = request.json.get('tab')
#         per_page = 30
#
#         print('tabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',tab)
#
#         if not tab:
#             return jsonify({'status': 0,'messege': 'Please select tab first'})
#
#         if not int(tab) in [1,2,3]:
#             return jsonify({'status': 0,'messege': 'Invalid tab'})
#
#         if int(tab) in [2,3]:
#
#             check_unread_request = MeetupRequest.query.filter_by(to_id=active_user.id, is_read=False).all()
#             if len(check_unread_request)>0:
#                 for i in check_unread_request:
#                     i.is_read = True
#                 db.session.commit()
#
#             if int(tab) == 2:
#
#                 check_request = MeetupRequest.query.filter_by(to_id=active_user.id,is_show=True).order_by(MeetupRequest.id.desc()).paginate(
#                             page=page,
#                             per_page=per_page,
#                             error_out=False
#                         )
#             else:
#                 check_request = MeetupRequest.query.filter_by(to_id=active_user.id,is_show=False).order_by(
#                     MeetupRequest.id.desc()).paginate(
#                     page=page,
#                     per_page=per_page,
#                     error_out=False
#                 )
#
#             request_list = []
#
#             if check_request.items:
#                 for i in check_request.items:
#                     meetup_data = i.meetup_request_data.as_dict_notification()
#
#                     meetup_data.update(i.as_dict())
#                     request_list.append(meetup_data)
#             pagination_info = {
#                 "current_page": check_request.page,
#                 "has_next": check_request.has_next,
#                 "per_page": check_request.per_page,
#                 "total_pages": check_request.pages
#             }
#
#             return jsonify({'status': 1,'messege': "Success","request_list":request_list,'pagination_info':pagination_info})
#
#         else:
#             unread_group_post_notification_data = GroupNotification.query.filter_by(to_id=active_user.id,
#                                                                                     is_read=False).all()
#
#             if len(unread_group_post_notification_data) > 0:
#                 for i in unread_group_post_notification_data:
#                     i.is_read = True
#                 db.session.commit()
#
#             get_group_post_notification_data = GroupNotification.query.filter(
#                 GroupNotification.to_id == active_user.id).order_by(GroupNotification.id.desc()).paginate(page=page,
#                                                                                                           per_page=per_page,
#                                                                                                           error_out=False)
#
#             group_post_notification_list = [i.as_dict() for i in get_group_post_notification_data.items]
#
#             pagination_info = {
#                 "current_page": get_group_post_notification_data.page,
#                 "has_next": get_group_post_notification_data.has_next,
#                 "per_page": get_group_post_notification_data.per_page,
#                 "total_pages": get_group_post_notification_data.pages
#             }
#
#             return jsonify({'status': 1,'messege': "Success","request_list":group_post_notification_list,'pagination_info':pagination_info})
#
#     except Exception as e:
#         print('errorrrrrrrrrrrrrrrrr:', str(e))
#         return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/meetup_notification_list', methods=['POST'])
@token_required
def meetup_notification_list(active_user):
    try:
        page = int(request.json.get('page', 1))
        tab = request.json.get('tab')
        per_page = 30

        print('tabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',tab)

        if not tab:
            return jsonify({'status': 0,'messege': 'Please select tab first'})

        if not int(tab) in [1,2,3]:
            return jsonify({'status': 0,'messege': 'Invalid tab'})

        tab_1_counts = GroupNotification.query.filter_by(to_id=active_user.id,is_read=False).count()
        tab_2_counts = MeetupRequest.query.filter_by(to_id=active_user.id, is_read=False,is_show=True).count()
        tab_3_counts = MeetupRequest.query.filter_by(to_id=active_user.id, is_read=False,is_show=False).count()

        if int(tab) in [2, 3]:

            check_unread_request = MeetupRequest.query.filter_by(to_id=active_user.id, is_read=False).all()
            if len(check_unread_request)>0:
                for i in check_unread_request:
                    i.is_read = True
                db.session.commit()

            if tab == 3:

                check_request = MeetupRequest.query.filter_by(to_id=active_user.id,is_show=True).order_by(MeetupRequest.id.desc()).paginate(
                                page=page,
                                per_page=per_page,
                                error_out=False
                            )
            else:
                check_request = MeetupRequest.query.filter_by(to_id=active_user.id,is_show=False).order_by(
                        MeetupRequest.id.desc()).paginate(
                        page=page,
                        per_page=per_page,
                        error_out=False
                    )

            request_list = []

            if check_request.items:
                for i in check_request.items:
                    meetup_data = i.meetup_request_data.as_dict_notification()

                    meetup_data.update(i.as_dict())
                    request_list.append(meetup_data)

            pagination_info = {
                    "current_page": check_request.page,
                    "has_next": check_request.has_next,
                    "per_page": check_request.per_page,
                    "total_pages": check_request.pages
                }

            return jsonify({'status': 1,'messege': "Success","tab_2_counts":tab_1_counts,"tab_3_counts": tab_2_counts,"tab_4_counts": tab_3_counts,"request_list":request_list,'pagination_info':pagination_info})

        else:
            unread_group_post_notification_data = GroupNotification.query.filter_by(to_id=active_user.id,
                                                                                        is_read=False).all()

            if len(unread_group_post_notification_data) > 0:
                for i in unread_group_post_notification_data:
                    i.is_read = True
                db.session.commit()

            get_group_post_notification_data = GroupNotification.query.filter(
                    GroupNotification.to_id == active_user.id).order_by(GroupNotification.id.desc()).paginate(page=page,
                                                                                                              per_page=per_page,
                                                                                                              error_out=False)

            group_post_notification_list = [i.as_dict() for i in get_group_post_notification_data.items]

            pagination_info = {
                    "current_page": get_group_post_notification_data.page,
                    "has_next": get_group_post_notification_data.has_next,
                    "per_page": get_group_post_notification_data.per_page,
                    "total_pages": get_group_post_notification_data.pages
                }

            return jsonify({'status': 1,'messege': "Success","tab_2_counts":tab_1_counts,"tab_3_counts": tab_2_counts,"tab_4_counts": tab_3_counts,"request_list":group_post_notification_list,'pagination_info':pagination_info})

        # else:
        #
        #     notification_data = NewNotification.query.filter(NewNotification.to_id == active_user.id).order_by(
        #             NewNotification.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
        #
        #     has_next = notification_data.has_next  # Check if there is a next page
        #     total_pages = notification_data.pages  # Total number of pages
        #
        #     # Pagination information
        #     pagination_info = {
        #         "current_page": page,
        #         "has_next": has_next,
        #         "per_page": per_page,
        #         "total_pages": total_pages,
        #     }
        #
        #     notification_list = []
        #
        #     notification_counts = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).all()
        #     if len(notification_counts) > 0:
        #         for j in notification_counts:
        #             j.is_read = True
        #             db.session.commit()
        #
        #     if notification_data.items:
        #         for i in notification_data.items:
        #             input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
        #             output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        #
        #             notification_data = {
        #                 'id': i.id,
        #                 'title': i.title,
        #                 'message': i.message,
        #                 'page': i.page,
        #                 'created_time': output_date,
        #                 'user_id': i.by_user_notification.id,
        #                 'username': i.by_user_notification.fullname,
        #                 'user_image': i.by_user_notification.image_path,
        #
        #                 #static feilds
        #
        #                 "address": "",
        #                 "any_date": "",
        #                 "any_time": "",
        #                 "city": "",
        #                 "description": "",
        #                 "end_time": "",
        #                 "meetup_date": "",
        #                 "place": "",
        #                 "start_time": "",
        #                 "state": ""
        #
        #             }
        #             notification_list.append(notification_data)
        #
        #         return jsonify({'status': 1, 'messege': 'Success',"tab_2_counts":tab_2_counts,"tab_3_counts": tab_3_counts,"tab_4_counts": tab_4_counts, 'request_list': notification_list,
        #                         'pagination_info': pagination_info})
        #
        #     else:
        #         pagination_info = {
        #             "current_page": 1,
        #             "has_next": False,
        #             "per_page": 10,
        #             "total_pages": 1,
        #         }
        #         return jsonify({'status': 1, 'messege': 'Success', 'request_list': notification_list,
        #                         'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/user_meetup_request', methods=['POST'])
@token_required
def user_meetup_request(active_user):
    try:
        data = request.get_json()

        user_id = data.get('user_id')
        place = data.get('place')
        city = data.get('city')
        state = data.get('state')
        address = data.get('address')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        meetup_date = data.get('meetup_date')
        description = data.get('description')

        if not user_id:
            return jsonify({'status': 0,'messege': 'Please select meetup post first'})
        if not place:
            return jsonify({'status': 0,'messege': 'Please provide place name'})
        if not address:
            return jsonify({'status': 0,'messege': 'Please provide meetup address'})
        if not start_time:
            return jsonify({'status': 0,'messege': 'Please provide meetup start time'})
        if not end_time:
            return jsonify({'status': 0,'messege': 'Please provide meetup end time'})
        if not meetup_date:
            return jsonify({'status': 0,'messege': 'Please provide meetup date'})
        if not description:
            return jsonify({'status': 0,'messege': 'Please provide event description'})

        if active_user.id == user_id:
            return jsonify({'status': 0,'messege': "You can not send yourself for meetup request"})

        user_data = User.query.get(user_id)
        if not user_data:
            return jsonify({'status': 0,'messege': 'Invalid user'})

        add_new_meetup = Meetup(is_show=False,city=city, state=state, meetup_date=meetup_date, user_id=active_user.id, place=place,
                                address=address, start_time=start_time, end_time=end_time, description=description,
                                created_time=datetime.utcnow())
        db.session.add(add_new_meetup)
        db.session.commit()

        title = 'New Meetup Request'
        msg = f'{active_user.fullname} wants to meet you for a FriendDate. Send a message!'

        add_meetup_request = MeetupRequest(is_show=False,message=msg,title=title,by_id=active_user.id,to_id = user_data.id,meetup_id=add_new_meetup.id,created_time=datetime.utcnow())
        db.session.add(add_meetup_request)
        db.session.commit()

        if user_data.device_token is not None and user_data.device_token != "":

            notification = push_notification(device_token=user_data.device_token, title=title, msg=msg,
                                             image_url=None, device_type=user_data.device_type)

        return jsonify({"status": 1,'messege': "Meet up request send successfully"})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/meetup_request', methods=['POST'])
@token_required
def meetup_request(active_user):
    try:
        meetup_id = request.json.get('meetup_id')
        if not meetup_id:
            return jsonify({'status': 0,'messege': 'Please select meetup post first'})

        get_meetup_data = Meetup.query.get(meetup_id)
        if not get_meetup_data:
            return jsonify({'status': 0,'messege': 'Invalid meetup post'})

        if active_user.id == get_meetup_data.user_id:
            return jsonify({'status': 0,'messege': "You can not send yourself for meetup request"})

        check_request = MeetupRequest.query.filter_by(by_id=active_user.id,to_id = get_meetup_data.user_id, meetup_id=meetup_id).first()
        if not check_request:

            title = 'New Meetup Request'
            msg = f'{active_user.fullname} wants to meet you for a FriendDate. Send a message!'

            add_meetup_request = MeetupRequest(is_show=True,message=msg,title=title,by_id=active_user.id,to_id = get_meetup_data.user_id,meetup_id=meetup_id,created_time=datetime.utcnow())
            db.session.add(add_meetup_request)
            db.session.commit()

            if get_meetup_data.meetup_data.device_token is not None and get_meetup_data.meetup_data.device_token != "":

                notification = push_notification(device_token=get_meetup_data.meetup_data.device_token, title=title, msg=msg,
                                             image_url=None, device_type=get_meetup_data.meetup_data.device_type)

            return jsonify({"status": 1,'messege': "Meet up requested successfully"})

        else:

            db.session.delete(check_request)
            db.session.commit()

            return jsonify({"status": 1, 'messege': "Meet up cancelled successfully"})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/meetup_list', methods=['POST'])
@token_required
def meetup_list(active_user):
    try:
        page = int(request.json.get('page', 1))
        search_text = request.json.get('search_text')

        gender = request.json.get('gender')
        city = request.json.get('city')
        state = request.json.get('state')

        # user_id = request.json.get('user_id')
        per_page = 30

        hidden_meetup_ids = db.session.query(HideMeetup.meetup_id).filter(
            HideMeetup.user_id == active_user.id
        )

        check_gender = [active_user.gender, 'All'] if active_user.gender is not None else ['All']

        query = Meetup.query.filter(
            Meetup.is_show == True,
            ~Meetup.id.in_(hidden_meetup_ids),
            Meetup.gender.in_(check_gender)
        )

        if search_text:
            query = Meetup.query.filter(
                or_(
                    Meetup.place.ilike(f"{search_text}%"),
                    Meetup.address.ilike(f"{search_text}%"),
            Meetup.gender.in_(check_gender)
                )
            )

        # if gender:
        #     query = query.filter(Meetup.gender == gender)

        if city:
            query = query.filter(Meetup.city.ilike(f"{city}%"))

        if state:
            query = query.filter(Meetup.state.ilike(f"{state}%"))

        query = query.order_by(Meetup.id.desc())

        get_meetup_data = query.paginate(page=page, per_page=per_page, error_out=False)

        meetup_list = [ i.as_dict(active_user.id) for i in get_meetup_data.items ]

        pagination_info = {
            "current_page": get_meetup_data.page,
            "has_next": get_meetup_data.has_next,
            "per_page": get_meetup_data.per_page,
            "total_pages": get_meetup_data.pages
        }

        return jsonify({'status': 1,'messege': 'Success','meetup_list': meetup_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/delete_meetup', methods=['POST'])
@token_required
def delete_meetup(active_user):
    try:
        meetup_id = request.json.get('meetup_id')
        if not meetup_id:
            return jsonify({'status': 0,'messege': 'Please select meetup data first'})

        get_meetup_data = Meetup.query.filter_by(user_id = active_user.id,id=meetup_id).first()
        if not get_meetup_data:
            return jsonify({'status': 0,'messege': 'Invalid meetup data'})

        check_all_request = MeetupRequest.query.filter_by(meetup_id=meetup_id).all()
        if len(check_all_request)>0:
            for i in check_all_request:
                db.session.delete(i)
            db.session.commit()

        db.session.delete(get_meetup_data)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Meetup data deleted successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/create_meetup', methods=['POST'])
@token_required
def create_meetup(active_user):
    try:
        data = request.form

        place = data.get('place')
        city = data.get('city')
        state = data.get('state')
        address = data.get('address')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        meetup_date = data.get('meetup_date')
        description = data.get('description')

        gender = data.get('gender')
        sexuality = data.get('sexuality')
        start_age = data.get('start_age')
        end_age = data.get('end_age')

        any_time = data.get('any_time')
        any_date = data.get('any_date')

        content = request.files.get('content')
        content_media_type = data.get('content_type')

        if not place:
            return jsonify({'status': 0,'messege': 'Please provide place name'})
        if not address:
            return jsonify({'status': 0,'messege': 'Please provide meetup address'})
        if not start_time:
            return jsonify({'status': 0,'messege': 'Please provide meetup start time'})
        if not end_time:
            return jsonify({'status': 0,'messege': 'Please provide meetup end time'})
        if not meetup_date:
            return jsonify({'status': 0,'messege': 'Please provide meetup date'})
        if not description:
            return jsonify({'status': 0,'messege': 'Please provide event description'})

        image_name = None
        image_url = None

        video_url = None
        thumbnail_path = None

        type = 'text'

        if content_media_type == 'image':

            if content and content.filename:
                type = 'image'
                image_name = secure_filename(content.filename)
                extension = os.path.splitext(image_name)[1]
                extension2 = os.path.splitext(image_name)[1][1:].lower()

                content_type = f'image/{extension2}'
                x = secrets.token_hex(10)

                image_name = x + extension

                s3_client.upload_fileobj(content, S3_BUCKET, image_name,
                                         ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
                image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

        elif content_media_type == 'video':

            if content and content.filename:
                type = 'video'
                video_name = secure_filename(content.filename)
                extension = os.path.splitext(video_name)[1]
                extension2 = os.path.splitext(video_name)[1][1:].lower()

                unique_name = secrets.token_hex(10)

                with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
                    content.save(tmp.name)
                    # Rewind the file pointer to the beginning of the video file
                    tmp.seek(0)

                    # Generate a thumbnail for the video
                    clip = VideoFileClip(tmp.name)
                    thumbnail_name = f"thumb_{unique_name}.jpg"
                    clip.save_frame(thumbnail_name, t=1)  # Save the frame at 1 second as the thumbnail

                    # Close the VideoFileClip object
                    clip.reader.close()
                    if clip.audio and clip.audio.reader:
                        clip.audio.reader.close_proc()

                    # Upload the thumbnail to S
                    with open(thumbnail_name, 'rb') as thumb:
                        s3_client.upload_fileobj(thumb, S3_BUCKET, thumbnail_name,
                                                 ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpeg'})
                    thumbnail_path = f"https://{S3_BUCKET}.s3.amazonaws.com/{thumbnail_name}"
                    print(f'Thumbnail URL: {thumbnail_path}')

                    # Clean up the temporary thumbnail file
                    os.remove(thumbnail_name)

                # Upload the original post (video or image)
                content.seek(0)  # Rewind the file pointer to the beginning

                content_type = f'video/{extension2}'
                x = secrets.token_hex(10)

                video_name = x + extension

                s3_client.upload_fileobj(content, S3_BUCKET, video_name,
                                         ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
                video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{video_name}"

                # Clean up the temporary video file after uploading
                try:
                    os.remove(tmp.name)
                    print('itssssssssssssssssss successsssssssssssssssssssss')
                except PermissionError as e:
                    print(f"Error removing temporary file: {e}")
                print('video_url', video_url)

        else:
            type = "text"

        add_new_meetup = Meetup(type=type,thumbnail_path= thumbnail_path,video_path = video_url, image_name=image_name, image_path=image_url,any_time=any_time,any_date=any_date,gender=gender,sexuality=sexuality,start_age=start_age,end_age=end_age,city=city,state=state,meetup_date=meetup_date,user_id = active_user.id,place=place,address=address,start_time=start_time,end_time=end_time,description=description,created_time=datetime.utcnow())
        db.session.add(add_new_meetup)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Meetup created successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'messege': 'Something went wrong'}, 500

@user_view_v5.route('/hide_meetup', methods=['POST'])
@token_required
def hide_meetup(active_user):
    try:
        data = request.get_json() or {}

        meetup_id = data.get("meetup_id")

        if not meetup_id:
            return jsonify({'status': 0,'messege': 'Please select post first'})

        get_meetup_data = Meetup.query.get(meetup_id)
        if not get_meetup_data:
            return jsonify({'status': 0,'messege': 'Invalid meetup post'})

        add_data = HideMeetup(created_time=datetime.utcnow(),meetup_id=get_meetup_data.id,user_id = active_user.id)
        db.session.add(add_data)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully hided meeetup post'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/report_meetup', methods=['POST'])
@token_required
def report_meetup(active_user):
    try:
        data = request.get_json() or {}

        meetup_id = data.get("meetup_id")

        if not meetup_id:
            return jsonify({'status': 0,'messege': 'Please select post first'})

        get_meetup_data = Meetup.query.get(meetup_id)
        if not get_meetup_data:
            return jsonify({'status': 0,'messege': 'Invalid meetup post'})

        check_data = ReportMeetup.query.filter_by(meetup_id=get_meetup_data.id,user_id = active_user.id).first()
        if check_data:
            return jsonify({"status": 0,"messege": "You cannot report again for same post"})

        add_data = ReportMeetup(created_time=datetime.utcnow(),meetup_id=get_meetup_data.id,user_id = active_user.id)
        db.session.add(add_data)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully reported meeetup post'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/explore_page', methods=['POST'])
@token_required
def explore_page(active_user):
    page = int(request.json.get('page', 1))
    search_text = request.json.get('search_text')
    city = request.json.get('city')
    state = request.json.get('state')
    per_page = 30

    # Subquery to count likes per post
    subquery_likes = (
        db.session.query(
            LikeNewUserPosts.image_id.label('image_id'),
            func.count(LikeNewUserPosts.id).label('like_count')
        )
        .group_by(LikeNewUserPosts.image_id)
        .subquery()
    )

    # Subquery for hidden posts for the active user
    subquery_hidden = (
        db.session.query(HideNewUserPosts.image_id)
        .filter(HideNewUserPosts.user_id == active_user.id)
        .subquery()
    )

    # Main query - exclude hidden posts
    posts_query = (
    db.session.query(NewUserPosts)
    .outerjoin(subquery_likes, NewUserPosts.id == subquery_likes.c.image_id)
    .filter(~NewUserPosts.id.in_(subquery_hidden),NewUserPosts.content_type == 'image')  # Exclude hidden posts
    .order_by(
        subquery_likes.c.like_count.is_(None),       # Sort NULLs last
        subquery_likes.c.like_count.desc()           # Then sort descending
    )
)

    if city:
        posts_query = posts_query.filter(NewUserPosts.city.ilike(f"{city}%"))

    if state:
        posts_query = posts_query.filter(NewUserPosts.state.ilike(f"{state}%"))

    if search_text:
        posts_query = posts_query.filter(NewUserPosts.title.ilike(f"{search_text}%"))


    # Paginate results
    get_posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)

    pagination_info = {
        "current_page": get_posts.page,
        "has_next": get_posts.has_next,
        "per_page": get_posts.per_page,
        "total_pages": get_posts.pages
    }

    # Format posts
    get_posts_list = [post.as_dict(active_user.id) for post in get_posts.items]

    return jsonify({
        'status': 1,
        'messege': 'Success',
        'post_list': get_posts_list,
        'pagination_info': pagination_info
    })

@user_view_v5.route('/filter_on_off', methods=['GET'])
@token_required
def filter_on_off(active_user):

    if active_user.is_filter == False:
        active_user.is_filter = True
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Filter applied successfully','is_filter' : active_user.is_filter})

    else:
        active_user.is_filter = False
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Filter removed successfully', 'is_filter': active_user.is_filter})

@user_view_v5.route('/get_user_new_page_filter_data', methods=['GET'])
@token_required
def get_user_new_page_filter_data(active_user):

    gender = active_user.saved_gender if active_user.saved_gender is not None else ''
    looking_for = 'Both'
    if active_user.saved_looking_for and active_user.saved_looking_for != '':
        looking_for = 'Both' if active_user.saved_looking_for == 'Here for friends and dating' else active_user.saved_looking_for

    start_age = active_user.start_age if active_user.start_age is not None else '0'
    end_age = active_user.end_age if active_user.end_age is not None else '40'

    return jsonify({'status': 1,'messege': 'Success','gender': gender,'looking_for': looking_for,'start_age': start_age,'end_age': end_age,'is_filter': active_user.is_filter})

@user_view_v5.route('/saved_new_user_page_filter', methods=['POST'])
@token_required
def saved_new_user_page_filter(active_user):
    try:
        gender = request.json.get('gender') #Male, Female,Trans
        looking_for = request.json.get('looking_for') # Friends, Dating, Both
        start_age = request.json.get('start_age')
        end_age = request.json.get('end_age')

        if not gender in ["Male","Female","Trans"]:
            return jsonify({'status': 0,'messege': 'Invalid gender'})
        if not looking_for in ["Friends","Dating","Both"]:
            return jsonify({'status': 0,'messege': 'Invalid looking for'})

        looking_for_check = looking_for

        if looking_for == 'Both':
            looking_for_check = 'Here for friends and dating'

        active_user.saved_looking_for = looking_for_check
        active_user.saved_gender = gender
        active_user.start_age = start_age
        active_user.end_age = end_age

        db.session.commit()

        return jsonify({'status': 1,'message': 'Filter saved successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/event_comment_list', methods=['POST'])
@token_required
def event_comment_list(active_user):
    try:
        event_id = request.json.get('event_id')
        page = int(request.json.get('page', 1))
        per_page = 30

        if not event_id:
            return jsonify({'status': 0, 'messege': 'Please select event first'})

        get_event = Events.query.filter_by(id=event_id).first()
        if not get_event:
            return jsonify({'status': 0, 'messege': 'Invalid event'})

        get_comment_data = EventComments.query.order_by(EventComments.id.desc()).paginate(page=page,per_page=per_page,error_out=False)

        comment_list = [i.as_dict() for i in get_comment_data.items]

        pagination_info = {
            "current_page": get_comment_data.page,
            "has_next": get_comment_data.has_next,
            "per_page": get_comment_data.per_page,
            "total_pages": get_comment_data.pages
        }

        return jsonify({'status': 1,'messege': 'Success','comment_list': comment_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/event_comment', methods=['POST'])
@token_required
def event_comment(active_user):
    try:
        event_id = request.json.get('event_id')
        comment = request.json.get('comment')

        if not comment:
            return jsonify({'status': 0, 'messege': 'Please provide comment'})
        if not event_id:
            return jsonify({'status': 0, 'messege': 'Please select event first'})

        get_event = Events.query.filter_by(id=event_id).first()
        if not get_event:
            return jsonify({'status': 0, 'messege': 'Invalid event'})

        add_comment = EventComments(comment=comment,event_id=event_id,user_id = active_user.id,created_time=datetime.utcnow())
        db.session.add(add_comment)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Comment added successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/event_going_list', methods=['POST'])
@token_required
def event_going_list(active_user):
    try:
        event_id = request.json.get('event_id')
        if not event_id:
            return jsonify({'status': 0, 'messege': 'Please select event first'})

        get_event = Events.query.filter_by(user_id=active_user.id, id=event_id).first()
        if not get_event:
            return jsonify({'status': 0, 'messege': 'Invalid event'})

        add_iam_going = IamGoing.query.filter_by(event_id=event_id).all()

        going_list = [ i.as_dict() for i in add_iam_going ]

        return jsonify({'status': 1,'message': 'Success','going_list': going_list})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/confirm_event_going', methods=['POST'])
@token_required
def confirm_event_going(active_user):
    try:
        event_id = request.json.get('event_id')
        if not event_id:
            return jsonify({'status': 0, 'messege': 'Please select event first'})

        get_event = Events.query.filter_by(id=event_id).first()
        if not get_event:
            return jsonify({'status': 0, 'messege': 'Invalid event'})

        add_iam_going = IamGoing(event_id=event_id,user_id = active_user.id,created_time=datetime.utcnow())
        db.session.add(add_iam_going)
        db.session.commit()

        reciver_user = User.query.get(get_event.user_id)

        if reciver_user.id != active_user.id:

            title = 'New People Confirmation for Event'
            # image_url = f'{active_user.image_path}'
            msg = f'{active_user.fullname} is going to your event.'
            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=reciver_user.id,
                                               is_read=False, created_time=datetime.utcnow(), page='like on answer')
            db.session.add(add_notification)
            db.session.commit()
            # if reciver_user.device_token:
            notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                             image_url=None, device_type=reciver_user.device_type)

        return jsonify({'status': 1,'message': 'You are confirmed'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/my_event_list', methods=['POST'])
@token_required
def my_event_list(active_user):
    try:
        page = int(request.json.get('page', 1))
        search_text = request.json.get('search_text')
        # user_id = request.json.get('user_id')
        per_page = 30

        if search_text:
            get_events_data = Events.query.filter(
                or_(
                    Events.name.ilike(f"{search_text}%"),
                    Events.address.ilike(f"{search_text}%"),Events.is_deleted == False,Events.user_id == active_user.id
                )
            ).order_by(Events.id.desc()).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

        else:

            get_events_data = Events.query.filter(Events.is_deleted == False,Events.user_id == active_user.id).order_by(Events.id.desc()).paginate(page=page,per_page=per_page,error_out=False)

        event_list = [ i.as_dict(active_user.id) for i in get_events_data.items ]

        pagination_info = {
            "current_page": get_events_data.page,
            "has_next": get_events_data.has_next,
            "per_page": get_events_data.per_page,
            "total_pages": get_events_data.pages
        }

        return jsonify({'status': 1,'message': 'Success','event_list': event_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/event_list', methods=['POST'])
@token_required
def event_list(active_user):
    try:
        page = int(request.json.get('page', 1))
        search_text = request.json.get('search_text')
        # user_id = request.json.get('user_id')
        per_page = 30

        # final_user_id = active_user.id
        #
        # if user_id:
        #     get_user = User.query.get(user_id)
        #     if not get_user:
        #         return jsonify({'status': 0,'messege': 'Invalid user'})
        #     final_user_id = user_id

        # get_events_data = Events.query.filter_by(user_id = final_user_id).order_by(Events.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

        if search_text:
            get_events_data = Events.query.filter(
                or_(
                    Events.name.ilike(f"{search_text}%"),
                    Events.address.ilike(f"{search_text}%"),Events.is_deleted == False
                )
            ).order_by(Events.id.desc()).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

        else:

            get_events_data = Events.query.filter(Events.is_deleted == False).order_by(Events.id.desc()).paginate(page=page,per_page=per_page,error_out=False)

        event_list = [ i.as_dict(active_user.id) for i in get_events_data.items ]

        pagination_info = {
            "current_page": get_events_data.page,
            "has_next": get_events_data.has_next,
            "per_page": get_events_data.per_page,
            "total_pages": get_events_data.pages
        }

        return jsonify({'status': 1,'message': 'Success','event_list': event_list,'pagination_info': pagination_info})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/delete_event', methods=['POST'])
@token_required
def delete_event(active_user):
    try:
        event_id = request.json.get('event_id')
        if not event_id:
            return jsonify({'status': 0,'messege': 'Please select event first'})

        get_event = Events.query.filter_by(user_id = active_user.id,id=event_id).first()
        if not get_event:
            return jsonify({'status': 0,'messege': 'Invalid event'})

        if get_event.image_name:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=get_event.image_name)

        db.session.delete(get_event)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Event deleted successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/create_event', methods=['POST'])
@token_required
def create_event(active_user):
    try:
        data = request.form

        name = data.get('name')
        city = data.get('city')
        state = data.get('state')
        address = data.get('address')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        event_date = data.get('event_date')
        description = data.get('description')
        image = request.files.get('image')

        if not name:
            return jsonify({'status': 0,'messege': 'Please provide event name'})
        if not address:
            return jsonify({'status': 0,'messege': 'Please provide event address'})
        if not start_time:
            return jsonify({'status': 0,'messege': 'Please provide event start time'})
        if not end_time:
            return jsonify({'status': 0,'messege': 'Please provide event end time'})
        if not event_date:
            return jsonify({'status': 0,'messege': 'Please provide event date'})
        if not description:
            return jsonify({'status': 0,'messege': 'Please provide event description'})
        if not image:
            return jsonify({'status': 0,'messege': 'Please provide event image'})

        image_name = None
        image_path = None

        if image:
            file_path, picture = upload_photos(image)
            image_name = picture
            image_path = file_path

        add_event = Events(city=city,state=state,event_date=event_date,user_id = active_user.id,image_path=image_path,image_name=image_name,name=name,address=address,start_time=start_time,end_time=end_time,description=description,created_time=datetime.utcnow())
        db.session.add(add_event)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Event created successfully'})

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

@user_view_v5.route('/hide_user', methods=['POST'])
@token_required
def hide_user(active_user):
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0,'messege': 'Please select user first.'})

    get_user = User.query.get(user_id)
    if not get_user:
        return jsonify({'status': 0,'messege': 'Invalid user'})

    check_already_exists = HideUser.query.filter_by(by_id = active_user.id ,to_id = user_id).first()

    if check_already_exists:
        db.session.delete(check_already_exists)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully removed from hide list'})

    else:
        add_hide_data = HideUser(by_id = active_user.id,to_id = user_id,created_time = datetime.utcnow())
        db.session.add(add_hide_data)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully added to hide'})

@user_view_v5.route('/favorite_user_list', methods=['POST'])
@token_required
def favorite_user_list(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    favorite_count_subq = (
        db.session.query(
            FavoriteUser.to_id.label("user_id"),
            func.count(FavoriteUser.by_id).label("favorite_count")
        )
            .group_by(FavoriteUser.to_id)
            .subquery()
    )

    get_favorites = (
        db.session.query(
            User,
            favorite_count_subq.c.favorite_count
        )
            .join(FavoriteUser, FavoriteUser.to_id == User.id)
            .join(favorite_count_subq, favorite_count_subq.c.user_id == User.id)
            .filter(FavoriteUser.by_id == active_user.id)
            .order_by(desc(favorite_count_subq.c.favorite_count))
            .paginate(page=page, per_page=per_page, error_out=False)

    )

    user_list = []

    if get_favorites.items:
        for user, count in get_favorites:
            user_dict = {

                'id': user.id,
                'username': user.fullname,
                'user_image': user.image_path if user.image_name is not None else '',
                'favorite_count': str(count)
            }

            user_list.append(user_dict)

    pagination_info = {
        "current_page": get_favorites.page,
        "has_next": get_favorites.has_next,
        "per_page": get_favorites.per_page,
        "total_pages": get_favorites.pages
    }

    return jsonify({'status': 1,'messege': 'Success','user_list': user_list,'pagination_info': pagination_info})

@user_view_v5.route('/favorite_user', methods=['POST'])
@token_required
def favorite_user(active_user):
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0,'messege': 'Please select user first.'})

    get_user = User.query.get(user_id)
    if not get_user:
        return jsonify({'status': 0,'messege': 'Invalid user'})

    check_already_exists = FavoriteUser.query.filter_by(by_id = active_user.id ,to_id = user_id).first()

    if check_already_exists:
        db.session.delete(check_already_exists)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully removed from favorites'})

    else:
        add_fav_data = FavoriteUser(by_id = active_user.id,to_id = user_id,created_time = datetime.utcnow())
        db.session.add(add_fav_data)
        db.session.commit()

        title = 'New Meetup Request'

        msg = f'{active_user.fullname} wants to meet up with you! Send a message!'

        if get_user.device_token:
            notification = push_notification(device_token=get_user.device_token, title=title, msg=msg,
                                             image_url=None, device_type=get_user.device_type)

        add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=get_user.id,
                                           is_read=False, created_time=datetime.utcnow(), page='new user favorite')
        db.session.add(add_notification)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully added to favorites'})

@user_view_v5.route('/user_report_new_post', methods=['POST'])
@token_required
def user_report_new_post(active_user):

    post_id = request.json.get('post_id')

    if not post_id:
        return jsonify({'status': 0,'messege': 'Please select post first'})

    get_post_data = NewUserPosts.query.get(post_id)
    if not get_post_data:
        return jsonify({'status': 0,'messege': 'Invalid post'})

    check_reported = ReportNewUserPosts.query.filter_by(image_id = post_id,user_id = active_user.id).first()
    if check_reported:
        return jsonify({'status': 0,'messege': 'You already reported this post'})

    add_report = ReportNewUserPosts(image_id = post_id,user_id = active_user.id,created_time = datetime.utcnow())
    db.session.add(add_report)
    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully reported'})

@user_view_v5.route('/user_hide_new_post', methods=['POST'])
@token_required
def user_hide_new_post(active_user):

    post_id = request.json.get('post_id')

    if not post_id:
        return jsonify({'status': 0,'messege': 'Please select post first'})

    get_post_data = NewUserPosts.query.get(post_id)
    if not get_post_data:
        return jsonify({'status': 0,'messege': 'Invalid post'})

    check_hide = HideNewUserPosts.query.filter_by(image_id = post_id,user_id = active_user.id).first()

    if not check_hide:
        add_hide = HideNewUserPosts(image_id = post_id,user_id = active_user.id)
        db.session.add(add_hide)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully hided'})

    else:
        db.session.delete(check_hide)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully removed from hide'})

@user_view_v5.route('/user_like_new_post', methods=['POST'])
@token_required
def user_like_new_post(active_user):

    post_id = request.json.get('post_id')

    if not post_id:
        return jsonify({'status': 0,'messege': 'Please select post first'})

    get_post_data = NewUserPosts.query.get(post_id)
    if not get_post_data:
        return jsonify({'status': 0,'messege': 'Invalid post'})

    check_liked = LikeNewUserPosts.query.filter_by(image_id = post_id,user_id = active_user.id).first()

    if not check_liked:
        add_like = LikeNewUserPosts(image_id = post_id,user_id = active_user.id,main_user_id = get_post_data.user_id)
        db.session.add(add_like)
        db.session.commit()

        get_user_data = User.query.get(get_post_data.user_id)

        if not get_user_data:
            return jsonify({'status': 0,'messege': 'User not found'})


        if active_user.id != get_user_data.id:
            title = 'New Like'
            # image_url = f'{active_user.image_path}'
            msg = f'{active_user.fullname} liked your post'

            if get_user_data.device_token:
                notification = push_notification(device_token=get_user_data.device_token, title=title, msg=msg,
                                         image_url=None, device_type=get_user_data.device_type)

            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=get_user_data.id,
                                               is_read=False, created_time=datetime.utcnow(), page='new post like')
            db.session.add(add_notification)
            db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully liked'})

    else:
        db.session.delete(check_liked)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully like removed'})

# @user_view_v5.route('/user_new_post_listing', methods=['POST'])
# @token_required
# def user_new_post_listing(active_user):
#     page = int(request.json.get('page', 1))
#     per_page = 30
#
#     # Join with LikeNewUserPosts and count likes per post
#     subquery = (
#         db.session.query(
#             LikeNewUserPosts.image_id.label('image_id'),
#             func.count(LikeNewUserPosts.id).label('like_count')
#         )
#         .group_by(LikeNewUserPosts.image_id)
#         .subquery()
#     )
#
#     # Join the subquery with NewUserPosts to get only liked posts
#     posts_query = (
#         db.session.query(NewUserPosts)
#         .join(subquery, NewUserPosts.id == subquery.c.image_id)
#         .order_by(subquery.c.like_count.desc())  # Most likes first
#     )
#
#     get_posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)
#
#     pagination_info = {
#         "current_page": get_posts.page,
#         "has_next": get_posts.has_next,
#         "per_page": get_posts.per_page,
#         "total_pages": get_posts.pages
#     }
#
#     get_posts_list = [post.as_dict(active_user.id) for post in get_posts.items]
#
#     return jsonify({
#         'status': 1,
#         'messege': 'Success',
#         'post_list': get_posts_list,
#         'pagination_info': pagination_info
#     })

@user_view_v5.route('/my_new_post_listing', methods=['POST'])
@token_required
def my_new_post_listing(active_user):
    page = int(request.json.get('page', 1))
    # city = request.json.get('city')
    # state = request.json.get('state')
    per_page = 30

    # Subquery to count likes per post
    subquery_likes = (
        db.session.query(
            LikeNewUserPosts.image_id.label('image_id'),
            func.count(LikeNewUserPosts.id).label('like_count')
        )
        .group_by(LikeNewUserPosts.image_id)
        .subquery()
    )

    # Subquery for hidden posts for the active user
    subquery_hidden = (
        db.session.query(HideNewUserPosts.image_id)
        .filter(HideNewUserPosts.user_id == active_user.id)
        .subquery()
    )

    # Main query - exclude hidden posts
    posts_query = (
    db.session.query(NewUserPosts)
    .outerjoin(subquery_likes, NewUserPosts.id == subquery_likes.c.image_id)
    .filter(~NewUserPosts.id.in_(subquery_hidden),NewUserPosts.user_id == active_user.id)  # Exclude hidden posts
    .order_by(
        subquery_likes.c.like_count.is_(None),       # Sort NULLs last
        subquery_likes.c.like_count.desc()           # Then sort descending
    )
)

    # if city:
    #     posts_query = posts_query.filter(NewUserPosts.city.ilike(f"{city}%"))
    #
    # if state:
    #     posts_query = posts_query.filter(NewUserPosts.state.ilike(f"{state}%"))


    # Paginate results
    get_posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)

    pagination_info = {
        "current_page": get_posts.page,
        "has_next": get_posts.has_next,
        "per_page": get_posts.per_page,
        "total_pages": get_posts.pages
    }

    # Format posts
    get_posts_list = [post.as_dict(active_user.id) for post in get_posts.items]

    return jsonify({
        'status': 1,
        'messege': 'Success',
        'post_list': get_posts_list,
        'pagination_info': pagination_info
    })

@user_view_v5.route('/another_user_post_listing', methods=['POST'])
@token_required
def another_user_post_listing(active_user):
    page = int(request.json.get('page', 1))
    user_id = request.json.get('user_id')
    # city = request.json.get('city')
    # state = request.json.get('state')
    per_page = 30

    if not user_id:
        return jsonify({"status": 0,'messege':'Please select user first'})

    # Subquery to count likes per post
    subquery_likes = (
        db.session.query(
            LikeNewUserPosts.image_id.label('image_id'),
            func.count(LikeNewUserPosts.id).label('like_count')
        )
        .group_by(LikeNewUserPosts.image_id)
        .subquery()
    )

    # Subquery for hidden posts for the active user
    subquery_hidden = (
        db.session.query(HideNewUserPosts.image_id)
        .filter(HideNewUserPosts.user_id == active_user.id)
        .subquery()
    )

    # Main query - exclude hidden posts
    posts_query = (
    db.session.query(NewUserPosts)
    .outerjoin(subquery_likes, NewUserPosts.id == subquery_likes.c.image_id)
    .filter(~NewUserPosts.id.in_(subquery_hidden),NewUserPosts.user_id == user_id)  # Exclude hidden posts
    .order_by(
        subquery_likes.c.like_count.is_(None),       # Sort NULLs last
        subquery_likes.c.like_count.desc()           # Then sort descending
    )
)

    # if city:
    #     posts_query = posts_query.filter(NewUserPosts.city.ilike(f"{city}%"))
    #
    # if state:
    #     posts_query = posts_query.filter(NewUserPosts.state.ilike(f"{state}%"))


    # Paginate results
    get_posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)

    pagination_info = {
        "current_page": get_posts.page,
        "has_next": get_posts.has_next,
        "per_page": get_posts.per_page,
        "total_pages": get_posts.pages
    }

    # Format posts
    get_posts_list = [post.as_dict(active_user.id) for post in get_posts.items]

    return jsonify({
        'status': 1,
        'messege': 'Success',
        'post_list': get_posts_list,
        'pagination_info': pagination_info
    })

@user_view_v5.route('/seperate_new_post', methods=['POST'])
@token_required
def seperate_new_post(active_user):
    post_id = request.json.get('post_id')
    if not post_id:
        return jsonify({'status': 0,'messege': 'Please select post to view'})

    get_post = NewUserPosts.query.get(post_id)
    if not get_post:
        return jsonify({'status': 0,'messege': 'Invalid post'})

    return jsonify({'status': 1,'messege': 'Success','data': get_post.as_dict(active_user.id)})

@user_view_v5.route('/user_new_post_listing', methods=['POST'])
@token_required
def user_new_post_listing(active_user):
    page = int(request.json.get('page', 1))
    city = request.json.get('city')
    state = request.json.get('state')

    # new feilds

    gender = request.json.get('gender')
    age_start = request.json.get('age_start')
    age_end = request.json.get('age_end')
    looking_for = request.json.get('looking_for')
    sexual_orientation = request.json.get('sexual_orientation')

    per_page = 30

    # Subquery to count likes per post
    subquery_likes = (
        db.session.query(
            LikeNewUserPosts.image_id.label('image_id'),
            func.count(LikeNewUserPosts.id).label('like_count')
        )
        .group_by(LikeNewUserPosts.image_id)
        .subquery()
    )

    # Subquery for hidden posts for the active user
    subquery_hidden = (
        db.session.query(HideNewUserPosts.image_id)
        .filter(HideNewUserPosts.user_id == active_user.id)
        .subquery()
    )

    # Main query - exclude hidden posts
    posts_query = (
    db.session.query(NewUserPosts)
    .outerjoin(subquery_likes, NewUserPosts.id == subquery_likes.c.image_id)
    .filter(~NewUserPosts.id.in_(subquery_hidden))  # Exclude hidden posts
    .order_by(
        subquery_likes.c.like_count.is_(None),       # Sort NULLs last
        subquery_likes.c.like_count.desc()           # Then sort descending
    )
)

    if city:
        posts_query = posts_query.filter(NewUserPosts.city.ilike(f"{city}%"))

    if state:
        posts_query = posts_query.filter(NewUserPosts.state.ilike(f"{state}%"))
    if gender:
        posts_query = posts_query.filter(NewUserPosts.gender==gender)
    if looking_for:
        posts_query = posts_query.filter(NewUserPosts.looking_for==looking_for)
    if sexual_orientation:
        posts_query = posts_query.filter(NewUserPosts.sexual_orientation==sexual_orientation)
    if age_start and age_end:

        age_start = int(age_start)
        age_end = int(age_end)

        posts_query = posts_query.filter(
            db.cast(NewUserPosts.age_start, db.Integer) <= age_end,
            db.cast(NewUserPosts.age_end, db.Integer) >= age_start
        )


    # Paginate results
    get_posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)

    pagination_info = {
        "current_page": get_posts.page,
        "has_next": get_posts.has_next,
        "per_page": get_posts.per_page,
        "total_pages": get_posts.pages
    }

    # Format posts
    get_posts_list = [post.as_dict(active_user.id) for post in get_posts.items]

    return jsonify({
        'status': 1,
        'messege': 'Success',
        'post_list': get_posts_list,
        'pagination_info': pagination_info
    })

@user_view_v5.route('/delete_new_post', methods=['POST'])
@token_required
def delete_new_post(active_user):
    post_id = request.json.get('post_id')

    if not post_id:
        return jsonify({'status':0,'messege': 'Please select post first.'})

    get_post = NewUserPosts.query.filter_by(id =post_id,user_id = active_user.id).first()

    if not get_post:
        return jsonify({'status':0,'messege': 'Invalid post.'})
    db.session.delete(get_post)
    db.session.commit()

    return jsonify({'status':1,'messege':'Post deleted successfully'})

@user_view_v5.route('/user_new_post', methods=['POST'])
@token_required
def user_new_post(active_user):
    title = request.form.get('title')
    content = request.files.get('image')
    content_type = request.form.get('content_type')
    city = request.form.get('city')
    state = request.form.get('state')

    # new feilds

    gender = request.form.get('gender')
    age_start = request.form.get('age_start')
    age_end = request.form.get('age_end')
    looking_for = request.form.get('looking_for')
    sexual_orientation = request.form.get('sexual_orientation')

    if not content:
        return jsonify({'status': 0, 'messege': 'Please select content'})

    if content_type == 'video':
        if content and content.filename:
            video_name = secure_filename(content.filename)
            extension = os.path.splitext(video_name)[1]
            extension2 = os.path.splitext(video_name)[1][1:].lower()

            unique_name = secrets.token_hex(10)

            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
                content.save(tmp.name)
                # Rewind the file pointer to the beginning of the video file
                tmp.seek(0)

                # Generate a thumbnail for the video
                clip = VideoFileClip(tmp.name)
                thumbnail_name = f"thumb_{unique_name}.jpg"
                clip.save_frame(thumbnail_name, t=1)  # Save the frame at 1 second as the thumbnail

                # Close the VideoFileClip object
                clip.reader.close()
                if clip.audio and clip.audio.reader:
                    clip.audio.reader.close_proc()

                # Upload the thumbnail to S
                with open(thumbnail_name, 'rb') as thumb:

                    s3_client.upload_fileobj(thumb, S3_BUCKET, thumbnail_name,
                                             ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpeg'})
                thumbnail_path = f"https://{S3_BUCKET}.s3.amazonaws.com/{thumbnail_name}"
                print(f'Thumbnail URL: {thumbnail_path}')

                # Clean up the temporary thumbnail file
                os.remove(thumbnail_name)

            # Upload the original post (video or image)
            content.seek(0)  # Rewind the file pointer to the beginning

            content_type2 = f'video/{extension2}'
            x = secrets.token_hex(10)

            video_name = x + extension

            s3_client.upload_fileobj(content, S3_BUCKET, video_name,
                                     ExtraArgs={'ACL': 'public-read', 'ContentType': content_type2})
            video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{video_name}"

            # Clean up the temporary video file after uploading
            try:
                os.remove(tmp.name)
                print('itssssssssssssssssss successsssssssssssssssssssss')
            except PermissionError as e:
                print(f"Error removing temporary file: {e}")
            print('video_url', video_url)

            add_new_post = NewUserPosts(sexual_orientation=sexual_orientation,looking_for=looking_for,age_end=age_end,age_start=age_start,gender=gender,city=city,state=state,content_type=content_type, title=title, created_time=datetime.utcnow(),
                                        image_name=video_name, image_path=video_url,thumbnail_path=thumbnail_path,user_id = active_user.id)
            db.session.add(add_new_post)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Successfully post added'})
        else:
            return jsonify({'status': 0,'messege': 'Video not found'})

    else:
        file_path, picture = upload_photos(content)
        image_name = picture
        image_path = file_path

        add_new_post = NewUserPosts(sexual_orientation=sexual_orientation,looking_for=looking_for,age_end=age_end,age_start=age_start,gender=gender,city=city,state=state,content_type='image',title=title,created_time = datetime.utcnow(),image_name=image_name,image_path=image_path,user_id = active_user.id)
        db.session.add(add_new_post)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully post added'})

@user_view_v5.route('/update_profile_pic', methods=['POST'])
@token_required
def update_profile_pic(active_user):
    image = request.files.get('image')

    if not image:
        return jsonify({'status': 0,'messege': 'Please select image'})

    file_path, picture = upload_photos(image)
    active_user.image_name = picture
    active_user.image_path = file_path

    db.session.commit()

    return jsonify(
        {'status': 1, 'messege': 'Profile pic updated successfully','data': active_user.as_dict()})

@user_view_v5.route('/user_box_data', methods=['POST'])
@token_required
def user_box_data(active_user):
    data = request.get_json()

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 0, 'messege': 'Please select user first'})

    get_user = User.query.filter(User.id == user_id,User.is_block == False,User.deleted == False).first()
    if not get_user:
        return jsonify({'status': 0, 'messege': 'Invalid user'})

    user_id = get_user.id
    username = get_user.fullname if get_user.fullname is not None else ''
    user_image = get_user.image_path

    return jsonify({'status': 1,'messege': 'Success','box_data': get_user.as_dict_box(),"user_id": user_id,"username": username,"user_image":user_image})

@user_view_v5.route('/update_box', methods=['POST'])
@token_required
def update_box(active_user):
    data = request.get_json()
    print('boxx data',data)

    active_user.box_1 = data.get('box_1')
    active_user.box_2 = data.get('box_2')
    active_user.box_3 = data.get('box_3')
    active_user.box_4 = data.get('box_4')
    active_user.box_5 = data.get('box_5')
    active_user.box_6 = data.get('box_6')
    active_user.box_7 = data.get('box_7')
    active_user.box_8 = data.get('box_8')
    active_user.box_9 = data.get('box_9')
    active_user.box_10 = data.get('box_10')

    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully description saved'})

@user_view_v5.route('/create_new_group', methods=['POST'])
@token_required
def create_new_group(active_user):

    group_name = request.json.get('group_name')
    if not group_name:
        return jsonify({'status': 0,'messege': 'Please provide group name'})

    get_existing_group = NewGroup.query.filter_by(user_id = active_user.id , group_name = group_name).first()
    if get_existing_group:
        return jsonify({'status': 0,'messege': 'You already created group with same name'})

    add_new_group = NewGroup(group_name=group_name,user_id = active_user.id,created_time = datetime.utcnow())
    db.session.add(add_new_group)
    db.session.commit()

    add_join_group = JoinedNewGroup(group_id = add_new_group.id, user_id = active_user.id)
    db.session.add(add_join_group)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Group created successfully'})

@user_view_v5.route('/new_group_list', methods=['POST'])
@token_required
def new_group_list(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    group_query = db.session.query(
        NewGroup,
        func.count(JoinedNewGroup.id).label('join_count')
    ).outerjoin(JoinedNewGroup, NewGroup.id == JoinedNewGroup.group_id
    ).group_by(NewGroup.id
    ).order_by(desc('join_count'))

    groups_with_counts = group_query.paginate(page=page, per_page=per_page, error_out=False)

    has_next = groups_with_counts.has_next
    total_pages = groups_with_counts.pages

    # Prepare pagination info for response
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    group_list = []

    for group, join_count in groups_with_counts.items:
        is_joined = JoinedNewGroup.query.filter_by(
            group_id=group.id,
            user_id=active_user.id
        ).first()

        group_dict = {
            'id': group.id,
            'group_name': group.group_name,
            'is_saved': bool(is_joined),
            'join_count': str(join_count)
        }

        group_list.append(group_dict)

    return jsonify({'status': 1, 'messege': 'Success', 'group_list': group_list,'pagination_info':pagination_info})

@user_view_v5.route('/join_unjoin_new_group', methods=['POST'])
@token_required
def unjoin_new_group(active_user):
    group_id = request.json.get('group_id')
    if not group_id:
        return jsonify({'status': 0,'messege': 'Please select group first'})

    get_group_data = NewGroup.query.get(group_id)
    if not get_group_data:
        return jsonify({'status': 0,'messege': 'Invalid group'})

    check_joined = JoinedNewGroup.query.filter_by(group_id=get_group_data.id, user_id=active_user.id).first()
    if check_joined:
        db.session.delete(check_joined)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully unjoin group'})

    else:
        add_join_group = JoinedNewGroup(group_id=get_group_data.id, user_id=active_user.id)
        db.session.add(add_join_group)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully join group'})

@user_view_v5.route('/get_request_status', methods=['GET'])
@token_required
def get_request_status(active_user):
    check_friend_request = FriendRequest.query.filter_by(to_id=active_user.id, request_status=2).first()
    check_profile_review_request = ProfileReviewRequest.query.filter_by(to_id = active_user.id,
                                                             request_status = 2).first()

    notification_counts = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).count()
    return jsonify({'status':1,'messege': 'Success','friend_request': bool(check_friend_request),'profile_review_request': bool(check_profile_review_request),'notification_count':str(notification_counts)})

@user_view_v5.route('/matches_category_page', methods=['POST'])
@token_required
def matches_category_page(active_user):
    category_id = request.json.get('category_id')
    category_type = request.json.get('category_type')
    city = request.json.get('city')
    state = request.json.get('state')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if not category_id:
        return jsonify({'status': 0, 'messege': 'Please select category'})
    if not category_type:
        return jsonify({'status': 0, 'messege': 'Please select category type'})

    # Block logic
    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    if category_type == 'places':

        get_category_data = Category.query.get(category_id)
        if not get_category_data:
            return jsonify({'status': 0, 'messege': 'Invalid category'})

        query = (
            db.session.query(
                User.id,
                User.fullname,
                User.image_path,
                User.city,
                User.state,
                User.new_bio
            )
                .join(SavedCommunity, SavedCommunity.user_id == User.id)
                .filter(
                SavedCommunity.category_id == category_id,
                User.id != active_user.id,
                User.deleted == False,
                User.is_block == False,
                ~User.id.in_(blocked_user_ids),
                ~User.id.in_(blocked_by_user_ids)
            )
                .distinct()

        )

    elif category_type == 'things':

        get_category_data = ThingsCategory.query.get(category_id)
        if not get_category_data:
            return jsonify({'status': 0, 'messege': 'Invalid category'})

        query = (
            db.session.query(
                User.id,
                User.fullname,
                User.image_path,
                User.city,
                User.state,
                User.new_bio
            )
                .join(SavedThingsCommunity, SavedThingsCommunity.user_id == User.id)
                .filter(
                SavedThingsCommunity.category_id == category_id,
                User.id != active_user.id,
                User.deleted == False,
                User.is_block == False,
                ~User.id.in_(blocked_user_ids),
                ~User.id.in_(blocked_by_user_ids)
            )
                .distinct()

        )

    else:
        return jsonify({'status': 0, 'messege': 'Invalid category type'})

    if city:
        query = query.filter(User.city.ilike(f"{city}%"))

    if state:
        query = query.filter(User.state.ilike(f"{state}%"))

    paginated_users = query.paginate(page=page, per_page=per_page, error_out=False)

    # Extract users and pagination info
    users = paginated_users.items

    pagination_info = {
        "current_page": paginated_users.page,
        "has_next": paginated_users.has_next,
        "per_page": paginated_users.per_page,
        "total_pages": paginated_users.pages
    }

    response = [
        {"id": u.id, "username": u.fullname, "user_image": u.image_path, "city": u.city if u.city is not None else '',
         "state": u.state if u.state is not None else '', "new_bio": u.new_bio if u.new_bio is not None else ''} for u
        in users]

    if len(response) > 0:
        return jsonify({'status': 1, 'messege': 'Success', 'user_list': response, "pagination_info": pagination_info})
    else:
        return jsonify(
            {'status': 1, 'messege': 'No users found', 'user_list': response, "pagination_info": pagination_info})

@user_view_v5.route('/favorite_subcategory_page', methods=['POST'])
@token_required
def favorite_subcategory_page(active_user):

    data = request.get_json()

    tab = data.get('tab')
    user_id = data.get('user_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    if tab is None:
        return jsonify({'status': 0,'messege': 'Please select tab'})
    if user_id is None:
        return jsonify({'status': 0,'messege': 'Please select tab'})

    get_user = User.query.get(user_id)
    if not get_user:
        return jsonify({'status': 0,'messege': 'Invalid user'})

    if tab == 0:

        get_fav_data = FavoriteSubCategory.query.filter_by(user_id = active_user.id,type = 'places').paginate(page=page, per_page=per_page, error_out=False)

        fav_list = []

        if get_fav_data.items:
            for i in get_fav_data.items:
                get_created_data = CreatedCommunity.query.get(i.places_id)
                if not get_created_data:
                    return jsonify({'status': 0,'messege': 'Invalid data'})

                fav_data = {

                    'community_id': i.places_id,
                    'type': i.type,
                    'community_name': get_created_data.community_name
                }

                fav_list.append(fav_data)

        return jsonify({'status': 1,'messege': 'Success','fav_list': fav_list})

    elif tab == 1:

        get_fav_data = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things').paginate(page=page,
                                                                                                           per_page=per_page,
                                                                                                           error_out=False)

        fav_list = []

        if get_fav_data.items:
            for i in get_fav_data.items:
                get_created_data = CreatedThingsCommunity.query.get(i.things_id)
                if not get_created_data:
                    return jsonify({'status': 0, 'messege': 'Invalid data'})

                fav_data = {

                    'community_id': i.things_id,
                    'type': i.type,
                    'community_name': get_created_data.community_name
                }

                fav_list.append(fav_data)

        return jsonify({'status': 1, 'messege': 'Success', 'fav_list': fav_list})

    else:
        return jsonify({'status': 0, 'messege': 'Invalid tab'})

@user_view_v5.route('/favorite_subcategory', methods=['POST'])
@token_required
def favorite_subcategory(active_user):

    data = request.get_json()

    created_id = data.get('created_id')
    type = data.get('type')

    if not created_id:
        return jsonify({'status': 0,'messege': 'Please select word first'})
    if not type:
        return jsonify({'status': 0,'messege': 'Please select places or things first'})

    if type == 'things':
        get_things_community_data = CreatedThingsCommunity.query.get(created_id)
        if not get_things_community_data:
            return jsonify({'status': 0, 'messege': 'Invalid data'})

        validate_fav = FavoriteSubCategory.query.filter_by(user_id=active_user.id, things_id=created_id, type=type).first()

        if validate_fav:
            db.session.delete(validate_fav)
            db.session.commit()

            return jsonify({'status': 1,'messege': 'Word removed from favorites'})

        else:
            add_fav = FavoriteSubCategory(user_id = active_user.id,things_id=created_id,type=type)
            db.session.add(add_fav)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Word added to favorites'})

    elif type == 'places':
        get_community_data = CreatedCommunity.query.get(created_id)
        if not get_community_data:
            return jsonify({'status': 0, 'messege': 'Invalid data'})

        validate_fav = FavoriteSubCategory.query.filter_by(user_id=active_user.id, places_id=created_id,
                                                           type=type).first()

        if validate_fav:
            db.session.delete(validate_fav)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Word removed from favorites'})

        else:
            add_fav = FavoriteSubCategory(user_id=active_user.id, places_id=created_id, type=type)
            db.session.add(add_fav)
            db.session.commit()

            return jsonify({'status': 1, 'messege': 'Word added to favorites'})

    else:
        return jsonify({'status': 1,'messege': "Invalid category type"})

# @user_view_v5.route('/create_event', methods=['POST'])
# @token_required
# def create_event(active_user):
#
#     data = request.get_json()
#
#     description = data.get('description')
#     address = data.get('address')
#     event_date = data.get('event_date')
#     event_time = data.get('event_time')
#
#     if not description and not address and not event_date and not event_time:
#         return jsonify({'status': 0, 'messege': 'Please provide inputs'})
#
#     add_feed_data = Feed(created_time=datetime.utcnow(), user_id=active_user.id,feed_type='event',description=description,
#                          address=address,event_date=event_date,event_time=event_time)
#     db.session.add(add_feed_data)
#     db.session.commit()
#
#     return jsonify({'status': 1, 'messege': 'Successfully event created'})

@user_view_v5.route('/get_user_bio', methods=['POST'])
@token_required
def get_user_bio(active_user):

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"status": 0,"messege": "Please select user first"})

    get_user = User.query.get(user_id)

    bio = get_user.new_bio if get_user.new_bio is not None else ""
    profile_link = active_user.profile_link if active_user.profile_link is not None else ""

    return jsonify({"status": 1,"messege": "Success","bio": bio,"profile_link": profile_link})

@user_view_v5.route('/save_filter_data', methods=['POST'])
@token_required
def save_filter_data(active_user):
    data = request.get_json()

    city = data.get('city')
    state = data.get('state')
    gender = data.get('gender')

    if city == "":
        city = None
    if state == "":
        state = None
    if gender == "":
        gender = None

    active_user.saved_city = city
    active_user.saved_state = state
    active_user.saved_gender = gender

    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Filter data saved'})


@user_view_v5.route('/new_user_page', methods=['POST'])
@token_required
def new_user_page(active_user):
    page = int(request.json.get('page', 1))
    search_text = request.json.get('search_text')
    city = request.json.get('city')
    state = request.json.get('state')
    # start_age = request.json.get('start_age')
    # end_age = request.json.get('end_age')

    per_page = 30

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
    hide_user_ids = [hide.to_id for hide in HideUser.query.filter_by(by_id=active_user.id).all()]

    # user_data = (
    #     User.query.filter(
    #         User.id != active_user.id,
    #         User.is_block != True,
    #         User.deleted != True,
    #         ~User.id.in_(blocked_user_ids),
    #         ~User.id.in_(blocked_by_user_ids)
    #     )
    #         .order_by(User.id.desc())  # Move order_by here
    #         .paginate(page=page, per_page=per_page, error_out=False)
    # )

    query = User.query.filter(
        User.id != active_user.id,
        User.is_block != True,
        User.deleted != True,
        ~User.id.in_(blocked_user_ids),
        ~User.id.in_(blocked_by_user_ids),
        ~User.id.in_(hide_user_ids)
    )

    # this is for saved search
    #
    # if active_user.saved_city is not None:
    #     query = query.filter(User.city == active_user.saved_city)
    #
    # if active_user.saved_state is not None:
    #     query = query.filter(User.state == active_user.saved_state)
    #
    # if active_user.saved_gender is not None:
    #     query = query.filter(User.gender == active_user.saved_gender)

    if city:
        query = query.filter(User.city.ilike(f"{city}%"))
    if state:
        query = query.filter(User.state.ilike(f"{state}%"))
    if search_text:
        query = query.filter(User.new_bio.ilike(f"{search_text}%"))

    if active_user.is_filter == True:

        start_age = active_user.start_age if active_user.start_age is not None else '0'
        end_age = active_user.end_age if active_user.end_age is not None else '40'

        if start_age and end_age:
            end_age = int(end_age)
            start_age = int(start_age)
            print('start_ageeeeeeeeeeeeeeeeeeeeeeeeeeee', start_age)
            today = date.today()
            min_dob = today - relativedelta(years=end_age)
            max_dob = today - relativedelta(years=start_age)

            query = query.filter(
                User.age.between(min_dob, max_dob),
                User.age.isnot(None),  # skip NULLs
                User.age != '0000-00-00'  # skip bad default date
            )

        if active_user.saved_gender is not None:
            query = query.filter(User.gender == active_user.saved_gender)

        if active_user.saved_looking_for is not None:
            query = query.filter(User.looking_for == active_user.saved_looking_for)

    user_data = query.order_by(User.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    print('user_data.items', user_data.items)

    response_list = []

    if user_data.items:
        for i in user_data.items:
            check_fav = FavoriteUser.query.filter_by(by_id=active_user.id, to_id=i.id).first()
            is_follow = Follow.query.filter_by(by_id=active_user.id, to_id=i.id).first()

            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'city': i.city if i.city is not None else '',
                             'state': i.state if i.state is not None else '',
                             'new_bio': i.new_bio if i.new_bio is not None else '',
                             'is_favorite': bool(check_fav),
                             'is_follow': bool(is_follow)
                             }

            response_list.append(response_dict)

    has_next = user_data.has_next  # Check if there is a next page
    total_pages = user_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages
    }

    if len(response_list) > 0:
        return jsonify({'status': 1, 'data': response_list, 'messege': 'Sucess', 'pagination': pagination_info})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'No users theire',
                        'pagination_info': pagination_info})

# @user_view_v5.route('/new_user_page', methods=['POST'])
# @token_required
# def new_user_page(active_user):
#     page = int(request.json.get('page', 1))
#     per_page = 30
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
#
#     matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('community_matches'))
#                     .join(User, User.id == SavedCommunity.user_id)
#                     .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
#                     .group_by(SavedCommunity.user_id)
#                     .subquery())
#
#     active_user_things_saved_ids = [j.created_id for j in active_user.save_things_community_id]
#
#     things_matches_subq = (db.session.query(SavedThingsCommunity.user_id, func.count().label('things_matches'))
#                            .join(User, User.id == SavedThingsCommunity.user_id)
#                            .filter(SavedThingsCommunity.created_id.in_(active_user_things_saved_ids))
#                            .group_by(SavedThingsCommunity.user_id)
#                            .subquery())
#
#     user_data = (
#         db.session.query(
#             User,
#             (func.coalesce(matches_subq.c.community_matches, 0) +
#              func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches'),
#         )
#             .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
#             .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
#             .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
#             .filter(~User.id.in_(blocked_user_ids))
#             .filter(~User.id.in_(blocked_by_user_ids))
#             .filter((matches_subq.c.community_matches != None) | (things_matches_subq.c.things_matches != None))
#             .order_by(User.id.desc())
#             .paginate(page=page, per_page=per_page, error_out=False)
#     )
#
#     user_data_count = (
#         db.session.query(
#             User,
#             (func.coalesce(matches_subq.c.community_matches, 0) +
#              func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches'),
#         )
#             .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
#             .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
#             .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
#             .filter(~User.id.in_(blocked_user_ids))
#             .filter(~User.id.in_(blocked_by_user_ids))
#             .filter((matches_subq.c.community_matches != None) | (things_matches_subq.c.things_matches != None))
#             .order_by((func.coalesce(matches_subq.c.community_matches, 0) +
#                        func.coalesce(things_matches_subq.c.things_matches, 0)).desc())
#             .count()
#     )
#
#     print('user_data_count', user_data_count)
#
#     response_list = []
#
#     print('user_data', user_data.items)
#
#     saved_my_favorites = []
#
#     for j in active_user.save_community_id:
#         saved_my_favorites.append(j.created_id)
#
#     if user_data.items:
#         print('user_data.items', user_data.items)
#         for specific_response, count in user_data.items:
#             count_value = str(count)
#             if not count:
#                 count_value = '0'
#
#             badge = ""
#             if specific_response.badge_name is not None:
#                 if specific_response.badge_name == "I'll Buy Us Coffee":
#                     badge = "☕"
#                 if specific_response.badge_name == "I'll Buy Us Food":
#                     badge = "🍔"
#
#                 if specific_response.badge_name == "I’ll buy us food":
#                     badge = "🍟"
#
#                 if specific_response.badge_name == "I’ll buy us drinks":
#                     badge = "☕"
#
#                 if specific_response.badge_name == "Activity Badge":
#                     badge = "🚴"
#                 if specific_response.badge_name == "Best Friend Forever Badge":
#                     badge = "🧑‍🤝‍🧑"
#                 if specific_response.badge_name == "Luxury Badge":
#                     badge = "🚁"
#                 if specific_response.badge_name == "Lavish Badge":
#                     badge = "💎"
#                     # badge = specific_response.badge_name
#             college = ""
#             if specific_response.college is not None:
#                 college = specific_response.college
#             sexuality = ""
#             if specific_response.sexuality is not None:
#                 sexuality = specific_response.sexuality
#
#             relationship_status = ""
#             if specific_response.relationship_status is not None:
#                 relationship_status = specific_response.relationship_status
#
#             looking_for = ""
#             if specific_response.looking_for is not None:
#                 looking_for = specific_response.looking_for
#
#             total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=specific_response.id).count()
#             total_liked_questions_answer = LikeUserAnswer.query.filter_by(main_user_id=specific_response.id).count()
#
#             user_places_review = PlacesReview.query.filter_by(user_id=specific_response.id).all()
#
#             review_likes_count = []
#             if len(user_places_review) > 0:
#                 for i in user_places_review:
#                     liked_places_review = PlacesReviewLike.query.filter_by(review_id=i.id).count()
#                     if liked_places_review > 0:
#                         review_likes_count.append(liked_places_review)
#
#             user_things_review = ThingsReview.query.filter_by(user_id=specific_response.id).all()
#             if len(user_things_review) > 0:
#                 for i in user_things_review:
#                     liked_things_review = ThingsReviewLike.query.filter_by(review_id=specific_response.id).count()
#                     if liked_things_review > 0:
#                         review_likes_count.append(liked_things_review)
#
#             total_review_likes_count = '0'
#             if len(review_likes_count) > 0:
#                 total_review_likes_count = str(sum(review_likes_count))
#
#             total_followers = Follow.query.filter_by(to_id=specific_response.id).count()
#             user_feed_data = Feed.query.filter_by(user_id=specific_response.id).all()
#
#             total_status_likes = []
#
#             if len(user_feed_data) > 0:
#                 for i in user_feed_data:
#                     feed_likes = FeedLike.query.filter_by(feed_id=i.id).count()
#                     if feed_likes > 0:
#                         total_status_likes.append(feed_likes)
#
#             get_approved_reviews_likes = ProfileReviewLike.query.filter_by(main_user_id=specific_response.id).count()
#             total_user_photos_likes = LikeUserPhotos.query.filter_by(main_user_id=specific_response.id).count()
#
#             age = ''
#             if specific_response.age is not None and specific_response.age != "0000-00-00":
#                 birthdate_datetime = datetime.combine(specific_response.age, datetime.min.time())
#                 age = (datetime.utcnow() - birthdate_datetime).days // 365
#
#             response_dict = {'user_id': str(specific_response.id),
#                              'user_name': specific_response.fullname,
#                              'user_image': specific_response.image_path,
#                              'state': specific_response.state,
#                              'city': specific_response.city,
#                              'badge': badge,
#                              'matches_count': count_value,
#                              'about_me': specific_response.about_me if specific_response.about_me is not None else '',
#                              'college': college,
#                              'sexuality': sexuality,
#                              'relationship_status': relationship_status,
#                              'looking_for': looking_for,
#                              'total_liked_Recommendation': str(total_liked_Recommendation),
#                              'total_liked_questions_answer': str(total_liked_questions_answer),
#                              'total_review_likes_count': total_review_likes_count,
#                              'total_followers': str(total_followers),
#                              'total_status_likes': str(sum(total_status_likes)),
#                              'total_profile_review_like': str(get_approved_reviews_likes),
#                              'total_user_photos_likes': str(total_user_photos_likes),
#                              'new_bio': specific_response.new_bio if specific_response.new_bio is not None else '',
#                              'age': str(age)
#
#                              }
#             response_list.append(response_dict)
#
#     has_next = user_data.has_next  # Check if there is a next page
#     total_pages = user_data.pages  # Total number of pages
#
#     # Pagination information
#     pagination_info = {
#         "current_page": page,
#         "has_next": has_next,
#         "per_page": per_page,
#         "total_pages": total_pages,
#     }
#
#     if len(response_list) > 0:
#         # sorted_list = sorted(response_list, key=lambda x: x['matches_count'], reverse=True)
#         return jsonify({'status': 1, 'data': response_list, 'messege': 'Sucess', 'pagination': pagination_info,
#                         'total_matches_count': str(user_data_count)})
#     else:
#         return jsonify({'status': 1, 'data': [], 'messege': 'You have zero matches. Click on Save to get started',
#                         'pagination_info': pagination_info, 'total_matches_count': str(user_data_count)})

@user_view_v5.route('/search_nearby_user', methods=['POST'])
@token_required
def search_nearby_user(active_user):

    data = request.get_json()
    lat = data.get('lat')
    long = data.get('long')
    gender = data.get('gender')
    looking_for = data.get('looking_for')
    miles = data.get('miles')

    if not lat:
        return jsonify({'status': 0,'messege': 'Latitude is required'})
    if not long:
        return jsonify({'status': 0,'messege': 'Longitude is required'})

    active_user.latitude = lat
    active_user.longitude = long
    db.session.commit()

    max_distance_miles = 1000
    earth_radius_km = 6371  # Earth's radius in KM
    if miles and miles != "":
        max_distance_miles = int(miles)

    # Validate user coordinates
    if not active_user.latitude or not active_user.longitude:
        return jsonify({'status': 0, 'messege': 'No user found, your lat/long is empty'}), 400

    lat1 = float(active_user.latitude)
    lon1 = float(active_user.longitude)
    # Debugging
    print("User Latitude:", lat1)
    print("User Longitude:", lon1)

    # Haversine formula using SQLAlchemy
    distance_expr = (
        earth_radius_km * 2 * func.asin(
            func.sqrt(
                func.pow(func.sin(func.radians(cast(User.latitude, Float) - lat1) / 2), 2) +
                func.cos(func.radians(lat1)) * func.cos(func.radians(cast(User.latitude, Float))) *
                func.pow(func.sin(func.radians(cast(User.longitude, Float) - lon1) / 2), 2)
            )
        ) * 0.621371  # Convert KM to miles
    )

    # Query nearby users
    query = db.session.query(
        User.id,
        User.image_path,
        User.latitude,
        User.longitude,
        User.fullname,
        distance_expr.label("distance_miles")
    ).filter(
        User.id != active_user.id,
        User.deleted == False,
        User.is_block == False,
        User.latitude.isnot(None),
        User.longitude.isnot(None),
        distance_expr <= max_distance_miles
    )

    if gender:
        query = query.filter(User.gender == gender)

    if looking_for:

        if looking_for == "Friendship":
            validate_looking_for_friends = ["Here for friends","Friends"]
            query = query.filter(User.looking_for.in_(validate_looking_for_friends))

        elif looking_for == "Dating":
            validate_looking_for = "Here for dating"
            query = query.filter(User.looking_for == validate_looking_for)

        elif looking_for == "Both":
            validate_looking_for = "Here for friends and dating"
            query = query.filter(User.looking_for == validate_looking_for)

        else:
            return jsonify({'status': 0,'messege': 'Invalid looking for'})

    users = query.order_by(distance_expr).all()

    # Print SQL query for debugging
    #print(str(users.statement.compile(db.engine, compile_kwargs={"literal_binds": True})))

    # Format response
    nearby_users = [
        {"user_id": user.id, "user_image": user.image_path,"lat": user.latitude,"long": user.longitude,'username': user.fullname, "distance_miles": str(round(user.distance_miles, 2)) + ' ' + 'miles away'}
        for user in users
    ]

    print('active_usersssssssssssssssssssss',active_user)

    return jsonify({"status": 1, "messege": "Success", "nearby_users": nearby_users}), 200

# @user_view_v5.route('/search_nearby_user', methods=['POST'])
# @token_required
# def search_nearby_user(active_user):
#     max_distance_miles = 40
#     nearby_users = []
#
#     if active_user.latitude == None and active_user.longitude == None:
#         return jsonify({'status': 0,'messege': 'No user found your lat long is empty'})
#
#     users = User.query.filter(User.deleted==False, User.is_block==False,User.latitude != None,User.longitude != None).all()
#
#     for user in users:
#         # if not user.latitude or not user.longitude:
#         #     continue
#
#         lat1, lon1, lat2, lon2 = map(radians, [
#             float(active_user.latitude), float(active_user.longitude),
#             float(user.latitude), float(user.longitude)
#         ])
#
#         # Haversine formula
#         dlon = lon2 - lon1
#         dlat = lat2 - lat1
#         a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
#         c = 2 * asin(sqrt(a))
#         km = 6371 * c  # Radius of Earth in kilometers
#         miles = km * 0.621371  # Convert km to miles
#
#         if miles <= max_distance_miles:
#             nearby_users.append({
#                 "id": user.id,
#                 "name": user.name,
#                 "distance_miles": round(miles, 2)
#             })
#
#     nearby_users.sort(key=lambda x: x["distance_miles"])
#
#     return jsonify({"nearby_users": nearby_users}), 200

@user_view_v5.route('/feed_repost', methods=['POST'])
@token_required
def feed_repost(active_user):
    data = request.get_json()

    if not data:
        return jsonify({'status': 0,'messege': 'Json is empty'})

    feed_id = data.get('feed_id')
    if not feed_id:
        return jsonify({'status': 0,'messege': 'Please select feed first'})

    check_feed_data = Feed.query.filter(Feed.id == feed_id,Feed.user_id != active_user.id).first()
    if not check_feed_data:
        return jsonify({'status': 0,'messege': 'Invalid data'})

    add_repost = Feed(feed_type = 'feed',is_repost=True,repost_feed_id=check_feed_data.id,user_id = active_user.id,created_time=datetime.utcnow())
    db.session.add(add_repost)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Reposted successfully'})

# @user_view_v5.route('/group_chat_list', methods=['POST'])
# @token_required
# def group_chat_list(active_user):
#     data = request.get_json()
#
#     if not data:
#         return jsonify({'status': 0,'messege': 'Json is empty'})
#
#     page = int(data.get('page', 1))
#     per_page = 10
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     included_things_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
#         SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
#     ).subquery()
#
#     things_query = db.session.query(
#         CreatedThingsCommunity.id, CreatedThingsCommunity.link, CreatedThingsCommunity.city,
#         CreatedThingsCommunity.state,
#         CreatedThingsCommunity.community_name,
#         func.count(SavedThingsCommunity.id).label('saved_count')
#     ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
#         join(User, SavedThingsCommunity.user_id == User.id). \
#         filter(User.deleted == False,User.is_block == False,
#                SavedThingsCommunity.user_id.not_in(blocked_user_ids),
#                SavedThingsCommunity.user_id.not_in(blocked_by_user_ids),
#                SavedThingsCommunity.created_id.in_(included_things_created_ids)). \
#         group_by(CreatedThingsCommunity.id)
#
#
#     included_places_created_ids = db.session.query(SavedCommunity.created_id).filter(
#         SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
#     ).subquery()
#
#     # Main query
#     places_query = db.session.query(
#         CreatedCommunity.id,
#         CreatedCommunity.link,
#         CreatedCommunity.city,
#         CreatedCommunity.state,
#         CreatedCommunity.community_name,
#         func.count(SavedCommunity.id).label('saved_count')
#     ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
#         join(User, SavedCommunity.user_id == User.id). \
#         filter(
#         User.deleted == False,
#         User.is_block == False,
#         SavedCommunity.user_id.not_in(blocked_user_ids),
#         SavedCommunity.user_id.not_in(blocked_by_user_ids),
#         SavedCommunity.created_id.in_(included_places_created_ids)
#     ). \
#         group_by(CreatedCommunity.id)
#
#
#     created_places_data = places_query.paginate(page=page, per_page=per_page, error_out=False)
#     created_things_data = things_query.paginate(page=page, per_page=per_page, error_out=False)
#
#     community_data = []
#
#     if created_places_data.items:
#         print('created_data.items', created_places_data.items)
#         for id, link, city, state, community_name, count in created_places_data.items:
#
#             dict = {
#                     'id': id,
#                     'group_name': community_name,
#                 'type': 'places'
#                     }
#             community_data.append(dict)
#
#     if created_things_data.items:
#         print('created_data.items', created_things_data.items)
#         for id, link, city, state, community_name, count in created_things_data.items:
#
#             dict = {
#                     'id': id,
#                     'group_name': community_name,
#                 'type': 'things'
#                     }
#             community_data.append(dict)
#
#     # Pagination metadata
#     pagination_info = {
#             "current_page": page,
#             "per_page": per_page,
#             "total_pages": max(created_places_data.pages, created_things_data.pages),
#             "has_next": created_places_data.has_next or created_things_data.has_next,
#         }
#
#     return jsonify({'status': 1, 'messege': 'Success', 'chat_list': group_chat_list,'pagination_info': pagination_info})

# i comment this on 15/04/2024
# @user_view_v5.route('/group_chat_list', methods=['POST'])
# @token_required
# def group_chat_list(active_user):
#     search_text = request.json.get('search_text') if request.json else None
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     included_things_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
#         SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
#     ).subquery()
#
#     # things_query = db.session.query(
#     #     CreatedThingsCommunity.id, CreatedThingsCommunity.link, CreatedThingsCommunity.city,
#     #     CreatedThingsCommunity.state, CreatedThingsCommunity.community_name,
#     #
#     #     CreatedThingsCommunity.category_id
#     #
#     # ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
#     #     join(User, SavedThingsCommunity.user_id == User.id). \
#     #     filter(
#     #     User.deleted == False, User.is_block == False,
#     #     SavedThingsCommunity.user_id.not_in(blocked_user_ids),
#     #     SavedThingsCommunity.user_id.not_in(blocked_by_user_ids),
#     #     SavedThingsCommunity.created_id.in_(included_things_created_ids)
#     # ).group_by(CreatedThingsCommunity.id)
#
#     things_query = db.session.query(
#         CreatedThingsCommunity.id,
#         CreatedThingsCommunity.link,
#         CreatedThingsCommunity.city,
#         CreatedThingsCommunity.state,
#         CreatedThingsCommunity.community_name,
#         CreatedThingsCommunity.category_id,
#         func.count(SavedThingsCommunity.user_id).label("member_count")
#     ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
#         join(User, SavedThingsCommunity.user_id == User.id). \
#         filter(
#         User.deleted == False,
#         User.is_block == False,
#         SavedThingsCommunity.user_id.notin_(blocked_user_ids),
#         SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
#         SavedThingsCommunity.created_id.in_(included_things_created_ids),
#         SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
#     ).group_by(CreatedThingsCommunity.id)
#
#     included_places_created_ids = db.session.query(SavedCommunity.created_id).filter(
#         SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
#     ).subquery()
#
#     # Main query
#     # places_query = db.session.query(
#     #     CreatedCommunity.id,
#     #     CreatedCommunity.link,
#     #     CreatedCommunity.city,
#     #     CreatedCommunity.state,
#     #     CreatedCommunity.community_name,
#     #
#     #     CreatedCommunity.category_id
#     #
#     # ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
#     #     join(User, SavedCommunity.user_id == User.id). \
#     #     filter(
#     #     User.deleted == False,
#     #     User.is_block == False,
#     #     SavedCommunity.user_id.not_in(blocked_user_ids),
#     #     SavedCommunity.user_id.not_in(blocked_by_user_ids),
#     #     SavedCommunity.created_id.in_(included_places_created_ids)
#     # ).group_by(CreatedCommunity.id)
#
#
#     places_query = db.session.query(
#         CreatedCommunity.id,
#         CreatedCommunity.link,
#         CreatedCommunity.city,
#         CreatedCommunity.state,
#         CreatedCommunity.community_name,
#         CreatedCommunity.category_id,
#         func.count(SavedCommunity.user_id).label("member_count")
#     ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
#         join(User, SavedCommunity.user_id == User.id). \
#         filter(
#         User.deleted == False,
#         User.is_block == False,
#         SavedCommunity.user_id.notin_(blocked_user_ids),
#         SavedCommunity.user_id.notin_(blocked_by_user_ids),
#         SavedCommunity.created_id.in_(included_places_created_ids),
#         SavedCommunity.user_id != active_user.id  # exclude current user from count
#     ).group_by(CreatedCommunity.id)
#
#     created_places_data = places_query.all()
#     created_things_data = things_query.all()
#
#     community_data = []
#
#     if search_text:
#
#         if len(created_places_data) > 0:
#             print('created_data.items placessss', created_places_data)
#             for id, link, city, state, community_name, category_id, member_count in created_places_data:
#
#                 if search_text.lower() in community_name.lower():
#                     group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
#
#                     category_name = ''
#                     category_data = Category.query.get(category_id)
#                     if category_data:
#                         category_name = category_data.category_name
#
#                     get_saved_users = (
#                         SavedCommunity.query
#                             .join(User, SavedCommunity.user_id == User.id)
#                             .filter(
#                             SavedCommunity.created_id == id,
#                             SavedCommunity.category_id == category_id,
#                             SavedCommunity.user_id != active_user.id,
#                             ~SavedCommunity.user_id.in_(blocked_user_ids),
#                             ~SavedCommunity.user_id.in_(blocked_by_user_ids),
#                             User.deleted == False,
#                             User.is_block == False
#                         )
#                             .limit(5)
#                             .all()
#                     )
#                     get_saved_user_list = []
#
#                     if len(get_saved_users) > 0:
#                         for j in get_saved_users:
#                             user_dict = {
#
#                                 'user_id': j.save_community.id,
#                                 'username': j.save_community.fullname,
#                                 'user_image': j.save_community.image_path
#                             }
#
#                             get_saved_user_list.append(user_dict)
#
#                     dict = {
#                         'id': id,
#                         'group_name': community_name,
#                         'type': 'places',
#                         'group_chat_count': group_chat_count,
#                         'member_count': member_count,
#                         'city': city if city is not None else '',
#                         'state': state if state is not None else '',
#                         'category_id': str(category_id),
#                         'category_name': category_name,
#                         'members_list': get_saved_user_list
#                     }
#
#                     community_data.append(dict)
#
#     else:
#         if len(created_places_data) > 0:
#             print('created_data.items placessss', created_places_data)
#             for id, link, city, state, community_name, category_id, member_count in created_places_data:
#
#                 group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
#
#                 category_name = ''
#                 category_data = Category.query.get(category_id)
#                 if category_data:
#                     category_name = category_data.category_name
#
#                 get_saved_users = (
#                     SavedCommunity.query
#                         .join(User, SavedCommunity.user_id == User.id)
#                         .filter(
#                         SavedCommunity.created_id == id,
#                         SavedCommunity.category_id == category_id,
#                         SavedCommunity.user_id != active_user.id,
#                         ~SavedCommunity.user_id.in_(blocked_user_ids),
#                         ~SavedCommunity.user_id.in_(blocked_by_user_ids),
#                         User.deleted == False,
#                         User.is_block == False
#                     )
#                         .limit(5)
#                         .all()
#                 )
#                 get_saved_user_list = []
#
#                 if len(get_saved_users) > 0:
#                     for j in get_saved_users:
#                         user_dict = {
#
#                             'user_id': j.save_community.id,
#                             'username': j.save_community.fullname,
#                             'user_image': j.save_community.image_path
#                         }
#
#                         get_saved_user_list.append(user_dict)
#
#                 dict = {
#                     'id': id,
#                     'group_name': community_name,
#                     'type': 'places',
#                     'group_chat_count': group_chat_count,
#                     'member_count': member_count,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'category_id': str(category_id),
#                     'category_name': category_name,
#                     'members_list': get_saved_user_list
#                 }
#
#                 community_data.append(dict)
#
#     if search_text:
#
#         if len(created_things_data) > 0:
#             print('created_data.items thingsss', created_things_data)
#             for id, link, city, state, community_name, category_id, member_count in created_things_data:
#
#                 if search_text.lower() in community_name.lower():
#
#                     group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
#
#                     category_name = ''
#                     category_data = ThingsCategory.query.get(category_id)
#                     if category_data:
#                         category_name = category_data.category_name
#
#                     get_saved_things_users = (
#                         SavedThingsCommunity.query
#                             .join(User, SavedThingsCommunity.user_id == User.id)
#                             .filter(
#                             SavedThingsCommunity.created_id == id,
#                             SavedThingsCommunity.category_id == category_id,
#                             SavedThingsCommunity.user_id != active_user.id,
#                             ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
#                             ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
#                             User.deleted == False,
#                             User.is_block == False
#                         )
#                             .limit(5)
#                             .all()
#                     )
#
#                     get_saved_things_user_list = []
#
#                     if len(get_saved_things_users) > 0:
#                         for j in get_saved_things_users:
#                             user_dict = {
#
#                                 'user_id': j.save_things_community.id,
#                                 'username': j.save_things_community.fullname,
#                                 'user_image': j.save_things_community.image_path
#                             }
#
#                             get_saved_things_user_list.append(user_dict)
#
#                     dict = {
#                         'id': id,
#                         'group_name': community_name,
#                         'type': 'things',
#                         'group_chat_count': group_chat_count,
#                         'member_count': member_count,
#                         'city': city if city is not None else '',
#                         'state': state if state is not None else '',
#                         'category_id': str(category_id),
#                         'category_name': category_name,
#                         'members_list': get_saved_things_user_list
#                     }
#
#                     community_data.append(dict)
#
#     else:
#         if len(created_things_data) > 0:
#             print('created_data.items thingsss', created_things_data)
#             for id, link, city, state, community_name, category_id, member_count in created_things_data:
#
#                 group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
#
#                 category_name = ''
#                 category_data = ThingsCategory.query.get(category_id)
#                 if category_data:
#                     category_name = category_data.category_name
#
#                 get_saved_things_users = (
#                     SavedThingsCommunity.query
#                         .join(User, SavedThingsCommunity.user_id == User.id)
#                         .filter(
#                         SavedThingsCommunity.created_id == id,
#                         SavedThingsCommunity.category_id == category_id,
#                         SavedThingsCommunity.user_id != active_user.id,
#                         ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
#                         ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
#                         User.deleted == False,
#                         User.is_block == False
#                     )
#                         .limit(5)
#                         .all()
#                 )
#
#                 get_saved_things_user_list = []
#
#                 if len(get_saved_things_users) > 0:
#                     for j in get_saved_things_users:
#                         user_dict = {
#
#                             'user_id': j.save_things_community.id,
#                             'username': j.save_things_community.fullname,
#                             'user_image': j.save_things_community.image_path
#                         }
#
#                         get_saved_things_user_list.append(user_dict)
#
#                 dict = {
#                     'id': id,
#                     'group_name': community_name,
#                     'type': 'things',
#                     'group_chat_count': group_chat_count,
#                     'member_count': member_count,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'category_id': str(category_id),
#                     'category_name': category_name,
#                     'members_list': get_saved_things_user_list
#                 }
#
#                 community_data.append(dict)
#
#     # all_data = sorted(community_data, key=lambda x: x['group_chat_count'], reverse=True)
#     all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)
#
#     return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})

@user_view_v5.route('/places_subcategory_bottom_page', methods=['POST'])
@token_required
def places_subcategory_bottom_page(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    places_query = db.session.query(
        CreatedCommunity.id,
        CreatedCommunity.link,
        CreatedCommunity.city,
        CreatedCommunity.state,
        CreatedCommunity.community_name,
        CreatedCommunity.category_id,
        func.count(SavedCommunity.user_id).label("member_count")
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        User.is_block == False,
        SavedCommunity.user_id.notin_(blocked_user_ids),
        SavedCommunity.user_id.notin_(blocked_by_user_ids),
        SavedCommunity.user_id != active_user.id  # exclude current user from count
    ).group_by(CreatedCommunity.id)

    created_places_data = places_query.paginate(page=page, per_page=per_page, error_out=False)

    has_next = created_places_data.has_next  # Check if there is a next page
    total_pages = created_places_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    community_data = []

    if len(created_places_data) > 0:
        print('created_data.items placessss', created_places_data)
        for id, link, city, state, community_name, category_id, member_count in created_places_data:

            group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
            check_saved = SavedCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
                                                             places_id=id).first()

            category_name = ''
            category_data = Category.query.get(category_id)
            if category_data:
                category_name = category_data.category_name

            # get_saved_users = (
            #     SavedCommunity.query
            #         .join(User, SavedCommunity.user_id == User.id)
            #         .filter(
            #         SavedCommunity.created_id == id,
            #         SavedCommunity.category_id == category_id,
            #         SavedCommunity.user_id != active_user.id,
            #         ~SavedCommunity.user_id.in_(blocked_user_ids),
            #         ~SavedCommunity.user_id.in_(blocked_by_user_ids),
            #         User.deleted == False,
            #         User.is_block == False
            #     )
            #         .limit(6)
            #         .all()
            # )
            # get_saved_user_list = []
            #
            # if len(get_saved_users) > 0:
            #     for j in get_saved_users:
            #         user_dict = {
            #
            #             'user_id': j.save_community.id,
            #             'username': j.save_community.fullname,
            #             'user_image': j.save_community.image_path
            #         }
            #
            #         get_saved_user_list.append(user_dict)

            dict = {
                'id': id,
                'group_name': community_name,
                'type': 'places',
                'group_chat_count': group_chat_count,
                'member_count': member_count,
                'city': city if city is not None else '',
                'state': state if state is not None else '',
                'category_id': str(category_id),
                'category_name': category_name,
                # 'members_list': get_saved_user_list,
                'is_recommendation': bool(have_recommendation),
                'link': link if link is not None else '',
                'community_id': str(id),
                'is_saved': bool(check_saved),
                'is_star': bool(check_star)
            }

            community_data.append(dict)

    return jsonify({'status': 1,'messege': 'Success','chat_list': community_data,'pagination_info': pagination_info})

@user_view_v5.route('/things_subcategory_bottom_page', methods=['POST'])
@token_required
def things_subcategory_bottom_page(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    things_query = db.session.query(
        CreatedThingsCommunity.id,
        CreatedThingsCommunity.link,
        CreatedThingsCommunity.city,
        CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        CreatedThingsCommunity.category_id,
        func.count(SavedThingsCommunity.user_id).label("member_count")
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        User.is_block == False,
        SavedThingsCommunity.user_id.notin_(blocked_user_ids),
        SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
        SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
    ).group_by(CreatedThingsCommunity.id)

    created_things_data = things_query.paginate(page=page, per_page=per_page, error_out=False)

    has_next = created_things_data.has_next  # Check if there is a next page
    total_pages = created_things_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    community_data = []

    if created_things_data.items:
        print('created_data.items thingsss', created_things_data.items)
        for id, link, city, state, community_name, category_id, member_count in created_things_data.items:

            group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
            check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
                                                             things_id=id).first()

            category_name = ''
            category_data = ThingsCategory.query.get(category_id)
            if category_data:
                category_name = category_data.category_name

            # get_saved_things_users = (
            #         SavedThingsCommunity.query
            #             .join(User, SavedThingsCommunity.user_id == User.id)
            #             .filter(
            #             SavedThingsCommunity.created_id == id,
            #             SavedThingsCommunity.category_id == category_id,
            #             SavedThingsCommunity.user_id != active_user.id,
            #             ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
            #             ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
            #             User.deleted == False,
            #             User.is_block == False
            #         )
            #             .limit(6)
            #             .all()
            #     )
            #
            # get_saved_things_user_list = []
            #
            # if len(get_saved_things_users) > 0:
            #     for j in get_saved_things_users:
            #         user_dict = {
            #
            #                 'user_id': j.save_things_community.id,
            #                 'username': j.save_things_community.fullname,
            #                 'user_image': j.save_things_community.image_path
            #             }
            #
            #         get_saved_things_user_list.append(user_dict)

            dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'things',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    # 'members_list': get_saved_things_user_list,
                    'is_recommendation': bool(have_recommendation),
                'link': link if link is not None else '',
                'community_id': str(id),
                'is_saved': bool(check_saved),
                    'is_star': bool(check_star)
                }

            community_data.append(dict)

    return jsonify({'status': 1, 'messege': 'Success', 'chat_list': community_data,
                    'pagination_info': pagination_info})

@user_view_v5.route('/all_subcategory_data', methods=['POST'])
@token_required
def all_subcategory_data(active_user):
    search_text = request.json.get('search_text') if request.json else None

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    things_query = db.session.query(
        CreatedThingsCommunity.id,
        CreatedThingsCommunity.link,
        CreatedThingsCommunity.city,
        CreatedThingsCommunity.state,
        CreatedThingsCommunity.community_name,
        CreatedThingsCommunity.category_id,
        func.count(SavedThingsCommunity.user_id).label("member_count")
    ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
        join(User, SavedThingsCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        User.is_block == False,
        SavedThingsCommunity.user_id.notin_(blocked_user_ids),
        SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
        SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
    ).group_by(CreatedThingsCommunity.id)


    if search_text:
        things_query = things_query.filter(or_(
            CreatedThingsCommunity.community_name.ilike(f"{search_text}%"),
            CreatedThingsCommunity.city.ilike(f"{search_text}%"),
            CreatedThingsCommunity.state.ilike(f"{search_text}%")
        ))

    places_query = db.session.query(
        CreatedCommunity.id,
        CreatedCommunity.link,
        CreatedCommunity.city,
        CreatedCommunity.state,
        CreatedCommunity.community_name,
        CreatedCommunity.category_id,
        func.count(SavedCommunity.user_id).label("member_count")
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        User.is_block == False,
        SavedCommunity.user_id.notin_(blocked_user_ids),
        SavedCommunity.user_id.notin_(blocked_by_user_ids),
        SavedCommunity.user_id != active_user.id  # exclude current user from count
    ).group_by(CreatedCommunity.id)


    if search_text:
        places_query = places_query.filter(or_(
                CreatedCommunity.community_name.ilike(f"{search_text}%"),
                CreatedCommunity.city.ilike(f"{search_text}%"),
                CreatedCommunity.state.ilike(f"{search_text}%")
            ))

    created_places_data = places_query.all()
    created_things_data = things_query.all()

    community_data = []

    if len(created_places_data) > 0:
        print('created_data.items placessss', created_places_data)
        for id, link, city, state, community_name, category_id, member_count in created_places_data:

            group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
            check_saved = SavedCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
                                                             places_id=id).first()

            category_name = ''
            category_data = Category.query.get(category_id)
            if category_data:
                category_name = category_data.category_name

            get_saved_users = (
                    SavedCommunity.query
                        .join(User, SavedCommunity.user_id == User.id)
                        .filter(
                        SavedCommunity.created_id == id,
                        SavedCommunity.category_id == category_id,
                        SavedCommunity.user_id != active_user.id,
                        ~SavedCommunity.user_id.in_(blocked_user_ids),
                        ~SavedCommunity.user_id.in_(blocked_by_user_ids),
                        User.deleted == False,
                        User.is_block == False
                    )
                        .limit(6)
                        .all()
                )
            get_saved_user_list = []

            if len(get_saved_users) > 0:
                for j in get_saved_users:
                    user_dict = {

                            'user_id': j.save_community.id,
                            'username': j.save_community.fullname,
                            'user_image': j.save_community.image_path
                        }

                    get_saved_user_list.append(user_dict)

            dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'places',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    'members_list': get_saved_user_list,
                    'is_recommendation': bool(have_recommendation),
                'link': link if link is not None else '',
                'community_id': str(id),
                'is_saved': bool(check_saved),
                    'is_star': bool(check_star)
                }

            community_data.append(dict)

    if len(created_things_data) > 0:
        print('created_data.items thingsss', created_things_data)
        for id, link, city, state, community_name, category_id, member_count in created_things_data:

            group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
            check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
                                                             things_id=id).first()

            category_name = ''
            category_data = ThingsCategory.query.get(category_id)
            if category_data:
                category_name = category_data.category_name

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

            dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'things',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    'members_list': get_saved_things_user_list,
                    'is_recommendation': bool(have_recommendation),
                'link': link if link is not None else '',
                'community_id': str(id),
                'is_saved': bool(check_saved),
                    'is_star': bool(check_star)
                }

            community_data.append(dict)

    all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)

    return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})

# @user_view_v5.route('/group_chat_list', methods=['POST'])
# @token_required
# def group_chat_list(active_user):
#     search_text = request.json.get('search_text') if request.json else None
#     # city = request.json.get('city') if request.json else None
#     # state = request.json.get('state') if request.json else None
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     included_things_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
#         SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
#     ).subquery()
#
#     things_query = db.session.query(
#         CreatedThingsCommunity.id,
#         CreatedThingsCommunity.link,
#         CreatedThingsCommunity.city,
#         CreatedThingsCommunity.state,
#         CreatedThingsCommunity.community_name,
#         CreatedThingsCommunity.category_id,
#         func.count(SavedThingsCommunity.user_id).label("member_count")
#     ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
#         join(User, SavedThingsCommunity.user_id == User.id). \
#         filter(
#         User.deleted == False,
#         User.is_block == False,
#         SavedThingsCommunity.user_id.notin_(blocked_user_ids),
#         SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
#         SavedThingsCommunity.created_id.in_(included_things_created_ids),
#         SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
#     ).group_by(CreatedThingsCommunity.id)
#
#     included_places_created_ids = db.session.query(SavedCommunity.created_id).filter(
#         SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
#     ).subquery()
#
#     if search_text:
#         things_query = things_query.filter(or_(
#             CreatedThingsCommunity.community_name.ilike(f"{search_text}%"),
#             CreatedThingsCommunity.city.ilike(f"{search_text}%"),
#             CreatedThingsCommunity.state.ilike(f"{search_text}%")
#         ))
#     # if city:
#     #     things_query = things_query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
#     # if state:
#     #     things_query = things_query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))
#
#     places_query = db.session.query(
#         CreatedCommunity.id,
#         CreatedCommunity.link,
#         CreatedCommunity.city,
#         CreatedCommunity.state,
#         CreatedCommunity.community_name,
#         CreatedCommunity.category_id,
#         func.count(SavedCommunity.user_id).label("member_count")
#     ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
#         join(User, SavedCommunity.user_id == User.id). \
#         filter(
#         User.deleted == False,
#         User.is_block == False,
#         SavedCommunity.user_id.notin_(blocked_user_ids),
#         SavedCommunity.user_id.notin_(blocked_by_user_ids),
#         SavedCommunity.created_id.in_(included_places_created_ids),
#         SavedCommunity.user_id != active_user.id  # exclude current user from count
#     ).group_by(CreatedCommunity.id)
#
#
#     if search_text:
#         places_query = places_query.filter(
#             or_(
#                 CreatedCommunity.community_name.ilike(f"{search_text}%"),
#                 CreatedCommunity.city.ilike(f"{search_text}%"),
#                 CreatedCommunity.state.ilike(f"{search_text}%")
#             )
#             )
#     # if city:
#     #     places_query = places_query.filter(CreatedCommunity.city.ilike(f"{city}%"))
#     # if state:
#     #     places_query = places_query.filter(CreatedCommunity.state.ilike(f"{state}%"))
#
#     created_places_data = places_query.all()
#     created_things_data = things_query.all()
#
#     community_data = []
#
#     if len(created_places_data) > 0:
#         print('created_data.items placessss', created_places_data)
#         for id, link, city, state, community_name, category_id, member_count in created_places_data:
#
#             group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
#             have_recommendation = PlacesRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
#             check_saved = SavedCommunity.query.filter_by(created_id = id,user_id = active_user.id).first()
#             check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
#                                                              places_id=id).first()
#
#             category_name = ''
#             category_data = Category.query.get(category_id)
#             if category_data:
#                 category_name = category_data.category_name
#
#             get_saved_users = (
#                     SavedCommunity.query
#                         .join(User, SavedCommunity.user_id == User.id)
#                         .filter(
#                         SavedCommunity.created_id == id,
#                         SavedCommunity.category_id == category_id,
#                         SavedCommunity.user_id != active_user.id,
#                         ~SavedCommunity.user_id.in_(blocked_user_ids),
#                         ~SavedCommunity.user_id.in_(blocked_by_user_ids),
#                         User.deleted == False,
#                         User.is_block == False
#                     )
#                         .limit(6)
#                         .all()
#                 )
#             get_saved_user_list = []
#
#             if len(get_saved_users) > 0:
#                 for j in get_saved_users:
#                     user_dict = {
#
#                             'user_id': j.save_community.id,
#                             'username': j.save_community.fullname,
#                             'user_image': j.save_community.image_path
#                         }
#
#                     get_saved_user_list.append(user_dict)
#
#             dict = {
#                     'id': id,
#                     'group_name': community_name,
#                     'type': 'places',
#                     'group_chat_count': group_chat_count,
#                     'member_count': member_count,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'category_id': str(category_id),
#                     'category_name': category_name,
#                     'members_list': get_saved_user_list,
#                     'is_recommendation': bool(have_recommendation),
#                 'link': link if link is not None else '',
#                 'community_id': str(id),
#                 'is_saved': bool(check_saved),
#                     'is_star': bool(check_star)
#                 }
#
#             community_data.append(dict)
#
#     if len(created_things_data) > 0:
#         print('created_data.items thingsss', created_things_data)
#         for id, link, city, state, community_name, category_id, member_count in created_things_data:
#
#             group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
#             have_recommendation = ThingsRecommendation.query.filter_by(community_id=id, user_id=active_user.id).first()
#             check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
#             check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
#                                                              things_id=id).first()
#
#             category_name = ''
#             category_data = ThingsCategory.query.get(category_id)
#             if category_data:
#                 category_name = category_data.category_name
#
#             get_saved_things_users = (
#                     SavedThingsCommunity.query
#                         .join(User, SavedThingsCommunity.user_id == User.id)
#                         .filter(
#                         SavedThingsCommunity.created_id == id,
#                         SavedThingsCommunity.category_id == category_id,
#                         SavedThingsCommunity.user_id != active_user.id,
#                         ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
#                         ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
#                         User.deleted == False,
#                         User.is_block == False
#                     )
#                         .limit(6)
#                         .all()
#                 )
#
#             get_saved_things_user_list = []
#
#             if len(get_saved_things_users) > 0:
#                 for j in get_saved_things_users:
#                     user_dict = {
#
#                             'user_id': j.save_things_community.id,
#                             'username': j.save_things_community.fullname,
#                             'user_image': j.save_things_community.image_path
#                         }
#
#                     get_saved_things_user_list.append(user_dict)
#
#             dict = {
#                     'id': id,
#                     'group_name': community_name,
#                     'type': 'things',
#                     'group_chat_count': group_chat_count,
#                     'member_count': member_count,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'category_id': str(category_id),
#                     'category_name': category_name,
#                     'members_list': get_saved_things_user_list,
#                     'is_recommendation': bool(have_recommendation),
#                 'link': link if link is not None else '',
#                 'community_id': str(id),
#                 'is_saved': bool(check_saved),
#                     'is_star': bool(check_star)
#                 }
#
#             community_data.append(dict)
#
#     all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)
#
#     return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})

@user_view_v5.route('/subcategory_trending_page', methods=['POST'])
@token_required
def subcategory_trending_page(active_user):
    tab = request.json.get('tab', 0)
    category_id = request.json.get('category_id')

    if tab is None:
        return jsonify({'status': 0, 'messege': 'Please select tab'})

    if not category_id:
        return jsonify({'status': 0, 'messege': 'Please select category first'})

    search_text = request.json.get('search_text') if request.json else None
    city = request.json.get('city') if request.json else None
    state = request.json.get('state') if request.json else None

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    if tab == 1:

        get_things_category = ThingsCategory.query.get(category_id)
        if not get_things_category:
            return jsonify({'status': 0,'messege': 'Invalid category'})

        things_query = db.session.query(
            CreatedThingsCommunity.id,
            CreatedThingsCommunity.link,
            CreatedThingsCommunity.city,
            CreatedThingsCommunity.state,
            CreatedThingsCommunity.community_name,
            CreatedThingsCommunity.category_id,
            func.count(SavedThingsCommunity.user_id).label("member_count")
        ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
            join(User, SavedThingsCommunity.user_id == User.id). \
            filter(
            User.deleted == False,
            User.is_block == False,
            SavedThingsCommunity.user_id.notin_(blocked_user_ids),
            SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
            SavedThingsCommunity.user_id != active_user.id,  # exclude current user from count
        CreatedThingsCommunity.category_id == category_id

        ).group_by(CreatedThingsCommunity.id)

        # if search_text:
        #     things_query = things_query.filter(or_(
        #         CreatedThingsCommunity.community_name.ilike(f"{search_text}%"),
        #         CreatedThingsCommunity.city.ilike(f"{search_text}%"),
        #         CreatedThingsCommunity.state.ilike(f"{search_text}%")
        #     ))

        if search_text:
            things_query = things_query.filter(CreatedThingsCommunity.community_name.ilike(f"{search_text}%"))

        if city:
            things_query = things_query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
        if state:
            things_query = things_query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))

        created_things_data = things_query.all()

        community_data = []

        if len(created_things_data) > 0:
            print('created_data.items thingsss', created_things_data)
            for id, link, city, state, community_name, category_id, member_count in created_things_data:

                group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
                have_recommendation = ThingsRecommendation.query.filter_by(community_id=id,
                                                                           user_id=active_user.id).first()
                check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
                check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
                                                                 things_id=id).first()

                category_name = ''
                category_data = ThingsCategory.query.get(category_id)
                if category_data:
                    category_name = category_data.category_name

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

                dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'things',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    'members_list': get_saved_things_user_list,
                    'is_recommendation': bool(have_recommendation),
                    'link': link if link is not None else '',
                    'community_id': str(id),
                    'is_saved': bool(check_saved),
                    'is_star': bool(check_star)
                }

                community_data.append(dict)

        all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)

        return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})

    elif tab == 0:

        get_places_category = Category.query.get(category_id)
        if not get_places_category:
            return jsonify({'status': 0, 'messege': 'Invalid category'})

        places_query = db.session.query(
            CreatedCommunity.id,
            CreatedCommunity.link,
            CreatedCommunity.city,
            CreatedCommunity.state,
            CreatedCommunity.community_name,
            CreatedCommunity.category_id,
            func.count(SavedCommunity.user_id).label("member_count")
        ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
            join(User, SavedCommunity.user_id == User.id). \
            filter(
            User.deleted == False,
            User.is_block == False,
            SavedCommunity.user_id.notin_(blocked_user_ids),
            SavedCommunity.user_id.notin_(blocked_by_user_ids),
            SavedCommunity.user_id != active_user.id,  # exclude current user from count
            CreatedCommunity.category_id == category_id
        ).group_by(CreatedCommunity.id)

        # if search_text:
        #     places_query = places_query.filter(or_(
        #         CreatedCommunity.community_name.ilike(f"{search_text}%"),
        #         CreatedCommunity.city.ilike(f"{search_text}%"),
        #         CreatedCommunity.state.ilike(f"{search_text}%")
        #     ))


        if search_text:
            places_query = places_query.filter(CreatedCommunity.community_name.ilike(f"{search_text}%"))

        if city:
            places_query = places_query.filter(CreatedCommunity.city.ilike(f"{city}%"))
        if state:
            places_query = places_query.filter(CreatedCommunity.state.ilike(f"{state}%"))

        created_places_data = places_query.all()

        community_data = []

        if len(created_places_data) > 0:
            print('created_data.items placessss', created_places_data)
            for id, link, city, state, community_name, category_id, member_count in created_places_data:

                group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
                have_recommendation = PlacesRecommendation.query.filter_by(community_id=id,
                                                                           user_id=active_user.id).first()
                check_saved = SavedCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
                check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
                                                                 places_id=id).first()

                category_name = ''
                category_data = Category.query.get(category_id)
                if category_data:
                    category_name = category_data.category_name

                get_saved_users = (
                    SavedCommunity.query
                        .join(User, SavedCommunity.user_id == User.id)
                        .filter(
                        SavedCommunity.created_id == id,
                        SavedCommunity.category_id == category_id,
                        SavedCommunity.user_id != active_user.id,
                        ~SavedCommunity.user_id.in_(blocked_user_ids),
                        ~SavedCommunity.user_id.in_(blocked_by_user_ids),
                        User.deleted == False,
                        User.is_block == False
                    )
                        .limit(6)
                        .all()
                )
                get_saved_user_list = []

                if len(get_saved_users) > 0:
                    for j in get_saved_users:
                        user_dict = {

                            'user_id': j.save_community.id,
                            'username': j.save_community.fullname,
                            'user_image': j.save_community.image_path
                        }

                        get_saved_user_list.append(user_dict)

                dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'places',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    'members_list': get_saved_user_list,
                    'is_recommendation': bool(have_recommendation),
                    'link': link if link is not None else '',
                    'community_id': str(id),
                    'is_saved': bool(check_saved),
                    'is_star': bool(check_star)
                }

                community_data.append(dict)

        all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)

        return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})

    else:
        return jsonify({'status': 0, 'messege': 'Invalid tab'})

@user_view_v5.route('/group_chat_notify_on_off', methods=['POST'])
@token_required
def group_chat_notify_on_off(active_user):

    type = request.json.get("type")
    community_id = request.json.get("id")

    if not type:
        return jsonify({'status': 0,'messege': 'Community type not found.'})
    if not community_id:
        return jsonify({'status': 0,'messege': 'Please select word first.'})

    if type == 'places':
        check_exists = GroupChatNotificationOnOff.query.filter_by(type =type,places_created_id=community_id,user_id=active_user.id).first()

        if check_exists:
            db.session.delete(check_exists)
            db.session.commit()

            return jsonify({'status': 1,'messsege': 'Notification on successfully','is_notify': True})

        else:
            add_data = GroupChatNotificationOnOff(type =type,places_created_id=community_id,user_id=active_user.id)
            db.session.add(add_data)
            db.session.commit()

            return jsonify({'status': 1, 'messsege': 'Notification off successfully', 'is_notify': False})

    elif type == 'things':
        check_exists = GroupChatNotificationOnOff.query.filter_by(type=type, things_created_id=community_id,
                                                                  user_id=active_user.id).first()

        if check_exists:
            db.session.delete(check_exists)
            db.session.commit()

            return jsonify({'status': 1, 'messsege': 'Notification on successfully', 'is_notify': True})

        else:
            add_data = GroupChatNotificationOnOff(type=type, things_created_id=community_id, user_id=active_user.id)
            db.session.add(add_data)
            db.session.commit()

            return jsonify({'status': 1, 'messsege': 'Notification off successfully', 'is_notify': False})

    else:
        return jsonify({'status': 0,'messege': 'Invalid type'})

# latest code 12_12_2025

# @user_view_v5.route('/group_chat_list', methods=['POST'])
# @token_required
# def group_chat_list(active_user):
#     tab = request.json.get('tab', 0)
#
#     if tab is None:
#         return jsonify({'status': 0, 'messege': 'Please select tab'})
#
#     search_text = request.json.get('search_text') if request.json else None
#     # city = request.json.get('city') if request.json else None
#     # state = request.json.get('state') if request.json else None
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     if tab == 1:
#
#         included_things_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
#             SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
#         ).subquery()
#
#         things_query = db.session.query(
#             CreatedThingsCommunity.id,
#             CreatedThingsCommunity.link,
#             CreatedThingsCommunity.city,
#             CreatedThingsCommunity.state,
#             CreatedThingsCommunity.community_name,
#             CreatedThingsCommunity.category_id,
#             func.count(SavedThingsCommunity.user_id).label("member_count")
#         ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
#             join(User, SavedThingsCommunity.user_id == User.id). \
#             filter(
#             User.deleted == False,
#             User.is_block == False,
#             SavedThingsCommunity.user_id.notin_(blocked_user_ids),
#             SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
#             SavedThingsCommunity.created_id.in_(included_things_created_ids),
#             SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
#         ).group_by(CreatedThingsCommunity.id)
#
#         if search_text:
#             things_query = things_query.filter(or_(
#                 CreatedThingsCommunity.community_name.ilike(f"{search_text}%"),
#                 CreatedThingsCommunity.city.ilike(f"{search_text}%"),
#                 CreatedThingsCommunity.state.ilike(f"{search_text}%")
#             ))
#
#             # if city:
#             # things_query = things_query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
#             # if state:
#             # things_query = things_query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))
#
#         created_things_data = things_query.all()
#
#         community_data = []
#
#         if len(created_things_data) > 0:
#             print('created_data.items thingsss', created_things_data)
#             for id, link, city, state, community_name, category_id, member_count in created_things_data:
#
#                 is_highlight = False
#
#                 check_visit = VisitGroupComments.query.filter(VisitGroupComments.things_created_id == id,
#                                                               VisitGroupComments.user_id == active_user.id,
#                                                               VisitGroupComments.type == 'things').order_by(
#                     VisitGroupComments.id.desc()).first()
#
#                 check_comment = GroupComments.query.filter(GroupComments.things_created_id == id,
#                                                            GroupComments.type == 'things',
#                                                            GroupComments.user_id != active_user.id).order_by(
#                     GroupComments.id.desc()).first()
#
#                 check_latest_comment = GroupComments.query.filter(GroupComments.things_created_id == id,
#                                                                   GroupComments.type == 'things').order_by(
#                     GroupComments.id.desc()).first()
#
#                 latest_comment = ""
#
#                 if check_latest_comment:
#                     latest_comment = check_latest_comment.comment
#
#                 if check_comment:
#                     if not check_visit:
#                         is_highlight = True
#
#                     else:
#                         if not check_visit.visit_time > check_comment.created_time:
#                             is_highlight = True
#
#                 group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
#                 have_recommendation = ThingsRecommendation.query.filter_by(community_id=id,
#                                                                            user_id=active_user.id).first()
#                 check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
#                 check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
#                                                                  things_id=id).first()
#
#                 check_exists = GroupChatNotificationOnOff.query.filter_by(type="things", things_created_id=id,
#                                                                           user_id=active_user.id).first()
#
#                 is_notify = True
#
#                 if check_exists:
#                     is_notify = False
#
#                 category_name = ''
#                 category_data = ThingsCategory.query.get(category_id)
#                 if category_data:
#                     category_name = category_data.category_name
#
#                 get_saved_things_users = (
#                     SavedThingsCommunity.query
#                         .join(User, SavedThingsCommunity.user_id == User.id)
#                         .filter(
#                         SavedThingsCommunity.created_id == id,
#                         SavedThingsCommunity.category_id == category_id,
#                         SavedThingsCommunity.user_id != active_user.id,
#                         ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
#                         ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
#                         User.deleted == False,
#                         User.is_block == False
#                     )
#                         .limit(1)
#                         .all()
#                 )
#
#                 get_saved_things_user_list = []
#
#                 if len(get_saved_things_users) > 0:
#                     for j in get_saved_things_users:
#                         user_dict = {
#
#                             'user_id': j.save_things_community.id,
#                             'username': j.save_things_community.fullname,
#                             'user_image': j.save_things_community.image_path
#                         }
#
#                         get_saved_things_user_list.append(user_dict)
#
#                 dict = {
#                     'id': id,
#                     'group_name': community_name,
#                     'type': 'things',
#                     'group_chat_count': group_chat_count,
#                     'member_count': member_count,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'category_id': str(category_id),
#                     'category_name': category_name,
#                     'members_list': get_saved_things_user_list,
#                     'is_recommendation': bool(have_recommendation),
#                     'link': link if link is not None else '',
#                     'community_id': str(id),
#                     'is_saved': bool(check_saved),
#                     'is_star': bool(check_star),
#                     'is_notify': is_notify,
#                     'is_highlight': is_highlight,
#                     'latest_comment': latest_comment
#                 }
#
#                 community_data.append(dict)
#
#         all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)
#
#         return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})
#
#     elif tab == 0:
#
#         included_places_created_ids = db.session.query(SavedCommunity.created_id).filter(
#             SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
#         ).subquery()
#
#         places_query = db.session.query(
#             CreatedCommunity.id,
#             CreatedCommunity.link,
#             CreatedCommunity.city,
#             CreatedCommunity.state,
#             CreatedCommunity.community_name,
#             CreatedCommunity.category_id,
#             func.count(SavedCommunity.user_id).label("member_count")
#         ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
#             join(User, SavedCommunity.user_id == User.id). \
#             filter(
#             User.deleted == False,
#             User.is_block == False,
#             SavedCommunity.user_id.notin_(blocked_user_ids),
#             SavedCommunity.user_id.notin_(blocked_by_user_ids),
#             SavedCommunity.created_id.in_(included_places_created_ids),
#             SavedCommunity.user_id != active_user.id  # exclude current user from count
#         ).group_by(CreatedCommunity.id)
#
#         if search_text:
#             places_query = places_query.filter(or_(
#                 CreatedCommunity.community_name.ilike(f"{search_text}%"),
#                 CreatedCommunity.city.ilike(f"{search_text}%"),
#                 CreatedCommunity.state.ilike(f"{search_text}%")
#             ))
#             # if city:
#             # places_query = places_query.filter(CreatedCommunity.city.ilike(f"{city}%"))
#             # if state:
#             # places_query = places_query.filter(CreatedCommunity.state.ilike(f"{state}%"))
#
#         created_places_data = places_query.all()
#
#         community_data = []
#
#         if len(created_places_data) > 0:
#             print('created_data.items placessss', created_places_data)
#             for id, link, city, state, community_name, category_id, member_count in created_places_data:
#
#                 is_highlight = False
#
#                 check_visit = VisitGroupComments.query.filter(VisitGroupComments.places_created_id == id,
#                                                               VisitGroupComments.user_id == active_user.id,
#                                                               VisitGroupComments.type == 'places').order_by(
#                     VisitGroupComments.id.desc()).first()
#
#                 check_comment = GroupComments.query.filter(GroupComments.places_created_id == id,
#                                                            GroupComments.type == 'places',
#                                                            GroupComments.user_id != active_user.id).order_by(
#                     GroupComments.id.desc()).first()
#
#                 check_latest_comment = GroupComments.query.filter(GroupComments.places_created_id == id,
#                                                                   GroupComments.type == 'places').order_by(
#                     GroupComments.id.desc()).first()
#
#                 latest_comment = ""
#
#                 if check_latest_comment:
#                     latest_comment = check_latest_comment.comment
#
#                 if check_comment:
#                     if not check_visit:
#                         is_highlight = True
#
#                     else:
#                         if not check_visit.visit_time > check_comment.created_time:
#                             is_highlight = True
#
#                 group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
#                 have_recommendation = PlacesRecommendation.query.filter_by(community_id=id,
#                                                                            user_id=active_user.id).first()
#                 check_saved = SavedCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
#                 check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
#                                                                  places_id=id).first()
#                 check_exists = GroupChatNotificationOnOff.query.filter_by(type="places", places_created_id=id,
#                                                                           user_id=active_user.id).first()
#
#                 is_notify = True
#
#                 if check_exists:
#                     is_notify = False
#
#                 category_name = ''
#                 category_data = Category.query.get(category_id)
#                 if category_data:
#                     category_name = category_data.category_name
#
#                 get_saved_users = (
#                     SavedCommunity.query
#                         .join(User, SavedCommunity.user_id == User.id)
#                         .filter(
#                         SavedCommunity.created_id == id,
#                         SavedCommunity.category_id == category_id,
#                         SavedCommunity.user_id != active_user.id,
#                         ~SavedCommunity.user_id.in_(blocked_user_ids),
#                         ~SavedCommunity.user_id.in_(blocked_by_user_ids),
#                         User.deleted == False,
#                         User.is_block == False
#                     )
#                         .limit(1)
#                         .all()
#                 )
#                 get_saved_user_list = []
#
#                 if len(get_saved_users) > 0:
#                     for j in get_saved_users:
#                         user_dict = {
#
#                             'user_id': j.save_community.id,
#                             'username': j.save_community.fullname,
#                             'user_image': j.save_community.image_path
#                         }
#
#                         get_saved_user_list.append(user_dict)
#
#                 dict = {
#                     'id': id,
#                     'group_name': community_name,
#                     'type': 'places',
#                     'group_chat_count': group_chat_count,
#                     'member_count': member_count,
#                     'city': city if city is not None else '',
#                     'state': state if state is not None else '',
#                     'category_id': str(category_id),
#                     'category_name': category_name,
#                     'members_list': get_saved_user_list,
#                     'is_recommendation': bool(have_recommendation),
#                     'link': link if link is not None else '',
#                     'community_id': str(id),
#                     'is_saved': bool(check_saved),
#                     'is_star': bool(check_star),
#                     'is_notify': is_notify,
#                     'is_highlight': is_highlight,
#                     'latest_comment': latest_comment
#
#                 }
#
#                 community_data.append(dict)
#
#         all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)
#
#         return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})
#
#     else:
#         return jsonify({'status': 0, 'messege': 'Invalid tab'})


@user_view_v5.route('/group_chat_list', methods=['POST'])
@token_required
def group_chat_list(active_user):
    data = request.get_json()

    page = int(data.get('page', 1))
    per_page = 30

    search_text = request.json.get('search_text') if request.json else None

    # city = request.json.get('city') if request.json else None
    # state = request.json.get('state') if request.json else None

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    # if tab == 1:
    #
    #     included_things_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
    #         SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
    #     ).subquery()
    #
    #     things_query = db.session.query(
    #         CreatedThingsCommunity.id,
    #         CreatedThingsCommunity.link,
    #         CreatedThingsCommunity.city,
    #         CreatedThingsCommunity.state,
    #         CreatedThingsCommunity.community_name,
    #         CreatedThingsCommunity.category_id,
    #         func.count(SavedThingsCommunity.user_id).label("member_count")
    #     ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
    #         join(User, SavedThingsCommunity.user_id == User.id). \
    #         filter(
    #         User.deleted == False,
    #         User.is_block == False,
    #         SavedThingsCommunity.user_id.notin_(blocked_user_ids),
    #         SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
    #         SavedThingsCommunity.created_id.in_(included_things_created_ids),
    #         SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
    #     ).group_by(CreatedThingsCommunity.id)
    #
    #     if search_text:
    #         things_query = things_query.filter(or_(
    #             CreatedThingsCommunity.community_name.ilike(f"{search_text}%"),
    #             CreatedThingsCommunity.city.ilike(f"{search_text}%"),
    #             CreatedThingsCommunity.state.ilike(f"{search_text}%")
    #         ))
    #
    #         # if city:
    #         # things_query = things_query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
    #         # if state:
    #         # things_query = things_query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))
    #
    #     created_things_data = things_query.all()
    #
    #     community_data = []
    #
    #     if len(created_things_data) > 0:
    #         print('created_data.items thingsss', created_things_data)
    #         for id, link, city, state, community_name, category_id, member_count in created_things_data:
    #
    #             is_highlight = False
    #
    #             check_visit = VisitGroupComments.query.filter(VisitGroupComments.things_created_id == id,
    #                                                           VisitGroupComments.user_id == active_user.id,
    #                                                           VisitGroupComments.type == 'things').order_by(
    #                 VisitGroupComments.id.desc()).first()
    #
    #             check_comment = GroupComments.query.filter(GroupComments.things_created_id == id,
    #                                                        GroupComments.type == 'things',
    #                                                        GroupComments.user_id != active_user.id).order_by(
    #                 GroupComments.id.desc()).first()
    #
    #             check_latest_comment = GroupComments.query.filter(GroupComments.things_created_id == id,
    #                                                               GroupComments.type == 'things').order_by(
    #                 GroupComments.id.desc()).first()
    #
    #             latest_comment = ""
    #
    #             if check_latest_comment:
    #                 latest_comment = check_latest_comment.comment
    #
    #             if check_comment:
    #                 if not check_visit:
    #                     is_highlight = True
    #
    #                 else:
    #                     if not check_visit.visit_time > check_comment.created_time:
    #                         is_highlight = True
    #
    #             group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
    #             have_recommendation = ThingsRecommendation.query.filter_by(community_id=id,
    #                                                                        user_id=active_user.id).first()
    #             check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
    #             check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
    #                                                              things_id=id).first()
    #
    #             check_exists = GroupChatNotificationOnOff.query.filter_by(type="things", things_created_id=id,
    #                                                                       user_id=active_user.id).first()
    #
    #             is_notify = True
    #
    #             if check_exists:
    #                 is_notify = False
    #
    #             category_name = ''
    #             category_data = ThingsCategory.query.get(category_id)
    #             if category_data:
    #                 category_name = category_data.category_name
    #
    #             get_saved_things_users = (
    #                 SavedThingsCommunity.query
    #                     .join(User, SavedThingsCommunity.user_id == User.id)
    #                     .filter(
    #                     SavedThingsCommunity.created_id == id,
    #                     SavedThingsCommunity.category_id == category_id,
    #                     SavedThingsCommunity.user_id != active_user.id,
    #                     ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
    #                     ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids),
    #                     User.deleted == False,
    #                     User.is_block == False
    #                 )
    #                     .limit(1)
    #                     .all()
    #             )
    #
    #             get_saved_things_user_list = []
    #
    #             if len(get_saved_things_users) > 0:
    #                 for j in get_saved_things_users:
    #                     user_dict = {
    #
    #                         'user_id': j.save_things_community.id,
    #                         'username': j.save_things_community.fullname,
    #                         'user_image': j.save_things_community.image_path
    #                     }
    #
    #                     get_saved_things_user_list.append(user_dict)
    #
    #             dict = {
    #                 'id': id,
    #                 'group_name': community_name,
    #                 'type': 'things',
    #                 'group_chat_count': group_chat_count,
    #                 'member_count': member_count,
    #                 'city': city if city is not None else '',
    #                 'state': state if state is not None else '',
    #                 'category_id': str(category_id),
    #                 'category_name': category_name,
    #                 'members_list': get_saved_things_user_list,
    #                 'is_recommendation': bool(have_recommendation),
    #                 'link': link if link is not None else '',
    #                 'community_id': str(id),
    #                 'is_saved': bool(check_saved),
    #                 'is_star': bool(check_star),
    #                 'is_notify': is_notify,
    #                 'is_highlight': is_highlight,
    #                 'latest_comment': latest_comment
    #             }
    #
    #             community_data.append(dict)
    #
    #     all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)
    #
    #     return jsonify({'status': 1, 'messege': 'Success', 'chat_list': all_data})


    included_places_created_ids = db.session.query(SavedCommunity.created_id).filter(
            SavedCommunity.user_id == active_user.id, SavedCommunity.is_saved == True
        ).subquery()

    places_query = db.session.query(
        CreatedCommunity.id,
        CreatedCommunity.link,
        CreatedCommunity.city,
        CreatedCommunity.state,
        CreatedCommunity.community_name,
        CreatedCommunity.category_id,
        func.count(SavedCommunity.user_id).label("member_count")
    ).join(SavedCommunity, CreatedCommunity.id == SavedCommunity.created_id). \
        join(User, SavedCommunity.user_id == User.id). \
        filter(
        User.deleted == False,
        User.is_block == False,
        SavedCommunity.user_id.notin_(blocked_user_ids),
        SavedCommunity.user_id.notin_(blocked_by_user_ids),
        SavedCommunity.created_id.in_(included_places_created_ids),
        SavedCommunity.user_id != active_user.id  # exclude current user from count
    ).group_by(CreatedCommunity.id).order_by(func.count(SavedCommunity.user_id).desc())

    if search_text:
        places_query = places_query.filter(or_(
                CreatedCommunity.community_name.ilike(f"{search_text}%"),
                CreatedCommunity.city.ilike(f"{search_text}%"),
                CreatedCommunity.state.ilike(f"{search_text}%")
            ))
    # if city:
    # places_query = places_query.filter(CreatedCommunity.city.ilike(f"{city}%"))
    # if state:
    # places_query = places_query.filter(CreatedCommunity.state.ilike(f"{state}%"))

    created_places_data = places_query.paginate(page=page, per_page=per_page,error_out=False)

    has_next = created_places_data.has_next
    total_pages = created_places_data.pages

    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    community_data = []

    if created_places_data.items:
        for id, link, city, state, community_name, category_id, member_count in created_places_data.items:

            is_highlight = False

            check_visit = VisitGroupComments.query.filter(VisitGroupComments.places_created_id == id,
                                                              VisitGroupComments.user_id == active_user.id,
                                                              VisitGroupComments.type == 'places').order_by(
                VisitGroupComments.id.desc()).first()

            check_comment = GroupComments.query.filter(GroupComments.places_created_id == id,
                                                           GroupComments.type == 'places',
                                                           GroupComments.user_id != active_user.id).order_by(
                GroupComments.id.desc()).first()

            check_latest_comment = GroupComments.query.filter(GroupComments.places_created_id == id,
                                                                  GroupComments.type == 'places').order_by(
                GroupComments.id.desc()).first()

            latest_comment = ""

            if check_latest_comment:
                latest_comment = check_latest_comment.comment

            if check_comment:
                if not check_visit:
                    is_highlight = True

                else:
                    if not check_visit.visit_time > check_comment.created_time:
                        is_highlight = True

            group_chat_count = GroupChat.query.filter_by(places_created_id=id).count()
            have_recommendation = PlacesRecommendation.query.filter_by(community_id=id,
                                                                           user_id=active_user.id).first()
            check_saved = SavedCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='places',
                                                                 places_id=id).first()
            check_exists = GroupChatNotificationOnOff.query.filter_by(type="places", places_created_id=id,
                                                                          user_id=active_user.id).first()

            is_notify = True

            if check_exists:
                is_notify = False

            category_name = ''
            category_data = Category.query.get(category_id)
            if category_data:
                category_name = category_data.category_name

            get_saved_users = (
                    SavedCommunity.query
                        .join(User, SavedCommunity.user_id == User.id)
                        .filter(
                        SavedCommunity.created_id == id,
                        SavedCommunity.category_id == category_id,
                        SavedCommunity.user_id != active_user.id,
                        ~SavedCommunity.user_id.in_(blocked_user_ids),
                        ~SavedCommunity.user_id.in_(blocked_by_user_ids),
                        User.deleted == False,
                        User.is_block == False
                    )
                        .limit(1)
                        .all()
                )
            get_saved_user_list = []

            if len(get_saved_users) > 0:
                for j in get_saved_users:
                    user_dict = {

                            'user_id': j.save_community.id,
                            'username': j.save_community.fullname,
                            'user_image': j.save_community.image_path
                        }

                    get_saved_user_list.append(user_dict)

            dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'places',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    'members_list': get_saved_user_list,
                    'is_recommendation': bool(have_recommendation),
                    'link': link if link is not None else '',
                    'community_id': str(id),
                    'is_saved': bool(check_saved),
                    'is_star': bool(check_star),
                    'is_notify': is_notify,
                    'is_highlight': is_highlight,
                    'latest_comment': latest_comment

                }

            community_data.append(dict)

    # all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)

    return jsonify({'status': 1, 'messege': 'Success', 'chat_list': community_data,'pagination_info': pagination_info})


@user_view_v5.route('/things_group_chat_list', methods=['POST'])
@token_required
def things_group_chat_list(active_user):
    data = request.get_json()

    page = int(data.get('page', 1))
    per_page = 30

    search_text = request.json.get('search_text') if request.json else None

    # city = request.json.get('city') if request.json else None
    # state = request.json.get('state') if request.json else None

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]


    included_things_created_ids = db.session.query(SavedThingsCommunity.created_id).filter(
            SavedThingsCommunity.user_id == active_user.id, SavedThingsCommunity.is_saved == True
        ).subquery()

    things_query = db.session.query(
            CreatedThingsCommunity.id,
            CreatedThingsCommunity.link,
            CreatedThingsCommunity.city,
            CreatedThingsCommunity.state,
            CreatedThingsCommunity.community_name,
            CreatedThingsCommunity.category_id,
            func.count(SavedThingsCommunity.user_id).label("member_count")
        ).join(SavedThingsCommunity, CreatedThingsCommunity.id == SavedThingsCommunity.created_id). \
            join(User, SavedThingsCommunity.user_id == User.id). \
            filter(
            User.deleted == False,
            User.is_block == False,
            SavedThingsCommunity.user_id.notin_(blocked_user_ids),
            SavedThingsCommunity.user_id.notin_(blocked_by_user_ids),
            SavedThingsCommunity.created_id.in_(included_things_created_ids),
            SavedThingsCommunity.user_id != active_user.id  # exclude current user from count
        ).group_by(CreatedThingsCommunity.id).order_by(func.count(SavedThingsCommunity.user_id).desc())

    if search_text:
        things_query = things_query.filter(or_(
                CreatedThingsCommunity.community_name.ilike(f"{search_text}%"),
                CreatedThingsCommunity.city.ilike(f"{search_text}%"),
                CreatedThingsCommunity.state.ilike(f"{search_text}%")
            ))

    # if city:
        # things_query = things_query.filter(CreatedThingsCommunity.city.ilike(f"{city}%"))
    # if state:
        # things_query = things_query.filter(CreatedThingsCommunity.state.ilike(f"{state}%"))

    created_things_data = things_query.paginate(page=page, per_page=per_page,error_out=False)

    has_next = created_things_data.has_next
    total_pages = created_things_data.pages

    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    community_data = []

    if created_things_data.items:
        for id, link, city, state, community_name, category_id, member_count in created_things_data.items:

            is_highlight = False

            check_visit = VisitGroupComments.query.filter(VisitGroupComments.things_created_id == id,
                                                              VisitGroupComments.user_id == active_user.id,
                                                              VisitGroupComments.type == 'things').order_by(
                    VisitGroupComments.id.desc()).first()

            check_comment = GroupComments.query.filter(GroupComments.things_created_id == id,
                                                           GroupComments.type == 'things',
                                                           GroupComments.user_id != active_user.id).order_by(
                    GroupComments.id.desc()).first()

            check_latest_comment = GroupComments.query.filter(GroupComments.things_created_id == id,
                                                                  GroupComments.type == 'things').order_by(
                    GroupComments.id.desc()).first()

            latest_comment = ""

            if check_latest_comment:
                latest_comment = check_latest_comment.comment

            if check_comment:
                if not check_visit:
                    is_highlight = True

                else:
                    if not check_visit.visit_time > check_comment.created_time:
                        is_highlight = True

            group_chat_count = GroupChat.query.filter_by(things_created_id=id).count()
            have_recommendation = ThingsRecommendation.query.filter_by(community_id=id,
                                                                           user_id=active_user.id).first()
            check_saved = SavedThingsCommunity.query.filter_by(created_id=id, user_id=active_user.id).first()
            check_star = FavoriteSubCategory.query.filter_by(user_id=active_user.id, type='things',
                                                                 things_id=id).first()

            check_exists = GroupChatNotificationOnOff.query.filter_by(type="things", things_created_id=id,
                                                                          user_id=active_user.id).first()

            is_notify = True

            if check_exists:
                is_notify = False

            category_name = ''
            category_data = ThingsCategory.query.get(category_id)
            if category_data:
                category_name = category_data.category_name

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
                        .limit(1)
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

            dict = {
                    'id': id,
                    'group_name': community_name,
                    'type': 'things',
                    'group_chat_count': group_chat_count,
                    'member_count': member_count,
                    'city': city if city is not None else '',
                    'state': state if state is not None else '',
                    'category_id': str(category_id),
                    'category_name': category_name,
                    'members_list': get_saved_things_user_list,
                    'is_recommendation': bool(have_recommendation),
                    'link': link if link is not None else '',
                    'community_id': str(id),
                    'is_saved': bool(check_saved),
                    'is_star': bool(check_star),
                    'is_notify': is_notify,
                    'is_highlight': is_highlight,
                    'latest_comment': latest_comment
                }

            community_data.append(dict)

    # all_data = sorted(community_data, key=lambda x: x['member_count'], reverse=True)

    return jsonify({'status': 1, 'messege': 'Success', 'things_chat_list': community_data,'pagination_info': pagination_info})

@user_view_v5.route('/chat_list', methods=['POST'])
@token_required
def chat_list(active_user):
    data = request.get_json()

    if not data:
        return jsonify({'status': 0,'messege': 'Json is empty'})

    community_id = data.get('community_id')
    type = data.get('type')

    page = int(data.get('page', 1))
    per_page = 30

    if type == 'places':

        get_chat_data = GroupChat.query.filter_by(places_created_id = community_id).order_by(GroupChat.id.desc()).paginate(page=page, per_page=per_page,
                                                                                error_out=False)

        group_chat_list = []

        if get_chat_data.items:
            for i in get_chat_data.items:
                input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                chat_dict = {
                    'id': i.id,
                    'text': i.text if i.text is not None else '',
                    'image': i.image_path if i.image_path is not None else '',
                    'is_my_chat': False if i.user_id != active_user.id else True,
                    'created_time': output_date,
                    'user_id': i.user_id,
                    'username': i.chat_data.fullname,
                    'user_image': i.chat_data.image_path
                }
                group_chat_list.append(chat_dict)

        has_next = get_chat_data.has_next
        total_pages = get_chat_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify({'status': 1,'messege': 'Success','chat_list': group_chat_list,'pagination_info': pagination_info})

    elif type == 'things':

        get_chat_data = GroupChat.query.filter_by(things_created_id=community_id).order_by(
            GroupChat.id.desc()).paginate(page=page, per_page=per_page,
                                          error_out=False)

        group_chat_list = []

        if get_chat_data.items:
            for i in get_chat_data.items:
                input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
                output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                chat_dict = {
                    'id': i.id,
                    'text': i.text if i.text is not None else '',
                    'image': i.image_path if i.image_path is not None else '',
                    'is_my_chat': False if i.user_id != active_user.id else True,
                    'created_time': output_date,
                    'user_id': i.user_id,
                    'username': i.chat_data.fullname,
                    'user_image': i.chat_data.image_path
                }
                group_chat_list.append(chat_dict)

        has_next = get_chat_data.has_next
        total_pages = get_chat_data.pages

        pagination_info = {
            "current_page": page,
            "has_next": has_next,
            "per_page": per_page,
            "total_pages": total_pages,
        }

        return jsonify(
            {'status': 1, 'messege': 'Success', 'chat_list': group_chat_list, 'pagination_info': pagination_info})

    else:
        return jsonify({'status': 0,'messege': 'Invalid type'})

@user_view_v5.route('/create_group_chat', methods=['POST'])
@token_required
def create_group_chat(active_user):

    text = request.form.get('text')
    community_id = request.form.get('community_id')
    type = request.form.get('type')
    image = request.files.get('image')

    if not text and not image:
        return jsonify({'status': 0, 'messege': 'Please add inputs'})

    if not type and type == '':
        return jsonify({'status': 0,'messege': 'Please choose type between things and places'})

    if not community_id:
        return jsonify({'status': 0,'messege': 'Please select word first'})

    things_created_id = None
    places_created_id = None

    if type == 'things':
        get_things_community_data = CreatedThingsCommunity.query.get(community_id)
        if get_things_community_data:
            things_created_id = get_things_community_data.id
    elif type == 'places':
        get_places_community_data = CreatedCommunity.query.get(community_id)
        if get_places_community_data:
            places_created_id = get_places_community_data.id

    if things_created_id is None and places_created_id is None:
        return jsonify({'status': 0,'messege': 'Invalid data'})

    image_name = None
    image_path = None

    if image:
        file_path, picture = upload_photos(image)
        image_name = picture
        image_path = file_path

    add_group_chat_data = GroupChat(text = text,image_name=image_name,image_path=image_path,places_created_id=places_created_id,things_created_id=things_created_id,created_time=datetime.utcnow(),user_id = active_user.id,type=type)
    db.session.add(add_group_chat_data)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Chat created successfully'})

@user_view_v5.route('/delete_group_chat', methods=['POST'])
@token_required
def delete_group_chat(active_user):

    data = request.get_json()
    chat_id = data.get('chat_id')

    if not data:
        return jsonify({'status': 0,'messege': 'Please select chat first'})

    if not chat_id:
        return jsonify({'status': 0, 'messege': 'Please select chat'})

    get_chat_data = GroupChat.query.get(chat_id)
    if not get_chat_data:
        return jsonify({'status': 0,'messege': 'Invalid data'})

    if get_chat_data.image_path is not None:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=get_chat_data.image_name)

    db.session.delete(get_chat_data)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Chat deleted successfully'})

@user_view_v5.route('/user_videos', methods=['POST'])
@token_required
def user_videos(active_user):
    page = int(request.json.get('page', 1))
    user_id = request.json.get('user_id')
    per_page = 30

    if not user_id:
        return jsonify({'status': 0,'messege': 'Please select user'})

    my_videos_data = UserVideos.query.filter_by(user_id = user_id).order_by(UserVideos.id.desc()).paginate(page=page,
                                                 per_page=per_page,
                                                 error_out=False)

    has_next = my_videos_data.has_next
    total_pages = my_videos_data.pages

    # Prepare pagination info for response
    pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

    video_list = [ i.as_dict(active_user.id) for i in my_videos_data ]

    if len(video_list)>0:
        return jsonify({'status': 1, 'messege': 'Success','video_list': video_list,'pagination_info': pagination_info })
    else:
        return jsonify({'status': 0, 'messege': 'No videos added', 'video_list': [], 'pagination_info': pagination_info})

@user_view_v5.route('/my_videos', methods=['POST'])
@token_required
def my_videos(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    my_videos_data = UserVideos.query.filter_by(user_id = active_user.id).order_by(UserVideos.id.desc()).paginate(page=page,
                                                 per_page=per_page,
                                                 error_out=False)

    has_next = my_videos_data.has_next
    total_pages = my_videos_data.pages

    # Prepare pagination info for response
    pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

    video_list = [ i.as_dict(active_user.id) for i in my_videos_data ]

    if len(video_list)>0:
        return jsonify({'status': 1, 'messege': 'Success','video_list': video_list,'pagination_info': pagination_info })
    else:
        return jsonify({'status': 0, 'messege': 'No videos added', 'video_list': [], 'pagination_info': pagination_info})

@user_view_v5.route('/delete_my_videos', methods=['POST'])
@token_required
def delete_my_videos(active_user):
    video_id = request.json.get('video_id')
    if not video_id:
        return jsonify({'status': 0,'messege': 'Please select video'})

    get_video = UserVideos.query.filter_by(id = video_id,user_id=active_user.id).first()

    if get_video.thumbnail is not None:
        thumbnail_name = get_video.thumbnail.replace("https://frienddate-app.s3.amazonaws.com/", "")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=thumbnail_name)
    if get_video.video_path is not None:
        video_name = get_video.video_path.replace("https://frienddate-app.s3.amazonaws.com/", "")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=video_name)

    db.session.delete(get_video)
    db.session.commit()

@user_view_v5.route('/add_videos', methods=['POST'])
@token_required
def add_videos(active_user):

    content = request.files.get('content')

    if content and content.filename:
        type = 'video'
        video_name = secure_filename(content.filename)
        extension = os.path.splitext(video_name)[1]
        extension2 = os.path.splitext(video_name)[1][1:].lower()

        unique_name = secrets.token_hex(10)

        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            content.save(tmp.name)
            # Rewind the file pointer to the beginning of the video file
            tmp.seek(0)

            # Generate a thumbnail for the video
            clip = VideoFileClip(tmp.name)
            thumbnail_name = f"thumb_{unique_name}.jpg"
            clip.save_frame(thumbnail_name, t=1)  # Save the frame at 1 second as the thumbnail

            # Close the VideoFileClip object
            clip.reader.close()
            clip.audio.reader.close_proc()

            # Upload the thumbnail to S3
            with open(thumbnail_name, 'rb') as thumb:
                s3_client.upload_fileobj(thumb, S3_BUCKET, thumbnail_name,
                                         ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpeg'})
            thumbnail_path = f"https://{S3_BUCKET}.s3.amazonaws.com/{thumbnail_name}"
            print(f'Thumbnail URL: {thumbnail_path}')

            # Clean up the temporary thumbnail file
            os.remove(thumbnail_name)

        # Upload the original post (video or image)
        content.seek(0)  # Rewind the file pointer to the beginning

        content_type = f'video/{extension2}'
        x = secrets.token_hex(10)

        video_name = x + extension

        s3_client.upload_fileobj(content, S3_BUCKET, video_name,
                                 ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
        video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{video_name}"

        # Clean up the temporary video file after uploading
        try:
            os.remove(tmp.name)
            print('itssssssssssssssssss successsssssssssssssssssssss')
        except PermissionError as e:
            print(f"Error removing temporary file: {e}")
        print('video_url', video_url)

        add_videos = UserVideos(video_path = video_url,thumbnail = thumbnail_path,user_id = active_user.id)
        db.session.add(add_videos)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Video added successfully'})

    else:
        return jsonify({'status':0,'messege': 'Please provide video'})

@user_view_v5.route('/like_user_answer', methods=['POST'])
@token_required
def like_user_answer(active_user):
    answer_id = request.json.get('answer_id')
    if not answer_id:
        return jsonify({'status': 0,'messege': 'Please select answer for like'})
    get_user_answer = CategoryAns.query.get(answer_id)
    if not get_user_answer:
        return jsonify({'status': 0,'messege': 'Invalid answer'})

    check_like = LikeUserAnswer.query.filter_by(user_id = active_user.id,answer_id = answer_id).first()
    if check_like:
        db.session.delete(check_like)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully answer unliked'})
    else:
        add_like = LikeUserAnswer(user_id = active_user.id, answer_id = answer_id,main_user_id = get_user_answer.user_id)
        db.session.add(add_like)
        db.session.commit()

        if get_user_answer.user_id != active_user.id:

            reciver_user = User.query.get(get_user_answer.user_id)

            title = 'Like'
            # image_url = f'{active_user.image_path}'
            msg = f'{active_user.fullname} like your answer.'
            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=reciver_user.id,
                                               is_read=False, created_time=datetime.utcnow(), page='like on answer')
            db.session.add(add_notification)
            db.session.commit()
            # if reciver_user.device_token:
            notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                             image_url=None, device_type=reciver_user.device_type)

        return jsonify({'status': 1, 'messege': 'Successfully answer liked'})

@user_view_v5.route('/user_answer_comment_list', methods=['POST'])
@token_required
def user_answer_comment_list(active_user):

    data = request.get_json()
    answer_id = data.get('answer_id')
    page = int(data.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    get_all_comments = CommentsUserAnswer.query.filter_by(answer_id=answer_id).order_by(
        CommentsUserAnswer.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

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

            input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
            output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            user_details = {

                'user_id': user_data.id,
                'username': user_data.fullname,
                'user_image': user_data.image_path,
                'comment': i.comment,
                'created_time': output_date
            }
            comment_list.append(user_details)

    return jsonify(
        {'status': 1, 'messege': 'Success', 'comment_list': comment_list, 'pagination_info': pagination_info})

@user_view_v5.route('/comment_on_user_answer', methods=['POST'])
@token_required
def comment_on_user_answer(active_user):

    data = request.get_json()
    answer_id = data.get('answer_id')
    comment = data.get('comment')

    if not data:
        return jsonify({'status': 0,'messege': 'Json is empty'})

    if not comment:
        return jsonify({'status': 0,'messege': 'Please add input'})

    if not answer_id:
        return jsonify({'status': 0,'messege': 'Please select answer for comment'})

    get_user_answer = CategoryAns.query.get(answer_id)

    if not get_user_answer:
        return jsonify({'status': 0,'messege': 'Invalid answer'})

    add_comment = CommentsUserAnswer(user_id = active_user.id, answer_id = answer_id,main_user_id = get_user_answer.user_id,comment = comment,created_time = datetime.utcnow())
    db.session.add(add_comment)
    db.session.commit()

    # if get_user_answer.user_id != active_user.id:
    #
    #     reciver_user = User.query.get(get_user_answer.user_id)
    #
    #     title = 'Like'
    #     # image_url = f'{active_user.image_path}'
    #     msg = f'{active_user.fullname} like your answer.'
    #     add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=reciver_user.id,
    #                                            is_read=False, created_time=datetime.utcnow(), page='like on answer')
    #     db.session.add(add_notification)
    #     db.session.commit()
    #     # if reciver_user.device_token:
    #     notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
    #                                          image_url=None, device_type=reciver_user.device_type)

    return jsonify({'status': 1, 'messege': 'Successfully comment added'})

@user_view_v5.route('/like_user_photo', methods=['POST'])
@token_required
def like_user_photo(active_user):
    image_id = request.json.get('image_id')
    if not image_id:
        return jsonify({'status': 0,'messege': 'Please select image for like'})
    get_user_photo = UserPhotos.query.get(image_id)
    if not get_user_photo:
        return jsonify({'status': 0,'messege': 'Invalid image'})

    check_like = LikeUserPhotos.query.filter_by(user_id = active_user.id,image_id = image_id).first()
    if check_like:
        db.session.delete(check_like)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully image unliked'})
    else:
        add_like = LikeUserPhotos(user_id = active_user.id, image_id = image_id,main_user_id = get_user_photo.user_id)
        db.session.add(add_like)
        db.session.commit()

        if get_user_photo.user_id != active_user.id:
            reciver_user = User.query.get(get_user_photo.user_id)

            title = 'Like on photo'
            # image_url = f'{active_user.image_path}'
            msg = f'{active_user.fullname} like your photo.'
            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=reciver_user.id,
                                               is_read=False, created_time=datetime.utcnow(), page='like on photo')
            db.session.add(add_notification)
            db.session.commit()
            # if reciver_user.device_token:
            notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                             image_url=None, device_type=reciver_user.device_type)

        return jsonify({'status': 1, 'messege': 'Successfully image liked'})

@user_view_v5.route('/delete_photos', methods=['POST'])
@token_required
def delete_photos(active_user):

    image = request.json.get('image')
    if not image:
        return jsonify({'status': 0,'messege': 'Image is required'})

    get_user_photo = UserPhotos.query.filter_by(image_path = image,user_id = active_user.id).first()
    if not get_user_photo:
        return jsonify({'status': 0,'messege': 'Invalid photo'})

    image_name = image.replace("https://frienddate-app.s3.amazonaws.com/", "")

    s3_client.delete_object(Bucket=S3_BUCKET, Key=image_name)


    # split_data = active_user.multiple_images.split(',')
    #
    # if image in split_data:
    #     split_data.remove(image)
    #
    # active_user.multiple_images = ','.join(split_data)
    # db.session.commit()

    db.session.delete(get_user_photo)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully deleted'})

@user_view_v5.route('/get_my_images', methods=['POST'])
@token_required
def get_my_images(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    get_user_photos = UserPhotos.query.filter_by(user_id=active_user.id).order_by(
        UserPhotos.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = get_user_photos.has_next  # Check if there is a next page
    total_pages = get_user_photos.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    get_user_photos_list = [ i.as_dict(active_user.id) for i in get_user_photos ]

    if len(get_user_photos_list)>0:
        return jsonify({'status': 1,'messege': 'Success', 'photos_list':get_user_photos_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'No photos added', 'photos_list': [],'pagination_info': pagination_info})

@user_view_v5.route('/get_user_images', methods=['POST'])
@token_required
def get_user_images(active_user):
    user_id = request.json.get('user_id')
    page = int(request.json.get('page', 1))
    per_page = 30

    if not user_id:
        return jsonify({'status': 0,'messege': 'User id missing'})

    user_data = User.query.get(user_id)
    if not user_data:
        return jsonify({'status': 0,'messege': 'Invalid User'})

    get_user_photos = UserPhotos.query.filter_by(user_id=user_id).order_by(
        UserPhotos.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = get_user_photos.has_next  # Check if there is a next page
    total_pages = get_user_photos.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    get_user_photos_list = [ i.as_dict(active_user.id) for i in get_user_photos.items ]

    if len(get_user_photos_list)>0:
        return jsonify({'status': 1,'messege': 'Success', 'photos_list':get_user_photos_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'No photos added', 'photos_list': [],'pagination_info': pagination_info})

@user_view_v5.route('/add_multiple_photos', methods=['POST'])
@token_required
def add_multiple_photos(active_user):
    photos = request.files.getlist('photos')
    if not len(photos)>0:
        return jsonify({'status': 0,'messege': 'Please add photos'})

    # multiple_images_list = []
    for i in photos:
        file_path, picture = upload_photos(i)
        add_photos = UserPhotos(user_id = active_user.id, image_path = file_path)
        db.session.add(add_photos)
        db.session.commit()


        # multiple_images_list.append(file_path)

    # active_user.multiple_images = ','.join(multiple_images_list)
    # db.session.commit()

    return jsonify({'status': 1,'messege': 'Successrfully uploaded'})

@user_view_v5.route('/delete_profile_review', methods=['POST'])
@token_required
def delete_profile_review(active_user):
    review_id = request.json.get('review_id')
    if not review_id:
        return jsonify({'status': 0, 'messege': 'Please select review first'})

    get_approved_reviews = ProfileReviewRequest.query.filter(id=review_id, to_id=active_user.id,
                                                             request_status=1).first()

    if not get_approved_reviews:
        return jsonify({'status': 0, 'messege': 'Invalid Profile Review'})

    get_all_review_likes = ProfileReviewLike.query.filter_by(profile_review_id=get_approved_reviews.id).all()

    if len(get_all_review_likes) > 0:
        for i in get_all_review_likes:
            db.session.delete(i)
        db.session.commit()

    db.session.delete(get_approved_reviews)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully review deleted'})

@user_view_v5.route('/profile_reviews_request_list', methods=['POST'])
@token_required
def profile_reviews_request_list(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    get_approved_reviews = ProfileReviewRequest.query.filter(ProfileReviewRequest.to_id == active_user.id,
                                                             ProfileReviewRequest.request_status == 2).order_by(
        ProfileReviewRequest.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = get_approved_reviews.has_next  # Check if there is a next page
    total_pages = get_approved_reviews.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    review_list = []

    if get_approved_reviews.items:
        for i in get_approved_reviews.items:
            input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
            output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            review_dict = {
                'review_id': i.id,
                'review': i.review,
                'username': i.by_review.fullname,
                'user_image': i.by_review.image_path,
                'created_time': output_date,
                'status': i.request_status
            }

            review_list.append(review_dict)

    return jsonify({'status': 1, 'messege': 'Success', 'review_request_list': review_list, 'pagination_info': pagination_info})

@user_view_v5.route('/approved_denied_reviews', methods=['POST'])
@token_required
def approved_denied_reviews(active_user):
    review_id = request.json.get('review_id')
    status = request.json.get('status')

    if not review_id:
        return jsonify({'status': 0, 'messege': 'Please select review'})
    if not status:
        return jsonify({'status': 0, 'messege': 'Please select approve or deny '})

    get_profile_review_data = ProfileReviewRequest.query.filter_by(id=review_id,request_status=False,to_id = active_user.id).first()
    if not get_profile_review_data:
        return jsonify({'status':0,'messege': 'Invalid review'})


    if int(status) == 1:
        get_profile_review_data.request_status = 1
        db.session.commit()

        title = 'Review Approved'
        # image_url = f'{active_user.image_path}'
        msg = f'{active_user.fullname} approved your review.'
        add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=get_profile_review_data.by_id,
                                           is_read=False, created_time=datetime.utcnow(), page='review approved')
        db.session.add(add_notification)
        db.session.commit()
        # if reciver_user.device_token:
        notification = push_notification(device_token=get_profile_review_data.by_review.device_token, title=title, msg=msg,
                                         image_url=None, device_type=get_profile_review_data.by_review.device_type)

        return jsonify({'status': 1,'messege': 'Successfully approved review'})

    elif int(status) == 2:

        title = 'Review Denied'
        # image_url = f'{active_user.image_path}'
        msg = f'{active_user.fullname} denied your review.'
        add_notification = NewNotification(title=title, message=msg, by_id=active_user.id,
                                           to_id=get_profile_review_data.by_id,
                                           is_read=False, created_time=datetime.utcnow(), page='review denied')
        db.session.add(add_notification)
        db.session.commit()
        # if reciver_user.device_token:
        notification = push_notification(device_token=get_profile_review_data.by_review.device_token, title=title,
                                         msg=msg,
                                         image_url=None, device_type=get_profile_review_data.by_review.device_type)

        db.session.delete(get_profile_review_data)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully declined review'})

    else:
        return jsonify({'status': 0,'messege': 'Invalid status'})

@user_view_v5.route('/profile_review_comments_list', methods=['POST'])
@token_required
def profile_review_comments_list(active_user):
    review_id = request.json.get('review_id')
    page = int(request.json.get('page', 1))
    per_page = 30

    if not review_id:
        return jsonify({'status': 0, 'messege': 'Review id is required'})

    get_profile_review_data = ProfileReviewRequest.query.filter_by(id=review_id, request_status=1).first()
    if not get_profile_review_data:
        return jsonify({'status': 0, 'messege': 'Invalid profile review'})

    get_comments_data = ProfileReviewComments.query.filter_by(profile_review_id=review_id).order_by(
        ProfileReviewComments.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = get_comments_data.has_next
    total_pages = get_comments_data.pages


    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    comment_list = [ i.as_dict() for i in get_comments_data.items ]

    return jsonify({'status': 1,'messege': 'Success','comment_list': comment_list,'pagination_info': pagination_info})

@user_view_v5.route('/add_profile_review_comment', methods=['POST'])
@token_required
def add_profile_review_comment(active_user):
    review_id = request.json.get('review_id')
    comment = request.json.get('comment')

    if not review_id:
        return jsonify({'status': 0, 'messege': 'Review id is required'})
    if not comment:
        return jsonify({'status': 0, 'messege': 'Please give input for comment'})

    get_profile_review_data = ProfileReviewRequest.query.filter_by(id=review_id, request_status=1).first()
    if not get_profile_review_data:
        return jsonify({'status': 0, 'messege': 'Invalid profile review'})

    add_new_comment = ProfileReviewComments(created_time = datetime.utcnow(),
        comment=comment,user_id=active_user.id, profile_review_id=review_id, main_user_id = get_profile_review_data.to_id)
    db.session.add(add_new_comment)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully comment on review'})

@user_view_v5.route('/like_profile_review', methods=['POST'])
@token_required
def like_profile_review(active_user):

    review_id = request.json.get('review_id')
    if not review_id:
        return jsonify({'status':0,'messege': 'Review id is required'})

    get_profile_review_data = ProfileReviewRequest.query.filter_by(id =review_id,request_status = 1).first()
    if not get_profile_review_data:
        return jsonify({'status':0,'messege': 'Invalid profile review'})

    check_like = ProfileReviewLike.query.filter_by(user_id = active_user.id,profile_review_id = review_id).first()

    if check_like:
        db.session.delete(check_like)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully unlike review'})

    else:
        add_like = ProfileReviewLike(user_id = active_user.id, main_user_id = get_profile_review_data.to_id,profile_review_id = review_id)
        db.session.add(add_like)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully like review'})

@user_view_v5.route('/get_profile_reviews', methods=['POST'])
@token_required
def get_profile_reviews(active_user):
    page = int(request.json.get('page', 1))
    per_page = 30

    get_approved_reviews = ProfileReviewRequest.query.filter(ProfileReviewRequest.to_id ==active_user.id,ProfileReviewRequest.request_status == 1).order_by(
        ProfileReviewRequest.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = get_approved_reviews.has_next  # Check if there is a next page
    total_pages = get_approved_reviews.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    review_list = []

    if get_approved_reviews.items:
        for i in get_approved_reviews.items:

            is_like = False

            check_like = ProfileReviewLike.query.filter_by(profile_review_id = i.id,user_id = active_user.id).first()

            if check_like:
                is_like = True

            input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
            output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            review_dict = {
                'review_id': i.id,
                'review': i.review,
                'username': i.by_review.fullname,
                'user_image': i.by_review.image_path,
                'created_time': output_date,
                'status': i.request_status,
                'is_like': is_like
            }

            review_list.append(review_dict)


    return jsonify({'status': 1,'messege': 'Success', 'review_list': review_list,'pagination_info' : pagination_info})


@user_view_v5.route('/get_user_profile_reviews', methods=['POST'])
@token_required
def get_user_profile_reviews(active_user):
    page = int(request.json.get('page', 1))
    user_id = request.json.get('user_id')
    per_page = 30

    if not user_id:
        return jsonify({'status': 0,'messege': 'Please select user first'})

    get_approved_reviews = ProfileReviewRequest.query.filter(ProfileReviewRequest.to_id ==user_id,ProfileReviewRequest.request_status == 1).order_by(
        ProfileReviewRequest.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = get_approved_reviews.has_next  # Check if there is a next page
    total_pages = get_approved_reviews.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    review_list = []

    if get_approved_reviews.items:
        for i in get_approved_reviews.items:

            is_like = False

            check_like = ProfileReviewLike.query.filter_by(profile_review_id = i.id,user_id = active_user.id).first()

            if check_like:
                is_like = True

            input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
            output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            review_dict = {
                'review_id': i.id,
                'review': i.review,
                'username': i.by_review.fullname,
                'user_image': i.by_review.image_path,
                'created_time': output_date,
                'status': i.request_status,
                'is_like': is_like
            }

            review_list.append(review_dict)

    return jsonify({'status': 1,'messege': 'Success', 'review_list': review_list,'pagination_info' : pagination_info})

@user_view_v5.route('/send_profile_review', methods=['POST'])
@token_required
def send_profile_review(active_user):
    user_id = request.json.get('user_id')
    review = request.json.get('review')
    if not user_id:
        return jsonify({'status': 0,'messege': 'Please select user'})
    if not review:
        return jsonify({'status': 0,'messege': 'Please enter review.'})

    user_data = User.query.filter_by(is_block = False, deleted = False).first()
    if not user_data:
        return jsonify({'status': 0,'messege': 'Invalid user'})

    send_profile_review = ProfileReviewRequest(by_id = active_user.id,to_id = user_id,review=review,request_status = 2,created_time=datetime.utcnow())
    db.session.add(send_profile_review)
    db.session.commit()

    title = 'New Review'
    # image_url = f'{active_user.image_path}'
    msg = f'{active_user.fullname} wrote a review of you!.'
    # add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=user_id,
    #                                    is_read=False, created_time=datetime.utcnow(), page='review on profile')
    # db.session.add(add_notification)
    # db.session.commit()
    # if reciver_user.device_token:
    notification = push_notification(device_token=user_data.device_token, title=title, msg=msg,
                                     image_url=None, device_type=user_data.device_type)

    return jsonify({'status': 1, 'messege': 'Thank you for creating a review. Please wait for this user to approve your review to get posted on their page.'})


@user_view_v5.route('/top_followed_users', methods=['GET'])
@token_required
def get_top_followed_users(active_user):
    # page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    # per_page = 10  # Number of items per page

    top_users = db.session.query(
        User,  # Select the User object
        db.func.count(Follow.to_id).label('follower_count')
    ).join(User, User.id == Follow.to_id  # Join Follow with User on to_id
           ).group_by(User.id  # Group by User ID
                      ).order_by(db.desc('follower_count')  # Order by follower count
                                 ).limit(100).all()  # Limit to top 100

    # has_next = top_users.has_next  # Check if there is a next page
    # total_pages = top_users.pages  # Total number of pages
    #
    # main_list = []
    #
    # if page >= 10:
    #     has_next = False
    #
    main_list = []

    if len(top_users)>0:
        for user, count in top_users:

            is_my_profile = False
            if user.id == active_user.id:
                is_my_profile = True

            user_data = {
                'user_id': user.id,
                'username': user.fullname,
                'user_image': user.image_path,
                'count': str(count),
                'is_my_profile': is_my_profile
                }

            main_list.append(user_data)

    # pagination_info = {
    #     "current_page": page,
    #     "has_next": has_next,
    #     "per_page": per_page,
    #     "total_pages": total_pages,
    # }
    #
    # print('top_users',top_users)

    return jsonify({'status': 1,'messege': 'Success','user_list': main_list})

@user_view_v5.route('/like_recommendation', methods=['POST'])
@token_required
def like_recommendation(active_user):
    community_id = request.json.get('community_id')
    type = request.json.get('type')
    user_id = request.json.get('user_id')
    category_id = request.json.get('category_id')

    if not id:
        return jsonify({'status':0, 'messege': 'Id is required'})
    if not type:
        return jsonify({'status':0, 'messege': 'Type is required'})

    user_id = user_id
    if not user_id:
        user_id = active_user.id

    if type == 'things':
        things_data = ThingsRecommendation.query.filter_by(user_id = user_id, community_id = community_id,category_id=category_id).first()
        if not things_data:
            return jsonify({'status': 0,'messege': 'Invalid data'})
        get_like_exists = LikeRecommendation.query.filter_by(user_id = active_user.id,type = type,things_id = things_data.id).first()

        if get_like_exists:
            db.session.delete(get_like_exists)
            db.session.commit()
            return jsonify({'status': 1, 'messege': 'Successfully like removed'})
        else:
            add_like = LikeRecommendation(user_id = active_user.id,things_id = things_data.id,type = type)
            db.session.add(add_like)
            db.session.commit()
            return jsonify({'status': 1, 'messege': 'Successfully liked'})

    elif type == 'places':
        places_data = PlacesRecommendation.query.filter_by(user_id=user_id, community_id=community_id,
                                                           category_id=category_id).first()
        if not places_data:
            return jsonify({'status': 0, 'messege': 'Invalid data'})

        get_like_exists = LikeRecommendation.query.filter_by(user_id=active_user.id, type=type,
                                                             places_id=places_data.id).first()

        if get_like_exists:
            db.session.delete(get_like_exists)
            db.session.commit()
            return jsonify({'status': 1, 'messege': 'Successfully like removed'})
        else:
            add_like = LikeRecommendation(user_id=active_user.id, places_id=places_data.id, type=type)
            db.session.add(add_like)
            db.session.commit()
            return jsonify({'status': 1, 'messege': 'Successfully liked'})
    else:
        return jsonify({'status': 0,'messege': 'Invalid type must be places or things'})


@user_view_v5.route('/add_recommendation_comments', methods=['POST'])
@token_required
def add_recommendation_comments(active_user):

    data = request.get_json()
    if not data:
        return jsonify({'status': 0, 'messege': 'Json is empty'})

    community_id = data.get('community_id')
    type = data.get('type')
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    comment = data.get('comment')

    if not id:
        return jsonify({'status':0, 'messege': 'Id is required'})
    if not type:
        return jsonify({'status':0, 'messege': 'Type is required'})
    if not comment:
        return jsonify({'status':0, 'messege': 'Please add input for comment'})

    user_id = user_id
    if not user_id:
        user_id = active_user.id

    if type == 'things':
        things_data = ThingsRecommendation.query.filter_by(user_id = user_id, community_id = community_id,category_id=category_id).first()
        if not things_data:
            return jsonify({'status': 0,'messege': 'Invalid data'})

        add_comment = RecommendationComments(user_id = active_user.id,things_id = things_data.id,type = type,comment=comment,created_time = datetime.utcnow())
        db.session.add(add_comment)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully post your comment'})

    elif type == 'places':
        places_data = PlacesRecommendation.query.filter_by(user_id=user_id, community_id=community_id,
                                                           category_id=category_id).first()
        if not places_data:
            return jsonify({'status': 0, 'messege': 'Invalid data'})

        add_comment = RecommendationComments(user_id=active_user.id, places_id=places_data.id, type=type,comment=comment,created_time = datetime.utcnow())
        db.session.add(add_comment)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully post your comment'})
    else:
        return jsonify({'status': 0,'messege': 'Invalid type must be places or things'})

@user_view_v5.route('/new_notification_list', methods=['POST'])
@token_required
def new_notification_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    tab = request.json.get('tab', 0)

    if tab == 0:

        notification_data = NewNotification.query.filter(NewNotification.to_id == active_user.id,NewNotification.page != 'things recommendation',NewNotification.page != 'places recommendation').order_by(
            NewNotification.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    else:
        notification_data = NewNotification.query.filter(NewNotification.to_id == active_user.id,
        NewNotification.page.in_(['things recommendation', 'places recommendation'])).order_by(
            NewNotification.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = notification_data.has_next  # Check if there is a next page
    total_pages = notification_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    notification_list = []

    notification_counts = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).all()
    if len(notification_counts) > 0:
        for j in notification_counts:
            j.is_read = True
            db.session.commit()

    if notification_data.items:
        for i in notification_data.items:
            input_date = datetime.strptime(str(i.created_time), "%Y-%m-%d %H:%M:%S")
            output_date = input_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            notification_data = {
                'id': i.id,
                'title': i.title,
                'message': i.message,
                'page': i.page,
                'created_time': output_date,
                'user_id': i.by_user_notification.id,
                'username': i.by_user_notification.fullname,
                'user_image': i.by_user_notification.image_path

            }
            notification_list.append(notification_data)
        return jsonify({'status': 1, 'messege': 'Success', 'notification_list': notification_list,
                        'pagination_info': pagination_info})
    else:
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify({'status': 1, 'messege': 'Success', 'notification_list': notification_list,
                        'pagination_info': pagination_info})

@user_view_v5.route('/like_things_review_comment', methods=['POST'])
@token_required
def like_things_review_comment(active_user):
    comment_id = request.json.get('comment_id')

    if not comment_id:
        return jsonify({'status': 0,'messege': 'Comment id is required'})

    things_review_comment = ThingsReviewComments.query.get(comment_id)
    if not things_review_comment:
        return jsonify({'status': 0, 'messege': 'Invalid comment'})

    check_like_exists = ThingsReviewCommentLike.query.filter_by(things_comment_id= comment_id,user_id = active_user.id).first()

    if check_like_exists:
        db.session.delete(check_like_exists)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully unlike comment'})

    else:
        add_like_things_review_comment = ThingsReviewCommentLike(things_comment_id= comment_id,user_id = active_user.id)
        db.session.add(add_like_things_review_comment)
        db.session.commit()
        return jsonify({'status': 1,'messege': 'Successfully like comment'})

@user_view_v5.route('/delete_things_review_comment', methods=['POST'])
@token_required
def delete_things_review_comment(active_user):
    comment_id = request.json.get('comment_id')

    if not comment_id:
        return jsonify({'status': 0,'messege': 'Comment id is required'})

    things_review_comment = ThingsReviewComments.query.filter_by(id =comment_id, user_id = active_user.id).first()
    if not things_review_comment:
        return jsonify({'status': 0, 'messege': 'Invalid comment'})

    db.session.delete(things_review_comment)
    db.session.commit()
    return jsonify({'status': 1,'messege': 'Successfully comment deleted'})

@user_view_v5.route('/add_comment_things_review', methods=['POST'])
@token_required
def add_comment_things_review(active_user):
    review_id = request.json.get('review_id')
    comment_text = request.json.get('comment_text')
    if not comment_text:
        return jsonify({'status': 0,'messege': 'input is required'})

    if not review_id:
        return jsonify({'status': 0,'messege': 'Review id is required'})

    review_data = ThingsReview.query.get(review_id)
    if not review_data:
        return jsonify({'status': 0, 'messege': 'Invalid review'})

    add_things_review_comment_data = ThingsReviewComments(text = comment_text,user_id = active_user.id,review_id = review_id)
    db.session.add(add_things_review_comment_data)
    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully comment added'})

@user_view_v5.route('/like_things_review', methods=['POST'])
@token_required
def like_things_review(active_user):
    review_id = request.json.get('review_id')
    if not review_id:
        return jsonify({'status': 0,'messege': 'Review id is required'})

    review_data = ThingsReview.query.get(review_id)
    if not review_data:
        return jsonify({'status': 0, 'messege': 'Invalid review'})

    check_liked = ThingsReviewLike.query.filter_by(review_id = review_data.id,user_id = active_user.id).first()

    if check_liked:
        db.session.delete(check_liked)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully remove like'})

    else:
        add_things_review_like = ThingsReviewLike(user_id = active_user.id, review_id = review_id)
        db.session.add(add_things_review_like)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully liked'})


@user_view_v5.route('/like_places_review_comment', methods=['POST'])
@token_required
def like_places_review_comment(active_user):
    comment_id = request.json.get('comment_id')

    if not comment_id:
        return jsonify({'status': 0,'messege': 'Comment id is required'})

    places_review_comment = PlacesReviewComments.query.get(comment_id)
    if not places_review_comment:
        return jsonify({'status': 0, 'messege': 'Invalid comment'})

    check_like_exists = PlacesReviewCommentLike.query.filter_by(places_comment_id= comment_id,user_id = active_user.id).first()

    if check_like_exists:
        db.session.delete(check_like_exists)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully unlike comment'})

    else:
        add_like_places_review_comment = PlacesReviewCommentLike(places_comment_id= comment_id,user_id = active_user.id)
        db.session.add(add_like_places_review_comment)
        db.session.commit()
        return jsonify({'status': 1,'messege': 'Successfully like comment'})

@user_view_v5.route('/delete_places_review_comment', methods=['POST'])
@token_required
def delete_places_review_comment(active_user):
    comment_id = request.json.get('comment_id')

    if not comment_id:
        return jsonify({'status': 0,'messege': 'Comment id is required'})

    places_review_comment = PlacesReviewComments.query.filter_by(id =comment_id, user_id = active_user.id).first()
    if not places_review_comment:
        return jsonify({'status': 0, 'messege': 'Invalid comment'})

    db.session.delete(places_review_comment)
    db.session.commit()
    return jsonify({'status': 1,'messege': 'Successfully comment deleted'})

@user_view_v5.route('/add_comment_places_review', methods=['POST'])
@token_required
def add_comment_places_review(active_user):
    review_id = request.json.get('review_id')
    comment_text = request.json.get('comment_text')
    if not comment_text:
        return jsonify({'status': 0,'messege': 'input is required'})

    if not review_id:
        return jsonify({'status': 0,'messege': 'Review id is required'})

    review_data = PlacesReview.query.get(review_id)
    if not review_data:
        return jsonify({'status': 0, 'messege': 'Invalid review'})

    add_places_review_comment_data = PlacesReviewComments(text = comment_text,user_id = active_user.id,review_id = review_id)
    db.session.add(add_places_review_comment_data)
    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully comment added'})

@user_view_v5.route('/like_places_review', methods=['POST'])
@token_required
def like_places_review(active_user):
    review_id = request.json.get('review_id')
    if not review_id:
        return jsonify({'status': 0,'messege': 'Review id is required'})

    review_data = PlacesReview.query.get(review_id)
    if not review_data:
        return jsonify({'status': 0, 'messege': 'Invalid review'})

    check_liked = PlacesReviewLike.query.filter_by(review_id = review_data.id,user_id = active_user.id).first()

    if check_liked:
        db.session.delete(check_liked)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully remove like'})

    else:
        add_places_review_like = PlacesReviewLike(user_id = active_user.id, review_id = review_id)
        db.session.add(add_places_review_like)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully liked'})

@user_view_v5.route('/like_feed_comment', methods=['POST'])
@token_required
def like_feed_comment(active_user):
    comment_id = request.json.get('comment_id')

    if not comment_id:
        return jsonify({'status': 0,'messege': 'Comment id is required'})

    feed_comment = FeedComments.query.get(comment_id)
    if not feed_comment:
        return jsonify({'status': 0, 'messege': 'Invalid comment'})

    check_like_exists = FeedCommentLike.query.filter_by(feed_comment_id= comment_id,user_id = active_user.id).first()

    if check_like_exists:
        db.session.delete(check_like_exists)
        db.session.commit()

        return jsonify({'status': 1,'messege': 'Successfully unlike comment'})

    else:
        add_like_feed_comment = FeedCommentLike(feed_comment_id= comment_id,user_id = active_user.id)
        db.session.add(add_like_feed_comment)
        db.session.commit()
        return jsonify({'status': 1,'messege': 'Successfully like comment'})

@user_view_v5.route('/delete_feed_comment', methods=['POST'])
@token_required
def delete_feed_comment(active_user):
    comment_id = request.json.get('comment_id')

    if not comment_id:
        return jsonify({'status': 0,'messege': 'Comment id is required'})

    feed_comment = FeedComments.query.filter_by(id =comment_id, user_id = active_user.id).first()
    if not feed_comment:
        return jsonify({'status': 0, 'messege': 'Invalid comment'})

    db.session.delete(feed_comment)
    db.session.commit()
    return jsonify({'status': 1,'messege': 'Successfully comment deleted'})


@user_view_v5.route('/feed_comment_list', methods=['POST'])
@token_required
def feed_comment_list(active_user):
    feed_id = request.json.get('feed_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    if not feed_id:
        return jsonify({'status': 0,'messsege': 'Please provide feed id'})

    comments_data = FeedComments.query.filter_by(feed_id = feed_id).paginate(page=page, per_page=per_page, error_out=False)

    has_next = comments_data.has_next  # Check if there is a next page
    total_pages = comments_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    comments_list = [ i.as_dict(active_user.id) for i in comments_data.items ]

    return jsonify({'status': 1,'messege': 'Success', 'comment_list': comments_list,'pagination_info': pagination_info})


@user_view_v5.route('/add_comment_feed', methods=['POST'])
@token_required
def add_comment_feed(active_user):
    feed_id = request.json.get('feed_id')
    comment_text = request.json.get('comment_text')
    if not comment_text:
        return jsonify({'status': 0,'messege': 'input is required'})

    if not feed_id:
        return jsonify({'status': 0,'messege': 'Feed id is required'})

    feed_data = Feed.query.get(feed_id)
    if not feed_data:
        return jsonify({'status': 0, 'messege': 'Invalid feed'})

    add_feed_comment_data = FeedComments(text = comment_text,user_id = active_user.id,feed_id = feed_id, created_time = datetime.utcnow())
    db.session.add(add_feed_comment_data)
    db.session.commit()

    if active_user.id != feed_data.feed_id.id:
        title = 'Feed comment'
        # image_url = f'{active_user.image_path}'
        msg = f'{active_user.fullname} commented on your post'
        add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=feed_data.feed_id.id,
                                           is_read=False, created_time=datetime.utcnow(), page='comment on feed')
        db.session.add(add_notification)
        db.session.commit()
        # if reciver_user.device_token:
        notification = push_notification(device_token=feed_data.feed_id.device_token, title=title, msg=msg,
                                         image_url=None, device_type=feed_data.feed_id.device_type)

    return jsonify({'status': 1,'messege': 'Successfully comment added'})

@user_view_v5.route('/like_feed', methods=['POST'])
@token_required
def like_feed(active_user):
    feed_id = request.json.get('feed_id')
    if not feed_id:
        return jsonify({'status': 0,'messege': 'Feed id is required'})

    feed_data = Feed.query.get(feed_id)
    if not feed_data:
        return jsonify({'status': 0, 'messege': 'Invalid feed'})

    check_liked = FeedLike.query.filter_by(feed_id = feed_data.id,user_id = active_user.id).first()

    if check_liked:
        db.session.delete(check_liked)
        db.session.commit()
        return jsonify({'status': 1, 'messege': 'Successfully remove like'})

    else:
        add_feed_like = FeedLike(user_id = active_user.id, feed_id = feed_id)
        db.session.add(add_feed_like)
        db.session.commit()

        if active_user.id != feed_data.feed_id.id:

            title = 'Like'
            # image_url = f'{active_user.image_path}'
            msg = f'{active_user.fullname} likes your feed'
            add_notification = NewNotification(feed_id =feed_data.id,title=title, message=msg, by_id=active_user.id, to_id=feed_data.feed_id.id,
                                               is_read=False, created_time=datetime.utcnow(), page='like feed')
            db.session.add(add_notification)
            db.session.commit()
            # if reciver_user.device_token:
            notification = push_notification(device_token=feed_data.feed_id.device_token, title=title, msg=msg,
                                             image_url=None, device_type=feed_data.feed_id.device_type)

        return jsonify({'status': 1, 'messege': 'Successfully liked'})

@user_view_v5.route('/delete_feed', methods=['POST'])
@token_required
def delete_feed(active_user):
    feed_id = request.json.get('feed_id')
    if not feed_id:
        return jsonify({'status': 0,'messege': 'Feed id is required'})

    feed_data = Feed.query.filter_by(user_id = active_user.id, id = feed_id).first()
    if not feed_data:
        return jsonify({'status': 0, 'messege': 'Invalid feed'})

    if feed_data.image_name is not None and feed_data.is_review == False:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=feed_data.image_name)

    if feed_data.video_path is not None and feed_data.is_review == False:
        video_name = feed_data.video_path.replace("https://frienddate-app.s3.amazonaws.com/", "")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=video_name)

        thumbnail_name = feed_data.thumbnail_path.replace("https://frienddate-app.s3.amazonaws.com/", "")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=thumbnail_name)

    db.session.delete(feed_data)
    db.session.commit()

    return jsonify({'status': 1,'messege': 'Successfully deleted feed'})

@user_view_v5.route('/my_review_list', methods=['POST'])
@token_required
def my_review_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    get_places_reviews = PlacesReview.query.filter(PlacesReview.user_id == active_user.id).order_by(
        PlacesReview.created_time.desc()).all()
    get_things_reviews = ThingsReview.query.filter(ThingsReview.user_id == active_user.id).order_by(
        ThingsReview.created_time.desc()).all()

    get_all_reviews = get_places_reviews + get_things_reviews

    get_all_reviews.sort(key=lambda review: review.created_time, reverse=True)

    total_reviews = len(get_all_reviews)
    total_pages = (total_reviews + per_page - 1) // per_page  # Calculate total pages
    start = (page - 1) * per_page
    end = start + per_page
    paginated_reviews = get_all_reviews[start:end]

    has_next = page < total_pages

    # feed_data = Feed.query.filter(Feed.is_review == True, Feed.user_id == user_id).order_by(
    #     Feed.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    #
    # has_next = feed_data.has_next  # Check if there is a next page
    # total_pages = feed_data.pages  # Total number of pages
    #
    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if len(paginated_reviews)>0:
        feed_list = [i.as_dict2(active_user.id) for i in paginated_reviews]
        return jsonify({'status': 1, 'messege': 'Success', 'review_list': feed_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no reviews share by user', 'review_list': [],'pagination_info': pagination_info})

@user_view_v5.route('/users_review_list', methods=['POST'])
@token_required
def users_review_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0,'messege': 'User id is required'})

    get_places_reviews = PlacesReview.query.filter(PlacesReview.user_id == user_id).order_by(
        PlacesReview.created_time.desc()).all()
    get_things_reviews = ThingsReview.query.filter(ThingsReview.user_id == user_id).order_by(
        ThingsReview.created_time.desc()).all()

    get_all_reviews = get_places_reviews + get_things_reviews

    get_all_reviews.sort(key=lambda review: review.created_time, reverse=True)

    total_reviews = len(get_all_reviews)
    total_pages = (total_reviews + per_page - 1) // per_page  # Calculate total pages
    start = (page - 1) * per_page
    end = start + per_page
    paginated_reviews = get_all_reviews[start:end]

    has_next = page < total_pages

    # feed_data = Feed.query.filter(Feed.is_review == True, Feed.user_id == user_id).order_by(
    #     Feed.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    #
    # has_next = feed_data.has_next  # Check if there is a next page
    # total_pages = feed_data.pages  # Total number of pages
    #
    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if len(paginated_reviews)>0:
        feed_list = [i.as_dict2(active_user.id) for i in paginated_reviews]
        return jsonify({'status': 1, 'messege': 'Success', 'review_list': feed_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no reviews share by user', 'review_list': [],'pagination_info': pagination_info})

@user_view_v5.route('/hide_feed', methods=['POST'])
@token_required
def hide_feed(active_user):

    feed_id = request.json.get('feed_id')
    if not feed_id:
        return jsonify({'status':0, 'messege': 'Please select feed'})

    get_feed = Feed.query.get(feed_id)
    if not get_feed:
        return jsonify({'status':0, 'messege': 'Invalid feed'})

    add_hide_feed = HideFeed(user_id = active_user.id, feed_id = feed_id)
    db.session.add(add_hide_feed)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully hide feed'})

@user_view_v5.route('/liked_feed_users', methods=['POST'])
@token_required
def liked_feed_users(active_user):

    data = request.get_json()
    page = int(data.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    feed_id = data.get('feed_id')
    if not feed_id:
        return jsonify({'status': 0,'messege': 'Please select feed first'})

    get_feed_likes = FeedLike.query.filter(FeedLike.feed_id==feed_id, FeedLike.user_id != active_user.id).order_by(FeedLike.id.desc()).paginate(page=page,
                                                 per_page=per_page,
                                                 error_out=False)

    get_liked_users_list = []

    if get_feed_likes.items:
        for i in get_feed_likes.items:
            get_follow_data = Follow.query.filter_by(by_id=active_user.id,to_id = i.feed_like_id.id).first()
            user_dict = {

                'id': i.feed_like_id.id,
                'username': i.feed_like_id.fullname,
                'user_image': i.feed_like_id.image_path,
                'is_follow': bool(get_follow_data)
            }

            get_liked_users_list.append(user_dict)

    return jsonify({'status': 1, 'messege': 'Success','user_list': get_liked_users_list})



@user_view_v5.route('/feed_page', methods=['POST'])
@token_required
def feed_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    notification_count = NewNotification.query.filter_by(to_id = active_user.id,is_read = False).count()

    follow_data = Follow.query.filter_by(by_id = active_user.id).all()
    print('follow_data',follow_data)

    if not follow_data:
        return jsonify({'status':1,'messege': '', 'feed_list': []})

    followed_list = [ i.to_id for i in follow_data ]

    get_hide_feed = HideFeed.query.filter_by(user_id = active_user.id).all()
    get_hide_feed_ids = [ i.feed_id for i in get_hide_feed ]

    feed_data = Feed.query.filter(Feed.feed_type != 'feed',Feed.user_id != active_user.id, Feed.user_id.in_(followed_list),Feed.id.not_in(get_hide_feed_ids)).order_by(Feed.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = feed_data.has_next  # Check if there is a next page
    total_pages = feed_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages
    }

    feed_list = []
    if feed_data.items:
        for i in feed_data.items:
            main_dict = i.as_dict(active_user.id)
            if i.is_repost == True:
                if i.repost_feed_id is None:
                    return jsonify({'status': 0,'messege': 'Something went wrong'})

                get_repost_data = Feed.query.get(i.repost_feed_id)
                if not get_repost_data:
                    return jsonify({'status': 0, 'messege': 'Something went wrong'})

                main_dict = get_repost_data.as_dict(active_user.id)

                main_dict['id'] = get_repost_data.id
                main_dict['user_id'] = get_repost_data.user_id
                main_dict['username'] = get_repost_data.feed_id.fullname
                main_dict['user_image'] = get_repost_data.feed_id.image_path

            is_like= False
            check_like = FeedLike.query.filter_by(user_id = active_user.id, feed_id = i.id).first()
            comments_count = FeedComments.query.filter_by(feed_id=i.id).count()
            feed_like_count = FeedLike.query.filter_by(feed_id=i.id).count()
            if check_like:
                is_like = True
            main_dict['is_like'] = is_like
            main_dict['comments_count'] = str(comments_count)
            main_dict['like_count'] = str(feed_like_count)
            feed_list.append(main_dict)

        return jsonify({'status': 1, 'messege': 'Success','notification_count': str(notification_count), 'feed_list': feed_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones','notification_count': str(notification_count), 'feed_list': [],'pagination_info': pagination_info})

@user_view_v5.route('/my_feed_page', methods=['POST'])
@token_required
def my_feed_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    feed_data = Feed.query.filter( Feed.user_id == active_user.id).order_by(Feed.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = feed_data.has_next  # Check if there is a next page
    total_pages = feed_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if feed_data.items:
        #feed_list = [ i.as_dict() for i in feed_data.items]

        feed_list = []

        for i in feed_data.items:
            main_dict = i.as_dict(active_user.id)

            if i.is_repost == True:
                if i.repost_feed_id is None:
                    return jsonify({'status': 0,'messege': 'Something went wrong'})

                get_repost_data = Feed.query.get(i.repost_feed_id)
                if not get_repost_data:
                    return jsonify({'status': 0, 'messege': 'Something went wrong'})

                main_dict = get_repost_data.as_dict(active_user.id)

                main_dict['id'] = get_repost_data.id
                main_dict['user_id'] = get_repost_data.user_id
                main_dict['username'] = get_repost_data.feed_id.fullname
                main_dict['user_image'] = get_repost_data.feed_id.image_path
            is_like = False
            check_like = FeedLike.query.filter_by(user_id=active_user.id, feed_id=i.id).first()
            comments_count = FeedComments.query.filter_by(feed_id=i.id).count()
            feed_like_count = FeedLike.query.filter_by(feed_id=i.id).count()

            if check_like:
                is_like = True
            main_dict['is_like'] = is_like

            main_dict['comments_count'] = str(comments_count)
            main_dict['like_count'] = str(feed_like_count)

            feed_list.append(main_dict)

        return jsonify({'status': 1, 'messege': 'Success', 'feed_list': feed_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones', 'feed_list': [],'pagination_info': pagination_info})


# @user_view_v5.route('/user_feed_page', methods=['POST'])
# @token_required
# def user_feed_page(active_user):
#     page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#     per_page = 10  # Number of items per page
#     user_id = request.json.get('user_id')
#     if not user_id:
#         return jsonify({'status': 0, 'messege': 'User id is required'})
#
#     follow_data = Follow.query.filter_by(by_id=active_user.id, to_id=user_id).first()
#     print('follow_data', follow_data)
#
#     if not follow_data:
#         return jsonify({'status': 1, 'messege': 'First you need to follow someone to see their activity in feed page',
#                         'feed_list': []})
#
#     feed_data = Feed.query.filter(Feed.user_id == user_id).order_by(Feed.id.desc()).paginate(page=page,
#                                                                                              per_page=per_page,
#                                                                                              error_out=False)
#
#     has_next = feed_data.has_next  # Check if there is a next page
#     total_pages = feed_data.pages  # Total number of pages
#
#     # Pagination information
#     pagination_info = {
#         "current_page": page,
#         "has_next": has_next,
#         "per_page": per_page,
#         "total_pages": total_pages,
#     }
#
#     if feed_data.items:
#         # feed_list = [ i.as_dict() for i in feed_data.items]
#
#         feed_list = []
#
#         for i in feed_data.items:
#             main_dict = i.as_dict(active_user.id)
#             is_like = False
#             check_like = FeedLike.query.filter_by(user_id=active_user.id, feed_id=i.id).first()
#             comments_count = FeedComments.query.filter_by(feed_id=i.id).count()
#             if check_like:
#                 is_like = True
#             main_dict['is_like'] = is_like
#             main_dict['comments_count'] = str(comments_count)
#             feed_list.append(main_dict)
#
#         return jsonify({'status': 1, 'messege': 'Success', 'feed_list': feed_list, 'pagination_info': pagination_info})
#     else:
#         return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones', 'feed_list': [],
#                         'pagination_info': pagination_info})

@user_view_v5.route('/user_feed_page', methods=['POST'])
@token_required
def user_feed_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0,'messege': 'User id is required'})

    user_data = User.query.get(user_id)
    if not user_data:
        return jsonify({'status': 0,'messege': 'Invalid user'})

    username = user_data.fullname if user_data.fullname is not None else ''
    user_image = user_data.image_path if user_data.image_path is not None else ''

    user_link = user_data.profile_link if not None else ''

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    is_follow = 0

    follow_data = Follow.query.filter_by(by_id = active_user.id, to_id = user_id).first()
    print('follow_data',follow_data)

    is_friend = 0

    friend_request = FriendRequest.query.filter(
        (FriendRequest.to_id == active_user.id) & (FriendRequest.by_id == user_id)
        | (FriendRequest.by_id == active_user.id) & (FriendRequest.to_id == user_id)
    ).first()

    if friend_request:
        is_friend = friend_request.request_status

    query = (
        db.session.query(User)
            .filter(
            User.id.not_in(blocked_user_ids),
            User.id.not_in(blocked_by_user_ids), User.is_block == False, User.deleted == False
        )
            .join(Follow, Follow.to_id == User.id)
            .filter(Follow.to_id == user_id)
    )

    following_count = query.count()

    if not follow_data:
        return jsonify({'status':1,'messege': '', 'feed_list': [], 'is_friend': is_friend, 'is_follow': is_follow,
         'following_count': str(following_count),'show_link': user_link})

    is_follow = 1

    feed_data = Feed.query.filter( Feed.user_id == user_id).order_by(Feed.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    has_next = feed_data.has_next  # Check if there is a next page
    total_pages = feed_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    if feed_data.items:
        #feed_list = [ i.as_dict() for i in feed_data.items]

        feed_list = []

        for i in feed_data.items:
            main_dict = i.as_dict(active_user.id)
            is_like = False
            check_like = FeedLike.query.filter_by(user_id=active_user.id, feed_id=i.id).first()
            comments_count = FeedComments.query.filter_by(feed_id=i.id).count()
            feed_like_count = FeedLike.query.filter_by(feed_id=i.id).count()

            if check_like:
                is_like = True
            main_dict['is_like'] = is_like

            main_dict['comments_count'] = str(comments_count)
            main_dict['like_count'] = str(feed_like_count)
            main_dict['show_link'] = user_data.profile_link

            feed_list.append(main_dict)

        return jsonify({'status': 1, 'messege': 'Success',"username" : username,"user_image": user_image, 'feed_list': feed_list,'pagination_info': pagination_info, 'is_friend': is_friend, 'is_follow': is_follow,
         'following_count': str(following_count),'show_link': user_link})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones',"username" : username,"user_image": user_image, 'feed_list': [],'pagination_info': pagination_info, 'is_friend': is_friend, 'is_follow': is_follow,
         'following_count': str(following_count),'show_link': user_link})

@user_view_v5.route('/add_activity_post', methods=['POST'])
@token_required
def add_activity_post(active_user):
    text = request.form.get('text')
    link = request.form.get('link')
    website_link = request.form.get('website_link')
    content = request.files.get('content')
    content_media_type = request.form.get('content_type')

    if not text and not content.filename and not link:
        return jsonify({'status': 0, 'messege': 'Please provide inputs'})

    image_name = None
    image_url = None

    video_url = None
    thumbnail_path = None

    type = 'text'

    if content_media_type == 'image':

        if content and content.filename:
            type = 'image'
            image_name = secure_filename(content.filename)
            extension = os.path.splitext(image_name)[1]
            extension2 = os.path.splitext(image_name)[1][1:].lower()

            content_type = f'image/{extension2}'
            x = secrets.token_hex(10)

            image_name = x + extension

            s3_client.upload_fileobj(content, S3_BUCKET, image_name,
                                     ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
            image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{image_name}"

    elif content_media_type == 'video':

        if content and content.filename:
            type = 'video'
            video_name = secure_filename(content.filename)
            extension = os.path.splitext(video_name)[1]
            extension2 = os.path.splitext(video_name)[1][1:].lower()

            unique_name = secrets.token_hex(10)

            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
                content.save(tmp.name)
                # Rewind the file pointer to the beginning of the video file
                tmp.seek(0)

                # Generate a thumbnail for the video
                clip = VideoFileClip(tmp.name)
                thumbnail_name = f"thumb_{unique_name}.jpg"
                clip.save_frame(thumbnail_name, t=1)  # Save the frame at 1 second as the thumbnail

                # Close the VideoFileClip object
                clip.reader.close()
                if clip.audio and clip.audio.reader:
                    clip.audio.reader.close_proc()

                # Upload the thumbnail to S
                with open(thumbnail_name, 'rb') as thumb:

                    s3_client.upload_fileobj(thumb, S3_BUCKET, thumbnail_name,
                                             ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpeg'})
                thumbnail_path = f"https://{S3_BUCKET}.s3.amazonaws.com/{thumbnail_name}"
                print(f'Thumbnail URL: {thumbnail_path}')

                # Clean up the temporary thumbnail file
                os.remove(thumbnail_name)

            # Upload the original post (video or image)
            content.seek(0)  # Rewind the file pointer to the beginning

            content_type = f'video/{extension2}'
            x = secrets.token_hex(10)

            video_name = x + extension

            s3_client.upload_fileobj(content, S3_BUCKET, video_name,
                                         ExtraArgs={'ACL': 'public-read', 'ContentType': content_type})
            video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{video_name}"

            # Clean up the temporary video file after uploading
            try:
                os.remove(tmp.name)
                print('itssssssssssssssssss successsssssssssssssssssssss')
            except PermissionError as e:
                print(f"Error removing temporary file: {e}")
            print('video_url', video_url)

    elif content_media_type == 'link':
        type = 'link'

    add_feed_data = Feed(website_link=website_link,link=link,type = type,text=text,thumbnail_path= thumbnail_path,video_path = video_url, image_name=image_name, image_path=image_url,
                                     created_time=datetime.utcnow(), user_id=active_user.id)
    db.session.add(add_feed_data)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully added your activity post'})

@user_view_v5.route('/follow_user', methods=['POST'])
@token_required
def follow_user(active_user):
    user_id = request.json.get('user_id')

    if not user_id:
        return jsonify({'status': 0,'messege': 'Please select user first'})

    user_data = User.query.get(user_id)
    if not user_data:
        return jsonify({'status': 0,'messege': 'Invalid user'})

    get_followed_data = Follow.query.filter_by(by_id = active_user.id, to_id = user_id).first()

    if get_followed_data:
        db.session.delete(get_followed_data)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Successfully unfollow user'})

    else:
        add_follow_data = Follow(by_id = active_user.id, to_id = user_id)
        db.session.add(add_follow_data)
        db.session.commit()

        if active_user.id != user_data.id:

            title = 'New Follower'
            # image_url = f'{active_user.image_path}'
            msg = f'{active_user.fullname} starting following you'
            add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=user_data.id,
                                            is_read=False, created_time=datetime.utcnow(), page='follow')
            db.session.add(add_notification)
            db.session.commit()
            # if reciver_user.device_token:
            notification = push_notification(device_token=user_data.device_token, title=title, msg=msg,
                                             image_url=None, device_type=user_data.device_type)

        return jsonify({'status': 1, 'messege': 'Successfully follow user'})

@user_view_v5.route('/my_followers_list', methods=['POST'])
@token_required
def my_followers_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    get_followers_data = Follow.query.filter(Follow.to_id==active_user.id).order_by(Follow.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    followes_list = [ i.as_dict() for i in get_followers_data.items ]

    has_next = get_followers_data.has_next  # Check if there is a next page
    total_pages = get_followers_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    return jsonify({'status': 1,'messege': 'Success', 'followes_list': followes_list,'pagination_info': pagination_info})

@user_view_v5.route('/followers_list', methods=['POST'])
@token_required
def followers_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0, 'messege': 'Please select user first'})

    get_followers_data = Follow.query.filter(Follow.to_id==user_id).order_by(Follow.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    followes_list = [ i.as_dict() for i in get_followers_data.items ]

    has_next = get_followers_data.has_next  # Check if there is a next page
    total_pages = get_followers_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    return jsonify({'status': 1,'messege': 'Success', 'followes_list': followes_list,'pagination_info': pagination_info})

@user_view_v5.route('/user_my_recommendation_category', methods=['POST'])
@token_required
def user_my_recommendation_category(active_user):
    tab = request.json.get('tab')

    category_object_list = []

    if not tab:
        return jsonify({'status': 0, 'messege': 'Select valid tab'})


    if tab == 1:

        get_places_recommendation_data= PlacesRecommendation.query.filter_by(user_id = active_user.id).all()

        if not len(get_places_recommendation_data)>0:
            return jsonify({'status': 1,'messege': 'Dont have any recommendation yet', 'recommendation_category': []})

        for i in get_places_recommendation_data:
            if not i.places_recommendation.community_places_id in category_object_list:

                category_object_list.append(i.places_recommendation.community_places_id)

    if tab == 2:

        get_things_recommendation_data= ThingsRecommendation.query.filter_by(user_id = active_user.id).all()

        if not len(get_things_recommendation_data)>0:
            return jsonify({'status': 1,'messege': 'Dont have any recommendation yet', 'recommendation_category': []})

        for i in get_things_recommendation_data:
            if not i.things_recommendation.community_things_id in category_object_list:

                category_object_list.append(i.things_recommendation.community_things_id)
    final_list = [ i.as_dict() for i in category_object_list ]

    if len(final_list)>0:
        return jsonify({'status': 1, 'messege': 'Success','recommendation_category': final_list})
    else:
        return jsonify({'status': 1,'messege': 'Dont have any recommendation yet','recommendation_category': []})

@user_view_v5.route('/user_recommendation_category', methods=['POST'])
@token_required
def user_recommendation_category(active_user):
    user_id = request.json.get('user_id')
    tab = request.json.get('tab')

    category_object_list = []

    if not user_id:
        return jsonify({'status': 0, 'messege': 'Please provide valid data'})

    if not tab:
        return jsonify({'status': 0, 'messege': 'Select valid tab'})


    if tab == 1:

        get_places_recommendation_data= PlacesRecommendation.query.filter_by(user_id = user_id).all()

        if not len(get_places_recommendation_data)>0:
            return jsonify({'status': 1,'messege': 'Dont have any recommendation yet', 'recommendation_category': []})

        for i in get_places_recommendation_data:
            if not i.places_recommendation.community_places_id in category_object_list:

                category_object_list.append(i.places_recommendation.community_places_id)

    if tab == 2:

        get_things_recommendation_data= ThingsRecommendation.query.filter_by(user_id = user_id).all()

        if not len(get_things_recommendation_data)>0:
            return jsonify({'status': 1,'messege': 'Dont have any recommendation yet', 'recommendation_category': []})

        for i in get_things_recommendation_data:
            if not i.things_recommendation.community_things_id in category_object_list:

                category_object_list.append(i.things_recommendation.community_things_id)
    final_list = [ i.as_dict() for i in category_object_list ]

    if len(final_list)>0:
        return jsonify({'status': 1, 'messege': 'Success','recommendation_category': final_list})
    else:
        return jsonify({'status': 1,'messege': 'Dont have any recommendation yet','recommendation_category': []})

@user_view_v5.route('/homepage_verify_token', methods=['POST'])
@token_required
def homepage_verify_token(active_user):
    data = request.get_json()
    receipt_data = data['receipt']
    product_id = data['product_id']

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
                        active_user.user_badge = None

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


# @user_view_v5.route('/homepage', methods=['POST'])
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
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#     active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
#
#     matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('matches'))
#                     .join(User, User.id == SavedCommunity.user_id)
#                     .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
#                     .group_by(SavedCommunity.user_id)
#                     .subquery())
#
#     user_data = (db.session.query(User, matches_subq.c.matches)
#                  .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
#                  .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
#                  .filter(~User.id.in_(blocked_user_ids))
#                  .filter(~User.id.in_(blocked_by_user_ids)).filter(matches_subq.c.matches != None)
#                  .order_by(matches_subq.c.matches.desc()).paginate(page=page, per_page=per_page, error_out=False))
#     response_list = []
#
#     print('user_data', user_data.items)
#
#     saved_my_favorites = []
#
#     for j in active_user.save_community_id:
#         saved_my_favorites.append(j.created_id)
#
#     if user_data.items:
#         print('user_data.items', user_data.items)
#         for specific_response, count in user_data.items:
#             count_value = str(count)
#             if not count:
#                 count_value = '0'
#
#             badge = ""
#             if specific_response.badge_name is not None:
#                 if specific_response.badge_name == "I'll Buy Us Coffee":
#                     badge = "☕"
#                 if specific_response.badge_name == "I'll Buy Us Food":
#                     badge = "🍔"
#                 if specific_response.badge_name == "Activity Badge":
#                     badge = "🚴"
#                 if specific_response.badge_name == "Best Friend Forever Badge":
#                     badge = "🧑‍🤝‍🧑"
#                 if specific_response.badge_name == "Luxury Badge":
#                     badge = "🚁"
#                 if specific_response.badge_name == "Lavish Badge":
#                     badge = "💎"
#
#                     # badge = specific_response.badge_name
#             college = ""
#             if specific_response.college is not None:
#                 college = specific_response.college
#             sexuality = ""
#             if specific_response.sexuality is not None:
#                 sexuality = specific_response.sexuality
#
#             relationship_status = ""
#             if specific_response.relationship_status is not None:
#                 relationship_status = specific_response.relationship_status
#
#             looking_for = ""
#             if specific_response.looking_for is not None:
#                 looking_for = specific_response.looking_for
#
#             total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=specific_response.id).count()
#             total_liked_questions_answer = LikeUserAnswer.query.filter_by(main_user_id=specific_response.id).count()
#
#             user_places_review = PlacesReview.query.filter_by(user_id=specific_response.id).all()
#
#             review_likes_count = []
#             if len(user_places_review) > 0:
#                 for i in user_places_review:
#                     liked_places_review = PlacesReviewLike.query.filter_by(review_id=i.id).count()
#                     if liked_places_review > 0:
#                         review_likes_count.append(liked_places_review)
#
#             user_things_review = ThingsReview.query.filter_by(user_id=specific_response.id).all()
#             if len(user_things_review) > 0:
#                 for i in user_things_review:
#                     liked_things_review = ThingsReviewLike.query.filter_by(review_id=specific_response.id).count()
#                     if liked_things_review > 0:
#                         review_likes_count.append(liked_things_review)
#
#             total_review_likes_count = '0'
#             if len(review_likes_count) > 0:
#                 total_review_likes_count = str(sum(review_likes_count))
#
#             total_followers = Follow.query.filter_by(to_id=specific_response.id).count()
#
#             user_feed_data = Feed.query.filter_by(user_id=specific_response.id).all()
#
#             total_status_likes = []
#
#             if len(user_feed_data) > 0:
#                 for i in user_feed_data:
#                     feed_likes = FeedLike.query.filter_by(feed_id=i.id).count()
#                     if feed_likes > 0:
#                         total_status_likes.append(feed_likes)
#
#             get_approved_reviews_likes = ProfileReviewLike.query.filter_by(main_user_id=specific_response.id).count()
#             total_user_photos_likes = LikeUserPhotos.query.filter_by(main_user_id=specific_response.id).count()
#
#             response_dict = {'user_id': str(specific_response.id),
#                              'user_name': specific_response.fullname,
#                              'user_image': specific_response.image_path,
#                              'state': specific_response.state,
#                              'city': specific_response.city,
#                              'badge': badge,
#                              'matches_count': count_value,
#                              'about_me': specific_response.about_me if specific_response.about_me is not None else '',
#                              'college': college,
#                              'sexuality': sexuality,
#                              'relationship_status': relationship_status,
#                              'looking_for': looking_for,
#                              'new_bio': specific_response.new_bio if specific_response.new_bio is not None else '',
#                              'total_liked_Recommendation': str(total_liked_Recommendation),
#                              'total_liked_questions_answer': str(total_liked_questions_answer),
#                              'total_review_likes_count': total_review_likes_count,
#                              'total_followers': str(total_followers),
#                              'total_status_likes': str(sum(total_status_likes)),
#                              'total_profile_review_like': str(get_approved_reviews_likes),
#                              'total_user_photos_likes': str(total_user_photos_likes)
#
#                              }
#             response_list.append(response_dict)
#
#     has_next = user_data.has_next  # Check if there is a next page
#     total_pages = user_data.pages  # Total number of pages
#
#     # Pagination information
#     pagination_info = {
#         "current_page": page,
#         "has_next": has_next,
#         "per_page": per_page,
#         "total_pages": total_pages,
#     }
#
#     if len(response_list) > 0:
#         # sorted_list = sorted(response_list, key=lambda x: x['matches_count'], reverse=True)
#         return jsonify({'status': 1, 'data': response_list, 'messege': 'Sucess', 'pagination': pagination_info})
#     else:
#
#         return jsonify({'status': 1, 'data': [], 'messege': 'You have zero matches. Click on Save to get started',
#                         'pagination': pagination_info})


@user_view_v5.route('/homepage', methods=['POST'])
@token_required
def homepage(active_user):
    device_token = request.json.get('device_token')
    device_type = request.json.get('device_type')
    city = request.json.get('city')
    state = request.json.get('state')

    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    active_user.device_token = device_token
    active_user.device_type = device_type
    active_user.id = active_user.id
    db.session.commit()

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    active_user_saved_ids = [j.created_id for j in active_user.save_community_id]

    matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('community_matches'))
                    .join(User, User.id == SavedCommunity.user_id)
                    .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
                    .group_by(SavedCommunity.user_id)
                    .subquery())

    active_user_things_saved_ids = [j.created_id for j in active_user.save_things_community_id]

    things_matches_subq = (db.session.query(SavedThingsCommunity.user_id, func.count().label('things_matches'))
                    .join(User, User.id == SavedThingsCommunity.user_id)
                    .filter(SavedThingsCommunity.created_id.in_(active_user_things_saved_ids))
                    .group_by(SavedThingsCommunity.user_id)
                    .subquery())

    query = (
        db.session.query(
            User,
            (func.coalesce(matches_subq.c.community_matches, 0) +
             func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches'),
        )
            .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
            .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
            .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
            .filter(~User.id.in_(blocked_user_ids))
            .filter(~User.id.in_(blocked_by_user_ids))
            .filter((matches_subq.c.community_matches != None) | (things_matches_subq.c.things_matches != None))
            .order_by((func.coalesce(matches_subq.c.community_matches, 0) +
                       func.coalesce(things_matches_subq.c.things_matches, 0)).desc())

    )

    if city:
        query = query.filter(User.city.ilike(f"{city}%"))
    if state:
        query = query.filter(User.state.ilike(f"{state}%"))

    user_data = query.paginate(page=page, per_page=per_page, error_out=False)

    user_data_count = (
        db.session.query(
            User,
            (func.coalesce(matches_subq.c.community_matches, 0) +
             func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches'),
        )
            .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
            .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
            .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
            .filter(~User.id.in_(blocked_user_ids))
            .filter(~User.id.in_(blocked_by_user_ids))
            .filter((matches_subq.c.community_matches != None) | (things_matches_subq.c.things_matches != None))
            .order_by((func.coalesce(matches_subq.c.community_matches, 0) +
                       func.coalesce(things_matches_subq.c.things_matches, 0)).desc())
            .count()
    )

    print('user_data_count', user_data_count)

    response_list = []

    print('user_data',user_data.items)

    saved_my_favorites = []

    for j in active_user.save_community_id:
        saved_my_favorites.append(j.created_id)

    if user_data.items:
        print('user_data.items',user_data.items)
        for specific_response, count in user_data.items:
            count_value = str(count)
            if not count:
                count_value = '0'

            badge = ""
            if specific_response.badge_name is not None:
                if specific_response.badge_name == "I'll Buy Us Coffee":
                    badge = "☕"
                if specific_response.badge_name == "I'll Buy Us Food":
                    badge = "🍔"

                if specific_response.badge_name == "I’ll buy us food":
                    badge = "🍟"

                if specific_response.badge_name == "I’ll buy us drinks":
                    badge = "☕"

                if specific_response.badge_name == "Activity Badge":
                    badge = "🚴"
                if specific_response.badge_name == "Best Friend Forever Badge":
                    badge = "🧑‍🤝‍🧑"
                if specific_response.badge_name == "Luxury Badge":
                    badge = "🚁"
                if specific_response.badge_name == "Lavish Badge":
                    badge = "💎"
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

            total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=specific_response.id).count()
            total_liked_questions_answer = LikeUserAnswer.query.filter_by(main_user_id=specific_response.id).count()

            user_places_review = PlacesReview.query.filter_by(user_id=specific_response.id).all()

            review_likes_count = []
            if len(user_places_review)>0:
                for i in user_places_review:
                    liked_places_review = PlacesReviewLike.query.filter_by(review_id=i.id).count()
                    if liked_places_review > 0:
                        review_likes_count.append(liked_places_review)


            user_things_review = ThingsReview.query.filter_by(user_id=specific_response.id).all()
            if len(user_things_review)>0:
                for i in user_things_review:
                    liked_things_review = ThingsReviewLike.query.filter_by(review_id=specific_response.id).count()
                    if liked_things_review > 0:
                        review_likes_count.append(liked_things_review)

            total_review_likes_count = '0'
            if len(review_likes_count)>0:
                total_review_likes_count = str(sum(review_likes_count))

            total_followers = Follow.query.filter_by(to_id = specific_response.id).count()
            user_feed_data = Feed.query.filter_by(user_id  = specific_response.id).all()

            total_status_likes = []

            if len(user_feed_data)>0:
                for i in user_feed_data:
                    feed_likes = FeedLike.query.filter_by(feed_id = i.id).count()
                    if feed_likes > 0:
                        total_status_likes.append(feed_likes)

            get_approved_reviews_likes = ProfileReviewLike.query.filter_by(main_user_id = specific_response.id).count()
            total_user_photos_likes = LikeUserPhotos.query.filter_by(main_user_id = specific_response.id).count()

            age = ''
            if specific_response.age is not None and specific_response.age != "0000-00-00":
                birthdate_datetime = datetime.combine(specific_response.age, datetime.min.time())
                age = (datetime.utcnow() - birthdate_datetime).days // 365

            check_fav = FavoriteUser.query.filter_by(by_id=active_user.id, to_id=specific_response.id).first()

            response_dict = {'user_id': str(specific_response.id),
                             'user_name': specific_response.fullname,
                             'user_image': specific_response.image_path,
                             'state': specific_response.state if specific_response.state is not None else '',
                             'city': specific_response.city if specific_response.city is not None else '',
                             'badge': badge,
                             'matches_count': count_value,
                             'about_me': specific_response.about_me if specific_response.about_me is not None else '',
                             'college': college,
                             'sexuality': sexuality,
                             'relationship_status': relationship_status,
                             'looking_for': looking_for,
                             'total_liked_Recommendation': str(total_liked_Recommendation),
                             'total_liked_questions_answer': str(total_liked_questions_answer),
                             'total_review_likes_count': total_review_likes_count,
                             'total_followers': str(total_followers),
                             'total_status_likes': str(sum(total_status_likes)),
                             'total_profile_review_like': str(get_approved_reviews_likes),
                             'total_user_photos_likes': str(total_user_photos_likes),
                             'new_bio': specific_response.new_bio if specific_response.new_bio is not None else '',
                             'age': str(age),
                             'is_favorite': bool(check_fav)

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
        return jsonify({'status': 1, 'data': response_list, 'messege': 'Sucess', 'pagination': pagination_info,'total_matches_count': str(user_data_count)})
    else:
        return jsonify({'status': 1, 'data': [], 'messege': 'You have zero matches. Click on Save to get started','pagination_info': pagination_info,'total_matches_count': str(user_data_count)})


# @user_view_v5.route('/homepage_filter', methods=['GET', 'POST'])
# @token_required
# def homepage_filter(active_user):
#     if request.method == 'POST':
#         page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#         per_page = 10  # Number of items per page
#
#         current_date = func.current_date()
#         blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#         blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#
#         gender = request.json.get('gender')
#         gender_list = []
#         if gender == 0:
#             gender_list.append("Male")
#         if gender == 1:
#             gender_list.append("Female")
#         # if gender == 2:
#         #     gender_list.append("Other")
#         if gender == 2:
#             gender_list.extend(['Male', 'Female'])
#
#         age_start = request.json.get('age_start')
#
#         age_end = request.json.get('age_end')
#
#         country = request.json.get('country')
#         state = request.json.get('state')
#         city = request.json.get('city')
#
#         # age_expression = func.timestampdiff(text('YEAR'), User.age, current_date)
#
#         active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
#
#         # Subquery for match counts
#         matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('community_matches'))
#                         .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
#                         .group_by(SavedCommunity.user_id)
#                         .subquery())
#
#         # Filters for age between age_start and age_end
#         # age_filter = and_(age_expression >= age_start, age_expression <= age_end)
#         query = (db.session.query(User, matches_subq.c.matches).outerjoin(matches_subq,
#                                                                           User.id == matches_subq.c.user_id).filter(
#             User.gender.in_(gender_list),
#             User.id != active_user.id,
#             User.is_block != True, User.deleted != True,
#             User.id.not_in(blocked_user_ids),
#             User.id.not_in(blocked_by_user_ids)).filter(matches_subq.c.matches != None).order_by(
#             matches_subq.c.matches.desc()))
#         if country:
#             query = query.filter(func.lower(User.country) == country.lower())
#         if state:
#             query = query.filter(func.lower(User.state) == state.lower())
#         if city:
#             query = query.filter(func.lower(User.city) == city.lower())
#
#         user_list = query.paginate(page=page, per_page=per_page, error_out=False)
#         has_next = user_list.has_next  # Check if there is a next page
#         total_pages = user_list.pages  # Total number of pages
#
#         # Pagination information
#         pagination_info = {
#             "current_page": page,
#             "has_next": has_next,
#             "per_page": per_page,
#             "total_pages": total_pages,
#         }
#
#         response_list = []
#         if user_list.items:
#             for specific_response, count in user_list.items:
#                 count_value = str(count)
#                 if not count:
#                     count_value = '0'
#                 badge = ""
#                 if specific_response.badge_name is not None:
#                     if specific_response.badge_name == "I'll Buy Us Coffee":
#                         badge = "☕"
#                     if specific_response.badge_name == "I'll Buy Us Food":
#                         badge = "🍔"
#
#                     if specific_response.badge_name == "Activity Badge":
#                         badge = "🚴"
#                     if specific_response.badge_name == "Best Friend Forever Badge":
#                         badge = "🧑‍🤝‍🧑"
#                     if specific_response.badge_name == "Luxury Badge":
#                         badge = "🚁"
#                     if specific_response.badge_name == "Lavish Badge":
#                         badge = "💎"
#
#                 college = ""
#                 if specific_response.college is not None:
#                     college = specific_response.college
#                 sexuality = ""
#                 if specific_response.sexuality is not None:
#                     sexuality = specific_response.sexuality
#
#                 relationship_status = ""
#                 if specific_response.relationship_status is not None:
#                     relationship_status = specific_response.relationship_status
#
#                 looking_for = ""
#                 if specific_response.looking_for is not None:
#                     looking_for = specific_response.looking_for
#
#                 total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=specific_response.id).count()
#                 total_liked_questions_answer = LikeUserAnswer.query.filter_by(main_user_id=specific_response.id).count()
#
#                 user_places_review = PlacesReview.query.filter_by(user_id=specific_response.id).all()
#
#                 review_likes_count = []
#                 if len(user_places_review) > 0:
#                     for i in user_places_review:
#                         liked_places_review = PlacesReviewLike.query.filter_by(review_id=i.id).count()
#                         if liked_places_review > 0:
#                             review_likes_count.append(liked_places_review)
#
#                 user_things_review = ThingsReview.query.filter_by(user_id=specific_response.id).all()
#                 if len(user_things_review) > 0:
#                     for i in user_things_review:
#                         liked_things_review = ThingsReviewLike.query.filter_by(review_id=specific_response.id).count()
#                         if liked_things_review > 0:
#                             review_likes_count.append(liked_things_review)
#
#                 total_review_likes_count = '0'
#                 if len(review_likes_count) > 0:
#                     total_review_likes_count = str(sum(review_likes_count))
#
#                 total_followers = Follow.query.filter_by(to_id=specific_response.id).count()
#
#                 user_feed_data = Feed.query.filter_by(user_id=specific_response.id).all()
#
#                 total_status_likes = []
#
#                 if len(user_feed_data) > 0:
#                     for i in user_feed_data:
#                         feed_likes = FeedLike.query.filter_by(feed_id=i.id).count()
#                         if feed_likes > 0:
#                             total_status_likes.append(feed_likes)
#
#                 get_approved_reviews_likes = ProfileReviewLike.query.filter_by(
#                     main_user_id=specific_response.id).count()
#                 total_user_photos_likes = LikeUserPhotos.query.filter_by(main_user_id=specific_response.id).count()
#
#                 response_dict = {'user_id': str(specific_response.id),
#                                  'user_name': specific_response.fullname,
#                                  'user_image': specific_response.image_path
#                     ,
#                                  'state': specific_response.state,
#                                  'city': specific_response.city,
#                                  'badge': badge,
#                                  'matches_count': count_value,
#                                  'about_me': specific_response.about_me if specific_response.about_me is not None else '',
#                                  'college': college,
#                                  'sexuality': sexuality,
#                                  'relationship_status': relationship_status,
#                                  'looking_for': looking_for,
#                                  'new_bio': specific_response.new_bio if specific_response.new_bio is not None else '',
#                                  'total_liked_Recommendation': str(total_liked_Recommendation),
#                                  'total_liked_questions_answer': str(total_liked_questions_answer),
#                                  'total_review_likes_count': total_review_likes_count,
#                                  'total_followers': str(total_followers),
#                                  'total_status_likes': str(sum(total_status_likes)),
#                                  'total_profile_review_like': str(get_approved_reviews_likes),
#                                  'total_user_photos_likes': str(total_user_photos_likes)
#
#                                  }
#
#                 response_list.append(response_dict)
#
#         if len(response_list) > 0:
#
#             return jsonify({'status': 1, 'data': response_list,
#                             'messege': '', 'pagination': pagination_info})
#         else:
#             pagination_info = {
#                 "current_page": 1,
#                 "has_next": False,
#                 "per_page": 10,
#                 "total_pages": 1,
#             }
#             return jsonify({'status': 1, 'pagination': pagination_info, 'data': [],
#                             'messege': 'You have zero matches. Click on Save to get started',
#                             })
#
#     filter_dict = {'relationships': 0,
#                    'gender': 0,
#                    'age_start': '18',
#                    'age_end': '40',
#                    'sexuality': 0,
#                    'relationship_status': 0}
#
#     return jsonify({'status': 1, 'is_subscription': active_user.is_subscription_badge, 'data': filter_dict,
#                     })


@user_view_v5.route('/homepage_filter', methods=['GET', 'POST'])
@token_required
def homepage_filter(active_user):
    if request.method == 'POST':
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 30  # Number of items per page

        current_date = func.current_date()
        blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
        blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

        gender = request.json.get('gender')
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

        age_end = request.json.get('age_end')

        country = request.json.get('country')
        state = request.json.get('state')
        city = request.json.get('city')

        # age_expression = func.timestampdiff(text('YEAR'), User.age, current_date)

        active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
        active_user_things_saved_ids = [j.created_id for j in active_user.save_things_community_id]

        # Subquery for match counts
        matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('community_matches'))
                        .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
                        .group_by(SavedCommunity.user_id)
                        .subquery())

        things_matches_subq = (
            db.session.query(SavedThingsCommunity.user_id, func.count().label('things_matches'))
                .filter(SavedThingsCommunity.created_id.in_(active_user_things_saved_ids))
                .group_by(SavedThingsCommunity.user_id)
                .subquery()
        )

        # Filters for age between age_start and age_end
        # age_filter = and_(age_expression >= age_start, age_expression <= age_end)
        query = (
            db.session.query(
                User,
                (func.coalesce(matches_subq.c.community_matches, 0) +
                 func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches')
            )
                .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
                .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
                .filter(
                User.gender.in_(gender_list),
                User.id != active_user.id,
                User.is_block != True,
                User.deleted != True,
                User.id.not_in(blocked_user_ids),
                User.id.not_in(blocked_by_user_ids)
            )
                .filter(
                (matches_subq.c.community_matches != None) |
                (things_matches_subq.c.things_matches != None)
            )
                .order_by(
                (func.coalesce(matches_subq.c.community_matches, 0) +
                 func.coalesce(things_matches_subq.c.things_matches, 0)).desc()
            )
        )
        if country:
            query = query.filter(func.lower(User.country) == country.lower())
        if state:
            query = query.filter(func.lower(User.state) == state.lower())
        if city:
            query = query.filter(func.lower(User.city) == city.lower())

        user_data_count = query.count()
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
                    if specific_response.badge_name == "I'll Buy Us Coffee":
                        badge = "☕"
                    if specific_response.badge_name == "I'll Buy Us Food":
                        badge = "🍔"

                    if specific_response.badge_name == "I’ll buy us food":
                        badge = "🍟"

                    if specific_response.badge_name == "I’ll buy us drinks":
                        badge = "☕"

                    if specific_response.badge_name == "Activity Badge":
                        badge = "🚴"
                    if specific_response.badge_name == "Best Friend Forever Badge":
                        badge = "🧑‍🤝‍🧑"
                    if specific_response.badge_name == "Luxury Badge":
                        badge = "🚁"
                    if specific_response.badge_name == "Lavish Badge":
                        badge = "💎"

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

                total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=specific_response.id).count()

                total_liked_questions_answer = LikeUserAnswer.query.filter_by(main_user_id=specific_response.id).count()

                user_places_review = PlacesReview.query.filter_by(user_id=specific_response.id).all()

                review_likes_count = []
                if len(user_places_review) > 0:
                    for i in user_places_review:
                        liked_places_review = PlacesReviewLike.query.filter_by(review_id=i.id).count()
                        if liked_places_review > 0:
                            review_likes_count.append(liked_places_review)

                user_things_review = ThingsReview.query.filter_by(user_id=specific_response.id).all()
                if len(user_things_review) > 0:
                    for i in user_things_review:
                        liked_things_review = ThingsReviewLike.query.filter_by(review_id=specific_response.id).count()
                        if liked_things_review > 0:
                            review_likes_count.append(liked_things_review)

                total_review_likes_count = '0'
                if len(review_likes_count) > 0:
                    total_review_likes_count = str(sum(review_likes_count))

                total_followers = Follow.query.filter_by(to_id=specific_response.id).count()

                user_feed_data = Feed.query.filter_by(user_id=specific_response.id).all()

                total_status_likes = []

                if len(user_feed_data) > 0:
                    for i in user_feed_data:
                        feed_likes = FeedLike.query.filter_by(feed_id=i.id).count()
                        if feed_likes > 0:
                            total_status_likes.append(feed_likes)

                age = ''
                if specific_response.age is not None and specific_response.age != "0000-00-00":
                    birthdate_datetime = datetime.combine(specific_response.age, datetime.min.time())
                    age = (datetime.utcnow() - birthdate_datetime).days // 365

                check_fav = FavoriteUser.query.filter_by(by_id=active_user.id, to_id=specific_response.id).first()

                response_dict = {'user_id': str(specific_response.id),
                                 'user_name': specific_response.fullname,
                                 'user_image': specific_response.image_path
                    ,
                                 'state': specific_response.state,
                                 'city': specific_response.city,
                                 'badge': badge,
                                 'matches_count': count_value,
                                 'about_me': specific_response.about_me if specific_response.about_me is not None else '',
                                 'college': college,
                                 'sexuality': sexuality,
                                 'relationship_status': relationship_status,
                                 'looking_for': looking_for,
                             'total_liked_Recommendation': str(total_liked_Recommendation),
                             'total_liked_questions_answer': str(total_liked_questions_answer),
                             'total_review_likes_count': total_review_likes_count,
                                 'total_followers':str(total_followers),
                             'total_status_likes': str(sum(total_status_likes)),
                             'new_bio': specific_response.new_bio if specific_response.new_bio is not None else '',
                                 'age': str(age),
                                 'is_favorite': bool(check_fav)

                                 }

                response_list.append(response_dict)

        if len(response_list) > 0:

            return jsonify({'status': 1, 'data': response_list,
                            'messege': '', 'pagination': pagination_info,'total_matches_count': str(user_data_count)})
        else:
            pagination_info = {
                "current_page": 1,
                "has_next": False,
                "per_page": 10,
                "total_pages": 1,
            }
            return jsonify({'status': 1, 'data': [],
                            'messege': 'You have zero matches. Click on Save to get started','pagination_info': pagination_info,'total_matches_count': str(user_data_count)
                            })

    filter_dict = {'relationships': 0,
                   'gender': 0,
                   'age_start': '18',
                   'age_end': '40',
                   'sexuality': 0,
                   'relationship_status': 0}

    return jsonify({'status': 1, 'is_subscription': active_user.is_subscription_badge, 'data': filter_dict,'total_matches_count': str(user_data_count)
                    })


@user_view_v5.route('/liked_category_list', methods=['GET', 'POST'])
@token_required
def liked_places_category_list(active_user):
    # i am not added delete and block user condition for calculate count
    filter_text = request.json.get('filter_text')
    print('filter_textttttttttttttttttttttttttttttttttttttttttt', filter_text)
    tab = request.json.get('tab')
    # recommendation_tab = request.json.get('recommendation_tab')
    search_text = request.json.get('search_text')

    notification_count = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).count()

    category_list = []

    if tab == 0:

        # categories_with_count = db.session.query(
        #     Category,
        #     func.count(CreatedCommunity.id).label('words_count')).outerjoin(CreatedCommunity).group_by(
        #     Category.id).order_by(func.count(CreatedCommunity.id).desc()).all()

        query = db.session.query(
            Category,
            func.count(CreatedCommunity.id).label('words_count')
        ).outerjoin(CreatedCommunity).group_by(Category.id)

        if search_text and search_text != '':
            query = query.filter(
                func.lower(Category.category_name).like(f"%{search_text.lower()}%")
            )

        query = query.order_by(func.count(CreatedCommunity.id).desc())

        categories_with_count = query.all()

        # category_list = [category.as_dict(str(count)) for category, count in categories_with_count]
        category_list = []

        if categories_with_count:
            for category, count in categories_with_count:
                check_is_saved = SavedCommunity.query.filter_by(category_id = category.id,is_saved = True,user_id = active_user.id).first()
                if check_is_saved:
                    category_list.append(category.as_dict(str(count)))

        if filter_text == 1:
            sort_key = lambda d: d['category_name']
            reverse = False
        elif filter_text == 2:
            sort_key = lambda d: d['category_name']
            reverse = True
        elif filter_text == 3:
            sort_key = lambda d: d['id']
            reverse = True
        elif filter_text == 4:
            sort_key = lambda d: d['id']
            reverse = False
        else:
            sort_key = lambda d: d['words_count']
            reverse = True

            if len(category_list) > 0:
                return jsonify({'status': 1, 'messege': 'Success',
                                'category_list': category_list,'notification_count': str(notification_count)})
            else:
                return jsonify(
                    {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

        if len(category_list) > 0:
            return jsonify({'status': 1, 'messege': 'Success',
                            'category_list': sorted(category_list, key=sort_key, reverse=reverse),'notification_count': str(notification_count)})
        else:
            return jsonify(
                {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

    if tab == 1:
        # things_category = ThingsCategory.query.all()

        query = (
            db.session.query(
                ThingsCategory,
                func.count(CreatedThingsCommunity.id).label('words_count')
            )
                .outerjoin(CreatedThingsCommunity, ThingsCategory.id == CreatedThingsCommunity.category_id)
                .group_by(ThingsCategory.id)
        )

        # query = ThingsCategory.query

        if search_text and search_text != '':
            query = query.filter(
                func.lower(ThingsCategory.category_name).like(f"%{search_text.lower()}%")
            )
        # query = query.order_by(ThingsCategory.id.desc())

        query = query.order_by(func.count(CreatedThingsCommunity.id).desc())

        categories_with_count = query.all()

        # category_list = [category.as_dict(str(count)) for category, count in categories_with_count]

        category_list = []

        if categories_with_count:
            for category, count in categories_with_count:
                check_is_saved = SavedThingsCommunity.query.filter_by(category_id=category.id, is_saved=True,
                                                                user_id=active_user.id).first()
                if check_is_saved:
                    category_list.append(category.as_dict(str(count)))

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

    # if tab == 3:
    #     if not recommendation_tab:
    #         return jsonify({'status': 0, 'messege': 'Please select recommendation tab'})
    #
    #     category_object_list = []
    #
    #     if recommendation_tab == 1:
    #
    #         get_places_recommendation_data = PlacesRecommendation.query.filter_by(user_id=active_user.id).all()
    #
    #         if len(get_places_recommendation_data) > 0:
    #
    #             for i in get_places_recommendation_data:
    #                 if not i.places_recommendation.community_places_id in category_object_list:
    #                     category_object_list.append(i.places_recommendation.community_places_id)
    #
    #     if recommendation_tab == 2:
    #
    #         get_things_recommendation_data = ThingsRecommendation.query.filter_by(user_id=active_user.id).all()
    #
    #         if len(get_things_recommendation_data) > 0:
    #
    #             for i in get_things_recommendation_data:
    #                 if not i.things_recommendation.community_things_id in category_object_list:
    #                     category_object_list.append(i.things_recommendation.community_things_id)
    #     final_list = [i.as_dict() for i in category_object_list]
    #
    #     if len(final_list) > 0:
    #         category_list.extend(final_list)

    if len(category_list) > 0:
        return jsonify(
            {'status': 1, 'messege': 'Success', 'category_list': sorted(category_list, key=sort_key, reverse=reverse),'notification_count': str(notification_count)})
    else:
        return jsonify(
            {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

# @user_view_v5.route('/category_list', methods=['GET', 'POST'])
# @token_required
# def category_list(active_user):
#     # i am not added delete and block user condition for calculate count
#     filter_text = request.json.get('filter_text')
#     print('filter_textttttttttttttttttttttttttttttttttttttttttt', filter_text)
#     tab = request.json.get('tab')
#     # recommendation_tab = request.json.get('recommendation_tab')
#     search_text = request.json.get('search_text')
#
#     notification_count = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).count()
#
#     category_list = []
#
#     if tab == 0 or tab == 1:
#
#         # categories_with_count = db.session.query(
#         #     Category,
#         #     func.count(CreatedCommunity.id).label('words_count')).outerjoin(CreatedCommunity).group_by(
#         #     Category.id).order_by(func.count(CreatedCommunity.id).desc()).all()
#
#         query = db.session.query(
#             Category,
#             func.count(CreatedCommunity.id).label('words_count')
#         ).outerjoin(CreatedCommunity).group_by(Category.id)
#
#         if search_text and search_text != '':
#             query = query.filter(
#                 func.lower(Category.category_name).like(f"%{search_text.lower()}%")
#             )
#
#         query = query.order_by(func.count(CreatedCommunity.id).desc())
#
#         categories_with_count = query.all()
#
#         # category_list = [category.as_dict(str(count)) for category, count in categories_with_count]
#         category_list = []
#
#         if categories_with_count:
#             for category, count in categories_with_count:
#                 if tab == 1:
#                     check_is_saved = SavedCommunity.query.filter_by(category_id=category.id, is_saved=True,
#                                                                     user_id=active_user.id).first()
#                     if check_is_saved:
#                         category_list.append(category.as_dict(str(count)))
#                 else:
#                     category_list.append(category.as_dict(str(count)))
#
#         if filter_text == 1:
#             sort_key = lambda d: d['category_name']
#             reverse = False
#         elif filter_text == 2:
#             sort_key = lambda d: d['category_name']
#             reverse = True
#         elif filter_text == 3:
#             sort_key = lambda d: d['id']
#             reverse = True
#         elif filter_text == 4:
#             sort_key = lambda d: d['id']
#             reverse = False
#         else:
#             sort_key = lambda d: d['words_count']
#             reverse = True
#
#             if len(category_list) > 0:
#                 return jsonify({'status': 1, 'messege': 'Success',
#                                 'category_list': category_list,'notification_count': str(notification_count)})
#             else:
#                 return jsonify(
#                     {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})
#
#         if len(category_list) > 0:
#             return jsonify({'status': 1, 'messege': 'Success',
#                             'category_list': sorted(category_list, key=sort_key, reverse=reverse),'notification_count': str(notification_count)})
#         else:
#             return jsonify(
#                 {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})
#
#     if tab == 2 or tab == 3:
#         # things_category = ThingsCategory.query.all()
#
#         query = (
#             db.session.query(
#                 ThingsCategory,
#                 func.count(CreatedThingsCommunity.id).label('words_count')
#             )
#                 .outerjoin(CreatedThingsCommunity, ThingsCategory.id == CreatedThingsCommunity.category_id)
#                 .group_by(ThingsCategory.id)
#         )
#
#         # query = ThingsCategory.query
#
#         if search_text and search_text != '':
#             query = query.filter(
#                 func.lower(ThingsCategory.category_name).like(f"%{search_text.lower()}%")
#             )
#         # query = query.order_by(ThingsCategory.id.desc())
#
#         query = query.order_by(func.count(CreatedThingsCommunity.id).desc())
#
#         categories_with_count = query.all()
#
#         # category_list = [category.as_dict(str(count)) for category, count in categories_with_count]
#
#         category_list = []
#
#         if categories_with_count:
#             for category, count in categories_with_count:
#                 if tab == 3:
#                     check_is_saved = SavedThingsCommunity.query.filter_by(category_id=category.id, is_saved=True,
#                                                                           user_id=active_user.id).first()
#                     if check_is_saved:
#                         category_list.append(category.as_dict(str(count)))
#                 else:
#                     category_list.append(category.as_dict(str(count)))
#
#     if tab == 4:
#         questions_category = QuestionsCategory.query.join(QuestionsCategory.category_que).filter(
#             QuestionsCategory.category_que.any()).all()
#
#         # Alternatively, using exists
#         # things_category = ThingsCategory.query.filter(
#         #     ThingsCategory.category_que.any()
#         # ).all()
#
#         category_list = [i.as_dict() for i in questions_category]
#
#     if filter_text == 1:
#         sort_key = lambda d: d['category_name']
#         reverse = True
#     elif filter_text == 2:
#         sort_key = lambda d: d['id']
#         reverse = True
#     elif filter_text == 3:
#         sort_key = lambda d: d['id']
#         reverse = False
#     else:
#         sort_key = lambda d: d['category_name']
#         reverse = False
#
#     # if tab == 3:
#     #     if not recommendation_tab:
#     #         return jsonify({'status': 0, 'messege': 'Please select recommendation tab'})
#     #
#     #     category_object_list = []
#     #
#     #     if recommendation_tab == 1:
#     #
#     #         get_places_recommendation_data = PlacesRecommendation.query.filter_by(user_id=active_user.id).all()
#     #
#     #         if len(get_places_recommendation_data) > 0:
#     #
#     #             for i in get_places_recommendation_data:
#     #                 if not i.places_recommendation.community_places_id in category_object_list:
#     #                     category_object_list.append(i.places_recommendation.community_places_id)
#     #
#     #     if recommendation_tab == 2:
#     #
#     #         get_things_recommendation_data = ThingsRecommendation.query.filter_by(user_id=active_user.id).all()
#     #
#     #         if len(get_things_recommendation_data) > 0:
#     #
#     #             for i in get_things_recommendation_data:
#     #                 if not i.things_recommendation.community_things_id in category_object_list:
#     #                     category_object_list.append(i.things_recommendation.community_things_id)
#     #     final_list = [i.as_dict() for i in category_object_list]
#     #
#     #     if len(final_list) > 0:
#     #         category_list.extend(final_list)
#
#     if len(category_list) > 0:
#         return jsonify(
#             {'status': 1, 'messege': 'Success', 'category_list': sorted(category_list, key=sort_key, reverse=reverse),'notification_count': str(notification_count)})
#     else:
#         return jsonify(
#             {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

# @user_view_v5.route('/category_list', methods=['GET', 'POST'])
# @token_required
# def category_list(active_user):
#     # i am not added delete and block user condition for calculate count
#     filter_text = request.json.get('filter_text')
#     print('filter_textttttttttttttttttttttttttttttttttttttttttt', filter_text)
#     tab = request.json.get('tab')
#     # recommendation_tab = request.json.get('recommendation_tab')
#     search_text = request.json.get('search_text')
#
#     notification_count = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).count()
#
#     category_list = []
#
#     if tab == 0:
#
#         # categories_with_count = db.session.query(
#         #     Category,
#         #     func.count(CreatedCommunity.id).label('words_count')).outerjoin(CreatedCommunity).group_by(
#         #     Category.id).order_by(func.count(CreatedCommunity.id).desc()).all()
#
#         query = db.session.query(
#             Category,
#             func.count(CreatedCommunity.id).label('words_count')
#         ).outerjoin(CreatedCommunity).group_by(Category.id)
#
#         if search_text and search_text != '':
#             query = query.filter(
#                 func.lower(Category.category_name).like(f"%{search_text.lower()}%")
#             )
#
#         query = query.order_by(func.count(CreatedCommunity.id).desc())
#
#         categories_with_count = query.all()
#
#         category_list = [category.as_dict(str(count)) for category, count in categories_with_count]
#         # category_list = []
#         #
#         # if categories_with_count:
#         #     for category, count in categories_with_count:
#         #         if tab == 1:
#         #             check_is_saved = SavedCommunity.query.filter_by(category_id=category.id, is_saved=True,
#         #                                                             user_id=active_user.id).first()
#         #             if check_is_saved:
#         #                 category_list.append(category.as_dict(str(count)))
#         #         else:
#         #             category_list.append(category.as_dict(str(count)))
#
#         if filter_text == 1:
#             sort_key = lambda d: d['category_name']
#             reverse = False
#         elif filter_text == 2:
#             sort_key = lambda d: d['category_name']
#             reverse = True
#         elif filter_text == 3:
#             sort_key = lambda d: d['id']
#             reverse = True
#         elif filter_text == 4:
#             sort_key = lambda d: d['id']
#             reverse = False
#         else:
#             sort_key = lambda d: d['words_count']
#             reverse = True
#
#             if len(category_list) > 0:
#                 return jsonify({'status': 1, 'messege': 'Success',
#                                 'category_list': category_list,'notification_count': str(notification_count)})
#             else:
#                 return jsonify(
#                     {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})
#
#         if len(category_list) > 0:
#             return jsonify({'status': 1, 'messege': 'Success',
#                             'category_list': sorted(category_list, key=sort_key, reverse=reverse),'notification_count': str(notification_count)})
#         else:
#             return jsonify(
#                 {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})
#
#     if tab == 1:
#         # things_category = ThingsCategory.query.all()
#
#         query = (
#             db.session.query(
#                 ThingsCategory,
#                 func.count(CreatedThingsCommunity.id).label('words_count')
#             )
#                 .outerjoin(CreatedThingsCommunity, ThingsCategory.id == CreatedThingsCommunity.category_id)
#                 .group_by(ThingsCategory.id)
#         )
#
#         # query = ThingsCategory.query
#
#         if search_text and search_text != '':
#             query = query.filter(
#                 func.lower(ThingsCategory.category_name).like(f"%{search_text.lower()}%")
#             )
#         # query = query.order_by(ThingsCategory.id.desc())
#
#         query = query.order_by(func.count(CreatedThingsCommunity.id).desc())
#
#         categories_with_count = query.all()
#
#         category_list = [category.as_dict(str(count)) for category, count in categories_with_count]
#
#         # category_list = []
#         #
#         # if categories_with_count:
#         #     for category, count in categories_with_count:
#         #         if tab == 3:
#         #             check_is_saved = SavedThingsCommunity.query.filter_by(category_id=category.id, is_saved=True,
#         #                                                                   user_id=active_user.id).first()
#         #             if check_is_saved:
#         #                 category_list.append(category.as_dict(str(count)))
#         #         else:
#         #             category_list.append(category.as_dict(str(count)))
#
#     if tab == 2:
#         questions_category = QuestionsCategory.query.join(QuestionsCategory.category_que).filter(
#             QuestionsCategory.category_que.any()).all()
#
#         # Alternatively, using exists
#         # things_category = ThingsCategory.query.filter(
#         #     ThingsCategory.category_que.any()
#         # ).all()
#
#         category_list = [i.as_dict() for i in questions_category]
#
#     if filter_text == 1:
#         sort_key = lambda d: d['category_name']
#         reverse = True
#     elif filter_text == 2:
#         sort_key = lambda d: d['id']
#         reverse = True
#     elif filter_text == 3:
#         sort_key = lambda d: d['id']
#         reverse = False
#     else:
#         sort_key = lambda d: d['category_name']
#         reverse = False
#
#     # if tab == 3:
#     #     if not recommendation_tab:
#     #         return jsonify({'status': 0, 'messege': 'Please select recommendation tab'})
#     #
#     #     category_object_list = []
#     #
#     #     if recommendation_tab == 1:
#     #
#     #         get_places_recommendation_data = PlacesRecommendation.query.filter_by(user_id=active_user.id).all()
#     #
#     #         if len(get_places_recommendation_data) > 0:
#     #
#     #             for i in get_places_recommendation_data:
#     #                 if not i.places_recommendation.community_places_id in category_object_list:
#     #                     category_object_list.append(i.places_recommendation.community_places_id)
#     #
#     #     if recommendation_tab == 2:
#     #
#     #         get_things_recommendation_data = ThingsRecommendation.query.filter_by(user_id=active_user.id).all()
#     #
#     #         if len(get_things_recommendation_data) > 0:
#     #
#     #             for i in get_things_recommendation_data:
#     #                 if not i.things_recommendation.community_things_id in category_object_list:
#     #                     category_object_list.append(i.things_recommendation.community_things_id)
#     #     final_list = [i.as_dict() for i in category_object_list]
#     #
#     #     if len(final_list) > 0:
#     #         category_list.extend(final_list)
#
#     if len(category_list) > 0:
#         return jsonify(
#             {'status': 1, 'messege': 'Success', 'category_list': sorted(category_list, key=sort_key, reverse=reverse),'notification_count': str(notification_count)})
#     else:
#         return jsonify(
#             {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

# last one 12/04/2025
# @user_view_v5.route('/category_list', methods=['GET', 'POST'])
# @token_required
# def category_list(active_user):
#     # i am not added delete and block user condition for calculate count
#     # filter_text = request.json.get('filter_text')
#     # print('filter_textttttttttttttttttttttttttttttttttttttttttt', filter_text)
#     tab = request.json.get('tab')
#     # recommendation_tab = request.json.get('recommendation_tab')
#     search_text = request.json.get('search_text')
#
#     notification_count = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).count()
#
#     category_list = []
#
#     if tab == 0:
#
#         query = db.session.query(
#             Category,
#             func.count(CreatedCommunity.id).label('words_count'),
#             func.coalesce(func.sum(CategoryVisited.visited_counts), 0).label('total_visited')
#         ).outerjoin(CreatedCommunity) \
#             .outerjoin(CategoryVisited, Category.id == CategoryVisited.category_id) \
#             .group_by(Category.id) \
#             .order_by(desc('total_visited'))
#
#         if search_text and search_text != '':
#             query = query.filter(
#                 func.lower(Category.category_name).like(f"%{search_text.lower()}%")
#             )
#
#         # query = query.order_by(func.count(CreatedCommunity.id).desc())
#
#         categories_with_count = query.all()
#
#         category_list = [category.as_dict(str(count)) for category, count,visited_counts in categories_with_count]
#
#         if len(category_list) > 0:
#             return jsonify({'status': 1, 'messege': 'Success',
#                             'category_list': category_list,'notification_count': str(notification_count)})
#         else:
#             return jsonify(
#                 {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})
#
#     if tab == 1:
#
#         query = (
#     db.session.query(
#         ThingsCategory,
#         func.count(CreatedThingsCommunity.id).label('words_count'),
#         func.coalesce(func.sum(ThingsCategoryVisited.visited_counts), 0).label('total_visited')
#     )
#     .outerjoin(CreatedThingsCommunity, ThingsCategory.id == CreatedThingsCommunity.category_id)
#     .outerjoin(ThingsCategoryVisited, ThingsCategory.id == ThingsCategoryVisited.category_id)
#     .group_by(ThingsCategory.id)
#     .order_by(desc('total_visited'))
# )
#
#         if search_text and search_text != '':
#             query = query.filter(
#                 func.lower(ThingsCategory.category_name).like(f"%{search_text.lower()}%")
#             )
#
#         #query = query.order_by(func.count(CreatedThingsCommunity.id).desc())
#
#         categories_with_count = query.all()
#
#         category_list = [category.as_dict(str(count)) for category, count,visited_counts in categories_with_count]
#
#     if tab == 2:
#         questions_category = QuestionsCategory.query.join(QuestionsCategory.category_que).filter(
#             QuestionsCategory.category_que.any()).all()
#
#         category_list = [i.as_dict() for i in questions_category]
#
#     if len(category_list) > 0:
#         return jsonify(
#             {'status': 1, 'messege': 'Success', 'category_list': category_list,'notification_count': str(notification_count)})
#     else:
#         return jsonify(
#             {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

@user_view_v5.route('/merge_category_list', methods=['GET', 'POST'])
@token_required
def merge_category_list(active_user):

    category_list = []


    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    places_query = (
            db.session.query(
                Category,
                func.coalesce(func.count(
                    func.distinct(
                        case(
                            (
                                and_(
                                    SavedCommunity.user_id != active_user.id,
                                    User.deleted == False,
                                    User.is_block == False,
                                    ~SavedCommunity.user_id.in_(blocked_user_ids),
                                    ~SavedCommunity.user_id.in_(blocked_by_user_ids)
                                ),
                                SavedCommunity.user_id
                            )
                        )
                    )
                ), 0).label('community_matches')
            )
                .outerjoin(SavedCommunity, SavedCommunity.category_id == Category.id)
                .outerjoin(User, User.id == SavedCommunity.user_id)
                .group_by(Category.id)
                .order_by(desc('community_matches'))
        )

    things_query = (
            db.session.query(
                ThingsCategory,
                func.coalesce(func.count(
                    func.distinct(
                        case(
                            (and_(
                                SavedThingsCommunity.user_id != active_user.id,
                                User.deleted == False,
                                User.is_block == False,
                                ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
                                ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)
                            ), SavedThingsCommunity.user_id)
                        )
                    )
                ), 0).label('community_matches')
            )
                .outerjoin(SavedThingsCommunity, SavedThingsCommunity.category_id == ThingsCategory.id)
                .outerjoin(User, User.id == SavedThingsCommunity.user_id)
                .group_by(ThingsCategory.id)
                .order_by(desc('community_matches'))
        )

    places_categories_with_count = places_query.all()
    things_categories_with_count = things_query.all()

    places_category_list = [category.as_dict_merge(str(count)) for category, count in places_categories_with_count]
    things_category_list = [category.as_dict_merge(str(count)) for category, count in things_categories_with_count]

    # Merge both
    combined_category_list = places_category_list + things_category_list

    # Sort by count in descending order
    # Make sure count is treated as an integer
    sorted_combined_list = sorted(
        combined_category_list,
        key=lambda x: int(x.get('count', 0)),  # fallback to 0 if count missing
        reverse=True
    )

    if len(sorted_combined_list) > 0:
        return jsonify(
            {'status': 1, 'messege': 'Success', 'category_list': sorted_combined_list})
    else:
        return jsonify(
            {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet'})

@user_view_v5.route('/category_list', methods=['GET', 'POST'])
@token_required
def category_list(active_user):
    # i am not added delete and block user condition for calculate count
    # filter_text = request.json.get('filter_text')
    # print('filter_textttttttttttttttttttttttttttttttttttttttttt', filter_text)
    tab = request.json.get('tab')
    # recommendation_tab = request.json.get('recommendation_tab')
    search_text = request.json.get('search_text')

    notification_count = NewNotification.query.filter_by(to_id=active_user.id, is_read=False).count()

    category_list = []

    if tab == 0:

        active_user_saved_ids = [j.category_id for j in active_user.save_community_id]

        print('active_user_saved_ids', active_user.save_community_id)

        blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
        blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

        # query = (
        #     db.session.query(
        #         Category,
        #         func.coalesce(func.count(func.distinct(SavedCommunity.user_id)), 0).label('community_matches')
        #     )
        #         .outerjoin(SavedCommunity, SavedCommunity.category_id == Category.id)
        #         .outerjoin(User, User.id == SavedCommunity.user_id)
        #         .filter(
        #         or_(
        #             SavedCommunity.id == None,
        #             and_(
        #                 # SavedCommunity.category_id.in_(active_user_saved_ids),
        #                 SavedCommunity.user_id != active_user.id,
        #                 User.deleted == False,
        #                 User.is_block == False,
        #                 ~SavedCommunity.user_id.in_(blocked_user_ids),
        #                 ~SavedCommunity.user_id.in_(blocked_by_user_ids)
        #             )
        #         )
        #     )
        #         .group_by(Category.id)
        #         .order_by(desc('community_matches'))
        # )

        query = (
            db.session.query(
                Category,
                func.coalesce(func.count(
                    func.distinct(
                        case(
                            (
                                and_(
                                    SavedCommunity.user_id != active_user.id,
                                    User.deleted == False,
                                    User.is_block == False,
                                    ~SavedCommunity.user_id.in_(blocked_user_ids),
                                    ~SavedCommunity.user_id.in_(blocked_by_user_ids)
                                ),
                                SavedCommunity.user_id
                            )
                        )
                    )
                ), 0).label('community_matches')
            )
                .outerjoin(SavedCommunity, SavedCommunity.category_id == Category.id)
                .outerjoin(User, User.id == SavedCommunity.user_id)
                .group_by(Category.id)
                .order_by(desc('community_matches'))
        )

        if search_text and search_text != '':
            query = query.filter(
                func.lower(Category.category_name).like(f"%{search_text.lower()}%")
            )

        # query = query.order_by(func.count(CreatedCommunity.id).desc())

        categories_with_count = query.all()

        category_list = [category.as_dict(str(count)) for category, count in categories_with_count]

        if len(category_list) > 0:
            return jsonify({'status': 1, 'messege': 'Success',
                            'category_list': category_list, 'notification_count': str(notification_count)})
        else:
            return jsonify(
                {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet',
                 'notification_count': str(notification_count)})

    if tab == 1:

        active_user_things_saved_ids = [j.created_id for j in active_user.save_things_community_id]

        blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
        blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

        # query = (
        #     db.session.query(
        #         ThingsCategory,
        #         func.coalesce(func.count(func.distinct(SavedThingsCommunity.user_id)), 0).label('community_matches')
        #     )
        #         .outerjoin(SavedThingsCommunity, SavedThingsCommunity.category_id == ThingsCategory.id)
        #         .outerjoin(User, User.id == SavedThingsCommunity.user_id)
        #         .filter(
        #         or_(
        #             SavedThingsCommunity.id == None,
        #             and_(
        #                 # SavedThingsCommunity.category_id.in_(active_user_things_saved_ids),
        #                 SavedThingsCommunity.user_id != active_user.id,
        #                 User.deleted == False,
        #                 User.is_block == False,
        #                 ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
        #                 ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)
        #             )
        #         )
        #     )
        #         .group_by(ThingsCategory.id)
        #         .order_by(desc('community_matches'))
        # )

        query = (
            db.session.query(
                ThingsCategory,
                func.coalesce(func.count(
                    func.distinct(
                        case(
                            (and_(
                                SavedThingsCommunity.user_id != active_user.id,
                                User.deleted == False,
                                User.is_block == False,
                                ~SavedThingsCommunity.user_id.in_(blocked_user_ids),
                                ~SavedThingsCommunity.user_id.in_(blocked_by_user_ids)
                            ), SavedThingsCommunity.user_id)
                        )
                    )
                ), 0).label('community_matches')
            )
                .outerjoin(SavedThingsCommunity, SavedThingsCommunity.category_id == ThingsCategory.id)
                .outerjoin(User, User.id == SavedThingsCommunity.user_id)
                .group_by(ThingsCategory.id)
                .order_by(desc('community_matches'))
        )

        if search_text and search_text != '':
            query = query.filter(
                func.lower(ThingsCategory.category_name).like(f"%{search_text.lower()}%")
            )

        #query = query.order_by(func.count(CreatedThingsCommunity.id).desc())

        categories_with_count = query.all()

        category_list = [category.as_dict(str(count)) for category, count in categories_with_count]

    if tab == 2:
        questions_category = QuestionsCategory.query.join(QuestionsCategory.category_que).filter(
            QuestionsCategory.category_que.any()).all()

        category_list = [i.as_dict() for i in questions_category]

    if len(category_list) > 0:
        return jsonify(
            {'status': 1, 'messege': 'Success', 'category_list': category_list,'notification_count': str(notification_count)})
    else:
        return jsonify(
            {'status': 1, 'category_list': [], 'messege': 'Dont have any category yet','notification_count': str(notification_count)})

@user_view_v5.route('/answered_my_things_category_list', methods=['GET', 'POST'])
@token_required
def answered_my_things_category_list(active_user):
    filter_text = request.json.get('filter_text')

    get_answer_data = CategoryAns.query.filter_by(user_id=active_user.id).all()

    get_question_ids_list = []

    if len(get_answer_data) > 0:
        for i in get_answer_data:
            if not i.question_id in get_question_ids_list:
                get_question_ids_list.append(i.question_id)

    get_question_data = CategoryQue.query.filter(CategoryQue.id.in_(get_question_ids_list)).all()

    get_categories_ids_list = [i.questions_category_id for i in get_question_data]

    get_answered_category_data = QuestionsCategory.query.filter(QuestionsCategory.id.in_(get_categories_ids_list)).all()

    category_list = [i.as_dict() for i in get_answered_category_data]

    print('category_listtttttttttttttttttttt', category_list)

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
    if len(category_list) > 0:
        return jsonify(
            {'status': 1, 'messege': 'Success', 'category_list': sorted(category_list, key=sort_key, reverse=reverse)})
    else:
        return jsonify(
            {'status': 1, 'category_list': [],
             'messege': 'User has not yet provided an answer to any of the category questions'})

@user_view_v5.route('/answered_things_category_list', methods=['GET', 'POST'])
@token_required
def answered_things_category_list(active_user):
    filter_text = request.json.get('filter_text')
    user_id = request.json.get('user_id')

    get_answer_data = CategoryAns.query.filter_by(user_id=user_id).all()

    get_question_ids_list = []

    if len(get_answer_data) > 0:
        for i in get_answer_data:
            if not i.question_id in get_question_ids_list:
                get_question_ids_list.append(i.question_id)

    get_question_data = CategoryQue.query.filter(CategoryQue.id.in_(get_question_ids_list)).all()

    get_categories_ids_list = [i.questions_category_id for i in get_question_data]

    get_answered_category_data = QuestionsCategory.query.filter(QuestionsCategory.id.in_(get_categories_ids_list)).all()

    category_list = [i.as_dict() for i in get_answered_category_data]

    print('category_listtttttttttttttttttttt', category_list)

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
    if len(category_list) > 0:
        return jsonify(
            {'status': 1, 'messege': 'Success', 'category_list': sorted(category_list, key=sort_key, reverse=reverse)})
    else:
        return jsonify(
            {'status': 1, 'category_list': [],
             'messege': 'User has not yet provided an answer to any of the category questions'})


@user_view_v5.route('/users_list', methods=['GET'])
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


@user_view_v5.route('/send_friend_req', methods=['POST'])
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
                msg = f'{active_user.fullname} sent you a friend request!'
                add_notification = Notification(title=title, messege=msg, by_id=active_user.id, to_id=reciver_user.id,
                                                is_read=False, created_time=datetime.utcnow(), page='user')
                db.session.add(add_notification)
                db.session.commit()
                # if reciver_user.device_token:
                notification = push_notification(device_token=reciver_user.device_token, title=title, msg=msg,
                                                 image_url=None, device_type=reciver_user.device_type)
            else:
                title = 'Friends'
                msg = f'{active_user.fullname} sent you a friend request!'
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
                    msg = f'{active_user.fullname} Remove You From Friend list'
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
                {'status': 1, 'messege': 'This User Already Send Request To You!! Please Check In Your Request List!!'})
    else:
        return jsonify({'status': 0, 'messege': 'User Deleted There Account'})


@user_view_v5.route('/req_list', methods=['GET', 'POST'])
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


@user_view_v5.route('/req_action', methods=['POST'])
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
        msg = f'{active_user.fullname} accepted your friend request!'
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


@user_view_v5.route('/user_friends_list', methods=['POST'])
@token_required
def user_friends_list(active_user):
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'status': 0, 'messege': 'Please select user first'})

    list = []

    ls = []

    check = FriendRequest.query.filter_by(to_id=user_id, request_status=1).order_by(FriendRequest.id.desc()).all()

    checked = FriendRequest.query.filter_by(by_id=user_id, request_status=1).order_by(FriendRequest.id.desc()).all()

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
    per_page = 30  # Number of items per page

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
        return jsonify({'status': 1, 'friends_list': list, 'messege': 'Dont Have Any Friends Yet',
                        'pagination': pagination_info})

@user_view_v5.route('/friends_list', methods=['POST'])
@token_required
def friends_list(active_user):
    list = []

    ls = []

    check = FriendRequest.query.filter_by(to_id=active_user.id, request_status=1).order_by(FriendRequest.id.desc()).all()

    checked = FriendRequest.query.filter_by(by_id=active_user.id, request_status=1).order_by(FriendRequest.id.desc()).all()

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
    per_page = 30  # Number of items per page

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


@user_view_v5.route('/friends_list_id', methods=['GET', 'POST'])
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


@user_view_v5.route('/get_category', methods=['GET', 'POST'])
@token_required
def get_category(active_user):
    id = request.args.get('id')
    x = Category.query.filter_by(id=id).first()

    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxx ', x)

    return jsonify({'status': 1, 'category_data': x.as_dict()})


@user_view_v5.route('/view_profile', methods=['POST'])
@token_required
def view_profile(active_user):
    user = request.json.get('user_id')
    x = User.query.filter_by(id=user).first()
    ls = []

    check1 = FriendRequest.query.filter_by(to_id=x.id, request_status=1).all()
    checked1 = FriendRequest.query.filter_by(by_id=x.id, request_status=1).all()

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    if len(check1) > 0:
        for i in check1:
            x_delete = User.query.filter_by(id=i.by_id, deleted=False).all()
            ls.extend(x_delete)
    if len(checked1) > 0:
        for k in checked1:
            y_delete = User.query.filter_by(id=k.to_id, deleted=False).all()
            ls.extend(y_delete)

    query = (
        db.session.query(User)
            .filter(
            User.id.not_in(blocked_user_ids),
            User.id.not_in(blocked_by_user_ids), User.is_block == False, User.deleted == False
        )
            .join(Follow, Follow.to_id == User.id)
            .filter(Follow.to_id == user)
    )

    following_count = query.count()


    check = FriendRequest.query.filter_by(to_id=active_user.id, by_id=x.id, request_status=1).first()
    checked = FriendRequest.query.filter_by(by_id=active_user.id, to_id=x.id, request_status=1).first()

    # birthdate_datetime = datetime.combine(x.age, datetime.min.time())
    age = ""

    try:
        if x.age:
            if isinstance(x.age, date):
                birthdate = x.age
            elif isinstance(x.age, str) and x.age != "0000-00-00":
                birthdate = datetime.strptime(x.age, "%Y-%m-%d").date()
            else:
                birthdate = None

            if birthdate:
                birthdate_datetime = datetime.combine(birthdate, datetime.min.time())
                age = (datetime.utcnow() - birthdate_datetime).days // 365
    except:
        age = ""

    if not check and not checked:
        dict = [
            {'value': str(age), 'name': 'Age'},
            {'value': x.gender, 'name': 'Gender'},
            {'value': str(len(ls)), 'name': 'Total Friends'},
            {'value': str(following_count), 'name': 'Total Followers'},
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
            {'value': str(len(ls)), 'name': 'Total Friends'},
            {'value': str(following_count), 'name': 'Total Followers'},
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


@user_view_v5.route("/user/delete", methods=['GET', 'POST'])
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

@user_view_v5.route("/get_my_buttons_data", methods=['GET'])
@token_required
def get_my_buttons_data(active_user):

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    get_button_data = Buttons.query.all()
    # button_data = [i.as_dict() for i in get_button_data]


    dont_add = ["Favorites in common","My Info","My Friends","My Followers","My Reviews"]

    button_data = []

    if len(get_button_data)>0:
        for i in get_button_data:
            if i.button_original_name not in dont_add:
                button_data.append(i.as_dict())


    # following_count = Follow.query.filter_by(to_id=user_id).count()

    query = (
        db.session.query(User)
            .filter(
            User.id.not_in(blocked_user_ids),
            User.id.not_in(blocked_by_user_ids), User.is_block == False, User.deleted == False
        )
            .join(Follow, Follow.to_id == User.id)
            .filter(Follow.to_id == active_user.id)
    )

    following_count = query.count()

    # total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=active_user.id).count()
    total_liked_Recommendation = []

    things_reccomandations = ThingsRecommendation.query.filter_by(user_id = active_user.id).all()
    places_reccomandations = PlacesRecommendation.query.filter_by(user_id=active_user.id).all()

    if len(things_reccomandations)>0:
        for i in things_reccomandations:
            get_things_like_count = LikeRecommendation.query.filter_by(things_id = i.id).count()

            if get_things_like_count>0:
                total_liked_Recommendation.append(get_things_like_count)
    if len(places_reccomandations)>0:
        for i in places_reccomandations:
            get_places_like_count = LikeRecommendation.query.filter_by(places_id=i.id).count()

            if get_places_like_count > 0:
                total_liked_Recommendation.append(get_places_like_count)

    my_bio = active_user.new_bio if active_user.new_bio is not None else ''

    return jsonify({'status': 1, 'messege': 'Success','my_bio': my_bio, 'button_list': button_data,
                    'following_count': str(following_count),'total_liked_Recommendation': str(sum(total_liked_Recommendation))})

@user_view_v5.route("/get_buttons_data", methods=['POST'])
@token_required
def get_buttons_data(active_user):
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0, 'messege': 'user required'})

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    is_follow = 0
    follow_data = Follow.query.filter_by(by_id=active_user.id, to_id=user_id).first()

    is_friend = 0

    friend_request = FriendRequest.query.filter(
        (FriendRequest.to_id == active_user.id) & (FriendRequest.by_id == user_id)
        | (FriendRequest.by_id == active_user.id) & (FriendRequest.to_id == user_id)
    ).first()

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

    if friend_request:
        is_friend = friend_request.request_status

    if follow_data:
        is_follow = 1
    get_button_data = Buttons.query.all()

    static_remove_buttons = ["Favorites in common","My Info","My Status","What People Think Of Me","My Friends","My Followers","My Reviews","My Questionnarie","My Recommendations"]

    button_data = [i.as_dict() for i in get_button_data
    if i.button_original_name not in static_remove_buttons]

    # following_count = Follow.query.filter_by(to_id=user_id).count()

    query = (
        db.session.query(User)
            .filter(
            User.id.not_in(blocked_user_ids),
            User.id.not_in(blocked_by_user_ids), User.is_block == False, User.deleted == False
        )
            .join(Follow, Follow.to_id == User.id)
            .filter(Follow.to_id == user_id)
    )

    following_count = query.count()

    # total_liked_Recommendation = LikeRecommendation.query.filter_by(user_id=active_user.id).count()
    total_liked_Recommendation = []

    things_reccomandations = ThingsRecommendation.query.filter_by(user_id=user_id).all()
    places_reccomandations = PlacesRecommendation.query.filter_by(user_id=user_id).all()

    if len(things_reccomandations) > 0:
        for i in things_reccomandations:
            get_things_like_count = LikeRecommendation.query.filter_by(things_id=i.id).count()

            if get_things_like_count > 0:
                total_liked_Recommendation.append(get_things_like_count)
    if len(places_reccomandations) > 0:
        for i in places_reccomandations:
            get_places_like_count = LikeRecommendation.query.filter_by(places_id=i.id).count()

            if get_places_like_count > 0:
                total_liked_Recommendation.append(get_places_like_count)

    return jsonify({'status': 1, 'messege': 'Success','is_friend': is_friend,'friends_count': str(len(ls)), 'button_list': button_data, 'is_follow': is_follow,
                    'following_count': str(following_count),'total_liked_Recommendation': str(total_liked_Recommendation),'is_profile_private': active_user.is_profile_private})

# @user_view_v5.route("/matches/category_vise", methods=['POST'])
# @token_required
# def matches_category_vice(active_user):
#     user_id = request.json.get('user_id')
#     filter_text = request.json.get('filter_text')
#
#     only_user = User.query.filter_by(id=user_id).first()
#     if not only_user:
#         return jsonify({'status': 0, 'messege': 'Invalid user'})
#
#     is_follow = '0'
#     follow_data = Follow.query.filter_by(by_id = active_user.id, to_id = user_id).first()
#     if follow_data:
#         is_follow = '1'
#
#     if only_user:
#         if only_user.is_subscription_badge == True:
#             current_timestamp_ms = int(datetime.now().timestamp() * 1000)
#             if int(only_user.subscription_start_time_badge) <= current_timestamp_ms <= int(
#                     only_user.subscription_end_time_badge):
#                 pass
#         else:
#
#             only_user.is_subscription_badge = False
#             only_user.subscription_start_time_badge = None
#             only_user.subscription_end_time_badge = None
#             only_user.badge_name = None
#             only_user.product_id_badge = None
#             only_user.transaction_id_badge = None
#             only_user.purchase_date_badge = None
#             db.session.commit()
#
#     block_check = Block.query.filter_by(blocked_user=user_id, user_id=active_user.id).first()
#     if block_check:
#         is_block = True
#     else:
#         is_block = False
#
#     user_dict = {'user_name': '@' + only_user.fullname,
#                  'user_image': only_user.image_path, }
#
#     friend_request = FriendRequest.query.filter(
#         (FriendRequest.to_id == active_user.id) & (FriendRequest.by_id == user_id)
#         | (FriendRequest.by_id == active_user.id) & (FriendRequest.to_id == user_id)
#     ).first()
#
#     print('friend_requesttttttttttttttttttttttttttttttttttttt', friend_request)
#
#     if filter_text == 1:
#         sort_key = lambda d: d['community_name']
#         reverse = True
#     elif filter_text == 2:
#         sort_key = lambda d: d['created_time']
#         reverse = True
#     elif filter_text == 3:
#         sort_key = lambda d: d['created_time']
#         reverse = False
#     else:
#         sort_key = lambda d: d['community_name']
#         reverse = False
#
#     ls1 = []
#
#     for m in active_user.save_community_id:
#         community_save = SavedCommunity.query.filter_by(created_id=m.created_id, user_id=user_id).first()
#
#         if community_save:
#             ls1.append(community_save)
#
#     cat_list = Category.query.filter(Category.id.in_([c.category_id for c in ls1])).all()
#
#     dict_list1 = []
#     dict_list2 = []
#
#     res = []
#     res2 = []
#
#     [res.append(x) for x in ls1 if x not in res]
#     main_count_list = []
#
#     for category in cat_list:
#         community_list = [c.as_dict() for c in res if c.category_id == category.id]
#         dict1 = {
#             'category_name': category.category_name,
#             'community_count': str(len(community_list)),
#             'community_list': sorted(community_list, key=sort_key, reverse=reverse)
#         }
#         check_counts = (len(community_list))
#         main_count_list.append(check_counts)
#         dict_list1.append(dict1)
#
#     all_community = SavedCommunity.query.filter_by(user_id=user_id).all()
#     unmatched = [c for c in all_community if c not in ls1]
#     [res2.append(y) for y in unmatched if y not in res2]
#     cat_list2 = Category.query.filter(Category.id.in_([c.category_id for c in unmatched])).all()
#
#     for category in cat_list2:
#         community_list = [c.as_dict() for c in res2 if c.category_id == category.id]
#         dict2 = {
#             'category_name': category.category_name,
#             'community_count': str(len(community_list)),
#             'community_list': sorted(community_list, key=sort_key, reverse=reverse)
#         }
#         dict_list2.append(dict2)
#     already_send = DateRequest.query.filter(DateRequest.by_id == active_user.id, DateRequest.to_id == id).count() > 0
#     is_subscribed = False
#     if only_user.is_subscription_badge == True:
#         is_subscribed = True
#     else:
#         is_subscribed = False
#     description_box = ""
#     if only_user.description_box != None:
#         description_box = only_user.description_box
#     else:
#         description_box = ""
#     sum_count = sum(main_count_list)
#
#     if not friend_request:
#         return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 0, 'is_datereq': bool(already_send), 'user_data': user_dict,
#                         'matches': dict_list1, 'unmatches': ['this is static value'], 'filter': filter_text or 0,
#                         'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
#                         'matches_count': str(sum_count)})
#
#     elif friend_request.request_status == 2:
#         return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 2, 'is_datereq': bool(already_send), 'user_data': user_dict,
#                         'matches': dict_list1, 'unmatches': ['this is static value'], 'filter': filter_text or 0,
#                         'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
#                         'matches_count': str(sum_count)})
#
#     else:
#         return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 1, 'is_datereq': bool(already_send), 'user_data': user_dict,
#                         'matches': dict_list1, 'unmatches': dict_list2, 'filter': filter_text or 0,
#                         'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
#                         'matches_count': str(sum_count)})


def get_things_matches(active_user, user_id):
    # Step 1: Extract valid created_ids from active_user.save_things_community_id
    print('active_user.save_things_community_id',active_user.save_things_community_id)
    valid_created_ids = [k.created_id for k in active_user.save_things_community_id]
    print('valid_created_ids',valid_created_ids)

    # Step 2: Fetch SavedThingsCommunity records with valid created_ids and user_id
    saved_things = (
        SavedThingsCommunity.query
        .filter(SavedThingsCommunity.created_id.in_(valid_created_ids))
        .filter_by(user_id=user_id)
        .all()
    )

    if not saved_things:
        return {"things_matches": [], "total_matches_count": 0}  # Return an empty list if no matches

    # Step 3: Deduplicate results
    unique_communities = {thing.id: thing for thing in saved_things}.values()

    # Step 4: Fetch unique category IDs based on valid communities
    category_ids = list({thing.category_id for thing in unique_communities})
    if not category_ids:
        return {"things_matches": [], "total_matches_count": 0}  # Return empty if no valid categories are found

    # Step 5: Fetch categories that match the valid category_ids
    categories = ThingsCategory.query.filter(ThingsCategory.id.in_(category_ids)).all()

    # Step 6: Organize matched communities by category_id
    category_mapping = {}
    for community in unique_communities:
        if community.category_id not in category_mapping:
            category_mapping[community.category_id] = []
        category_mapping[community.category_id].append(community.as_dict())

    # Step 7: Format the final response
    things_matches = []
    total_matches_count = 0  # Initialize total matches counter

    for category in categories:
        # Include only categories with valid communities
        community_list = category_mapping.get(category.id, [])
        if community_list:  # Skip categories with no valid matches
            total_matches_count += len(community_list)  # Update total matches count
            things_matches.append({
                "category_name": category.category_name,
                "community_count": str(len(community_list)),
                "community_list": community_list
            })

    return {
        "things_matches": things_matches,
        "total_matches_count": total_matches_count
    }

@user_view_v5.route("/matches/category_vise", methods=['POST'])
@token_required
def matches_category_vice(active_user):
    user_id = request.json.get('user_id')

    only_user = User.query.filter_by(id=user_id).first()
    if not only_user:
        return jsonify({'status': 0, 'messege': 'Invalid user'})

    is_follow = 0
    follow_data = Follow.query.filter_by(by_id = active_user.id, to_id = user_id).first()
    if follow_data:
        is_follow = 1

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

    ls1 = []

    for m in active_user.save_community_id:
        community_save = SavedCommunity.query.filter_by(created_id=m.created_id, user_id=user_id).first()

        if community_save:
            ls1.append(community_save)

    cat_list = Category.query.filter(Category.id.in_([c.category_id for c in ls1])).all()

    dict_list1 = []

    res = []

    [res.append(x) for x in ls1 if x not in res]
    main_count_list = []

    for category in cat_list:
        community_list = [c.as_dict() for c in res if c.category_id == category.id]
        dict1 = {
            'category_name': category.category_name,
            'community_count': str(len(community_list)),
            'community_list': community_list
        }
        check_counts = (len(community_list))
        main_count_list.append(check_counts)
        dict_list1.append(dict1)

    # Call the get_things_matches function
    response = get_things_matches(active_user, user_id)

    # Extract 'things_matches' directly
    dict_list2 = response["things_matches"]

    already_send = DateRequest.query.filter(DateRequest.by_id == active_user.id,
                                                DateRequest.to_id == id).count() > 0
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
    # Extract total matches count if needed
    total_matches_count = response["total_matches_count"] + sum_count

    user_link = only_user.profile_link if not None else ''

    if not friend_request:
        return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 0, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1,'things_matches': dict_list2,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(total_matches_count),'show_link': user_link})

    elif friend_request.request_status == 2:
        return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 2, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1,'things_matches': dict_list2,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(total_matches_count),'show_link': user_link})

    else:
        return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 1, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1,'things_matches': dict_list2,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(total_matches_count),'show_link': user_link})


@user_view_v5.route("/get/terms_conditions", methods=['GET'])
def get_terms_conditions():
    x = terms_condition(1)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v5.route("/get/privacy_policy", methods=['GET'])
def get_privacy_policy():
    x = terms_condition(2)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v5.route("/get/news", methods=['GET'])
@token_required
def get_news(active_user):
    x = terms_condition(3)
    old_response = x.as_dict()
    old_response['youtube_link'] = x.youtube_link

    return jsonify({'status': 1, 'content': old_response})

@user_view_v5.route("/get/how_to_use", methods=['GET'])
@token_required
def how_to_use(active_user):
    x = terms_condition(4)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v5.route("/get/information", methods=['GET'])
@token_required
def information(active_user):
    x = terms_condition(5)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v5.route("/get/stores", methods=['GET'])
@token_required
def get_store(active_user):
    x = terms_condition(6)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v5.route("/get/brands_deals", methods=['GET'])
@token_required
def brands_deals(active_user):
    x = terms_condition(7)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v5.route("/get/faq", methods=['GET'])
@token_required
def get_faq(active_user):
    x = Faqs.query.all()
    list = [i.as_dict() for i in x]
    return jsonify({'status': 1, 'list': list})


@user_view_v5.route("/search/user", methods=['GET', 'POST'])
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


@user_view_v5.route('/get/tag_friends', methods=['POST'])
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


@user_view_v5.route('/tag_friends', methods=['GET', 'POST'])
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


@user_view_v5.route('/post/mute_unmute', methods=['GET', 'POST'])
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


@user_view_v5.route('/community/unsave', methods=['POST'])
@token_required
def community_unsave(active_user):
    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')

    # obj = SavedCommunity.query.filter_by(user_id=active_user.id, created_id=community_id,
    #                                      category_id=category_id).first()
    obj = CreatedCommunity.query.filter_by(user_id=active_user.id, id=community_id,
                                         category_id=category_id).first()

    if obj:
        if obj.saved:
            for i in obj.saved:
                db.session.delete(i)
            db.session.commit()
        db.session.delete(obj)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Sucessfully Deleted Word'})
    else:
        return jsonify({'status': 0, 'messege': 'Word Not Found'})

@user_view_v5.route('/delete_things_community', methods=['POST'])
@token_required
def delete_things_community(active_user):
    community_id = request.json.get('community_id')
    category_id = request.json.get('category_id')

    obj = CreatedThingsCommunity.query.filter_by(user_id=active_user.id, id=community_id,
                                         category_id=category_id).first()

    if obj:
        if obj.saved:
            for i in obj.saved:
                db.session.delete(i)
            db.session.commit()
        db.session.delete(obj)
        db.session.commit()

        return jsonify({'status': 1, 'messege': 'Sucessfully Deleted Word'})
    else:
        return jsonify({'status': 0, 'messege': 'Word Not Found'})


@user_view_v5.route('/featured_page', methods=['POST'])
@token_required
def featured_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page
    tab = request.json.get("tab")

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    if tab == 1:

        user_data = User.query.filter(User.is_featured == True,
                                      User.is_block != True,
                                      User.deleted != True,
                                      User.id.not_in(blocked_user_ids),
                                      User.id.not_in(blocked_by_user_ids)).paginate(page=page, per_page=per_page,
                                                                                    error_out=False)

    else:
        user_data = User.query.filter(User.is_business == True,
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

@user_view_v5.route('/business_page', methods=['POST'])
@token_required
def business_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    user_data = User.query.filter(User.is_business == True,
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

@user_view_v5.route('/matches/filter_community_vice', methods=['POST'])
@token_required
def matches_community_vice(active_user):
    if request.method == 'POST':
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 30  # Number of items per page
        created_id = request.json.get('community_id')
        print('created_iddddddddddddddddddddddddddddd',created_id)

        current_date = func.current_date()
        blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
        blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

        relationships = request.json.get('relationships')
        print('relationshipsssssssssssssssssssssssssssssss',relationships)
        relationships_list = []
        if relationships == 0:
            relationships_list.append('Here for friends')

        if relationships == 1:
            relationships_list.append("Here for dating")
        if relationships == 2:
            relationships_list.extend(["Here for friends","Here for dating","Here for friends and dating"])

        gender = request.json.get('gender')
        print('genderrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr',gender )
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
        print('age_startttttttttttttttttttttttttttttttttttttttt',age_start)

        age_end = request.json.get('age_end')
        print('age_endddddddddddddddddddddddddddddddddddddddddd',age_end)

        sexuality = request.json.get('sexuality')
        print('sexualityyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy',sexuality )
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

        print('countryyyyyyyyyyyyyyyyyyyyyyyyyyyyyy',country)
        print('stateeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',state)
        print('cityyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy',city )
        print('activeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',active_user.id)

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
        print('user_listttttttttttttttttttttttttttttttttttttt',user_list.items)
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

                age = ''
                if specific_response.age is not None and specific_response.age != "0000-00-00":
                    birthdate_datetime = datetime.combine(specific_response.age, datetime.min.time())
                    age = (datetime.utcnow() - birthdate_datetime).days // 365

                response_dict = {'user_id': str(specific_response.id),
                                 'user_name': specific_response.fullname,
                                 'user_image': specific_response.image_path,
                                 'state': specific_response.state,
                                 'city': specific_response.city,
                                 'badge': badge,
                                 'community_id': str(created_id),
                                 'matches_count': count_value,
                             'age': age}
                response_list.append(response_dict)

        if len(response_list) > 0:

            return jsonify({'status': 1, 'data': response_list,
                            'messege': '', 'pagination': pagination_info})
        else:
            return jsonify({'status': 1, 'data': [],
                            'messege': 'You Dont Have Any Matches Yet, Save More Words..',
                            })



# local one:
# @user_view_v5.route('/matches/community_vice', methods=['POST'])
# @token_required
# def matches_filter_community_vice(active_user):
#     created_id = request.json.get('community_id')
#     page = int(request.json.get('page', 1))  # Default to page 1 if not specified
#     per_page = 10  # Number of items per page
#
#     blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
#     blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
#     active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
#
#     matches_subq = (db.session.query(SavedCommunity.user_id, func.count().label('matches'))
#                     .join(User, User.id == SavedCommunity.user_id)
#                     .group_by(SavedCommunity.user_id)
#                     .subquery())
#
#     # Fetch user data, ensuring they have a match with the specific 'created_id'
#     user_data = (db.session.query(User, matches_subq.c.matches)
#                  .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
#                  .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
#                  .filter(~User.id.in_(blocked_user_ids))
#                  .filter(~User.id.in_(blocked_by_user_ids))
#                  .filter(User.id.in_(db.session.query(SavedCommunity.user_id)
#                                      .filter(SavedCommunity.created_id == created_id)))
#                  .order_by(
#         matches_subq.c.matches.desc())  # Order users by their total match counts across all created_ids
#                  .paginate(page=page, per_page=per_page, error_out=False))
#
#     final_list = []
#
#     if user_data.items:
#         for i, count in user_data.items:
#             # saved_data = SavedCommunity.query.filter_by(created_id=str(created_id), user_id=i.id).first()
#             badge = ""
#             if i.badge_name is not None:
#                 badge = i.badge_name
#             count_value = str(count)
#             if not count:
#                 count_value = '0'
#             response_dict = {'user_id': str(i.id),
#                              'user_name': i.fullname,
#                              'user_image': i.image_path,
#                              'state': i.state,
#                              'city': i.city,
#                              'badge': badge,
#                              'community_id': str(created_id),
#                              'matches_count': count_value,
#                              'new_bio': i.new_bio if i.new_bio is not None else ''}
#             final_list.append(response_dict)
#
#         has_next = user_data.has_next  # Check if there is a next page
#         total_pages = user_data.pages  # Total number of pages
#
#         # Pagination informatio
#         pagination_info = {
#             "current_page": page,
#             "has_next": has_next,
#             "per_page": per_page,
#             "total_pages": total_pages,
#         }
#
#         return jsonify({'status': 1, 'data': final_list, 'messege': 'sucess', 'pagination_info': pagination_info})
#     else:
#         return jsonify(
#             {'status': 1, 'data': [], 'messege': 'You Dont Have Any Matches Yet, Save More Words..'})

# @user_view_v5.route('/matches/community_vice', methods=['POST'])
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


@user_view_v5.route('/matches/things_community_vice', methods=['POST'])
@token_required
def matches_filter_things_community_vice(active_user):
    created_id = request.json.get('community_id')
    city = request.json.get('city')
    state = request.json.get('state')

    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]
    active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
    active_user_things_saved_ids = [j.created_id for j in active_user.save_things_community_id]

    # Step 2: Define Subqueries
    matches_subq = (
        db.session.query(SavedCommunity.user_id, func.count().label('community_matches'))
            .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
            .group_by(SavedCommunity.user_id)
            .subquery()
    )

    things_matches_subq = (
        db.session.query(SavedThingsCommunity.user_id, func.count().label('things_matches'))
            .filter(SavedThingsCommunity.created_id.in_(active_user_things_saved_ids))
            .group_by(SavedThingsCommunity.user_id)
            .subquery()
    )

    # Fetch user data, ensuring they have a match with the specific 'created_id'
    query = (db.session.query(User, (func.coalesce(matches_subq.c.community_matches, 0) +
         func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches'),
    )
                 .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
                 .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
                 .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
                 .filter(~User.id.in_(blocked_user_ids))
                 .filter(~User.id.in_(blocked_by_user_ids))
                 .filter(User.id.in_(db.session.query(SavedThingsCommunity.user_id)
                                     .filter(SavedThingsCommunity.created_id == created_id)))
                 .order_by(
        (func.coalesce(matches_subq.c.community_matches, 0) +
         func.coalesce(things_matches_subq.c.things_matches, 0)).desc())  # Order users by their total match counts across all created_ids
                 )

    if city:
        query = query.filter(User.city.ilike(f"{city}%"))
    if state:
        query = query.filter(User.state.ilike(f"{state}%"))

    user_data = query.paginate(page=page, per_page=per_page, error_out=False)

    final_list = []

    if user_data.items:
        for i, count in user_data.items:
            # saved_data = SavedCommunity.query.filter_by(created_id=str(created_id), user_id=i.id).first()

            check_fav = FavoriteUser.query.filter_by(by_id=active_user.id, to_id=i.id).first()

            badge = ""
            if i.badge_name is not None:
                if i.badge_name == "I'll Buy Us Coffee":
                    badge = "☕"
                if i.badge_name == "I'll Buy Us Food":
                    badge = "🍔"

                if i.badge_name == "Activity Badge":
                    badge = "🚴"
                if i.badge_name == "Best Friend Forever Badge":
                    badge = "🧑‍🤝‍🧑"
                if i.badge_name == "Luxury Badge":
                    badge = "🚁"
                if i.badge_name == "Lavish Badge":
                    badge = "💎"
            count_value = str(count)
            if not count:
                count_value = '0'

            age = ''
            if i.age is not None and i.age != "0000-00-00":
                birthdate_datetime = datetime.combine(i.age, datetime.min.time())
                age = (datetime.utcnow() - birthdate_datetime).days // 365

            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'state': i.state if i.state is not None else '',
                             'city': i.city if i.city is not None else '',
                             'badge': badge,
                             'community_id': str(created_id),
                             'matches_count': count_value,
                             'new_bio': i.new_bio if i.new_bio is not None else '',
                             'age': str(age),
                             'is_favorite': bool(check_fav)}
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
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify(
            {'status': 1, 'pagination_info': pagination_info, 'data': [],
             'messege': 'You Dont Have Any Matches Yet, Save More Words..'})


@user_view_v5.route('/matches/community_vice', methods=['POST'])
@token_required
def matches_filter_community_vice(active_user):
    created_id = request.json.get('community_id')
    city = request.json.get('city')
    state = request.json.get('state')

    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 30  # Number of items per page

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    active_user_saved_ids = [j.created_id for j in active_user.save_community_id]
    active_user_things_saved_ids = [j.created_id for j in active_user.save_things_community_id]

    # Step 2: Define Subqueries
    matches_subq = (
        db.session.query(SavedCommunity.user_id, func.count().label('community_matches'))
            .filter(SavedCommunity.created_id.in_(active_user_saved_ids))
            .group_by(SavedCommunity.user_id)
            .subquery()
    )

    things_matches_subq = (
        db.session.query(SavedThingsCommunity.user_id, func.count().label('things_matches'))
            .filter(SavedThingsCommunity.created_id.in_(active_user_things_saved_ids))
            .group_by(SavedThingsCommunity.user_id)
            .subquery()
    )



    # Fetch user data, ensuring they have a match with the specific 'created_id'
    query = (db.session.query(User, (func.coalesce(matches_subq.c.community_matches, 0) +
         func.coalesce(things_matches_subq.c.things_matches, 0)).label('total_matches'),
    )
                 .outerjoin(matches_subq, User.id == matches_subq.c.user_id)
                 .outerjoin(things_matches_subq, User.id == things_matches_subq.c.user_id)
                 .filter(User.id != active_user.id, User.is_block != True, User.deleted != True)
                 .filter(~User.id.in_(blocked_user_ids))
                 .filter(~User.id.in_(blocked_by_user_ids))
                 .filter(User.id.in_(db.session.query(SavedCommunity.user_id)
                                     .filter(SavedCommunity.created_id == created_id)))
                 .order_by(
        (func.coalesce(matches_subq.c.community_matches, 0) +
         func.coalesce(things_matches_subq.c.things_matches, 0)).desc())  # Order users by their total match counts across all created_ids
                 )

    if city:
        query = query.filter(User.city.ilike(f"{city}%"))
    if state:
        query = query.filter(User.state.ilike(f"{state}%"))

    user_data = query.paginate(page=page, per_page=per_page, error_out=False)

    final_list = []

    if user_data.items:
        for i, count in user_data.items:

            check_fav = FavoriteUser.query.filter_by(by_id = active_user.id,to_id = i.id).first()

            # saved_data = SavedCommunity.query.filter_by(created_id=str(created_id), user_id=i.id).first()
            badge = ""
            if i.badge_name is not None:
                if i.badge_name == "I'll Buy Us Coffee":
                    badge = "☕"
                if i.badge_name == "I'll Buy Us Food":
                    badge = "🍔"

                if i.badge_name == "Activity Badge":
                    badge = "🚴"
                if i.badge_name == "Best Friend Forever Badge":
                    badge = "🧑‍🤝‍🧑"
                if i.badge_name == "Luxury Badge":
                    badge = "🚁"
                if i.badge_name == "Lavish Badge":
                    badge = "💎"
            count_value = str(count)
            if not count:
                count_value = '0'

            age = ''
            if i.age is not None and i.age != "0000-00-00":
                birthdate_datetime = datetime.combine(i.age, datetime.min.time())
                age = (datetime.utcnow() - birthdate_datetime).days // 365

            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'state': i.state if i.state is not None else '',
                             'city': i.city if i.city is not None else '',
                             'badge': badge,
                             'community_id': str(created_id),
                             'matches_count': count_value,
                             'new_bio': i.new_bio if i.new_bio is not None else '',
                             'age': str(age),
                             'is_favorite': bool(check_fav)}
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
        pagination_info = {
            "current_page": 1,
            "has_next": False,
            "per_page": 10,
            "total_pages": 1,
        }
        return jsonify(
            {'status': 1, 'pagination_info': pagination_info, 'data': [],
             'messege': 'You Dont Have Any Matches Yet, Save More Words..'})

@user_view_v5.route('/notification_list', methods=['POST'])
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
        per_page = 30  # Number of items per page

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


@user_view_v5.route('/notification_button', methods=['POST'])
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


@user_view_v5.route('/get_notification_button', methods=['GET'])
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

@user_view_v5.route('/ranking_page', methods=['POST'])
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
    per_page = 30  # Number of items per page

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


@user_view_v5.route('/verify-receipt', methods=['POST'])
@token_required
def verify_receipt(active_user):
    data = request.get_json()
    receipt_data = data['receipt']
    subscription_type = data['subscription_type']
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

                        if subscription_type == 'badge':
                            active_user.is_subscription_badge = True
                            active_user.subscription_start_time_badge = entry['purchase_date_ms']
                            active_user.subscription_end_time_badge = entry['expires_date_ms']
                            # active_user.subscription_price_badge = "5.99"
                            active_user.product_id_badge = entry['product_id']
                            active_user.transaction_id_badge = entry['transaction_id']
                            active_user.purchase_date_badge = entry['purchase_date']
                            active_user.badge_name = badge_name
                            active_user.user_badge = badge_name
                            db.session.commit()

                            return jsonify({"status": 1, "messege": "Subscription verified successfully!"})

                        elif subscription_type == 'bio':
                            active_user.is_subscription = True
                            active_user.subscription_start_time = entry['purchase_date_ms']
                            active_user.subscription_end_time = entry['expires_date_ms']
                            active_user.product_id = entry['product_id']
                            active_user.transaction_id = entry['transaction_id']
                            active_user.purchase_date = entry['purchase_date']
                            db.session.commit()

                            return jsonify({"status": 1, "messege": "Subscription verified successfully!"})

                        else:
                            return jsonify({'status': 0, 'messege': "Invalid subscription type"})
                    else:
                        if subscription_type == 'badge':
                            active_user.is_subscription_badge = False
                            active_user.subscription_start_time_badge = None
                            active_user.subscription_end_time_badge = None
                            active_user.product_id_badge = None
                            active_user.transaction_id_badge = None
                            active_user.purchase_date_badge = None
                            active_user.badge_name = None
                            active_user.user_badge = None

                            db.session.commit()
                            return jsonify({"status": 1, "messege": "No subscription theire."})

                        if subscription_type == 'bio':
                            active_user.is_subscription = False
                            active_user.subscription_start_time = None
                            active_user.subscription_end_time = None
                            active_user.product_id = None
                            active_user.transaction_id = None
                            active_user.purchase_date = None

                            db.session.commit()
                            return jsonify({"status": 1, "messege": "No subscription theire."})

                        else:
                            return jsonify({'status': 0, 'messege': "Invalid subscription type"})
                    break
            # if not found:
            return jsonify({"status": 0, "messege": "Invalid product id."})
        else:
            return jsonify({"status": 0, "messege": "Invalid recipt data"})

    return jsonify({"status": 0, "messege": "Invalid receipt or no active subscription found."}), 400

@user_view_v5.route('/get/countries', methods=['GET'])
def get_countries():
    country_data = TblCountries.query.all()
    country_list = [i.as_dict() for i in country_data]

    return jsonify({'status': 1, 'messege': 'Sucess', 'list': country_list})


@user_view_v5.route('/get/states', methods=['POST'])
def get_states():
    country_id = request.json.get('country_id')

    if not country_id:
        return jsonify({'status': 0,'messege': 'Please select country'})

    states_data = TblStates.query.filter_by(country_id=country_id).all()
    states_list = [i.as_dict() for i in states_data]

    return jsonify({'status': 1, 'messege': 'Sucess', 'list': states_list})

@user_view_v5.route('/get_quetions', methods=['POST'])
@token_required
def get_quetions(active_user):
    category_id = request.json.get('category_id')
    if not category_id:
        return jsonify({'status':0,'messege': 'Please provide category id'})

    get_category_data = QuestionsCategory.query.get(category_id)
    if not get_category_data:
        return jsonify({'status':0,'messege': 'Invalid category you selected'})

    print('get_category_data',get_category_data)

    que_data = CategoryQue.query.filter_by(questions_category_id = get_category_data.id).all()

    get_all_que = []

    if len(que_data)>0:
        for i in que_data:

            answer_data = CategoryAns.query.filter_by(question_id = i.id,user_id = active_user.id).first()
            answer = ''
            is_like = False
            total_like=0

            if answer_data:
                answer = answer_data.answer
                check_like = LikeUserAnswer.query.filter_by(user_id=active_user.id, answer_id=answer_data.id).first()
                if check_like:
                    is_like = True

                total_like = LikeUserAnswer.query.filter_by(answer_id=answer_data.id).count()

            que_ans_data = {
                'id': i.id,
                'que': i.question,
                'ans': answer,
                'is_like': is_like,
                'total_like': str(total_like)
            }
            get_all_que.append(que_ans_data)

    print('get_all_que',get_all_que)
    return jsonify({'status': 1,'messege': 'Success', 'get_all_que': get_all_que})

@user_view_v5.route('/get_users_quetions_answers', methods=['POST'])
@token_required
def get_users_quetions_answers(active_user):
    category_id = request.json.get('category_id')
    user_id = request.json.get('user_id')
    if not category_id:
        return jsonify({'status':0,'messege': 'Please select category first'})
    if not user_id:
        return jsonify({'status':0,'messege': 'Please select user first'})

    get_category_data = QuestionsCategory.query.get(category_id)
    if not get_category_data:
        return jsonify({'status':0,'messege': 'Invalid category you selected'})

    print('get_category_data',get_category_data)

    que_data = CategoryQue.query.filter_by(questions_category_id = get_category_data.id).all()

    get_all_que = []

    if len(que_data)>0:
        for i in que_data:

            answer_data = CategoryAns.query.filter_by(question_id = i.id,user_id = user_id).first()
            answer = ''

            is_like = False
            total_like = 0
            if answer_data:
                answer = answer_data.answer

                check_like = LikeUserAnswer.query.filter_by(user_id = active_user.id,answer_id = answer_data.id).first()
                if check_like:
                    is_like = True

                total_like = LikeUserAnswer.query.filter_by(answer_id=answer_data.id).count()

            que_ans_data = {
                'id': i.id,
                'que': i.question,
                'ans': answer,
                'is_like': is_like,
                'total_like': str(total_like)
            }
            get_all_que.append(que_ans_data)

    print('get_all_que',get_all_que)
    return jsonify({'status': 1,'messege': 'Success', 'get_all_que': get_all_que})


@user_view_v5.route('/give_answer', methods=['POST'])
@token_required
def give_answer(active_user):
    data = request.get_json()
    main_data = data.get('data')
    if data:
        for i in main_data:
            print('iiiiiiiiiiiiiiiiiiiiiiiiiiiiiii', i)
            question_id = i['question_id']
            print('question_id', question_id)
            answer = i['answer']
            if not question_id:
                return jsonify({'status': 0, 'messege': 'Please provide question id'})

            if not answer:
                answer = None
            if answer == "":
                answer = None

            get_question_data = CategoryQue.query.get(question_id)
            if not get_question_data:
                return jsonify({'status': 0, 'messege': 'Invalid question you selected'})

            check_already_have_ans = CategoryAns.query.filter_by(question_id=question_id,
                                                                 user_id=active_user.id).first()


            if check_already_have_ans:
                if answer is not None:
                    check_already_have_ans.answer = answer
                    db.session.commit()

                    text = f'{active_user.fullname} updated answer in {get_question_data.category_que.category_name} category'

                    # add_feed_data = Feed(type='text', text=text, image_name=None, image_path=None,
                    #                      created_time=datetime.utcnow(), user_id=active_user.id)
                    #
                    # db.session.add(add_feed_data)
                    # db.session.commit()

                    # i not add notification data for this because no meaning feed is show all followers so need to send all followers this notification?

                else:
                    db.session.delete(check_already_have_ans)
                    db.session.commit()
                    # return jsonify({'status': 1, 'messege': 'Your answer saved successfully'})

            else:
                if answer is not None:
                    add_que_data = CategoryAns(answer=answer, question_id=question_id, user_id=active_user.id)
                    db.session.add(add_que_data)
                    db.session.commit()

                    text = f'{active_user.fullname} updated answer in {get_question_data.category_que.category_name} category'

                    # add_feed_data = Feed(type='text', text=text, image_name=None, image_path=None,
                    #                      created_time=datetime.utcnow(), user_id=active_user.id)
                    #
                    # db.session.add(add_feed_data)
                    # db.session.commit()


                    # i not add notification data for this because no meaning feed is show all followers so need to send all followers this notification?

        return jsonify({'status': 1, 'messege': 'Your answer saved successfully'})

    else:
        return jsonify({'status': 0, 'messege': 'Plesase provide input'})


