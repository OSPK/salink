Create a virrtual env

Clone this repo in it
`sudo apt-get install python-mysqldb build-essential python-dev libmysqlclient-dev`
`sudo apt-get install libjpeg-dev`

`pip install -r requirements.txt`

`python db.py db init`
`python db.py db migrate`
`python db.py db upgrade`