# Импорт необходимых библиотек
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from onetl.connection import SparkHDFS
from onetl.file import FileDFReader
from onetl.db import DBWriter
from onetl.file.format import CSV
from onetl.connection import Hive
from prefect import flow, task
from prefect.cache_policies import NONE


# Создание SparkSession
@task(cache_policy=NONE, cache_result_in_memory=False)
def create_session():
    spark = SparkSession.builder \
        .master("yarn") \
        .appName("spark-with-yarn") \
        .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
        .config("spark.hive.metastore.uris", "thrift://team-31-jn:9083") \
        .enableHiveSupport() \
        .getOrCreate()
    print('***** create_session OK! *****')
    return spark

# Установка соединения с HDFS
@task(cache_policy=NONE, cache_result_in_memory=False)
def extract_data(spark):
    hdfs = SparkHDFS(host="team-31-nn", port=9000, spark=spark, cluster="test")
    reader = FileDFReader(connection=hdfs, format=CSV(delimiter=",", header=True), source_path="/input")
    df = reader.run(["pvv5_log_202412042111.csv"])
    print('***** extract_data OK! *****')
    return df

# Работа с данными
@task(cache_policy=NONE, cache_result_in_memory=False)
def transform_data(df):
    df = df.withColumn("dt", F.to_date(F.col("dt")))
    df = df.filter('region = "Kamchatka Krai\r"') # Фильтрация данных
    df = df.select( # Преобразование данных
        "dt",
        "link",
        F.split(F.col("link"), "/").getItem(2).alias("domen"),
        F.split(F.col("user_agent"), "/").getItem(0).alias("browser"),
        F.split(F.col("user_agent"), "/").getItem(1).alias("tech_details")
    )
    df = df.withColumn("reg_year", F.year("dt"))
    df = df.repartition(10, "reg_year") # Перераспределение данных по разделам
    print('***** transform_data OK! *****')
    return df

@task(cache_policy=NONE, cache_result_in_memory=False)
def load_data(df):
    df.write.saveAsTable("regs_5_task", partitionBy="reg_year", mode="overwrite")
    print('***** load_data OK! *****')

@flow
def process_data():
    spark_sess = create_session()
    edata = extract_data(spark_sess)
    tdata = transform_data(edata)
    load_data(tdata)
    print('***** process_data OK! *****')

if __name__ == "__main__":
    process_data()
    print('***** pipeline OK! *****')