import os

bind = '0.0.0.0:' + os.getenv('X_ZOHO_CATALYST_LISTEN_PORT', os.getenv('PORT', '8080'))
workers = 2
threads = 4
timeout = 240
accesslog = '-'
errorlog = '-'
