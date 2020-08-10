import os
os.environ['dev'] = '1'
from main_app import server

if __name__ == '__main__':
    server.run(debug=False)