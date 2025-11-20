import json
import requests
import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate('base/frienddate_key.json')
firebase_admin.initialize_app(cred)


def push_notification(device_token, device_type, title, msg, image_url=None):
    try:

        data_payload = None

        sound = "default"

        # Create the notification message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=msg,

            ),

            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound=sound
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=sound ,
                         #content_available=True,
                    )
                )
            ),

            token=device_token,
            #data=data,
            data=data_payload,
        )

        # Send the message
        response = messaging.send(message)
        #message.data['type'] = notification_type

        # Log the response
        print(f'Successfully sent message: {response}')

    except Exception as e:
        print('Error sending message:', e)

# def push_notification(device_token, device_type, title, msg, image_url=None):
#     server_key = 'AAAAyJ_3rbE:APA91bGilZyHd3v6dlgOexbHt7aBtCm9apiLtLkfA44PfuF6VWENZo0ltxJMH0ExTRQrW4mxgW9_PWU4fW6NsDHiDZbsQaiQhWatNtfguXxeGBubTtBhiiUPbJ_wmajd05HTPQRhnCp-'
#     fcm_endpoint = 'https://fcm.googleapis.com/fcm/send'
#
#     headers = {
#         'Content-Type': 'application/json',
#         'Authorization': 'key=' + server_key,
#     }
#
#     payload = {
#         'notification': {
#             'title': title,
#             'body': msg,
#             'image': image_url
#         },
#         'priority': 'high',
#         'data': {
#             'title': title,
#             'body': msg,
#             'image': image_url
#         },
#         'to': device_token,
#     }
#
#     payload['notification']['sound'] = 'default'  # Set sound for iOS notifications
#
#     response = requests.post(fcm_endpoint, headers=headers, json=payload)
#
#     try:
#         response.raise_for_status()  # Check for any HTTP errors
#         result = response.json()
#         if 'error' in result:
#             print('FCM error:', result['error'])
#         return result
#     except requests.exceptions.HTTPError as e:
#         print('HTTP error occurred:', e)
#     except json.JSONDecodeError as e:
#         print('Error parsing response JSON:', e)
#     except Exception as e:
#         print('An error occurred:', e)
#
#     return {'error': 'Notification sending failed'}
