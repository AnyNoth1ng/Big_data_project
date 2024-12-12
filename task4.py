
# 7.1 Импортируем необходимые библиотеки:
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from onetl.connection import SparkHDFS
from onetl.file import FileDFReader
from onetl.db import DBWriter
from onetl.file.format import CSV
from onetl.connection import Hive

# 7.2 Создаем сессию спарка:
spark = SparkSession.builder \
	.master("yarn") \
	.appName("spark-with-yarn") \
	.config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
	.config("spark.hive.metastore.uris", "thrift://team-31-jn:9083") \
	.enableHiveSupport() \
	.getOrCreate()

# 7.3 Подключаемся и грузим датасет:
hdfs = SparkHDFS(host="team-31-nn", port=9000, spark=spark, cluster="test")
reader = FileDFReader(connection=hdfs, format=CSV(delimiter=",", header=True), source_path="/input")
df = reader.run(["pvv5_log_202412042111.csv"])

# 7.4 Делаем необходимые преобразования:
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
df = df.repartition(10, "reg_year")

# 7.5 Сохраняем как таблицу:
df.write.saveAsTable("regs_5_task", partitionBy="reg_year", mode="overwrite")
