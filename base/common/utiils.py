import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import url_for

COMMON_URL = 'http://52.15.172.172'
COMMON_PATH = ''

href = "{url_for('admin_auth.reset_token', token=token, _external=True)}"


def send_reset_email(user):
    token = user.get_token()

    print('Composing Email.......')

    SERVER = 'smtp.gmail.com'  # smtp server
    PORT = 587  # mail port number
    FROM = 'fearsfight211@gmail.com'  # sender Mail
    TO = user.email  # receiver mail
    PASS = 'mdltifkjmclajper'
    MAIL_FROM_NAME = "FriendDate"

    msg = MIMEMultipart()
    content = '''
<!DOCTYPE html>
<html>

<head>
    <title></title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <style type="text/css">
        @media screen { 
            @font-face {
                font-family: 'Lato';
                font-style: normal;
                font-weight: 400;
                src: local('Lato Regular'), local('Lato-Regular'), url(https://fonts.gstatic.com/s/lato/v11/qIIYRU-oROkIk8vfvxw6QvesZW2xOQ-xsNqO47m55DA.woff) format('woff');
            }

            @font-face {
                font-family: 'Lato';
                font-style: normal;
                font-weight: 700;
                src: local('Lato Bold'), local('Lato-Bold'), url(https://fonts.gstatic.com/s/lato/v11/qdgUG4U09HnJwhYI-uK18wLUuEpTyoUstqEm5AMlJo4.woff) format('woff');
            }

            @font-face {
                font-family: 'Lato';
                font-style: italic;
                font-weight: 400;
                src: local('Lato Italic'), local('Lato-Italic'), url(https://fonts.gstatic.com/s/lato/v11/RYyZNoeFgb0l7W3Vu1aSWOvvDin1pK8aKteLpeZ5c0A.woff) format('woff');
            }

            @font-face {
                font-family: 'Lato';
                font-style: italic;
                font-weight: 700;
                src: local('Lato Bold Italic'), local('Lato-BoldItalic'), url(https://fonts.gstatic.com/s/lato/v11/HkF_qI1x_noxlxhrhMQYELO3LdcAZYWl9Si6vvxL-qU.woff) format('woff');
            }
        }

        /* CLIENT-SPECIFIC STYLES */
        body,
        table,
        td,
        a {
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }

        table,
        td {
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }

        img {
            -ms-interpolation-mode: bicubic;
        }

        /* RESET STYLES */
        img {
            border: 0;
            height: auto;
            line-height: 100%;
            outline: none;
            text-decoration: none;
        }

        table {
            border-collapse: collapse !important;
        }

        body {
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }
        a[x-apple-data-detectors] {
            color: inherit !important;
            text-decoration: none !important;
            font-size: inherit !important;
            font-family: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
        }
        @media screen and (max-width:600px) {
            h1 {
                font-size: 32px !important;
                line-height: 32px !important;
            }
        }

        /* ANDROID CENTER FIX */
        div[style*="margin: 16px 0;"] {
            margin: 0 !important;
        }
    </style>
</head>

<body style="background-color: #f4f4f4; margin: 0 !important; padding: 0 !important;">
    <!-- HIDDEN PREHEADER TEXT -->
    <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: 'Lato', Helvetica, Arial, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;"> We're thrilled to have you here! Get ready to dive into your new account.
    </div>
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <!-- LOGO -->
        <tr>
            <td style="background:#f66e60" align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                    <tr>
                        <td align="center" valign="top" style="padding: 40px 10px 40px 10px;"> </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td style="background:#f66e60" align="center" style="padding: 0px 10px 0px 10px;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                    <tr>
                        <td bgcolor="#ffffff" align="center" valign="top" style="padding: 40px 20px 20px 20px; border-radius: 4px 4px 0px 0px; color: #111111; font-family: 'Lato', Helvetica, Arial, sans-serif; font-size: 48px; font-weight: 400; letter-spacing: 4px; line-height: 48px;">
                            <img src="https://frienddate-app.s3.amazonaws.com/app_icon0.png" width="125" height="125" style="display: block; border: 0px;" /> <h1 style="font-size: 36px; font-weight: 300; margin: 2;">Trouble signing in?</h1>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td bgcolor="#f4f4f4" align="center" style="padding: 0px 10px 0px 10px;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                    <tr>
                        <td bgcolor="#ffffff" align="left" style="padding: 20px 30px 40px 30px; color: #666666; font-family: 'Lato', Helvetica, Arial, sans-serif; font-size: 18px; font-weight: 400; line-height: 25px;">
                            <p style="margin: 0;">Resetting your password is easy. Just press the button below and follow the instructions. We'll have you up and running in no time.</p>
                        </td>
                    </tr>

                    <tr>
                        <td bgcolor="#ffffff" align="left" style="padding: 0px 30px 20px 30px; color: #666666; font-family: 'Lato', Helvetica, Arial, sans-serif; font-size: 18px; font-weight: 400; line-height: 25px;">
                            <p  style="margin: 0;"></p>
                        </td>
                    </tr>
                    <tr>
                        <td bgcolor="#ffffff" align="center" style="padding: 20px 30px 40px 30px; color: #666666; font-family: 'Lato', Helvetica, Arial, sans-serif; font-size: 18px; font-weight: 400; line-height: 25px;"><table border="0" cellspacing="0" cellpadding="0">
                          <tbody><tr>
                              <td align="center" style="border-radius:3px" bgcolor="#E74F5C"><a href="''' + url_for(
        'admin_auth.reset_token', token=token, _external=True) + '''" style="font-size:20px;font-family:Helvetica,Arial,sans-serif;color:#ffffff;text-decoration:none;color:#ffffff;text-decoration:none;padding:15px 25px;border-radius:5px;border:1px solid #00606;display:inline-block" target="_blank" data-saferedirecturl="https://www.google.com/url?q=https://litmus.com&amp;source=gmail&amp;ust=1674298732640000&amp;usg=AOvVaw22PP3F5NtbY4tTSagwbNCl">Reset Password</a></td>
                          </tr>
                        </tbody></table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

                </table>
            </td>

        </tr>
        <tr>
            <td bgcolor="#f4f4f4" align="center" style="padding: 0px 10px 0px 10px;">
            </td>
        </tr>
    </table>
</body>

</html>

 '''

    msg['Subject'] = 'Reset Password - FriendDate'
    msg['From'] = f'{MAIL_FROM_NAME} <{FROM}>'
    msg['To'] = TO

    msg.attach(MIMEText(content, 'html'))

    print('Initiating server ...')

    server = smtplib.SMTP(SERVER, PORT)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(FROM, PASS)
    server.sendmail(FROM, TO, msg.as_string())
    print('Email Sent...')
    server.quit()

def send_otp(user,otp):
    otp_value= str(otp)

    print('Composing Email.......')

    SERVER = 'smtp.gmail.com'  # smtp server
    PORT = 587  # mail port number
    FROM = 'fearsfight211@gmail.com'  # sender Mail
    TO = user.email  # receiver mail
    PASS = 'mdltifkjmclajper'
    MAIL_FROM_NAME = "FriendDate"

    msg = MIMEMultipart()
    content = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Sign-Up</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f26d6114;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 400px;
            margin: 40px auto;
            background: #f26d6114;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .header {
            background-color: #f26d61;
            padding: 30px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            display: flex;
            justify-content: center;
            align-items: center;
            
        }
        .logo {
    background: white;
    border-radius: 50%;
    padding: 10px;
    width: 80px;
    height: 80px;
    margin: auto;  /* Ensures centering */
}
        .title {
            font-size: 22px;
            font-weight: bold;
            color: #333333;
            margin: 20px 0 10px;
        }
        .message {
            font-size: 16px;
            color: #666666;
            margin-bottom: 20px;
        }
        .otp-box {
            background: #E5E7EB;
            padding: 15px;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 3px;
            border-radius: 5px;
            display: inline-block;
            color: #333333;
            margin-bottom: 20px;
        }
        .footer {
            font-size: 14px;
            color: #999999;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://frienddate-app.s3.amazonaws.com/app_icon0.png" alt="Logo" class="logo">
        </div>
        <div class="title">Verify Your Sign-Up</div>
        <div class="message">
            Enter the OTP below to verify your email and complete the sign-up process.
        </div>
        <div class="otp-box">'''+ otp_value +'''</div>
        <div class="footer">©2023 FriendDate. All rights reserved.</div>
    </div>
</body>
</html>


 '''

    msg['Subject'] = 'Email Verification - FriendDate'
    msg['From'] = f'{MAIL_FROM_NAME} <{FROM}>'
    msg['To'] = TO

    msg.attach(MIMEText(content, 'html'))

    print('Initiating server ...')

    server = smtplib.SMTP(SERVER, PORT)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(FROM, PASS)
    server.sendmail(FROM, TO, msg.as_string().encode('utf-8'))
    print('Email Sent...')
    server.quit()
