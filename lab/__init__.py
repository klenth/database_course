import logging
from database_course import settings

logging.basicConfig(filename=str(settings.BASE_DIR / 'log'), encoding='utf-8', level=logging.DEBUG, format='%(asctime)s %(message)s')
logging.debug('Logging started')
