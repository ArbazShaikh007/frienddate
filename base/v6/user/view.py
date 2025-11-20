from flask import request, jsonify, Blueprint
from base.user.queryset import view_data
from base.user.models import GroupChat,RecommendationComments,HideFeed,UserVideos,LikeUserVideos,ProfileReviewLike, LikeUserPhotos,UserPhotos, ProfileReviewRequest,token_required, FriendRequest, User, DateRequest, TagFriends, \
    ChatMute, Notification, Block, TblCountries, TblStates,Follow,Feed,FeedLike,FeedComments,FeedCommentLike,PlacesReviewLike,PlacesReviewCommentLike,PlacesReviewComments,ThingsReviewCommentLike,ThingsReviewComments,ThingsReviewLike,NewNotification,LikeRecommendation
from base.user.queryset import insert_data, delete_frnd_req
from base.admin.models import CommentsUserAnswer,LikeUserAnswer,Category, Faqs,ThingsCategory,CategoryQue,CategoryAns,QuestionsCategory,Buttons
from base import db
from base.community.models import SavedThingsCommunity,SavedCommunity,CreatedThingsCommunity, CreatedCommunity, CommunityPost,ThingsRecommendation,PlacesRecommendation,PlacesReview,ThingsReview
from base.admin.queryset import terms_condition
from base.push_notification.push_notification import push_notification
from base.community.queryset import get_community_chat
from datetime import datetime
import requests,secrets,os,boto3
from sqlalchemy import and_
from sqlalchemy.sql.expression import func
from sqlalchemy import text
from werkzeug.utils import secure_filename
from moviepy.editor import VideoFileClip
import tempfile
from sqlalchemy import union_all
user_view_v6 = Blueprint('user_view_v6', __name__)

REGION_NAME = os.getenv("REGION_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY)


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

@user_view_v6.route('/chat_list', methods=['POST'])
@token_required
def chat_list(active_user):
    data = request.get_json()

    if not data:
        return jsonify({'status': 0,'messege': 'Json is empty'})

    community_id = data.get('community_id')
    type = data.get('type')

    page = int(data.get('page', 1))
    per_page = 10

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

@user_view_v6.route('/create_group_chat', methods=['POST'])
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

@user_view_v6.route('/delete_group_chat', methods=['POST'])
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

@user_view_v6.route('/user_videos', methods=['POST'])
@token_required
def user_videos(active_user):
    page = int(request.json.get('page', 1))
    user_id = request.json.get('user_id')
    per_page = 10

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


@user_view_v6.route('/my_videos', methods=['POST'])
@token_required
def my_videos(active_user):
    page = int(request.json.get('page', 1))
    per_page = 10

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

@user_view_v6.route('/delete_my_videos', methods=['POST'])
@token_required
def delete_my_videos(active_user):
    video_id = request.json.get('video_id')
    if not video_id:
        return jsonify({'status': 0,'message': 'Please select video'})

    get_video = UserVideos.query.filter_by(id = video_id,user_id=active_user.id).first()

    if get_video.thumbnail is not None:
        thumbnail_name = get_video.thumbnail.replace("https://frienddate-app.s3.amazonaws.com/", "")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=thumbnail_name)
    if get_video.video_path is not None:
        video_name = get_video.video_path.replace("https://frienddate-app.s3.amazonaws.com/", "")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=video_name)

    db.session.delete(get_video)
    db.session.commit()

@user_view_v6.route('/add_videos', methods=['POST'])
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

@user_view_v6.route('/like_user_answer', methods=['POST'])
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

@user_view_v6.route('/user_answer_comment_list', methods=['POST'])
@token_required
def user_answer_comment_list(active_user):

    data = request.get_json()
    answer_id = data.get('answer_id')
    page = int(data.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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

@user_view_v6.route('/comment_on_user_answer', methods=['POST'])
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

@user_view_v6.route('/like_user_photo', methods=['POST'])
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

@user_view_v6.route('/delete_photos', methods=['POST'])
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

@user_view_v6.route('/get_my_images', methods=['POST'])
@token_required
def get_my_images(active_user):
    page = int(request.json.get('page', 1))
    per_page = 10

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

@user_view_v6.route('/get_user_images', methods=['POST'])
@token_required
def get_user_images(active_user):
    user_id = request.json.get('user_id')
    page = int(request.json.get('page', 1))
    per_page = 10

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

@user_view_v6.route('/add_multiple_photos', methods=['POST'])
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

@user_view_v6.route('/delete_profile_review', methods=['POST'])
@token_required
def delete_profile_review(active_user):
    review_id = request.json.get('review_id')
    if not review_id:
        return jsonify({'status': 0, 'message': 'Please select review first'})

    get_approved_reviews = ProfileReviewRequest.query.filter(id=review_id, to_id=active_user.id,
                                                             request_status=1).first()

    if not get_approved_reviews:
        return jsonify({'status': 0, 'messege': 'Invalid Profile Review'})

    get_all_review_likes = ProfileReviewLike.query.filter_by(profile_review_id = get_approved_reviews.id).all()

    if len(get_all_review_likes)>0:
        for i in get_all_review_likes:
            db.session.delete(i)
        db.session.commit()

    db.session.delete(get_approved_reviews)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully review deleted'})

@user_view_v6.route('/profile_reviews_request_list', methods=['POST'])
@token_required
def profile_reviews_request_list(active_user):
    page = int(request.json.get('page', 1))
    per_page = 10

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

@user_view_v6.route('/approved_denied_reviews', methods=['POST'])
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

@user_view_v6.route('/like_profile_review', methods=['POST'])
@token_required
def like_profile_review(active_user):

    review_id = request.json.get('review_id')
    if not review_id:
        return jsonify({'status':0,'message': 'Review id is required'})

    get_profile_review_data = ProfileReviewRequest.query.filter_by(id =review_id,request_status = 1).first()
    if not get_profile_review_data:
        return jsonify({'status':0,'message': 'Invalid profile review'})

    check_like = ProfileReviewLike.query.filter_by(user_id = active_user.id,profile_review_id = review_id).first()

    if check_like:
        db.session.delete(check_like)
        db.session.commit()

        return jsonify({'status': 1,'message': 'Successfully unlike review'})

    else:
        add_like = ProfileReviewLike(user_id = active_user.id, main_user_id = get_profile_review_data.to_id,profile_review_id = review_id)
        db.session.add(add_like)
        db.session.commit()

        return jsonify({'status': 1, 'message': 'Successfully like review'})

@user_view_v6.route('/get_profile_reviews', methods=['POST'])
@token_required
def get_profile_reviews(active_user):
    page = int(request.json.get('page', 1))
    per_page = 10

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


@user_view_v6.route('/get_user_profile_reviews', methods=['POST'])
@token_required
def get_user_profile_reviews(active_user):
    page = int(request.json.get('page', 1))
    user_id = request.json.get('user_id')
    per_page = 10

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

@user_view_v6.route('/send_profile_review', methods=['POST'])
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
    msg = f'{active_user.fullname} write review and send you.'
    # add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=user_id,
    #                                    is_read=False, created_time=datetime.utcnow(), page='review on profile')
    # db.session.add(add_notification)
    # db.session.commit()
    # if reciver_user.device_token:
    notification = push_notification(device_token=user_data.device_token, title=title, msg=msg,
                                     image_url=None, device_type=user_data.device_type)


    return jsonify({'status': 1, 'messege': 'Thank you for creating a review. Please wait for this user to approve your review to get posted on their page.'})


@user_view_v6.route('/top_followed_users', methods=['GET'])
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

@user_view_v6.route('/like_recommendation', methods=['POST'])
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

@user_view_v6.route('/add_recommendation_comments', methods=['POST'])
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

@user_view_v6.route('/new_notification_list', methods=['POST'])
@token_required
def new_notification_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    notification_data = NewNotification.query.filter(NewNotification.to_id == active_user.id).order_by(
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

@user_view_v6.route('/like_things_review_comment', methods=['POST'])
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

@user_view_v6.route('/delete_things_review_comment', methods=['POST'])
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

@user_view_v6.route('/add_comment_things_review', methods=['POST'])
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

@user_view_v6.route('/like_things_review', methods=['POST'])
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


@user_view_v6.route('/like_places_review_comment', methods=['POST'])
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

@user_view_v6.route('/delete_places_review_comment', methods=['POST'])
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

@user_view_v6.route('/add_comment_places_review', methods=['POST'])
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

@user_view_v6.route('/like_places_review', methods=['POST'])
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

@user_view_v6.route('/like_feed_comment', methods=['POST'])
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

@user_view_v6.route('/delete_feed_comment', methods=['POST'])
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


@user_view_v6.route('/feed_comment_list', methods=['POST'])
@token_required
def feed_comment_list(active_user):
    feed_id = request.json.get('feed_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page
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


@user_view_v6.route('/add_comment_feed', methods=['POST'])
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
        msg = f'{active_user.fullname} comment on your feed'
        add_notification = NewNotification(title=title, message=msg, by_id=active_user.id, to_id=feed_data.feed_id.id,
                                           is_read=False, created_time=datetime.utcnow(), page='comment on feed')
        db.session.add(add_notification)
        db.session.commit()
        # if reciver_user.device_token:
        notification = push_notification(device_token=feed_data.feed_id.device_token, title=title, msg=msg,
                                         image_url=None, device_type=feed_data.feed_id.device_type)

    return jsonify({'status': 1,'messege': 'Successfully comment added'})

@user_view_v6.route('/like_feed', methods=['POST'])
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

@user_view_v6.route('/delete_feed', methods=['POST'])
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

@user_view_v6.route('/my_review_list', methods=['POST'])
@token_required
def my_review_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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

@user_view_v6.route('/users_review_list', methods=['POST'])
@token_required
def users_review_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page
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

@user_view_v6.route('/hide_feed', methods=['POST'])
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


@user_view_v6.route('/liked_feed_users', methods=['POST'])
@token_required
def liked_feed_users(active_user):

    data = request.get_json()
    page = int(data.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page
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

@user_view_v6.route('/feed_page', methods=['POST'])
@token_required
def feed_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

    notification_count = NewNotification.query.filter_by(to_id = active_user.id,is_read = False).count()

    follow_data = Follow.query.filter_by(by_id = active_user.id).all()
    print('follow_data',follow_data)

    if not follow_data:
        return jsonify({'status':1,'messege': 'First you need to follow someone to see their activity in feed page', 'feed_list': []})

    followed_list = [ i.to_id for i in follow_data ]

    get_hide_feed = HideFeed.query.filter_by(user_id=active_user.id).all()
    get_hide_feed_ids = [i.feed_id for i in get_hide_feed]

    feed_data = Feed.query.filter(Feed.user_id != active_user.id, Feed.user_id.in_(followed_list),
                                  Feed.id.not_in(get_hide_feed_ids)).order_by(Feed.id.desc()).paginate(page=page,
                                                                                                       per_page=per_page,
                                                                                                       error_out=False)

    has_next = feed_data.has_next  # Check if there is a next page
    total_pages = feed_data.pages  # Total number of pages

    # Pagination information
    pagination_info = {
        "current_page": page,
        "has_next": has_next,
        "per_page": per_page,
        "total_pages": total_pages,
    }

    feed_list = []
    if feed_data.items:
        for i in feed_data.items:
            main_dict = i.as_dict(active_user.id)
            is_like= False
            check_like = FeedLike.query.filter_by(user_id = active_user.id, feed_id = i.id).first()
            comments_count = FeedComments.query.filter_by(feed_id=i.id).count()
            if check_like:
                is_like = True
            main_dict['is_like'] = is_like
            main_dict['comments_count'] = str(comments_count)
            feed_list.append(main_dict)

        return jsonify({'status': 1, 'messege': 'Success','notification_count': str(notification_count), 'feed_list': feed_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones','notification_count': str(notification_count), 'feed_list': [],'pagination_info': pagination_info})

@user_view_v6.route('/my_feed_page', methods=['POST'])
@token_required
def my_feed_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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
            is_like = False
            check_like = FeedLike.query.filter_by(user_id=active_user.id, feed_id=i.id).first()
            comments_count = FeedComments.query.filter_by(feed_id=i.id).count()
            if check_like:
                is_like = True
            main_dict['is_like'] = is_like
            main_dict['comments_count'] = str(comments_count)
            feed_list.append(main_dict)

        return jsonify({'status': 1, 'messege': 'Success', 'feed_list': feed_list,'pagination_info': pagination_info})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones', 'feed_list': [],'pagination_info': pagination_info})

@user_view_v6.route('/user_feed_page', methods=['POST'])
@token_required
def user_feed_page(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'status': 0,'messege': 'User id is required'})

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
        return jsonify({'status':1,'messege': 'First you need to follow someone to see their activity in feed page', 'feed_list': [], 'is_friend': is_friend, 'is_follow': is_follow,
         'following_count': str(following_count)})

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
            if check_like:
                is_like = True
            main_dict['is_like'] = is_like
            main_dict['comments_count'] = str(comments_count)
            feed_list.append(main_dict)

        return jsonify({'status': 1, 'messege': 'Success', 'feed_list': feed_list,'pagination_info': pagination_info, 'is_friend': is_friend, 'is_follow': is_follow,
         'following_count': str(following_count)})
    else:
        return jsonify({'status': 1, 'messege': 'Sorry no feeds share by anyones', 'feed_list': [],'pagination_info': pagination_info, 'is_friend': is_friend, 'is_follow': is_follow,
         'following_count': str(following_count)})

@user_view_v6.route('/add_activity_post', methods=['POST'])
@token_required
def add_activity_post(active_user):
    text = request.form.get('text')
    link = request.form.get('link')
    content = request.files.get('content')
    content_media_type = request.form.get('content_type')

    if not text and not content and not link:
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

    elif content_media_type == 'link':
        type = 'link'

    add_feed_data = Feed(link=link,type = type,text=text,thumbnail_path= thumbnail_path,video_path = video_url, image_name=image_name, image_path=image_url,
                                     created_time=datetime.utcnow(), user_id=active_user.id)
    db.session.add(add_feed_data)
    db.session.commit()

    return jsonify({'status': 1, 'messege': 'Successfully added your activity post'})

@user_view_v6.route('/follow_user', methods=['POST'])
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

@user_view_v6.route('/my_followers_list', methods=['POST'])
@token_required
def my_followers_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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

@user_view_v6.route('/followers_list', methods=['POST'])
@token_required
def followers_list(active_user):
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page
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

@user_view_v6.route('/user_my_recommendation_category', methods=['POST'])
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

@user_view_v6.route('/user_recommendation_category', methods=['POST'])
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

@user_view_v6.route('/homepage_verify_token', methods=['POST'])
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


@user_view_v6.route('/homepage', methods=['POST'])
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

    user_data = (
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
            .paginate(page=page, per_page=per_page, error_out=False)
    )

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

    print('user_data_count',user_data_count)

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

            response_dict = {'user_id': str(specific_response.id),
                             'user_name': specific_response.fullname,
                             'user_image': specific_response.image_path,
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
                             'total_followers': str(total_followers),
                             'total_status_likes': str(sum(total_status_likes)),
                             'total_profile_review_like': str(get_approved_reviews_likes),
                             'total_user_photos_likes': str(total_user_photos_likes),
                             'new_bio': specific_response.new_bio if specific_response.new_bio is not None else ''

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

@user_view_v6.route('/homepage_filter', methods=['GET', 'POST'])
@token_required
def homepage_filter(active_user):
    if request.method == 'POST':
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 10  # Number of items per page

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
                             'new_bio': specific_response.new_bio if specific_response.new_bio is not None else ''

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



    return jsonify({'status': 1, 'is_subscription': active_user.is_subscription_badge, 'data': filter_dict})

@user_view_v6.route('/liked_category_list', methods=['GET', 'POST'])
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

        category_list = [category.as_dict(str(count)) for category, count in categories_with_count]

    if tab == 2:
        questions_category = QuestionsCategory.query.join(QuestionsCategory.category_que).filter(
            QuestionsCategory.category_que.any()).all()

        # Alternatively, using exists
        # things_category = ThingsCategory.query.filter(
        #     ThingsCategory.category_que.any()
        # ).all()

        category_list = [i.as_dict() for i in questions_category]

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

@user_view_v6.route('/category_list', methods=['GET', 'POST'])
@token_required
def category_list(active_user):
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

        category_list = [category.as_dict(str(count)) for category, count in categories_with_count]
        # category_list = []
        #
        # if categories_with_count:
        #     for category, count in categories_with_count:
        #         if tab == 1:
        #             check_is_saved = SavedCommunity.query.filter_by(category_id=category.id, is_saved=True,
        #                                                             user_id=active_user.id).first()
        #             if check_is_saved:
        #                 category_list.append(category.as_dict(str(count)))
        #         else:
        #             category_list.append(category.as_dict(str(count)))

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

        category_list = [category.as_dict(str(count)) for category, count in categories_with_count]

        # category_list = []
        #
        # if categories_with_count:
        #     for category, count in categories_with_count:
        #         if tab == 3:
        #             check_is_saved = SavedThingsCommunity.query.filter_by(category_id=category.id, is_saved=True,
        #                                                                   user_id=active_user.id).first()
        #             if check_is_saved:
        #                 category_list.append(category.as_dict(str(count)))
        #         else:
        #             category_list.append(category.as_dict(str(count)))

    if tab == 2:
        questions_category = QuestionsCategory.query.join(QuestionsCategory.category_que).filter(
            QuestionsCategory.category_que.any()).all()

        # Alternatively, using exists
        # things_category = ThingsCategory.query.filter(
        #     ThingsCategory.category_que.any()
        # ).all()

        category_list = [i.as_dict() for i in questions_category]

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

@user_view_v6.route('/answered_my_things_category_list', methods=['GET', 'POST'])
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

@user_view_v6.route('/answered_things_category_list', methods=['GET', 'POST'])
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


@user_view_v6.route('/users_list', methods=['GET'])
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


@user_view_v6.route('/send_friend_req', methods=['POST'])
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


@user_view_v6.route('/req_list', methods=['GET', 'POST'])
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


@user_view_v6.route('/req_action', methods=['POST'])
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


@user_view_v6.route('/user_friends_list', methods=['POST'])
@token_required
def user_friends_list(active_user):
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'status': 0, 'message': 'Please select user first'})

    list = []

    ls = []

    check = FriendRequest.query.filter_by(to_id=user_id, request_status=1).all()

    checked = FriendRequest.query.filter_by(by_id=user_id, request_status=1).all()

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
        return jsonify({'status': 1, 'friends_list': list, 'messege': 'Dont Have Any Friends Yet',
                        'pagination': pagination_info})

@user_view_v6.route('/friends_list', methods=['POST'])
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


@user_view_v6.route('/friends_list_id', methods=['GET', 'POST'])
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


@user_view_v6.route('/get_category', methods=['GET', 'POST'])
@token_required
def get_category(active_user):
    id = request.args.get('id')
    x = Category.query.filter_by(id=id).first()

    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxx ', x)

    return jsonify({'status': 1, 'category_data': x.as_dict()})


@user_view_v6.route('/view_profile', methods=['POST'])
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


@user_view_v6.route("/user/delete", methods=['GET', 'POST'])
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

@user_view_v6.route("/get_my_buttons_data", methods=['GET'])
@token_required
def get_my_buttons_data(active_user):

    blocked_user_ids = [block.user_id for block in Block.query.filter_by(blocked_user=active_user.id).all()]
    blocked_by_user_ids = [block.blocked_user for block in Block.query.filter_by(user_id=active_user.id).all()]

    get_button_data = Buttons.query.all()
    # button_data = [i.as_dict() for i in get_button_data]

    dont_add = ["Favorites in common","My Info"]

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


@user_view_v6.route("/get_buttons_data", methods=['POST'])
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
        return {"things_matches": []}  # Return an empty list if no matches

    # Step 3: Deduplicate results
    unique_communities = {thing.id: thing for thing in saved_things}.values()

    # Step 4: Fetch unique category IDs based on valid communities
    category_ids = list({thing.category_id for thing in unique_communities})
    if not category_ids:
        return {"things_matches": []}  # Return empty if no valid categories are found

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

@user_view_v6.route("/matches/category_vise", methods=['POST'])
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

    if not friend_request:
        return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 0, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1,'things_matches': dict_list2,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(total_matches_count)})

    elif friend_request.request_status == 2:
        return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 2, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1,'things_matches': dict_list2,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(total_matches_count)})

    else:
        return jsonify({'status': 1,'is_follow' : is_follow, 'is_friends': 1, 'is_datereq': bool(already_send), 'user_data': user_dict,
                        'matches': dict_list1,'things_matches': dict_list2,
                        'is_block': is_block, "is_subscribed": is_subscribed, "description_box": description_box,
                        'matches_count': str(total_matches_count)})


@user_view_v6.route("/get/terms_conditions", methods=['GET'])
def get_terms_conditions():
    x = terms_condition(1)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/privacy_policy", methods=['GET'])
def get_privacy_policy():
    x = terms_condition(2)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/news", methods=['GET'])
@token_required
def get_news(active_user):
    x = terms_condition(3)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/how_to_use", methods=['GET'])
@token_required
def how_to_use(active_user):
    x = terms_condition(4)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/information", methods=['GET'])
@token_required
def information(active_user):
    x = terms_condition(5)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/stores", methods=['GET'])
@token_required
def get_store(active_user):
    x = terms_condition(6)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/brands_deals", methods=['GET'])
@token_required
def brands_deals(active_user):
    x = terms_condition(7)
    return jsonify({'status': 1, 'content': x.as_dict()})


@user_view_v6.route("/get/faq", methods=['GET'])
@token_required
def get_faq(active_user):
    x = Faqs.query.all()
    list = [i.as_dict() for i in x]
    return jsonify({'status': 1, 'list': list})


@user_view_v6.route("/search/user", methods=['GET', 'POST'])
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


@user_view_v6.route('/get/tag_friends', methods=['POST'])
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


@user_view_v6.route('/tag_friends', methods=['GET', 'POST'])
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


@user_view_v6.route('/post/mute_unmute', methods=['GET', 'POST'])
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


@user_view_v6.route('/community/unsave', methods=['POST'])
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

@user_view_v6.route('/delete_things_community', methods=['POST'])
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


@user_view_v6.route('/featured_page', methods=['POST'])
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


@user_view_v6.route('/matches/filter_community_vice', methods=['POST'])
@token_required
def matches_community_vice(active_user):
    if request.method == 'POST':
        page = int(request.json.get('page', 1))  # Default to page 1 if not specified
        per_page = 10  # Number of items per page
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
                if specific_response.age is not None:
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

@user_view_v6.route('/matches/things_community_vice', methods=['POST'])
@token_required
def matches_filter_things_community_vice(active_user):
    created_id = request.json.get('community_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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
    user_data = (db.session.query(User, (func.coalesce(matches_subq.c.community_matches, 0) +
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
                 .paginate(page=page, per_page=per_page, error_out=False))

    final_list = []

    if user_data.items:
        for i, count in user_data.items:
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
            if i.age is not None:
                birthdate_datetime = datetime.combine(i.age, datetime.min.time())
                age = (datetime.utcnow() - birthdate_datetime).days // 365

            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'state': i.state,
                             'city': i.city,
                             'badge': badge,
                             'community_id': str(created_id),
                             'matches_count': count_value,
                             'new_bio': i.new_bio if i.new_bio is not None else '',
                             'age': age}
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

@user_view_v6.route('/matches/community_vice', methods=['POST'])
@token_required
def matches_filter_community_vice(active_user):
    created_id = request.json.get('community_id')
    page = int(request.json.get('page', 1))  # Default to page 1 if not specified
    per_page = 10  # Number of items per page

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
    user_data = (db.session.query(User, (func.coalesce(matches_subq.c.community_matches, 0) +
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
                 .paginate(page=page, per_page=per_page, error_out=False))

    final_list = []

    if user_data.items:
        for i, count in user_data.items:
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
            if i.age is not None:
                birthdate_datetime = datetime.combine(i.age, datetime.min.time())
                age = (datetime.utcnow() - birthdate_datetime).days // 365

            response_dict = {'user_id': str(i.id),
                             'user_name': i.fullname,
                             'user_image': i.image_path,
                             'state': i.state,
                             'city': i.city,
                             'badge': badge,
                             'community_id': str(created_id),
                             'matches_count': count_value,
                             'new_bio': i.new_bio if i.new_bio is not None else '',
                             'age': age
                             }
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

# @user_view_v6.route('/matches/community_vice', methods=['POST'])
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


@user_view_v6.route('/notification_list', methods=['POST'])
@token_required
def notification_list(active_user):
    # notify = Notification.query.filter(
    #     and_(Notification.title != 'Friends', Notification.to_id == active_user.id)).all()

    notify = Notification.query.filter(
        and_(Notification.to_id == active_user.id)).all()

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


@user_view_v6.route('/notification_button', methods=['POST'])
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


@user_view_v6.route('/get_notification_button', methods=['GET'])
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

@user_view_v6.route('/ranking_page', methods=['POST'])
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


@user_view_v6.route('/verify-receipt', methods=['POST'])
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

@user_view_v6.route('/get/countries', methods=['GET'])
def get_countries():
    country_data = TblCountries.query.all()
    country_list = [i.as_dict() for i in country_data]

    return jsonify({'status': 1, 'message': 'Sucess', 'list': country_list})

@user_view_v6.route('/get/states', methods=['POST'])
def get_states():
    # country_id = request.json.get('country_id')
    states_data = TblStates.query.filter_by(country_id=233).all()
    states_list = [i.as_dict() for i in states_data]

    return jsonify({'status': 1, 'message': 'Sucess', 'list': states_list})

@user_view_v6.route('/get_quetions', methods=['POST'])
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

@user_view_v6.route('/get_users_quetions_answers', methods=['POST'])
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

            total_like = 0
            is_like = False

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


@user_view_v6.route('/give_answer', methods=['POST'])
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


