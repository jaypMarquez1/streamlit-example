import pandas as pd
import snowflake.connector
from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL

csv_file_path = 'C:\\Users\\matthewlewington\\Downloads\\frosty_steamlit-master (1)\\frosty_steamlit-master\\src\\feedback.csv'


confirmed_df = pd.read_csv(csv_file_path)  # or encoding='utf-16'



engine = create_engine(URL(
    account = 'paysafe.eu-central-1.privatelink',
    user = 'matthew.lewington@paysafe.com',
    authenticator='externalbrowser',
    database = 'DEV_ICICLE',
    schema = 'LOG_AI',
    warehouse = 'NON_PROD_GENERAL_PURPOSE',
    role='DEV_FR_ICICLE'
))
con=engine.connect()

chunksize = 10000 ##how many rows to send at a time
tablename = "feedback_log" ##what table to write into 




confirmed_df.to_sql(name=tablename, con=engine.connect(), if_exists='replace', index=False, index_label=None, chunksize=chunksize)
con.close()
engine.dispose()
