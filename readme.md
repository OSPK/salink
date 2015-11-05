Create a virrtual env

Clone this repo in it
`sudo apt-get install python-mysqldb build-essential python-dev libmysqlclient-dev`
`sudo apt-get install libjpeg-dev`

`pip install -r requirements.txt`
`pip install uwsgi`

#check if init script works ok
`sudo sh -x /etc/init/salink.conf start`

`python db.py db init`
`python db.py db migrate`
`python db.py db upgrade`