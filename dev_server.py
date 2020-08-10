import os
os.environ['dev'] = '1'
from main_app import dev_server

if __name__ == '__main__':
    dev_server(debug=False)