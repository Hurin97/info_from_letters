from datetime import datetime as dt
from .Own_imap_hook import OwnImapHook 
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.models import Variable
from airflow.providers.postgres.hooks.postgres import PostgresHook
from jinja2 import Environment
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


PATH_TO_PROJECT = '/opt/airflow/dags/'

def normaling_datetime(ts_nodash):
    print(ts_nodash, type(ts_nodash))
    date = dt.strptime(ts_nodash, '%Y%m%dT%H%M%S')
    return str(date.strftime('%Y-%m-%d %H:%M:%S'))


def insert_data(path_sql, table_name, columns, values):
        phook = PostgresHook(postgres_conn_id="post_em_v1")
        conn = phook.get_conn()
        presql = ''
        with open(path_sql) as ps:
              for line in ps:
                    presql+= line
        env = Environment()
        template = env.from_string(presql)
        sql = template.render(table_name = table_name, columns = columns, values = values)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        conn.close()


def get_column_from_table(path_sql):
        postgres_hook = PostgresHook(postgres_conn_id="post_em_v1")
        conn = postgres_hook.get_conn()
        sql = ''
        with open(path_sql) as ps:
              for line in ps:
                    sql += line
        cursor = conn.cursor()
        cursor.execute(sql)
        res = []
        for line in cursor:
            res+= line
        return ','.join(res)


def set_data_in_database(**kwargs):
    path_to_sql = f"{PATH_TO_PROJECT}sql/insert_into_table.sql"
    values = ''
    date_today = normaling_datetime(kwargs['date_today'])
    columns = get_column_from_table(f'{PATH_TO_PROJECT}/sql/column_letter.sql')
    rows = 0
    letters : dict =  kwargs['task_instance'].xcom_pull(task_ids='get')
    print(letters)
    # kwargs['info']
    for letter in letters.keys():
        if rows < 1000:
            print(tuple([letters[letter]['From'][0],kwargs['To'],letters[letter]['Subject'],letters[letter]['Date'], letters[letter]['Text'],date_today]))
            values += str(tuple([letters[letter]['From'][0],kwargs['To'],letters[letter]['Date'],   letters[letter]['Subject'], letters[letter]['Text'],date_today])) + ','
            rows += 1
            if rows == 1000:
                insert_data(path_to_sql,'letter', columns, values.rstrip(','))
                rows = 0
                values = ''
            if rows > 0 :
                 insert_data(path_to_sql,'letter', columns, values.rstrip(','))


def telegram_alert(self):
     from telebot import Telegram_log as tl
     token = Variable.get("tgm_tok")
     chat_id = Variable.get("tgm_chat_id")
     tl(token, chat_id).logger('email_stat_alert')


def get_mail():
    messages = 'ja'
    hook = OwnImapHook(imap_conn_id='mru')
    messages = hook.get_info_from_mail(search_criteria='UNSEEN',mailbox='INBOX')
    return messages
    

default_args = {
    'start_date': dt(2024, 3, 29, 0, 0),
    'catchup': False,
    'provide_context': True
}


dag = DAG(
    'imap_inbox_search',
    schedule_interval='@daily',
    default_args=default_args,
    catchup=False
)


get_info = PythonOperator(
      task_id = 'get',
      python_callable = get_mail,
      provide_context = True,
      on_failure_callback = telegram_alert,
      dag=dag
)


create_email_table = SQLExecuteQueryOperator(
      task_id = 'create_electronic_cards_stats_table_idexists', 
      conn_id = "postgres-test", 
      sql = 'sql/email_stats.sql', 
      dag=dag
      )



insert_to_table = PythonOperator(
    task_id = 'insert',
    python_callable = set_data_in_database,
    on_failure_callback = telegram_alert,
    provide_context = True,
    op_kwargs = { "date_today" : "{{ts_nodash}}",
          "To" : Variable.get("To")},
     dag=dag
)

[get_info , create_email_table] >> insert_to_table