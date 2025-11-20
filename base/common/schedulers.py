from datetime import datetime
from flask_apscheduler import APScheduler
from base.user.models import Events
from sqlalchemy import func
from base.database.db import db
scheduler = APScheduler()

# This will run every 12 hours
@scheduler.task("cron", id="test454", hour="*/12", max_instances=1)
def schedule_draws():
    with scheduler.app.app_context():
        try:
            today = datetime.today().strftime("%Y-%m-%d")

            get_expired_events = Events.query.filter(
                Events.is_deleted == False,
                func.date(Events.event_date) < today
            ).all()

            if len(get_expired_events)>0:
                for i in get_expired_events:
                    i.is_deleted = True
                db.session.commit()

            print('get_expired_events',get_expired_events)

            print("Running scheduled job at", datetime.now())

        except ValueError as e:
            print(f"Schdular not running: {e}")