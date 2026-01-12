from hdbcli import dbapi

def get_connection():
    conn = dbapi.connect(
        address="a99c4b45-cfe7-4d55-8293-ec6a4181e9f5.hana.prod-us10.hanacloud.ondemand.com",
        port=443,
        user="SBPTECHTEAM",
        password="Sbpcorp@25"
        # encrypt=True
    )
    return conn