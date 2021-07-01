import logging
from sql_lab import settings

logging.basicConfig(filename=str(settings.BASE_DIR / 'log'), encoding='utf-8', level=logging.DEBUG, format='%(asctime)s %(message)s')
logging.debug('Logging enabled')
