import schedule
import time
from ai_trainer import train_model

schedule.every().day.at("03:00").do(train_model)

while True:

    schedule.run_pending()
    time.sleep(60)