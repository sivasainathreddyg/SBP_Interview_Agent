from dbConnection.schema import create_table, insert_job

# create_table()

job_title = "Python Developer"
job_description = """
We are looking for a Python developer with experience in:
- Python programming
- SQL databases
- Machine Learning
- REST API development
"""

insert_job(job_title, job_description)
